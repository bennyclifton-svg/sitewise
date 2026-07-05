import uuid

from app.retrieval.schemas import SourcePassage
from app.sitewise.knowledge_catalog import LoadedKnowledge, select_required_paths
from app.sitewise.pmp_seed_routing import load_pmp_seed_sections, resolve_seed_routes
from tests.conftest import run_async


def _selected(building_class: str, work_type: str, user_role: str = "architect-pm"):
    return select_required_paths(
        workflow="create-pmp",
        archetype="",
        user_role=user_role,
        building_class=building_class,
        work_type=work_type,
    )


def _refs(**kwargs) -> set[str]:
    plan = resolve_seed_routes(**kwargs)
    return set(plan.refs)


def test_residential_new_scope_heavy_routes() -> None:
    refs = _refs(
        selected_paths=_selected("residential", "new"),
        building_class="residential",
        work_type="new",
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


def test_commercial_refurb_fire_services_routes_to_ncc_and_as_sections() -> None:
    refs = _refs(
        selected_paths=_selected("commercial", "refurb"),
        building_class="commercial",
        work_type="refurb",
        work_scope=("fire_services",),
    )

    assert (
        "seed/ncc-reference-guide.md#compliance-pathways-and-documentation" in refs
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
        selected_paths=_selected("industrial", "remediation"),
        building_class="industrial",
        work_type="remediation",
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


def test_advisory_routes_service_deliverable_sections() -> None:
    refs = _refs(
        selected_paths=_selected("commercial", "advisory"),
        building_class="commercial",
        work_type="advisory",
    )

    assert (
        "seed/procurement-tendering-guide.md#4-tender-documentation-and-deliverables"
        in refs
    )
    assert "seed/contract-administration-guide.md#contract-documentation-hierarchy" in refs


def test_archetype_fallback_selected_paths_validate_base_routes() -> None:
    selected_paths = select_required_paths(
        workflow="create-pmp",
        archetype="renovation",
        user_role="architect-pm",
    )
    refs = _refs(
        selected_paths=selected_paths,
        building_class=None,
        work_type=None,
    )

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

    from app.sitewise import pmp_seed_routing

    monkeypatch.setattr(pmp_seed_routing, "load_sections", fake_load_sections)

    result = run_async(
        load_pmp_seed_sections(
            object(),
            selected_paths=_selected("residential", "new"),
            building_class="residential",
            work_type="new",
            work_scope=("wet_areas",),
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
