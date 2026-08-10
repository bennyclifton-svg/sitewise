import pytest

from app.projects.artefact_context import RfpContext
from app.projects.generation_audit import build_generation_manifest
from app.projects.generation_brief import build_generation_brief
from app.projects.generation_context import ContextField


def _field(key: str, state: str, value=None) -> ContextField:
    return ContextField(
        key=key, label=key.replace("_", " ").title(), state=state, value=value
    )


def _context() -> RfpContext:
    return RfpContext(
        project_id="33333333-3333-3333-3333-333333333333",
        context_version=2,
        discipline="Architect",
        identity={"title": _field("title", "known", "Office Upgrade")},
        taxonomy={"building_class": _field("building_class", "known", "commercial")},
        scope={"ffe": _field("ffe", "explicitly_excluded")},
        scale={"gfa": _field("gfa", "unknown")},
        complexity={},
        programme={},
        procurement={},
        approvals={},
        stakeholders={},
        derived_risks=[],
        section_weights={},
        critical_unknowns=[],
    )


def test_manifest_separates_known_unknown_and_excluded_context() -> None:
    brief = build_generation_brief(
        _context(),
        evidence_refs=["brief.pdf"],
        seed_refs=["seed/rfp.md"],
    )
    manifest = build_generation_manifest(brief)

    assert manifest.taxonomy == {"building_class": "commercial"}
    assert manifest.known_profile["identity.title"] == "Office Upgrade"
    assert manifest.unknown_relevant_fields == ["scale.gfa"]
    assert manifest.explicitly_excluded_fields == ["scope.ffe"]
    assert manifest.generation_brief.model_dump(mode="json") == brief.model_dump(
        mode="json"
    )
    assert manifest.input_fingerprint == manifest.generation_brief.input_fingerprint


def test_manifest_rejects_a_stale_generation_brief() -> None:
    brief = build_generation_brief(_context(), evidence_refs=["brief.pdf"])
    brief.context.identity["title"].value = "Changed after construction"

    with pytest.raises(ValueError, match="fingerprint"):
        build_generation_manifest(brief)
