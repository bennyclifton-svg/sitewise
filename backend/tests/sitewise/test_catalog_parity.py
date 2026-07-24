from types import SimpleNamespace

import pytest

from app.sitewise import cost_plan_sources, pmp_sources
from app.sitewise.cost_plan_sources import (
    COST_PLAN_MANDATORY_SEED,
    NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE,
    NSW_RESIDENTIAL_COST_REFERENCE,
    RESIDENTIAL_ARCHETYPES,
)
from app.sitewise.knowledge_catalog import file_catalog, select_required_paths
from app.workflows.procurement_request import _required_guidance_paths
from app.sitewise.pmp_sources import (
    ARCHETYPE_SEED_PATHS,
    DOCTRINE_PATH,
    PMP_CROSS_CUTTING_SEED_PATHS,
    ROLE_SEED_PATHS,
)

ARCHETYPES = (
    "new-dwelling",
    "renovation",
    "multi-dwelling",
    "ancillary",
    "small-commercial",
)
ROLE_SEED = ROLE_SEED_PATHS["architect-pm"]


def _deduped(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def _expected_pmp_paths(archetype: str) -> list[str]:
    return _deduped(
        [
            DOCTRINE_PATH,
            ARCHETYPE_SEED_PATHS[archetype],
            ROLE_SEED,
            *PMP_CROSS_CUTTING_SEED_PATHS,
        ]
    )


def _expected_cost_plan_paths(archetype: str) -> list[str]:
    paths = [
        DOCTRINE_PATH,
        ARCHETYPE_SEED_PATHS[archetype],
        ROLE_SEED,
        COST_PLAN_MANDATORY_SEED,
    ]
    if archetype in RESIDENTIAL_ARCHETYPES:
        paths.append(NSW_RESIDENTIAL_COST_REFERENCE)
    return _deduped(paths)


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_create_pmp_paths_match_frozen_contract(archetype: str) -> None:
    expected = _expected_pmp_paths(archetype)
    assert (
        select_required_paths(workflow="create-pmp", archetype=archetype)
        == expected
    )
    assert (
        pmp_sources.required_platform_paths(archetype=archetype)
        == expected
    )


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_create_cost_plan_paths_match_frozen_contract(archetype: str) -> None:
    expected = _expected_cost_plan_paths(archetype)
    assert (
        select_required_paths(workflow="create-cost-plan", archetype=archetype)
        == expected
    )
    assert (
        cost_plan_sources.required_platform_paths(archetype=archetype)
        == expected
    )


@pytest.mark.parametrize(
    ("building_class", "work_type", "expected"),
    [
        (
            "commercial",
            "new",
            [
                "docs/clerk-brief.md",
                "seed/commercial-construction-guide.md",
                "seed/role-architect-pm.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
                "seed/procurement-tendering-guide.md",
            ],
        ),
        (
            "industrial",
            "new",
            [
                "docs/clerk-brief.md",
                "seed/commercial-construction-guide.md",
                "seed/role-architect-pm.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
                "seed/procurement-tendering-guide.md",
            ],
        ),
        (
            "institution",
            "refurb",
            [
                "docs/clerk-brief.md",
                "seed/commercial-construction-guide.md",
                "seed/role-architect-pm.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
                "seed/procurement-tendering-guide.md",
            ],
        ),
        (
            "commercial",
            "advisory",
            [
                "docs/clerk-brief.md",
                "seed/role-architect-pm.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
                "seed/procurement-tendering-guide.md",
            ],
        ),
        (
            "mixed",
            "new",
            [
                "docs/clerk-brief.md",
                "seed/commercial-construction-guide.md",
                "seed/multi-residential-apartments-guide.md",
                "seed/role-architect-pm.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
                "seed/procurement-tendering-guide.md",
            ],
        ),
        (
            "infrastructure",
            "new",
            [
                "docs/clerk-brief.md",
                "seed/role-architect-pm.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
                "seed/procurement-tendering-guide.md",
            ],
        ),
    ],
)
def test_taxonomy_create_pmp_paths_are_class_aware(
    building_class: str,
    work_type: str,
    expected: list[str],
) -> None:
    assert (
        select_required_paths(
            workflow="create-pmp",
            archetype="",
            building_class=building_class,
            work_type=work_type,
        )
        == expected
    )


def test_create_cost_plan_taxonomy_residential_excludes_industrial_ref() -> None:
    paths = select_required_paths(
        workflow="create-cost-plan",
        archetype="new-dwelling",
        user_role="architect-pm",
        building_class="residential",
        work_type="new",
    )
    assert NSW_RESIDENTIAL_COST_REFERENCE in paths
    assert NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE not in paths
    assert DOCTRINE_PATH in paths
    assert COST_PLAN_MANDATORY_SEED in paths
    assert ROLE_SEED_PATHS["architect-pm"] in paths


def test_create_cost_plan_taxonomy_industrial_excludes_residential_ref() -> None:
    paths = select_required_paths(
        workflow="create-cost-plan",
        archetype="new-dwelling",
        user_role="architect-pm",
        building_class="industrial",
        work_type="new",
    )
    assert NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE in paths
    assert NSW_RESIDENTIAL_COST_REFERENCE not in paths
    assert DOCTRINE_PATH in paths
    assert COST_PLAN_MANDATORY_SEED in paths
    assert ROLE_SEED_PATHS["architect-pm"] in paths


def test_catalog_covers_all_seed_files() -> None:
    entries = {entry.path: entry for entry in file_catalog()}
    seed_entries = [entry for path, entry in entries.items() if path.startswith("seed/")]
    assert len(seed_entries) == 28
    for entry in seed_entries:
        assert entry.tier in {"archetype", "role-overlay", "topic", "overlay"}
        assert entry.summary
    assert "seed/commercial-construction-guide.md" in entries
    assert "seed/remediation-due-diligence-guide.md" in entries


def test_head_contractor_procurement_paths_are_specific_and_class_aware() -> None:
    residential = select_required_paths(
        workflow="head-contractor-procurement",
        archetype="",
        building_class="residential",
        work_type="refurb",
    )
    commercial = select_required_paths(
        workflow="head-contractor-procurement",
        archetype="",
        building_class="commercial",
        work_type="new",
    )

    assert "seed/as-standards-reference.md" in residential
    assert "seed/procurement-tendering-guide.md" in commercial

    guidance = _required_guidance_paths(
        SimpleNamespace(
            archetype=None,
            building_class="residential",
            work_type="refurb",
        ),
        knowledge_workflow="head-contractor-procurement",
    )
    assert DOCTRINE_PATH not in guidance
    assert "seed/as-standards-reference.md" in guidance
