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
        "FFE Schedule",
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
    assert "FFE Schedule" in headings
    assert "Consultants" in headings
    assert "Citation key" in headings
    assert document_title("advisory") == "Advisory Services Plan"


def test_unknown_work_type_uses_base_labels() -> None:
    assert pmp_section_headings(work_type="mystery") == tuple(PMP_SECTION_HEADINGS.values())


def test_legacy_no_taxonomy_section_tuple_still_available() -> None:
    headings = required_section_headings()
    assert "Architect role and appointment" in headings
    assert "Project snapshot" not in headings


def test_project_with_building_class_dispatches_to_universal_skeleton() -> None:
    """A fitout refurb needs every section, FFE Schedule included."""
    project = SimpleNamespace(
        building_class="commercial",
        work_type="refurb",
        project_metadata={
            "taxonomy": {
                "subclasses": ["office"],
                "work_scope": ["internal_fitout"],
            }
        },
    )
    assert required_section_headings(project=project) == tuple(
        PMP_SECTION_HEADINGS.values()
    )


def test_services_refurb_drops_the_ffe_schedule() -> None:
    """Nothing is being finished or furnished, so the section has no content to
    carry. It used to render as a one-row placeholder on every such project."""
    project = SimpleNamespace(
        building_class="commercial",
        work_type="refurb",
        project_metadata={
            "taxonomy": {
                "subclasses": ["office"],
                "work_scope": ["fire_services"],
            }
        },
    )
    headings = required_section_headings(project=project)

    assert "FFE Schedule" not in headings
    assert "Consultants" in headings
    assert headings[-1] == "Citation key"


def test_an_asset_register_brings_the_schedule_back_as_equipment() -> None:
    project = SimpleNamespace(
        building_class="commercial",
        work_type="refurb",
        project_metadata={
            "taxonomy": {
                "subclasses": ["office"],
                "work_scope": ["mechanical_hvac"],
                "assets": [{"type": "Split ducted air conditioning system"}],
            }
        },
    )

    assert "FFE Schedule" in required_section_headings(project=project)


def test_advisory_drops_procurement_and_delivery() -> None:
    """An advisory engagement has no contractor to procure."""
    project = SimpleNamespace(
        building_class="institution",
        work_type="advisory",
        project_metadata={
            "taxonomy": {
                "subclasses": ["healthcare_medical_centre"],
                "work_scope": ["building_condition"],
            }
        },
    )
    headings = required_section_headings(project=project)

    assert not any("Procurement" in heading for heading in headings)
    assert "FFE Schedule" not in headings
    # The advisory heading variant still applies to what does render.
    assert "Programme of services" in headings
