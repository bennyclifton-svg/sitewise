"""Taxonomy config is the single source of truth for class/type/subclass/
scale/complexity options. These tests pin the contract the frontend and
seed selection depend on."""

from app.sitewise.taxonomy import (
    building_classes,
    complexity_dimensions_for,
    risk_flag_definitions,
    scale_fields_for,
    subclasses_for,
    validate_project_taxonomy,
    work_types,
)


def test_building_classes_complete() -> None:
    assert [c.value for c in building_classes()] == [
        "residential",
        "commercial",
        "industrial",
        "institution",
        "mixed",
        "infrastructure",
    ]


def test_work_types_complete() -> None:
    assert [w.value for w in work_types()] == [
        "new",
        "refurb",
        "extend",
        "remediation",
        "advisory",
    ]


def test_every_class_has_subclasses_with_other() -> None:
    for cls in building_classes():
        subs = subclasses_for(cls.value)
        assert len(subs) >= 3
        assert subs[-1].value == "other"


def test_mixed_class_allows_multiple_subclasses() -> None:
    assert next(c for c in building_classes() if c.value == "mixed").multi_subclass


def test_scale_fields_exist_for_every_subclass() -> None:
    for cls in building_classes():
        for sub in subclasses_for(cls.value):
            if sub.value == "other":
                continue
            assert scale_fields_for(cls.value, sub.value), f"{cls.value}/{sub.value}"


def test_universal_complexity_dimensions_present_for_all_classes() -> None:
    for cls in building_classes():
        keys = {d.key for d in complexity_dimensions_for(cls.value)}
        assert {
            "contamination_level",
            "access_constraints",
            "operational_constraints",
            "procurement_route",
            "stakeholder_complexity",
            "environmental_sensitivity",
        } <= keys


def test_risk_flag_definitions_include_derivable_flags() -> None:
    flags = risk_flag_definitions()
    assert {"remote_site", "live_operations", "flood_overlay"} <= set(flags)


def test_validate_rejects_unknown_combo() -> None:
    errors = validate_project_taxonomy(
        building_class="residential",
        work_type="teleportation",
        subclasses=["house"],
    )
    assert errors


def test_validate_accepts_minimal_brief_combo() -> None:
    assert (
        validate_project_taxonomy(
            building_class="residential",
            work_type="new",
            subclasses=["house"],
        )
        == []
    )


def test_emphasis_weights_normalised_for_every_combo() -> None:
    from app.sitewise.taxonomy import PMP_CORE_SECTIONS, section_weights_for

    for cls in building_classes():
        for wt in work_types():
            weights = section_weights_for(
                building_class=cls.value,
                work_type=wt.value,
                work_scope=[],
                risk_flags=[],
            )
            assert abs(sum(weights.values()) - 1.0) < 1e-6
            assert set(weights) == set(PMP_CORE_SECTIONS)


def test_fire_services_scope_boosts_compliance_weight() -> None:
    from app.sitewise.taxonomy import section_weights_for

    base = section_weights_for(
        building_class="commercial",
        work_type="refurb",
        work_scope=[],
        risk_flags=[],
    )
    boosted = section_weights_for(
        building_class="commercial",
        work_type="refurb",
        work_scope=["fire_services"],
        risk_flags=[],
    )
    assert boosted["compliance-approvals"] > base["compliance-approvals"]


def test_residential_new_scope_outweighs_compliance() -> None:
    from app.sitewise.taxonomy import section_weights_for

    weights = section_weights_for(
        building_class="residential",
        work_type="new",
        work_scope=[],
        risk_flags=[],
    )
    assert weights["scope-client-requirements"] > weights["compliance-approvals"]
