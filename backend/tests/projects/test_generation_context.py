from __future__ import annotations

import uuid
from datetime import UTC, datetime
from time import perf_counter

import pytest

from app.projects.generation_context import (
    FieldState,
    format_generation_context,
    resolve_project_generation_context,
)
from app.schemas.project_snapshot import ProjectSnapshot


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.mark.parametrize(
    ("building_class", "work_type", "subclass", "scope"),
    [
        ("residential", "new", "house", ["site_drainage"]),
        ("residential", "refurb", "house", ["stripout"]),
        ("commercial", "refurb", "office", ["live_environment_fitout"]),
        ("commercial", "refurb", "retail_standalone", ["services_upgrade"]),
        ("residential", "new", "apartments", ["vertical_transport"]),
        ("industrial", "new", "warehouse", ["steel_frame"]),
        ("commercial", "remediation", "office", ["facade_cladding"]),
        (
            "institution",
            "refurb",
            "healthcare_hospital",
            ["live_environment_fitout", "services_upgrade"],
        ),
    ],
)
def test_stage_zero_project_shapes_resolve_through_one_context_model(
    building_class: str,
    work_type: str,
    subclass: str,
    scope: list[str],
) -> None:
    snapshot = _snapshot(
        building_class=building_class,
        work_type=work_type,
        subclass=subclass,
        work_scope=scope,
    )

    context = resolve_project_generation_context(snapshot)

    assert context.project_id == PROJECT_ID
    assert context.context_version == 7
    assert context.taxonomy["building_class"].value == building_class
    assert context.taxonomy["work_type"].value == work_type
    assert context.taxonomy["subclasses"].value == [subclass]
    assert all(context.scope[item].state == FieldState.KNOWN for item in scope)
    assert "planning" in context.complexity


def test_relevant_unanswered_fields_and_explicit_states_are_preserved() -> None:
    snapshot = _snapshot(
        building_class="residential",
        work_type="new",
        subclass="house",
        work_scope=["site_drainage"],
        field_states={
            "scope.facade_system": "explicitly_excluded",
            "scope.curtain_wall": "not_applicable",
        },
    )

    context = resolve_project_generation_context(snapshot)

    assert context.identity["client"].state == FieldState.UNKNOWN
    assert context.commercial["budget"].state == FieldState.UNKNOWN
    assert context.scope["facade_system"].state == FieldState.EXPLICITLY_EXCLUDED
    assert context.scope["curtain_wall"].state == FieldState.NOT_APPLICABLE
    assert context.scope["glazing"].state == FieldState.UNKNOWN
    assert {field.key for field in context.critical_unknowns()} >= {
        "client",
        "budget",
        "timeframe",
    }


def test_request_cache_keys_by_project_and_context_version() -> None:
    snapshot = _snapshot(
        building_class="commercial",
        work_type="refurb",
        subclass="office",
        work_scope=["partitions_walls"],
    )
    cache = {}

    first = resolve_project_generation_context(snapshot, cache=cache)
    second = resolve_project_generation_context(snapshot, cache=cache)

    assert first is second
    assert list(cache) == [(PROJECT_ID, 7)]


def test_prompt_format_marks_unknowns_without_inventing_values() -> None:
    context = resolve_project_generation_context(
        _snapshot(
            building_class="industrial",
            work_type="new",
            subclass="warehouse",
            work_scope=["steel_frame"],
        )
    )

    rendered = format_generation_context(context)

    assert "context_version: 7" in rendered
    assert "client: UNKNOWN [unknown]" in rendered
    assert "steel_frame: True [known]" in rendered


def test_context_resolution_stays_below_the_stage_zero_budget() -> None:
    snapshot = _snapshot(
        building_class="commercial",
        work_type="refurb",
        subclass="office",
        work_scope=["live_environment_fitout", "services_upgrade"],
    )
    resolve_project_generation_context(snapshot)

    started = perf_counter()
    for _ in range(100):
        resolve_project_generation_context(snapshot)
    average_ms = (perf_counter() - started) * 1000 / 100

    assert average_ms < 25


def _snapshot(
    *,
    building_class: str,
    work_type: str,
    subclass: str,
    work_scope: list[str],
    field_states: dict[str, str] | None = None,
) -> ProjectSnapshot:
    return ProjectSnapshot.model_validate(
        {
            "generated_at": datetime(2026, 8, 10, tzinfo=UTC),
            "content_fingerprint": "a" * 64,
            "context_version": 7,
            "field_states": field_states or {},
            "identity": {
                "project_id": str(PROJECT_ID),
                "title": "Representative project",
                "slug": "representative-project",
                "workspace_path": "04-projects/representative-project",
                "phase": "procurement",
                "status": "active",
                "site_address": {
                    "status": "confirmed",
                    "value": "10 Test Street",
                    "source": "project_setup",
                },
                "client": {"status": "needs_input"},
            },
            "profile": {
                "project_id": str(PROJECT_ID),
                "profile_revision": 3,
                "building_class": building_class,
                "work_type": work_type,
                "subclasses": [subclass],
                "scale": {},
                "complexity": {
                    "planning": "da",
                    "operational_constraints": "live_environment",
                },
                "work_scope": work_scope,
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": 2, "items": []},
            "evidence": {
                "fingerprint": "b" * 64,
                "active_count": 0,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {
                "budget": {"status": "needs_input"},
                "timeframe": {"status": "needs_input"},
                "procurement_route": {
                    "status": "confirmed",
                    "value": "traditional",
                    "source": "project_decision",
                },
            },
            "open_profile_proposals": [],
        }
    )
