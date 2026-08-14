from types import SimpleNamespace
from pathlib import Path

import pytest

from app.sitewise import cost_plan_sources, pmp_sources
from app.sitewise.cost_plan_sources import (
    COST_PLAN_MANDATORY_SEED,
    NSW_COMMERCIAL_FITOUT_COST_REFERENCE,
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
    paths = [
        DOCTRINE_PATH,
        ARCHETYPE_SEED_PATHS[archetype],
        ROLE_SEED,
    ]
    if archetype in RESIDENTIAL_ARCHETYPES:
        paths.append(NSW_RESIDENTIAL_COST_REFERENCE)
    paths.extend(PMP_CROSS_CUTTING_SEED_PATHS)
    return _deduped(paths)


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
    ("building_class", "work_type", "subclasses", "work_scopes", "expected"),
    [
        (
            "commercial",
            "new",
            ("office",),
            (),
            [
                "docs/clerk-brief.md",
                "seed/commercial-construction-guide.md",
                "seed/role-architect-pm.md",
                "skills/reference/nsw-commercial-base-building-cost-breakdown-reference.md",
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
            ("warehouse",),
            (),
            [
                "docs/clerk-brief.md",
                "seed/industrial-construction-guide.md",
                "seed/role-architect-pm.md",
                "skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md",
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
            (),
            (),
            [
                "docs/clerk-brief.md",
                "seed/institution-construction-guide.md",
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
            "refurb",
            ("office",),
            ("partitions_walls",),
            [
                "docs/clerk-brief.md",
                "seed/commercial-construction-guide.md",
                "seed/role-architect-pm.md",
                "skills/reference/nsw-commercial-fitout-cost-breakdown-reference.md",
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
            ("office",),
            ("technical_dd",),
            [
                "docs/clerk-brief.md",
                "seed/advisory-services-guide.md",
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
            (),
            (),
            [
                "docs/clerk-brief.md",
                "seed/mixed-use-construction-guide.md",
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
            (),
            (),
            [
                "docs/clerk-brief.md",
                "seed/infrastructure-construction-guide.md",
                "seed/role-architect-pm.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
                "seed/procurement-tendering-guide.md",
            ],
        ),
        (
            "residential",
            "extend",
            ("house",),
            (),
            [
                "docs/clerk-brief.md",
                "seed/residential-construction-guide.md",
                "seed/renovation-guide.md",
                "seed/role-architect-pm.md",
                "skills/reference/nsw-residential-cost-breakdown-reference.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
                "seed/procurement-quoting-guide.md",
            ],
        ),
        (
            "residential",
            "remediation",
            ("apartments",),
            (),
            [
                "docs/clerk-brief.md",
                "seed/building-remediation-rectification-guide.md",
                "seed/role-architect-pm.md",
                "skills/reference/nsw-building-remediation-cost-breakdown-reference.md",
                "seed/setup-and-commission-guide.md",
                "seed/contract-administration-guide.md",
                "seed/cost-management-principles.md",
                "seed/program-scheduling-guide.md",
            ],
        ),
    ],
)
def test_taxonomy_create_pmp_paths_are_class_aware(
    building_class: str,
    work_type: str,
    subclasses: tuple[str, ...],
    work_scopes: tuple[str, ...],
    expected: list[str],
) -> None:
    assert (
        select_required_paths(
            workflow="create-pmp",
            archetype="",
            building_class=building_class,
            work_type=work_type,
            subclasses=subclasses,
            work_scopes=work_scopes,
        )
        == expected
    )


def test_create_cost_plan_taxonomy_residential_excludes_industrial_ref() -> None:
    paths = select_required_paths(
        workflow="create-cost-plan",
        archetype="new-dwelling",
        building_class="residential",
        work_type="new",
        subclasses=("house",),
        work_scopes=(),
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
        building_class="industrial",
        work_type="new",
        subclasses=("warehouse",),
        work_scopes=(),
    )
    assert NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE in paths
    assert NSW_RESIDENTIAL_COST_REFERENCE not in paths
    assert DOCTRINE_PATH in paths
    assert COST_PLAN_MANDATORY_SEED in paths
    assert ROLE_SEED_PATHS["architect-pm"] in paths


def test_commercial_fitout_reference_routes_to_pmp_cost_plan_and_rfp() -> None:
    for workflow in ("create-pmp", "create-cost-plan", "consultant-procurement"):
        paths = select_required_paths(
            workflow=workflow,
            archetype="",
            building_class="commercial",
            work_type="refurb",
            subclasses=("office",),
            work_scopes=("partitions_walls",),
        )
        assert NSW_COMMERCIAL_FITOUT_COST_REFERENCE in paths
        assert NSW_RESIDENTIAL_COST_REFERENCE not in paths
        assert NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE not in paths


def test_catalog_covers_all_seed_files() -> None:
    entries = {entry.path: entry for entry in file_catalog()}
    seed_entries = [entry for path, entry in entries.items() if path.startswith("seed/")]
    seed_root = Path(__file__).resolve().parents[3] / "data" / "seed"
    assert len(seed_entries) == len(list(seed_root.glob("*.md")))
    for entry in seed_entries:
        assert entry.tier in {"archetype", "role-overlay", "topic", "overlay"}
        assert entry.summary
    assert "seed/commercial-construction-guide.md" in entries
    assert "seed/mechanical-services-guide.md" in entries
    assert "seed/remediation-due-diligence-guide.md" in entries
    mechanical = entries["seed/mechanical-services-guide.md"]
    assert mechanical.loaded_by == "discipline: mechanical-services"
    assert "mechanical-services" in mechanical.topics
    assert "mixed" in (mechanical.applies_to_classes or ())


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
