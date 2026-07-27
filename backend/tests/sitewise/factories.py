"""Shared fixture builders for the sitewise cost-plan tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.database.project import Project
from app.sitewise.cost_plan_evidence import CostPlanEvidencePack
from app.sitewise.mobilisation_evidence import MobilisationEvidencePack

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def commercial_fitout_project() -> Project:
    """A NSW Class 5 office refurbishment — resolves to the commercial_fitout family."""
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="meridian-legal-fitout",
        title="Meridian Legal Fitout",
        workspace_path="04-projects/meridian-legal-fitout",
        phase="brief-planning",
        archetype=None,
        building_class="commercial",
        work_type="refurb",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={"taxonomy": {"subclasses": ["office"]}},
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )


def fitout_evidence_pack() -> CostPlanEvidencePack:
    """Fee and contingency are evidenced; the certifier is still an open gap."""
    mobilisation = MobilisationEvidencePack(
        owners="Meridian Legal Pty Ltd",
        site_address="Level 12, 1 Chifley Square, Sydney NSW 2000",
        appointee="Meridian Interior Architects Pty Ltd",
        fee_total_ex_gst="$185,000",
        engagement_executed_date="12/03/2026",
        gaps=[
            "Geotechnical report",
            "Certifier appointment",
            "Master programme on file",
            "Owner project brief formal sign-off",
            "Construction budget",
        ],
        evidence_refs=["ref:a"],
    )
    return CostPlanEvidencePack(
        mobilisation=mobilisation,
        project_name="Meridian Legal Fitout",
        construction_budget_ceiling="$6,200,000",
        contingency_amount="$310,000",
        contingency_percent="5",
        owner_brief_on_file=True,
        evidence_refs=["ref:a"],
    )
