from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.projects.artefact_context import RfpContext
from app.projects.generation_brief import (
    build_generation_brief,
    format_generation_brief,
    verify_generation_brief_integrity,
)


def _context() -> RfpContext:
    return RfpContext(
        project_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        context_version=9,
        discipline="Structural Engineer",
        identity={},
        taxonomy={},
        scope={},
        scale={},
        complexity={},
        programme={},
        procurement={},
        approvals={},
        stakeholders={},
        derived_risks=[],
        section_weights={"requested_services": 1.0},
        critical_unknowns=[],
    )


def test_generation_brief_deduplicates_sources_and_is_deterministic() -> None:
    first = build_generation_brief(
        _context(),
        evidence_refs=["brief.pdf", "brief.pdf"],
        seed_refs=["seed/rfp.md"],
        constraints=["Do not invent facts."],
    )
    second = build_generation_brief(
        _context(),
        evidence_refs=["brief.pdf"],
        seed_refs=["seed/rfp.md"],
        constraints=["Do not invent facts."],
    )

    assert first.evidence_refs == ("brief.pdf",)
    assert first.input_fingerprint == second.input_fingerprint


def test_generation_brief_fingerprint_changes_with_an_input() -> None:
    first = build_generation_brief(_context(), evidence_refs=["brief.pdf"])
    second = build_generation_brief(_context(), evidence_refs=["drawing.pdf"])

    assert first.input_fingerprint != second.input_fingerprint


def test_generation_brief_rejects_assignment() -> None:
    brief = build_generation_brief(_context(), evidence_refs=["brief.pdf"])

    with pytest.raises(ValidationError, match="frozen"):
        brief.constraints = ("Changed after construction.",)


def test_generation_brief_is_detached_from_its_source_context() -> None:
    context = _context()
    brief = build_generation_brief(context, evidence_refs=["brief.pdf"])

    context.discipline = "Changed discipline"
    context.section_weights["requested_services"] = 0.25

    assert brief.context.discipline == "Structural Engineer"
    assert brief.context.section_weights == {"requested_services": 1.0}


def test_generation_brief_integrity_rejects_nested_mutation() -> None:
    brief = build_generation_brief(_context(), evidence_refs=["brief.pdf"])
    brief.context.section_weights["requested_services"] = 0.25

    with pytest.raises(ValueError, match="fingerprint"):
        verify_generation_brief_integrity(brief)


def test_generation_brief_formatting_rejects_stale_fingerprint() -> None:
    brief = build_generation_brief(_context(), evidence_refs=["brief.pdf"])
    brief.context.section_weights["requested_services"] = 0.25

    with pytest.raises(ValueError, match="fingerprint"):
        format_generation_brief(brief)
