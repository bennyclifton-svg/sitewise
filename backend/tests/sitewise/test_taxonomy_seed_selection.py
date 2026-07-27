from app.sitewise.knowledge_catalog import select_required_paths


def test_contamination_scope_pulls_environmental_remediation_guide() -> None:
    for building_class in ["residential", "commercial", "industrial"]:
        paths = select_required_paths(
            workflow="create-pmp",
            archetype="",
            building_class=building_class,
            work_type="remediation",
            subclasses=(),
            work_scopes=("contamination_remediation",),
        )
        assert "seed/remediation-due-diligence-guide.md" in paths
        assert "seed/building-remediation-rectification-guide.md" not in paths


def test_building_rectification_scope_pulls_rectification_guide() -> None:
    paths = select_required_paths(
        workflow="create-pmp",
        archetype="",
        building_class="commercial",
        work_type="remediation",
        subclasses=("office",),
        work_scopes=("facade_cladding",),
    )

    assert "seed/building-remediation-rectification-guide.md" in paths
    assert "seed/remediation-due-diligence-guide.md" not in paths


def test_residential_procurement_uses_quoting_not_commercial_tendering() -> None:
    paths = select_required_paths(
        workflow="create-pmp",
        archetype="",
        building_class="residential",
        work_type="new",
    )
    assert "seed/residential-construction-guide.md" in paths
    assert "seed/procurement-quoting-guide.md" in paths
    assert "seed/procurement-tendering-guide.md" not in paths


def test_commercial_procurement_uses_tendering_not_residential_quoting() -> None:
    paths = select_required_paths(
        workflow="create-pmp",
        archetype="",
        building_class="commercial",
        work_type="new",
    )
    assert "seed/procurement-tendering-guide.md" in paths
    assert "seed/procurement-quoting-guide.md" not in paths
