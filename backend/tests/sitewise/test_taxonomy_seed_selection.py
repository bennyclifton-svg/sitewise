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


def test_empty_remediation_scope_loads_rectification_guide() -> None:
    """Prompt 6 left work_scope empty; remediation doctrine must still load."""
    paths = select_required_paths(
        workflow="create-pmp",
        archetype="",
        building_class="residential",
        work_type="remediation",
        subclasses=("apartments",),
        work_scopes=(),
    )
    assert "seed/building-remediation-rectification-guide.md" in paths
    assert (
        "skills/reference/nsw-building-remediation-cost-breakdown-reference.md"
        in paths
    )
    assert "seed/remediation-due-diligence-guide.md" not in paths


def test_residential_extend_loads_renovation_guide() -> None:
    """Prompt 14 is a house extension; heritage/tie-in doctrine must be reachable."""
    paths = select_required_paths(
        workflow="create-pmp",
        archetype="",
        building_class="residential",
        work_type="extend",
        subclasses=("house",),
        work_scopes=(),
    )
    assert "seed/renovation-guide.md" in paths
    assert "seed/residential-construction-guide.md" in paths


def test_class_guides_load_for_institution_mixed_and_infrastructure() -> None:
    cases = (
        ("institution", "new", "seed/institution-construction-guide.md"),
        ("institution", "refurb", "seed/institution-construction-guide.md"),
        ("mixed", "new", "seed/mixed-use-construction-guide.md"),
        ("mixed", "refurb", "seed/mixed-use-construction-guide.md"),
        ("infrastructure", "new", "seed/infrastructure-construction-guide.md"),
        ("infrastructure", "refurb", "seed/infrastructure-construction-guide.md"),
        ("infrastructure", "extend", "seed/infrastructure-construction-guide.md"),
    )
    for building_class, work_type, expected in cases:
        paths = select_required_paths(
            workflow="create-pmp",
            archetype="",
            building_class=building_class,
            work_type=work_type,
        )
        assert expected in paths, (building_class, work_type, paths)
