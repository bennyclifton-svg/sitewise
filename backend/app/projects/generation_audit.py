"""Persistable explanation of the inputs used for artefact generation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.projects.generation_brief import (
    ArtefactGenerationBrief,
    verify_generation_brief_integrity,
)


class GenerationManifest(BaseModel):
    schema_version: int = 1
    artefact_type: str
    context_version: int
    input_fingerprint: str
    generation_brief: ArtefactGenerationBrief
    taxonomy: dict[str, Any]
    known_profile: dict[str, Any]
    unknown_relevant_fields: list[str]
    explicitly_excluded_fields: list[str]
    evidence_used: list[str]
    seed_knowledge: list[str]
    constraints: list[str]


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
