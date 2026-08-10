"""Frozen shared briefs supplied to every narrative section in one generation."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.projects.artefact_context import ArtefactContext, format_artefact_context


class ArtefactGenerationBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1] = 1
    artefact_type: Literal["pmp", "cost_plan", "rfp", "rft"]
    context_version: int = Field(ge=1)
    context: ArtefactContext
    evidence_refs: tuple[str, ...] = ()
    seed_refs: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    input_fingerprint: str = Field(min_length=64, max_length=64)


def _brief_payload(
    context: ArtefactContext,
    *,
    evidence_refs: tuple[str, ...],
    seed_refs: tuple[str, ...],
    constraints: tuple[str, ...],
) -> dict[str, object]:
    return {
        "context": context.model_dump(mode="json"),
        "evidence_refs": evidence_refs,
        "seed_refs": seed_refs,
        "constraints": constraints,
    }


def _payload_fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_generation_brief(
    context: ArtefactContext,
    *,
    evidence_refs: list[str] | tuple[str, ...] = (),
    seed_refs: list[str] | tuple[str, ...] = (),
    constraints: list[str] | tuple[str, ...] = (),
) -> ArtefactGenerationBrief:
    """Freeze the shared context and sources used by all narrative section jobs."""
    frozen_context = context.model_copy(deep=True)
    evidence = tuple(dict.fromkeys(evidence_refs))
    seeds = tuple(dict.fromkeys(seed_refs))
    rules = tuple(dict.fromkeys(constraints))
    payload = _brief_payload(
        frozen_context,
        evidence_refs=evidence,
        seed_refs=seeds,
        constraints=rules,
    )
    fingerprint = _payload_fingerprint(payload)
    return ArtefactGenerationBrief(
        artefact_type=frozen_context.artefact_type,
        context_version=frozen_context.context_version,
        context=frozen_context,
        evidence_refs=evidence,
        seed_refs=seeds,
        constraints=rules,
        input_fingerprint=fingerprint,
    )


def verify_generation_brief_integrity(brief: ArtefactGenerationBrief) -> None:
    """Reject a brief whose frozen fingerprint no longer matches its inputs."""
    expected = _payload_fingerprint(
        _brief_payload(
            brief.context,
            evidence_refs=brief.evidence_refs,
            seed_refs=brief.seed_refs,
            constraints=brief.constraints,
        )
    )
    if expected != brief.input_fingerprint:
        raise ValueError("generation brief input fingerprint is stale")


def format_generation_brief(brief: ArtefactGenerationBrief) -> str:
    verify_generation_brief_integrity(brief)
    lines = [
        f"{brief.artefact_type.upper().replace('_', ' ')} shared generation brief:",
        f"- input_fingerprint: {brief.input_fingerprint}",
        format_artefact_context(brief.context),
        "- project_evidence_refs: "
        + (", ".join(brief.evidence_refs) if brief.evidence_refs else "none"),
        "- seed_guidance_refs: "
        + (", ".join(brief.seed_refs) if brief.seed_refs else "none"),
    ]
    if brief.constraints:
        lines.extend(
            ["- shared_constraints:", *[f"  - {item}" for item in brief.constraints]]
        )
    return "\n".join(lines)
