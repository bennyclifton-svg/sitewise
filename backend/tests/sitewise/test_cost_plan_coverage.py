import pytest

from app.sitewise.cost_plan_coverage import resolve_cost_plan_coverage
from app.sitewise.knowledge_catalog import file_catalog, select_required_paths


@pytest.mark.parametrize(
    ("building_class", "work_type", "subclass", "expected_family"),
    [
        ("residential", "new", "house", "residential_class1_new"),
        ("residential", "extend", "townhouses", "residential_class1_refurb"),
        ("residential", "new", "apartments", "multi_residential"),
        ("commercial", "refurb", "office", "commercial_fitout"),
        ("commercial", "new", "retail_standalone", "commercial_base_building"),
        ("industrial", "new", "warehouse", "industrial_warehouse"),
        ("industrial", "refurb", "manufacturing", "industrial_process"),
        ("industrial", "extend", "cold_storage", "industrial_cold_chain"),
        ("industrial", "new", "data_centre", "data_centre"),
    ],
)
def test_supported_taxonomy_resolves_one_exact_family(
    building_class: str,
    work_type: str,
    subclass: str,
    expected_family: str,
) -> None:
    coverage = resolve_cost_plan_coverage(
        building_class=building_class,
        work_type=work_type,
        subclasses=(subclass,),
    )

    assert coverage is not None
    assert coverage.family == expected_family
    assert coverage.reference_path.endswith(".md")


def test_building_remediation_requires_a_supported_rectification_scope() -> None:
    coverage = resolve_cost_plan_coverage(
        building_class="commercial",
        work_type="remediation",
        subclasses=("office",),
        work_scopes=("fire_safety_orders",),
    )
    contamination = resolve_cost_plan_coverage(
        building_class="industrial",
        work_type="remediation",
        subclasses=("manufacturing",),
        work_scopes=("contamination_remediation",),
    )

    assert coverage is not None
    assert coverage.family == "building_remediation"
    assert contamination is None


@pytest.mark.parametrize(
    ("building_class", "work_type", "subclass"),
    [
        ("residential", "refurb", "apartments"),
        ("residential", "new", "residential_aged_care"),
        ("commercial", "refurb", "food_beverage"),
        ("commercial", "new", "hotel"),
        ("industrial", "new", "pharmaceutical_gmp"),
        ("industrial", "new", "dangerous_goods"),
        ("industrial", "new", "battery_manufacturing"),
        ("industrial", "advisory", "warehouse"),
    ],
)
def test_specialist_or_non_construction_gaps_remain_unsupported(
    building_class: str,
    work_type: str,
    subclass: str,
) -> None:
    assert (
        resolve_cost_plan_coverage(
            building_class=building_class,
            work_type=work_type,
            subclasses=(subclass,),
        )
        is None
    )


@pytest.mark.parametrize(
    ("building_class", "work_type", "subclass", "work_scopes"),
    [
        ("residential", "new", "house", ()),
        ("residential", "extend", "townhouses", ()),
        ("residential", "new", "apartments", ()),
        ("commercial", "refurb", "office", ("partitions_walls",)),
        ("commercial", "new", "retail_standalone", ()),
        (
            "commercial",
            "remediation",
            "office",
            ("waterproofing_rectification",),
        ),
        ("industrial", "new", "warehouse", ()),
        ("industrial", "refurb", "manufacturing", ()),
        ("industrial", "extend", "cold_storage", ()),
        ("industrial", "new", "data_centre", ()),
    ],
)
def test_capability_family_and_catalog_reference_stay_in_parity(
    building_class: str,
    work_type: str,
    subclass: str,
    work_scopes: tuple[str, ...],
) -> None:
    coverage = resolve_cost_plan_coverage(
        building_class=building_class,
        work_type=work_type,
        subclasses=(subclass,),
        work_scopes=work_scopes,
    )
    assert coverage is not None

    selected = select_required_paths(
        workflow="create-cost-plan",
        archetype="",
        building_class=building_class,
        work_type=work_type,
        subclasses=(subclass,),
        work_scopes=work_scopes,
    )
    governed_cost_refs = {
        entry.path
        for entry in file_catalog()
        if entry.path.startswith("skills/reference/nsw-")
        and "create-cost-plan" in entry.required_by
    }

    assert set(selected) & governed_cost_refs == {coverage.reference_path}
