"""Persistable explanation of the inputs used for artefact generation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from app.projects.generation_brief import (
    ArtefactGenerationBrief,
    verify_generation_brief_integrity,
)

_MUTATION_LOG_LIMIT = 20


class GenerationManifest(BaseModel):
    schema_version: int = 1
    artefact_type: str
    context_version: int
    source_version: str = Field(min_length=16, max_length=16)
    seed_version: str = Field(min_length=16, max_length=16)
    input_fingerprint: str
    generation_brief: ArtefactGenerationBrief
    taxonomy: dict[str, Any]
    known_profile: dict[str, Any]
    unknown_relevant_fields: list[str]
    explicitly_excluded_fields: list[str]
    evidence_used: list[str]
    seed_knowledge: list[str]
    constraints: list[str]


def _stable_version_token(values: list[str] | tuple[str, ...]) -> str:
    payload = json.dumps(list(values), sort_keys=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def build_generation_manifest(
    brief: ArtefactGenerationBrief,
) -> GenerationManifest:
    verify_generation_brief_integrity(brief)
    payload = brief.context.model_dump(mode="json")
    known: dict[str, Any] = {}
    unknown: list[str] = []
    excluded: list[str] = []
    for group, value in payload.items():
        if not isinstance(value, dict):
            continue
        for key, field in value.items():
            if not isinstance(field, dict) or "state" not in field:
                continue
            path = f"{group}.{key}"
            state = field.get("state")
            if state == "known":
                known[path] = field.get("value")
            elif state == "unknown":
                unknown.append(path)
            elif state in {"explicitly_excluded", "not_applicable"}:
                excluded.append(path)
    taxonomy = {
        key: value.get("value")
        for key, value in payload.get("taxonomy", {}).items()
        if isinstance(value, dict) and value.get("state") == "known"
    }
    return GenerationManifest(
        artefact_type=brief.artefact_type,
        context_version=brief.context_version,
        source_version=_stable_version_token(brief.evidence_refs),
        seed_version=_stable_version_token(brief.seed_refs),
        input_fingerprint=brief.input_fingerprint,
        generation_brief=brief,
        taxonomy=taxonomy,
        known_profile=known,
        unknown_relevant_fields=sorted(unknown),
        explicitly_excluded_fields=sorted(excluded),
        evidence_used=list(brief.evidence_refs),
        seed_knowledge=list(brief.seed_refs),
        constraints=list(brief.constraints),
    )


def generation_audit_provenance(
    prior_provenance: dict[str, Any] | None,
    brief: ArtefactGenerationBrief | None,
    *,
    mutation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build carryable audit fields from an optional prior revision and brief."""
    refresh = (
        build_generation_manifest(brief).model_dump(mode="json")
        if brief is not None
        else None
    )
    return carry_generation_audit(
        prior_provenance,
        refresh_manifest=refresh,
        mutation=mutation,
    )


def carry_generation_audit(
    prior_provenance: dict[str, Any] | None,
    *,
    refresh_manifest: dict[str, Any] | GenerationManifest | None = None,
    mutation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Preserve the originating generation manifest across later revisions.

    First generation (or a revision with no prior manifest) installs the provided
    manifest as both ``generation_manifest`` and ``originating_generation_manifest``.
    Later refreshes keep that originating copy and expose the newest brief dump as
    ``latest_generation_manifest``. Mutations append a bounded ``mutation_log``.
    """
    prior = dict(prior_provenance or {})
    refresh_dump: dict[str, Any] | None
    if isinstance(refresh_manifest, GenerationManifest):
        refresh_dump = refresh_manifest.model_dump(mode="json")
    else:
        refresh_dump = refresh_manifest

    originating = prior.get("originating_generation_manifest")
    if not isinstance(originating, dict):
        originating = prior.get("generation_manifest")
    if not isinstance(originating, dict):
        originating = refresh_dump

    carried: dict[str, Any] = {}
    if isinstance(originating, dict):
        carried["generation_manifest"] = originating
        carried["originating_generation_manifest"] = originating
    if (
        isinstance(refresh_dump, dict)
        and isinstance(originating, dict)
        and refresh_dump != originating
    ):
        carried["latest_generation_manifest"] = refresh_dump

    if mutation is not None:
        carried["mutation"] = mutation
        prior_log = prior.get("mutation_log")
        log = list(prior_log) if isinstance(prior_log, list) else []
        log.append(mutation)
        carried["mutation_log"] = log[-_MUTATION_LOG_LIMIT:]

    return carried
