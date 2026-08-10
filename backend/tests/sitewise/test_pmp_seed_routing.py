import uuid

from app.retrieval.schemas import SourcePassage
from app.sitewise.knowledge_catalog import LoadedKnowledge, select_required_paths
from app.sitewise.seed_routing import (
    load_seed_knowledge,
    select_seed_knowledge_for_taxonomy,
)
from tests.conftest import run_async


def _selected(
    building_class: str,
    work_type: str,
    *,
    subclasses: tuple[str, ...] = (),
    work_scopes: tuple[str, ...] = (),
):
    return select_required_paths(
        workflow="create-pmp",
        archetype="",
        building_class=building_class,
        work_type=work_type,
        subclasses=subclasses,
        work_scopes=work_scopes,
    )


def _refs(**kwargs) -> set[str]:
    kwargs.pop("selected_paths")
    work_scopes = kwargs.pop("work_scope", ())
    selection = select_seed_knowledge_for_taxonomy(
        "pmp",
        archetype="",
        work_scopes=work_scopes,
        **kwargs,
    )
    return set(selection.section_refs)


def test_residential_new_scope_heavy_routes() -> None:
    refs = _refs(
        selected_paths=_selected(
            "residential",
            "new",
            subclasses=("house",),
            work_scopes=("substructure", "superstructure", "wet_areas"),
        ),
        building_class="residential",
        work_type="new",
        subclasses=("house",),
        work_scope=("substructure", "superstructure", "wet_areas"),
    )

    assert (
        "seed/residential-construction-guide.md#site-assessment-and-due-diligence"
        in refs
    )
    assert (
        "seed/residential-construction-guide.md#foundations-and-footing-systems"
        in refs
    )
    assert (
        "seed/residential-construction-guide.md#wet-area-construction-and-waterproofing"
        in refs
    )


def test_apartment_new_with_structure_scopes_does_not_require_class1_guide() -> None:
    """Apartments select the multi-res guide; Class 1 house routes must not fire."""
    refs = _refs(
        selected_paths=_selected(
            "residential",
            "new",
            subclasses=("apartments",),
            work_scopes=("substructure", "superstructure", "wet_areas"),
        ),
        building_class="residential",
        work_type="new",
        subclasses=("apartments",),
        work_scope=("substructure", "superstructure", "wet_areas"),
    )

    assert any("multi-residential-apartments-guide.md" in ref for ref in refs)
    assert not any("residential-construction-guide.md" in ref for ref in refs)


def test_commercial_refurb_fire_services_routes_to_ncc_and_as_sections() -> None:
    refs = _refs(
        selected_paths=_selected(
            "commercial",
            "refurb",
            subclasses=("office",),
            work_scopes=("fire_services",),
        ),
        building_class="commercial",
        work_type="refurb",
        subclasses=("office",),
        work_scope=("fire_services",),
    )

    assert (
        "seed/ncc-reference-guide.md#compliance-pathways-and-documentation" in refs
    )
    assert (
        "seed/fire-life-safety-guide.md#compliance-strategy-and-responsibility"
        in refs
    )
    assert (
        "seed/as-standards-reference.md#as-2419-series-fire-hydrant-installations"
        in refs
    )
    assert (
        "seed/as-standards-reference.md#as-2941-fixed-fire-protection-installations-pumpset-systems"
        in refs
    )


def test_remediation_routes_due_diligence_sections() -> None:
    refs = _refs(
        selected_paths=_selected(
            "industrial",
            "remediation",
            subclasses=("manufacturing",),
            work_scopes=("contamination_remediation",),
        ),
        building_class="industrial",
        work_type="remediation",
        subclasses=("manufacturing",),
        work_scope=("contamination_remediation",),
    )

    assert (
        "seed/remediation-due-diligence-guide.md#preliminary-site-assessment-phase-1"
        in refs
    )
    assert (
        "seed/remediation-due-diligence-guide.md#detailed-site-investigation-phase-2"
        in refs
    )
    assert (
        "seed/remediation-due-diligence-guide.md#remediation-action-plans-raps"
        in refs
    )


def test_building_remediation_routes_rectification_sections() -> None:
    refs = _refs(
        selected_paths=_selected(
            "commercial",
            "remediation",
            subclasses=("office",),
            work_scopes=("facade_cladding",),
        ),
        building_class="commercial",
        work_type="remediation",
        subclasses=("office",),
        work_scope=("facade_cladding",),
    )

    assert (
        "seed/building-remediation-rectification-guide.md"
        "#investigation-before-solution"
    ) in refs
    assert not any("remediation-due-diligence-guide.md" in ref for ref in refs)


def test_advisory_routes_service_deliverable_sections() -> None:
    refs = _refs(
        selected_paths=_selected(
            "commercial",
            "advisory",
            subclasses=("office",),
            work_scopes=("technical_dd",),
        ),
        building_class="commercial",
        work_type="advisory",
        subclasses=("office",),
        work_scope=("technical_dd",),
    )

    assert (
        "seed/advisory-services-guide.md#define-the-decision-before-the-scope"
        in refs
    )
    assert (
        "seed/procurement-tendering-guide.md#4-tender-documentation-and-deliverables"
        in refs
    )
    assert "seed/contract-administration-guide.md#contract-documentation-hierarchy" in refs


def test_archetype_fallback_selected_paths_validate_base_routes() -> None:
    selection = select_seed_knowledge_for_taxonomy(
        "pmp",
        archetype="renovation",
        building_class=None,
        work_type=None,
    )
    refs = set(selection.section_refs)

    assert "seed/setup-and-commission-guide.md#shared-setup-workflow-all-roles" in refs
    assert "seed/cost-management-principles.md#cost-planning-fundamentals" in refs


def _passage(path: str, section_id: str) -> SourcePassage:
    return SourcePassage(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content=f"## {section_id}\nLoaded content.",
        project="seed",
        phase="reference",
        source_type="reference",
        document_class="reference",
        filename=path.rsplit("/", 1)[-1],
        relative_path=path,
        document_metadata={"knowledge_scope": "platform"},
        chunk_metadata={"whole_document": True, "section_ids": [section_id]},
        score=1.0,
    )


def test_loader_records_section_refs_and_warns_for_optional_missing(monkeypatch) -> None:
    async def fake_load_sections(_session, path, section_ids, *, max_chars):
        section_id = section_ids[0]
        if section_id == "wet-area-construction-and-waterproofing":
            return None
        return LoadedKnowledge(
            passage=_passage(path, section_id),
            missing_sections=[],
            available_sections=[section_id],
        )

    from app.sitewise import seed_routing

    monkeypatch.setattr(seed_routing, "load_sections", fake_load_sections)

    selection = select_seed_knowledge_for_taxonomy(
        "pmp",
        archetype="",
        building_class="residential",
        work_type="new",
        subclasses=("house",),
        work_scopes=("wet_areas",),
    )

    result = run_async(
        load_seed_knowledge(
            object(),
            selection,
            max_chars=1000,
        )
    )

    assert result.missing_required_refs == []
    assert result.optional_warnings == [
        "seed/residential-construction-guide.md#wet-area-construction-and-waterproofing"
    ]
    refs = [
        ref
        for passage in result.passages
        for ref in passage.chunk_metadata["seed_section_refs"]
    ]
    assert "seed/setup-and-commission-guide.md#shared-setup-workflow-all-roles" in refs
    assert any(event.status == "warning" for event in result.trace_events)
