"""F9: originating generation manifests survive later artefact revisions."""

from __future__ import annotations

from app.projects.artefact_context import RfpContext
from app.projects.generation_audit import (
    build_generation_manifest,
    carry_generation_audit,
)
from app.projects.generation_brief import build_generation_brief
from app.projects.generation_context import ContextField


def _field(key: str, state: str, value=None) -> ContextField:
    return ContextField(
        key=key, label=key.replace("_", " ").title(), state=state, value=value
    )


def _context(*, version: int = 2) -> RfpContext:
    return RfpContext(
        project_id="33333333-3333-3333-3333-333333333333",
        context_version=version,
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


def _manifest(*, version: int = 2):
    brief = build_generation_brief(
        _context(version=version),
        evidence_refs=["brief.pdf"],
        seed_refs=["seed/rfp.md"],
        constraints=["Use known GFA only"],
    )
    return build_generation_manifest(brief)


def test_manifest_exposes_source_and_seed_versions() -> None:
    manifest = _manifest()

    assert manifest.context_version == 2
    assert isinstance(manifest.source_version, str) and len(manifest.source_version) == 16
    assert isinstance(manifest.seed_version, str) and len(manifest.seed_version) == 16
    assert manifest.source_version != manifest.seed_version
    assert manifest.explicitly_excluded_fields == ["scope.ffe"]
    assert manifest.constraints == ["Use known GFA only"]


def test_carry_preserves_originating_manifest_and_records_mutation() -> None:
    originating = _manifest(version=2).model_dump(mode="json")
    refresh = _manifest(version=3).model_dump(mode="json")
    prior = {
        "generation_manifest": originating,
        "typed_cost_plan": True,
    }

    carried = carry_generation_audit(
        prior,
        refresh_manifest=refresh,
        mutation={
            "kind": "cost_plan_edit",
            "actor_source": "cost_plan_tool",
            "from_version": 1,
            "to_version": 2,
            "operations": [{"operation": "UPDATE"}],
        },
    )

    assert carried["generation_manifest"] == originating
    assert carried["originating_generation_manifest"] == originating
    assert carried["latest_generation_manifest"] == refresh
    assert carried["mutation"]["kind"] == "cost_plan_edit"
    assert carried["mutation_log"] == [carried["mutation"]]


def test_carry_sets_originating_manifest_on_first_generation() -> None:
    first = _manifest().model_dump(mode="json")

    carried = carry_generation_audit(None, refresh_manifest=first)

    assert carried["generation_manifest"] == first
    assert carried["originating_generation_manifest"] == first
    assert "latest_generation_manifest" not in carried
    assert "mutation_log" not in carried
