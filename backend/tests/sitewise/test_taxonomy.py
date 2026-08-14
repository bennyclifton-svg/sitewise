"""Taxonomy config is the single source of truth for class/type/subclass/
scale/complexity options. These tests pin the contract the frontend and
seed selection depend on."""

from app.sitewise.taxonomy import (
    building_classes,
    complexity_dimensions_for,
    derive_risk_flags,
    design_lead_discipline,
    risk_flag_definitions,
    scale_fields_for,
    subclasses_for,
    validate_project_taxonomy,
    work_scope_options_for,
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
            "planning",
            "contamination_level",
            "access_constraints",
            "operational_constraints",
            "procurement_route",
            "stakeholder_complexity",
            "environmental_sensitivity",
            "heritage_status",
        } <= keys


def test_risk_flag_definitions_include_derivable_flags() -> None:
    flags = risk_flag_definitions()
    assert {"remote_site", "live_operations", "flood_overlay"} <= set(flags)


def test_refurb_services_scope_is_discipline_grained() -> None:
    values = {item.value for item in work_scope_options_for("refurb")}
    assert {
        "mechanical_hvac",
        "electrical_power",
        "lighting",
        "hydraulic_plumbing",
        "fire_services",
        "accessibility_upgrade",
    } <= values
    assert "services_upgrade" not in values
    assert "lighting" in {item.value for item in work_scope_options_for("new")}


def test_planning_dimension_offers_exempt_cdc_da_ssd() -> None:
    for cls in building_classes():
        planning = next(d for d in complexity_dimensions_for(cls.value) if d.key == "planning")
        assert planning.label == "Planning"
        assert [(option.value, option.label) for option in planning.options] == [
            ("exempt", "Exempt"),
            ("cdc", "CDC"),
            ("da", "DA"),
            ("ssd", "State Significant Development (SSD)"),
        ]


def test_bushfire_and_flood_are_dimensions_of_their_own() -> None:
    """Bushfire and flood must not be options under environmental_sensitivity:
    a site can be BAL rated, flood affected, and Aboriginal heritage at once,
    and the BAL rating has to stay machine-readable for cost and risk."""
    for cls in building_classes():
        keys = {d.key for d in complexity_dimensions_for(cls.value)}
        assert {"bushfire_exposure", "flood_exposure"} <= keys


def test_bal_rating_derives_bushfire_risk_flags() -> None:
    assert [flag.value for flag in derive_risk_flags({"bushfire_exposure": "bal_29"}, [])] == [
        "bushfire_prone"
    ]
    assert {
        flag.value for flag in derive_risk_flags({"bushfire_exposure": "bal_fz"}, [])
    } == {"bushfire_prone", "bushfire_flame_zone"}
    assert derive_risk_flags({"bushfire_exposure": "not_bushfire_prone"}, []) == []


def test_flood_exposure_derives_flood_overlay() -> None:
    assert [
        flag.value for flag in derive_risk_flags({"flood_exposure": "below_1pc_aep"}, [])
    ] == ["flood_overlay"]
    assert derive_risk_flags({"flood_exposure": "above_fpl"}, []) == []


def test_environmental_sensitivity_still_independent_of_bushfire() -> None:
    flags = {
        flag.value
        for flag in derive_risk_flags(
            {
                "environmental_sensitivity": "aboriginal_heritage",
                "bushfire_exposure": "bal_29",
                "flood_exposure": "floodway",
            },
            [],
        )
    }
    assert flags == {"native_title", "bushfire_prone", "flood_overlay"}


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


def test_remediation_has_structural_remediation_scope() -> None:
    items = work_scope_options_for("remediation")
    structural = next(item for item in items if item.value == "structural_remediation")
    assert structural.consultants[0] == "Structural Engineer"
    assert design_lead_discipline("remediation", ["structural_remediation"]) == (
        "Structural Engineer"
    )


def test_extend_includes_refurb_fitout_scopes() -> None:
    values = {item.value for item in work_scope_options_for("extend")}
    assert {
        "partitions_walls",
        "joinery",
        "flooring",
        "hydraulic_plumbing",
        "structural_tie_in",
    } <= values


def test_heritage_status_is_a_universal_dimension() -> None:
    expected_options = [
        "none",
        "conservation_area",
        "local_heritage_item",
        "state_heritage_register",
    ]
    for cls in building_classes():
        heritage = next(
            d for d in complexity_dimensions_for(cls.value) if d.key == "heritage_status"
        )
        assert [option.value for option in heritage.options] == expected_options
    assert [
        flag.value
        for flag in derive_risk_flags({"heritage_status": "conservation_area"}, [])
    ] == ["heritage_adaptive_reuse"]
    assert derive_risk_flags({"heritage_status": "none"}, []) == []


def test_energy_generation_storage_scope_on_extend_and_refurb() -> None:
    for work_type in ("extend", "refurb"):
        values = {item.value for item in work_scope_options_for(work_type)}
        assert "energy_generation_storage" in values
        assert design_lead_discipline(work_type, ["energy_generation_storage"]) == (
            "Services Engineer (Electrical)"
        )


def test_industrial_and_commercial_expose_energy_scale_fields() -> None:
    energy_keys = {"capacity_mw", "battery_storage_mwh"}
    for building_class, subclass in (
        ("industrial", "other"),
        ("industrial", "warehouse"),
        ("commercial", "office"),
        ("infrastructure", "energy_renewables"),
    ):
        keys = {field.key for field in scale_fields_for(building_class, subclass)}
        assert energy_keys <= keys, f"{building_class}/{subclass}"
