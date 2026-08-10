from __future__ import annotations

import uuid

import pytest

from app.projects.generation_context import (
    ContextField,
    FieldState,
    GenerationContextRisk,
    ProjectGenerationContext,
)
from app.sitewise.seed_routing import (
    SeedRoutingError,
    clear_seed_routing_caches,
    seed_routing_cache_info,
    select_seed_knowledge,
)


def test_all_generated_artefacts_use_the_shared_catalog_router() -> None:
    context = _context()

    pmp = select_seed_knowledge("pmp", context)
    cost_plan = select_seed_knowledge("cost_plan", context)
    rfp = select_seed_knowledge(
        "rfp",
        context,
        discipline="Mechanical Services",
        required_paths=("seed/mechanical-services-guide.md",),
    )
    rft = select_seed_knowledge(
        "rft",
        context,
        package="Mechanical Services",
        required_paths=("seed/trade-interfaces-coordination-guide.md",),
    )

    assert {item.seed_version for item in (pmp, cost_plan, rfp, rft)} == {
        pmp.seed_version
    }
    assert pmp.workflow == "create-pmp"
    assert cost_plan.workflow == "create-cost-plan"
    assert rfp.workflow == "consultant-procurement"
    assert rft.workflow == "trade-procurement"
    assert "seed/mechanical-services-guide.md" in rfp.guidance_paths
    assert "seed/trade-interfaces-coordination-guide.md" in rft.guidance_paths
    assert set(rfp.guidance_paths).issubset(rfp.applicable_paths)
    assert set(rft.guidance_paths).issubset(rft.applicable_paths)


def test_pmp_section_and_risk_routes_use_canonical_context() -> None:
    context = _context(risk_flags=("contaminated_land",))

    selection = select_seed_knowledge(
        "pmp",
        context,
        section="cost-budget",
    )

    assert selection.section_refs == (
        "seed/cost-management-principles.md#cost-planning-fundamentals",
        "seed/cost-management-principles.md#risk-adjusted-budgets",
    )


def test_route_cache_keys_context_and_seed_version() -> None:
    clear_seed_routing_caches()
    context = _context()

    select_seed_knowledge("cost_plan", context)
    first = seed_routing_cache_info()
    select_seed_knowledge("cost_plan", context)
    second = seed_routing_cache_info()
    select_seed_knowledge("pmp", context)
    third = seed_routing_cache_info()

    assert second.hits == first.hits + 1
    assert third.misses == second.misses + 1


def test_unknown_explicit_guidance_path_is_rejected() -> None:
    with pytest.raises(SeedRoutingError, match="Unknown seed guidance path"):
        select_seed_knowledge(
            "rfp",
            _context(),
            discipline="Mechanical Services",
            required_paths=("seed/not-a-real-guide.md",),
        )


def _context(*, risk_flags: tuple[str, ...] = ()) -> ProjectGenerationContext:
    return ProjectGenerationContext(
        project_id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        context_version=3,
        identity={},
        taxonomy={
            "building_class": _field("building_class", "commercial"),
            "subclasses": _field("subclasses", ["office"]),
            "work_type": _field("work_type", "refurb"),
            "state": _field("state", "NSW"),
        },
        scale={},
        complexity={"access": _field("access", "live_operations")},
        scope={
            "partitions_walls": _field("partitions_walls", True),
            "fire_services": _field("fire_services", True),
        },
        commercial={},
        programme={},
        approvals={},
        stakeholders={},
        derived_risks=[
            GenerationContextRisk(
                key=key,
                severity="high",
                title=key,
                description=f"Risk: {key}",
            )
            for key in risk_flags
        ],
    )


def _field(key: str, value: object) -> ContextField:
    return ContextField(
        key=key,
        label=key.replace("_", " ").title(),
        value=value,
        state=FieldState.KNOWN,
        source="project_profile",
    )
