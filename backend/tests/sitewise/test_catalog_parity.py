"""Parity gate: the metadata-driven catalog must reproduce the previously
hand-coded required-path lists exactly (order included) for every
archetype x role combination. Expected lists are built from the frozen
constants in pmp_sources/cost_plan_sources — not from the functions, which
now delegate to the catalog — so this stays a real guard, not a tautology."""

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

ALL_COMBOS = list(itertools.product(ARCHETYPES, USER_ROLES))


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


def test_every_combo_is_covered() -> None:
    assert len(ALL_COMBOS) == 20


@pytest.mark.parametrize(("archetype", "user_role"), ALL_COMBOS)
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


@pytest.mark.parametrize(("archetype", "user_role"), ALL_COMBOS)
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
    ("archetype", "user_role"),
    [("warehouse", "builder"), ("new-dwelling", "superintendent")],
)
def test_unsupported_combos_raise_like_the_source_modules(
    archetype: str, user_role: str
) -> None:
    with pytest.raises(ValueError, match="Unsupported overlay combination"):
        select_required_paths(
            workflow="create-pmp", archetype=archetype, user_role=user_role
        )
    with pytest.raises(ValueError, match="Unsupported overlay combination"):
        pmp_sources.required_platform_paths(archetype=archetype, user_role=user_role)


def test_catalog_covers_all_seed_files() -> None:
    """Every checked-in seed and the doctrine must appear in the catalog with
    a tier — an untagged seed is invisible to progressive disclosure."""
    entries = {entry.path: entry for entry in file_catalog()}

    assert "docs/clerk-brief.md" in entries
    seed_entries = [entry for path, entry in entries.items() if path.startswith("seed/")]
    assert len(seed_entries) == 23
    for entry in seed_entries:
        assert entry.tier in {"archetype", "role-overlay", "topic"}, entry.path
        assert entry.summary, entry.path
    nsw = entries["skills/reference/nsw-residential-cost-breakdown-reference.md"]
    assert nsw.required_by == {"create-cost-plan": 2}


def test_topic_filtering_finds_cost_seeds() -> None:
    cost_entries = [
        entry
        for entry in file_catalog()
        if "cost" in entry.topics
    ]
    paths = {entry.path for entry in cost_entries}
    assert "seed/cost-management-principles.md" in paths
    assert "skills/reference/nsw-residential-cost-breakdown-reference.md" in paths
