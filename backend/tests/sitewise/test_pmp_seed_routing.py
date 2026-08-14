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


def test_apartments_remediation_resolves_without_route_error() -> None:
    """Regression: apartments + remediation hard-failed the PMP workflow.

    The section map required seed/multi-residential-apartments-guide.md for any
    residential/apartments project, but that guide's frontmatter declares
    applies_to_work_types [new, refurb, extend]. On remediation the catalog
    therefore never selected the file and route validation raised, killing the
    run before generation.
    """
    refs = _refs(
        selected_paths=_selected(
            "residential",
            "remediation",
            subclasses=("apartments",),
            work_scopes=("facade_cladding",),
        ),
        building_class="residential",
        work_type="remediation",
        subclasses=("apartments",),
        work_scope=("facade_cladding",),
    )

    assert refs
    assert not any("multi-residential-apartments-guide.md" in ref for ref in refs)


def test_advisory_guide_routes_for_every_building_class() -> None:
    """The advisory overlay is cross-class; institution/mixed/infrastructure
    advisory projects previously hard-failed because its frontmatter listed
    only residential, commercial and industrial."""
    for building_class, subclass in (
        ("institution", "healthcare_medical_centre"),
        ("mixed", "retail_office"),
        ("infrastructure", "rail_metro"),
    ):
        refs = _refs(
            selected_paths=_selected(
                building_class,
                "advisory",
                subclasses=(subclass,),
                work_scopes=("technical_dd",),
            ),
            building_class=building_class,
            work_type="advisory",
            subclasses=(subclass,),
            work_scope=("technical_dd",),
        )
        assert (
            "seed/advisory-services-guide.md#define-the-decision-before-the-scope"
            in refs
        ), building_class


def test_residential_advisory_skips_commercial_procurement_guide() -> None:
    """procurement-tendering-guide is authored commercial-and-up; a residential
    advisory project must not have it routed as required."""
    refs = _refs(
        selected_paths=_selected(
            "residential",
            "advisory",
            subclasses=("house",),
            work_scopes=("technical_dd",),
        ),
        building_class="residential",
        work_type="advisory",
        subclasses=("house",),
        work_scope=("technical_dd",),
    )

    assert refs
    assert not any("procurement-tendering-guide.md" in ref for ref in refs)


def test_every_taxonomy_combination_resolves_seed_routes() -> None:
    """No class/subclass/work-type combination may raise during route resolution.

    Seed frontmatter and the section-seed map evolve independently; a
    disagreement between them must degrade to a dropped route, never to a
    workflow failure.
    """
    import json

    from app.sitewise.knowledge_catalog import REPO_ROOT

    taxonomy = json.loads(
        (REPO_ROOT / "data" / "taxonomy" / "building-classes.json").read_text(
            encoding="utf-8"
        )
    )
    work_types = tuple(item["value"] for item in taxonomy["work_types"])

    failures: list[str] = []
    for entry in taxonomy["building_classes"]:
        building_class = entry["value"]
        for subclass in entry.get("subclasses", []):
            for work_type in work_types:
                try:
                    select_seed_knowledge_for_taxonomy(
                        "pmp",
                        archetype="",
                        building_class=building_class,
                        work_type=work_type,
                        subclasses=(subclass["value"],),
                        work_scopes=(),
                    )
                except Exception as exc:  # noqa: BLE001 - reporting all failures
                    failures.append(
                        f"{building_class}/{subclass['value']}/{work_type}: {exc}"
                    )

    assert not failures, "\n".join(failures)


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


def test_infrastructure_rail_routes_possessions_and_accreditation() -> None:
    refs = _refs(
        selected_paths=_selected(
            "infrastructure",
            "refurb",
            subclasses=("rail_metro",),
        ),
        building_class="infrastructure",
        work_type="refurb",
        subclasses=("rail_metro",),
    )
    assert (
        "seed/infrastructure-construction-guide.md#possessions-outages-and-live-network-access"
        in refs
    )
    assert (
        "seed/infrastructure-construction-guide.md#safety-accreditation-and-worker-competency"
        in refs
    )
    assert (
        "seed/infrastructure-construction-guide.md#authority-interfaces-and-network-operators"
        in refs
    )


def test_institution_and_mixed_class_guides_route_core_sections() -> None:
    institution_refs = _refs(
        selected_paths=_selected("institution", "new"),
        building_class="institution",
        work_type="new",
    )
    mixed_refs = _refs(
        selected_paths=_selected("mixed", "new"),
        building_class="mixed",
        work_type="new",
    )
    assert (
        "seed/institution-construction-guide.md#public-procurement-and-probity"
        in institution_refs
    )
    assert (
        "seed/mixed-use-construction-guide.md#multiple-classifications-in-one-structure"
        in mixed_refs
    )
    assert (
        "seed/mixed-use-construction-guide.md#staged-handover-by-use" in mixed_refs
    )


def test_empty_remediation_scope_routes_rectification_sections() -> None:
    refs = _refs(
        selected_paths=_selected(
            "residential",
            "remediation",
            subclasses=("apartments",),
        ),
        building_class="residential",
        work_type="remediation",
        subclasses=("apartments",),
    )
    assert (
        "seed/building-remediation-rectification-guide.md"
        "#investigation-before-solution"
    ) in refs
    assert not any("remediation-due-diligence-guide.md" in ref for ref in refs)


def test_residential_extend_routes_heritage_and_tie_in() -> None:
    refs = _refs(
        selected_paths=_selected(
            "residential",
            "extend",
            subclasses=("house",),
        ),
        building_class="residential",
        work_type="extend",
        subclasses=("house",),
    )
    assert (
        "seed/renovation-guide.md#heritage-and-character-due-diligence" in refs
    )
    assert (
        "seed/renovation-guide.md#waterproofing-and-old-to-new-tie-ins" in refs
    )
