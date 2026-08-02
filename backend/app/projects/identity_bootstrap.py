"""Ingest-time bootstrap of empty project identity fields."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from app.database.project import Project
from app.database.source_document import SourceDocument
from app.projects.identity_confidence import (
    IdentityFieldDecision,
    score_identity_from_text,
)
from app.projects.profile import read_profile
from app.projects.profile_proposals import (
    accept_profile_proposal,
    list_profile_proposals,
    propose_project_profile_change,
)
from app.schemas.profile_proposals import (
    ProfileEvidenceReference,
    ProjectProfileProposalView,
)

logger = logging.getLogger(__name__)

INGEST_PROPOSER = "ingest"

BootstrapStatus = Literal["noop", "proposed", "auto_applied", "mixed", "error"]


@dataclass(frozen=True, slots=True)
class IdentityBootstrapResult:
    status: BootstrapStatus
    proposal: ProjectProfileProposalView | None = None
    auto_applied_fields: tuple[str, ...] = ()
    proposed_fields: tuple[str, ...] = ()
    detail: str | None = None


async def bootstrap_identity_from_document(
    session,
    *,
    project: Project,
    source_document_id: uuid.UUID,
    document_text: str | None = None,
) -> IdentityBootstrapResult:
    """Auto-apply empty client/site_address from an ingested document."""
    profile = read_profile(project)
    if profile.site_address and profile.client:
        return IdentityBootstrapResult(status="noop", detail="identity already set")

    text = document_text
    if text is None:
        document = await session.get(SourceDocument, source_document_id)
        if document is None:
            return IdentityBootstrapResult(
                status="noop", detail="source document missing"
            )
        text = getattr(document, "normalized_content", None) or ""
    if not isinstance(text, str) or not text.strip():
        return IdentityBootstrapResult(status="noop", detail="empty document text")

    decisions = score_identity_from_text(text)
    pending = await list_profile_proposals(
        session, project_id=project.id, state="pending"
    )

    auto_values: dict[str, Any] = {}
    auto_confidences: list[float] = []

    for decision in decisions:
        if decision.action == "skip" or not decision.value:
            continue
        if getattr(profile, decision.field):
            continue
        conflict = _pending_conflict(pending, decision)
        if conflict == "duplicate":
            continue
        if conflict == "conflict":
            continue
        auto_values[decision.field] = decision.value
        auto_confidences.append(decision.confidence)

    if not auto_values:
        return IdentityBootstrapResult(
            status="noop", detail="no eligible identity fields"
        )

    auto_proposal: ProjectProfileProposalView | None = None
    auto_fields = tuple(sorted(auto_values))

    if auto_values:
        auto_proposal = await _propose(
            session,
            project=project,
            values=auto_values,
            source_document_id=source_document_id,
            confidence=min(auto_confidences) if auto_confidences else None,
        )
        resolution = await accept_profile_proposal(
            session,
            project=project,
            proposal_id=auto_proposal.id,
            expected_profile_revision=auto_proposal.profile_revision,
            actor_source=INGEST_PROPOSER,
        )
        auto_proposal = resolution.proposal
    return IdentityBootstrapResult(
        status="auto_applied",
        proposal=auto_proposal,
        auto_applied_fields=auto_fields,
    )


async def safe_bootstrap_identity_from_document(
    session,
    *,
    project: Project,
    source_document_id: uuid.UUID,
) -> IdentityBootstrapResult:
    """Best-effort wrapper — never raise into the ingest upload path."""
    try:
        return await bootstrap_identity_from_document(
            session,
            project=project,
            source_document_id=source_document_id,
        )
    except Exception as exc:  # noqa: BLE001 - ingest must not fail on bootstrap
        logger.exception(
            "identity_bootstrap_failed project_id=%s source_document_id=%s error=%s",
            project.id,
            source_document_id,
            exc,
        )
        return IdentityBootstrapResult(status="error", detail=str(exc))


async def _propose(
    session,
    *,
    project: Project,
    values: dict[str, Any],
    source_document_id: uuid.UUID,
    confidence: float | None,
) -> ProjectProfileProposalView:
    claim = "; ".join(f"{key}={value}" for key, value in sorted(values.items()))
    return await propose_project_profile_change(
        session,
        project=project,
        proposed_values=values,
        evidence_references=[
            ProfileEvidenceReference(
                source_document_id=source_document_id,
                locator="normalized_content",
                claim=claim[:2048],
            )
        ],
        confidence=confidence,
        proposer=INGEST_PROPOSER,
    )


def _pending_conflict(
    pending: list[ProjectProfileProposalView],
    decision: IdentityFieldDecision,
) -> Literal["none", "duplicate", "conflict"]:
    for proposal in pending:
        existing = proposal.proposed_values.get(decision.field)
        if existing is None:
            continue
        if (
            isinstance(existing, str)
            and existing.strip().lower() == decision.value.strip().lower()
        ):
            return "duplicate"
        return "conflict"
    return "none"
