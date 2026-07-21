from types import SimpleNamespace

from app.sitewise.section_contracts import (
    PMP_SECTION_HEADINGS,
    document_title,
    pmp_section_headings,
)
from app.sitewise.pmp_sources import required_section_headings
from app.sitewise.taxonomy import building_classes


def test_universal_skeleton_is_identical_across_classes() -> None:
    expected = (
        "Project Summary",
        "Brief",
        "Consultants",
        "Planning and Compliance",
        "Programme",
        "Cost Planning",
        "Procurement and Delivery",
        "Risks and mitigations",
        "Actions and decisions",
        "Citation key",
    )
    assert tuple(PMP_SECTION_HEADINGS.values()) == expected
    for building_class in building_classes():
        assert (
            required_section_headings(
                "architect-pm",
                building_class=building_class.value,
                work_type="new",
            )
            == expected
        )


def test_advisory_label_variants_share_skeleton_slots() -> None:
    headings = pmp_section_headings(work_type="advisory")
    assert "Services and deliverables" in headings
    assert "Programme of services" in headings
    assert "Procurement and Delivery" not in headings
    assert "Programme" not in headings
    assert "Consultants" in headings
    assert "Citation key" in headings
    assert document_title("architect-pm", "advisory") == "Advisory Services Plan"


def test_unknown_work_type_uses_base_labels() -> None:
    assert pmp_section_headings(work_type="mystery") == tuple(PMP_SECTION_HEADINGS.values())


def test_legacy_no_taxonomy_role_tuple_still_available() -> None:
    headings = required_section_headings("builder")
    assert "Statutory instruments and insurance" in headings
    assert "Project snapshot" not in headings


def test_project_with_building_class_dispatches_to_universal_skeleton() -> None:
    project = SimpleNamespace(
        building_class="commercial",
        work_type="refurb",
        project_metadata={"taxonomy": {"subclasses": ["office"]}},
    )
    assert required_section_headings("architect-pm", project=project) == tuple(
        PMP_SECTION_HEADINGS.values()
    )
