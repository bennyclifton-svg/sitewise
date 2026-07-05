import itertools

import pytest

from app.sitewise import cost_plan_sources, pmp_sources
from app.sitewise.cost_plan_sources import (
    COST_PLAN_MANDATORY_SEED,
    NSW_RESIDENTIAL_COST_REFERENCE,
    RESIDENTIAL_ARCHETYPES,
)
from app.sitewise.knowledge_catalog import file_catalog, select_required_paths
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
USER_ROLES = ("owner-builder", "architect-pm", "builder", "d-and-c")


def _deduped(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def _expected_pmp_paths(archetype: str, user_role: str) -> list[str]:
    return _deduped(
        [
            DOCTRINE_PATH,
            ARCHETYPE_SEED_PATHS[archetype],
            ROLE_SEED_PATHS[user_role],
            *PMP_CROSS_CUTTING_SEED_PATHS,
        ]
    )


def _expected_cost_plan_paths(archetype: str, user_role: str) -> list[str]:
    paths = [
        DOCTRINE_PATH,
        ARCHETYPE_SEED_PATHS[archetype],
        ROLE_SEED_PATHS[user_role],
        COST_PLAN_MANDATORY_SEED,
    ]
    if archetype in RESIDENTIAL_ARCHETYPES:
        paths.append(NSW_RESIDENTIAL_COST_REFERENCE)
    return _deduped(paths)


@pytest.mark.parametrize(("archetype", "user_role"), itertools.product(ARCHETYPES, USER_ROLES))
def test_create_pmp_paths_match_frozen_contract(archetype: str, user_role: str) -> None:
    expected = _expected_pmp_paths(archetype, user_role)
    assert (
        select_required_paths(
            workflow="create-pmp", archetype=archetype, user_role=user_role
        )
        == expected
    )
    assert (
        pmp_sources.required_platform_paths(archetype=archetype, user_role=user_role)
        == expected
    )


@pytest.mark.parametrize(("archetype", "user_role"), itertools.product(ARCHETYPES, USER_ROLES))
def test_create_cost_plan_paths_match_frozen_contract(
    archetype: str, user_role: str
) -> None:
    expected = _expected_cost_plan_paths(archetype, user_role)
    assert (
        select_required_paths(
            workflow="create-cost-plan", archetype=archetype, user_role=user_role
        )
        == expected
    )
    assert (
        cost_plan_sources.required_platform_paths(
            archetype=archetype, user_role=user_role
        )
        == expected
    )


@pytest.mark.parametrize(
    ("building_class", "work_type", "user_role", "expected"),
    [
        (
            "commercial",
            "new",
            "architect-pm",
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
            "d-and-c",
            [
                "docs/clerk-brief.md",
                "seed/commercial-construction-guide.md",
                "seed/role-d-and-c.md",
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
            "architect-pm",
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
            "architect-pm",
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
            "architect-pm",
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
            "architect-pm",
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
    user_role: str,
    expected: list[str],
) -> None:
    assert (
        select_required_paths(
            workflow="create-pmp",
            archetype="",
            user_role=user_role,
            building_class=building_class,
            work_type=work_type,
        )
        == expected
    )


def test_catalog_covers_all_seed_files() -> None:
    entries = {entry.path: entry for entry in file_catalog()}
    seed_entries = [entry for path, entry in entries.items() if path.startswith("seed/")]
    assert len(seed_entries) == 28
    for entry in seed_entries:
        assert entry.tier in {"archetype", "role-overlay", "topic", "overlay"}
        assert entry.summary
    assert "seed/commercial-construction-guide.md" in entries
    assert "seed/remediation-due-diligence-guide.md" in entries
