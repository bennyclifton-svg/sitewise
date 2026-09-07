"""Join reviewed submissions, validate the comparison and publish a Markdown artefact."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.project import Project
from tender.llm.review_client import ReviewClient
from tender.models import TenderComparison, TenderJob, TenderQuote, TenderReport
from tender.review_schemas import ReviewSelection
from tender.services import jobs
from tender.services.artefact_publisher import tender_artefact_publisher
from tender.services.report import load_report_language
from tender.services.review_facts import (
    numbered_facts,
    reconcile_submission,
    validate_selection,
    remove_enclosed_prices,
)
from tender.services.review_render import render_review
from tender.services.review_layout import validate_review_layout


async def review_evidence(
    session: AsyncSession, comparison: TenderComparison
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = await session.execute(
        select(TenderQuote)
        .where(TenderQuote.comparison_id == comparison.id)
        .options(selectinload(TenderQuote.documents))
        .order_by(TenderQuote.created_at, TenderQuote.id)
    )
    quotes = list(result.scalars())
    paths = {
        file["id"]: file["path"]
        for submission in comparison.context_provenance["submissions"]
        for file in submission["files"]
    }
    ordered = sorted(
        quotes,
        key=lambda quote: min(doc.quote_group_position for doc in quote.documents),
    )
    documents = []
    for quote in ordered:
        for document in sorted(quote.documents, key=lambda value: value.input_position):
            if not (document.review_data or {}).get("complete"):
                raise ValueError(
                    f"{document.original_filename} has not been completely read"
                )
            documents.append(
                {
                    "id": str(document.id),
                    "quote_id": str(quote.id),
                    "filename": document.original_filename,
                    "path": paths[str(document.workspace_file_id)],
                    "page_count": document.page_count,
                    "facts": document.review_data["facts"],
                    "uncaptured": document.review_data.get("uncaptured", []),
                }
            )
    return [
        {"id": str(quote.id), "name": quote.builder_name} for quote in ordered
    ], documents


async def prepare_procurement_review(
    session: AsyncSession, job: TenderJob, *, client: ReviewClient | None = None
) -> None:
    comparison = await session.get(TenderComparison, job.comparison_id)
    if comparison is None:
        raise ValueError("Comparison not found")
    existing = await session.scalar(
        select(TenderReport).where(TenderReport.comparison_id == comparison.id).limit(1)
    )
    if existing is not None:
        return
    quotes, documents = await review_evidence(session, comparison)
    facts = numbered_facts(documents)
    profile = comparison.context["review_profile"]
    review_date = date.fromisoformat(comparison.context_provenance["review_date"])
    calculations = {
        quote["id"]: reconcile_submission(
            [fact for fact in facts if fact["quote_id"] == quote["id"]],
            review_date=review_date,
        )
        for quote in quotes
    }
    language = await load_report_language(session)
    if "procurement_review" not in language:
        raise ValueError(
            "Procurement review language is not installed; run the tender seed loader"
        )
    client = client or ReviewClient()
    payload = {
        "profile": profile,
        "package": comparison.context["package_name"],
        "review_date": review_date.isoformat(),
        "quotes": quotes,
        "facts": facts,
        "calculations": calculations,
    }
    await session.commit()
    for attempt in range(2):
        selection = await client.request(
            stage="select", payload=payload, schema=ReviewSelection
        )
        remove_enclosed_prices(selection, facts)
        try:
            validate_selection(
                selection, facts, [quote["id"] for quote in quotes], profile
            )
            markdown = render_review(
                package=comparison.context["package_name"],
                profile=profile,
                review_date=review_date.isoformat(),
                quotes=quotes,
                documents=documents,
                facts=facts,
                selection=selection,
                calculations=calculations,
                language=language,
            )
            validate_review_layout(markdown, profile)
            break
        except ValueError as exc:
            if attempt:
                raise
            payload["validation_error"] = str(exc)
    await jobs.assert_lease(session, job)
    project = await session.get(Project, comparison.project_id)
    provenance = {
        **comparison.context_provenance,
        "input_fingerprint": comparison.input_fingerprint,
        "review_profile": profile,
    }
    draft_id = await tender_artefact_publisher().publish_draft(
        session,
        project=project,
        comparison_id=comparison.id,
        report_version=1,
        author_user_id=comparison.created_by,
        title=language["procurement_review"]["title"].format(
            package=comparison.context["package_name"]
        ),
        workspace_path=f"{project.workspace_path}/05-procurement/review-{provenance['row_id']}-{comparison.id}.md",
        markdown=markdown,
        provenance=provenance,
    )
    session.add(TenderReport(comparison_id=comparison.id, draft_id=draft_id, version=1))
    comparison.context_provenance = {
        **comparison.context_provenance,
        "review": {
            "selection": selection.model_dump(mode="json"),
            "calculations": calculations,
        },
    }
    comparison.status = "report_draft"
    for quote in (
        await session.execute(
            select(TenderQuote).where(TenderQuote.comparison_id == comparison.id)
        )
    ).scalars():
        quote.stage = "complete"
    await session.flush()
