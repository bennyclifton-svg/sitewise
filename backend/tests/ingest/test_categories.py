from ingest.categories import (
    canonical_category,
    category_label,
    resolve_category,
)


def test_short_names_are_canonical() -> None:
    assert canonical_category("Mechanical") == "mechanical"
    assert canonical_category("structural engineer") == "structural"
    assert canonical_category("Landscape Architect") == "landscape"
    assert canonical_category("Services Engineer (Hydraulic)") == "hydraulic"
    assert canonical_category("Civil / stormwater") == "civil"
    assert canonical_category("Civil Stormwater") == "civil"
    assert canonical_category("ESD") == "esd"
    assert canonical_category("Interior Designer") == "interior_design"
    assert canonical_category("Archaeology") == "archaeology"
    assert canonical_category("Ecology") == "ecology"
    assert canonical_category("Roof Access") == "roof_access"
    assert canonical_category("Heritage Consultant") == "heritage"
    assert canonical_category("Building Certifier") == "certifier"
    assert canonical_category("BCA") == "bca"
    assert canonical_category("Fire Services") == "fire_services"
    assert canonical_category("Fire Engineer") == "fire_engineer"


def test_legacy_subjects_map_onto_categories() -> None:
    assert canonical_category("architecture") == "architect"
    assert canonical_category("planning") == "town_planner"
    assert canonical_category("survey") == "surveyor"
    assert canonical_category("sustainability") == "esd"
    assert canonical_category("civil_stormwater") == "civil"
    assert canonical_category("services") == "none"


def test_resolve_prefers_subject_then_discipline() -> None:
    assert (
        resolve_category(document_subject="none", discipline="Mechanical")
        == "mechanical"
    )
    assert (
        resolve_category(document_subject="heritage", discipline="Architectural")
        == "heritage"
    )


def test_category_label_is_short() -> None:
    assert category_label("mechanical") == "Mechanical"
    assert category_label("fire_engineer") == "Fire Engineer"
    assert category_label("civil") == "Civil"
    assert category_label("esd") == "ESD"
    assert category_label("none") == ""
