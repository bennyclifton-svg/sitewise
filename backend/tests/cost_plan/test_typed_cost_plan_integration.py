from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cost_plan.models import CostPlanItem, CostPlanVersion
from app.cost_plan.import_legacy import import_legacy_draft
from app.cost_plan.service import CostPlanNotFound, get_cost_plan
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.user import User
from tests.conftest import run_async


@pytest.mark.integration
def test_typed_cost_plan_constraints_and_two_owner_isolation() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if os.environ.get("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1" or not database_url:
        pytest.skip("requires an explicitly opted-in disposable PostgreSQL database")
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    async def exercise() -> None:
        engine = create_async_engine(async_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        owners = [uuid.uuid4(), uuid.uuid4()]
        projects = [uuid.uuid4(), uuid.uuid4()]
        drafts = [uuid.uuid4(), uuid.uuid4()]
        async with factory() as session, session.begin():
            await session.execute(delete(CostPlanItem))
            await session.execute(delete(CostPlanVersion))
            for index, owner_id in enumerate(owners):
                session.add(
                    User(id=owner_id, email=f"cost-owner-{owner_id}@example.com")
                )
                session.add(
                    Project(
                        id=projects[index],
                        owner_user_id=owner_id,
                        slug="same-slug",
                        title="Cost project",
                        workspace_path=f"projects/{projects[index]}",
                        phase="construction",
                        status="active",
                    )
                )
                session.add(
                    DraftArtifact(
                        id=drafts[index],
                        project_id=projects[index],
                        workflow_type="create_cost_plan",
                        version=1,
                        status="draft",
                        title="Cost Plan",
                        workspace_path="same/path/cost.md",
                        author_user_id=owner_id,
                        content_markdown="# Cost Plan",
                        runtime="test",
                    )
                )
            await session.flush()
            for index in range(2):
                version = CostPlanVersion(
                    project_id=projects[index],
                    artefact_revision_id=drafts[index],
                    version=1,
                    created_by_user_id=owners[index],
                    status="proposed",
                    contingency_percent=Decimal("0"),
                    escalation_percent=Decimal("0"),
                    gst_treatment="exclusive",
                    assumptions={},
                    narrative={},
                    dependency_snapshot={
                        "profile_revision": 1,
                        "evidence_fingerprint": "same-path-isolated",
                        "decision_set_revision": 1,
                        "upstream_artefacts": [],
                        "runtime_version": "test",
                    },
                    deterministic_totals={},
                )
                version.items = [
                    CostPlanItem(
                        item_key="demolition",
                        cost_code="01",
                        category="Works",
                        item="Demolition",
                        budget=Decimal("80000"),
                        committed=Decimal("0"),
                        forecast=Decimal("80000"),
                        paid=Decimal("0"),
                        allowance_type="ps",
                        basis="Fixture",
                        source_refs=[],
                    )
                ]
                session.add(version)

        async with factory() as session:
            own = await get_cost_plan(
                session,
                project_id=projects[0],
                owner_user_id=owners[0],
            )
            assert own.items[0].budget == Decimal("80000.00")
            with pytest.raises(CostPlanNotFound):
                await get_cost_plan(
                    session,
                    project_id=projects[0],
                    owner_user_id=owners[1],
                )

            session.add(
                CostPlanItem(
                    cost_plan_version_id=own.id,
                    item_key="demolition",
                    cost_code="02",
                    category="Works",
                    item="Duplicate",
                    budget=Decimal("1"),
                    committed=Decimal("0"),
                    forecast=Decimal("0"),
                    paid=Decimal("0"),
                    allowance_type="none",
                    basis="Fixture",
                    source_refs=[],
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()
            await session.rollback()

        legacy_draft_id = uuid.uuid4()
        async with factory() as session, session.begin():
            legacy = DraftArtifact(
                id=legacy_draft_id,
                project_id=projects[0],
                workflow_type="create_cost_plan",
                version=2,
                status="accepted",
                title="Legacy accepted Cost Plan",
                workspace_path="same/path/cost-v2.md",
                author_user_id=owners[0],
                content_markdown="""# Cost Plan

| Cost code | Category | Cost item | Budget | Basis |
|---|---|---|---:|---|
| 02 | Structure | Framing | $100,000 | Accepted estimate |
| | | Grand total | $100,000 | |
""",
                runtime="legacy",
                provenance_metadata={
                    "profile_revision": 1,
                    "evidence_fingerprint": "legacy-evidence",
                    "decision_set_revision": 1,
                },
            )
            session.add(legacy)
            await session.flush()
            first_import = await import_legacy_draft(session, draft=legacy, apply=True)
            replay = await import_legacy_draft(session, draft=legacy, apply=True)
            assert first_import.applied is True
            assert replay.applied is False
            assert replay.typed_version_id == first_import.typed_version_id
            assert replay.parsed_budget_total == Decimal("100000.00")
        await engine.dispose()

    run_async(exercise())
