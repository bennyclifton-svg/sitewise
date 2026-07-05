from app.sitewise.knowledge_catalog import select_required_paths


def test_remediation_work_type_always_pulls_remediation_guide() -> None:
    for building_class in [
        "residential",
        "commercial",
        "industrial",
        "institution",
        "mixed",
        "infrastructure",
    ]:
        paths = select_required_paths(
            workflow="create-pmp",
            archetype="",
            user_role="architect-pm",
            building_class=building_class,
            work_type="remediation",
        )
        assert "seed/remediation-due-diligence-guide.md" in paths


def test_residential_procurement_uses_quoting_not_commercial_tendering() -> None:
    paths = select_required_paths(
        workflow="create-pmp",
        archetype="",
        user_role="architect-pm",
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
        user_role="architect-pm",
        building_class="commercial",
        work_type="new",
    )
    assert "seed/procurement-tendering-guide.md" in paths
    assert "seed/procurement-quoting-guide.md" not in paths
