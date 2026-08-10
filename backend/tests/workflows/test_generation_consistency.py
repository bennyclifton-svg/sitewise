from __future__ import annotations

import asyncio
import uuid
from datetime import date

import pytest

from app.projects.artefact_context import RfpContext
from app.projects.generation_brief import build_generation_brief
from app.projects.generation_context import ContextField
from app.workflows.generation_consistency import (
    ConsistencySection,
    format_consistency_failures,
    run_generation_consistency_gate,
)


def _field(key: str, value: object) -> ContextField:
    return ContextField(
        key=key,
        label=key.replace("_", " ").title(),
        state="known",
        value=value,
        source="test",
    )


def _brief(*, tender_close: str | None = None):
    context = RfpContext(
        project_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        context_version=4,
        discipline="Structural Engineer",
        identity={"title": _field("title", "Walsh Renovation")},
        taxonomy={},
        scope={},
        scale={},
        complexity={},
        programme=(
            {"tender_close": _field("tender_close", tender_close)}
            if tender_close is not None
            else {}
        ),
        procurement={"procurement_route": _field("procurement_route", "traditional")},
        approvals={},
        stakeholders={"consultants": _field("consultants", ["Structural Engineer"])},
        derived_risks=[],
        section_weights={},
        critical_unknowns=[],
    )
    return build_generation_brief(context)


def test_consistency_gate_rejects_a_stale_nested_generation_brief() -> None:
    brief = _brief()
    brief.context.identity["title"].value = "Tampered project"

    with pytest.raises(ValueError, match="fingerprint is stale"):
        asyncio.run(run_generation_consistency_gate(brief, ()))


def test_valid_combined_sections_do_not_call_semantic_resolver() -> None:
    resolver_calls = 0

    async def resolver(brief, candidates):
        nonlocal resolver_calls
        del brief, candidates
        resolver_calls += 1
        return set()

    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="background",
                    text=(
                        "Project: Walsh Renovation",
                        "Consultant discipline: Structural Engineer",
                        "Procurement route: Traditional lump sum",
                    ),
                ),
                ConsistencySection(
                    key="scope",
                    scope_items=(
                        "Review the structural design basis and existing conditions.",
                        "Coordinate structural openings with architectural documentation.",
                    ),
                ),
                ConsistencySection(
                    key="risks",
                    risk_items=(
                        "Existing footings may constrain the proposed structural alterations.",
                    ),
                ),
            ),
            resolver=resolver,
        )
    )

    assert report.is_consistent
    assert report.ai_call_count == 0
    assert resolver_calls == 0


def test_labelled_project_name_conflict_is_deterministic() -> None:
    resolver_calls = 0

    async def resolver(brief, candidates):
        nonlocal resolver_calls
        del brief, candidates
        resolver_calls += 1
        return set()

    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="background",
                    text=("Project name: Chen Residence",),
                ),
            ),
            resolver=resolver,
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == [
        "project_name_conflict"
    ]
    assert not report.is_consistent
    assert report.ai_call_count == 0
    assert resolver_calls == 0


def test_labelled_consultant_conflict_is_deterministic() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="background",
                    text=("Consultant discipline: Town Planner",),
                ),
            ),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == [
        "consultant_name_conflict"
    ]
    assert report.ai_call_count == 0


def test_labelled_procurement_route_conflict_is_deterministic() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="background",
                    text=("Procurement model: Design & Construct",),
                ),
            ),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == [
        "procurement_terminology_conflict"
    ]
    assert report.ai_call_count == 0


@pytest.mark.parametrize(
    ("text", "expected_code"),
    (
        (
            "The project name is Chen Residence.",
            "project_name_conflict",
        ),
        (
            "The consultant discipline is Town Planner.",
            "consultant_name_conflict",
        ),
        (
            "The works will use a design and construct procurement route.",
            "procurement_terminology_conflict",
        ),
    ),
)
def test_explicit_free_prose_claim_conflicts_are_deterministic(
    text: str,
    expected_code: str,
) -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (ConsistencySection(key="background", text=(text,)),),
        )
    )

    assert expected_code in {issue.code for issue in report.deterministic_issues}
    assert report.ai_call_count == 0


def test_matching_free_prose_claims_do_not_trigger_ai_review() -> None:
    resolver_calls = 0

    async def resolver(brief, candidates):
        nonlocal resolver_calls
        del brief, candidates
        resolver_calls += 1
        return set()

    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="background",
                    text=(
                        "The project name is Walsh Renovation.",
                        "The consultant discipline is Structural Engineer.",
                        "The works will use a traditional procurement route.",
                    ),
                ),
            ),
            resolver=resolver,
        )
    )

    assert report.is_consistent
    assert report.ai_call_count == 0
    assert resolver_calls == 0


def test_invalid_iso_date_is_deterministic() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="programme",
                    text=("Tender close: 2026-02-30",),
                ),
            ),
            run_date=date(2026, 8, 10),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == ["invalid_date"]


def test_due_date_before_generation_date_is_deterministic() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="programme",
                    text=("Submit the fee proposal by 2026-08-01.",),
                ),
            ),
            run_date=date(2026, 8, 10),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == [
        "date_before_generation"
    ]


def test_conflicting_dates_for_same_milestone_are_deterministic() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="background",
                    text=("Tender close: 2026-09-01",),
                ),
                ConsistencySection(
                    key="programme",
                    text=("Tender close date: 2026-09-08",),
                ),
            ),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == [
        "milestone_date_conflict"
    ]
    assert report.deterministic_issues[0].section_keys == (
        "background",
        "programme",
    )


def test_milestone_date_conflicting_with_brief_is_deterministic() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(tender_close="2026-09-01"),
            (
                ConsistencySection(
                    key="programme",
                    text=("Tender close: 2026-09-08",),
                ),
            ),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == [
        "milestone_date_conflict"
    ]
    assert "shared generation brief" in report.deterministic_issues[0].message


def test_equivalent_scope_items_are_a_deterministic_duplicate() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="scope",
                    scope_items=(
                        "1. Coordinate structural openings with architectural documentation [1].",
                    ),
                ),
                ConsistencySection(
                    key="deliverables",
                    scope_items=(
                        "- Coordinate structural openings with architectural documentation.",
                    ),
                ),
            ),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == ["duplicate_scope"]
    assert report.semantic_candidates == ()
    assert report.ai_call_count == 0


def test_equivalent_risk_items_are_a_deterministic_duplicate() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="assessment",
                    risk_items=(
                        "Existing footings may constrain the proposed structural alterations.",
                    ),
                ),
                ConsistencySection(
                    key="risk_register",
                    risk_items=(
                        "Existing footings may constrain the proposed structural alterations [2].",
                    ),
                ),
            ),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == ["duplicate_risk"]


def test_near_identical_scope_items_are_a_deterministic_duplicate() -> None:
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="scope",
                    scope_items=(
                        "Coordinate structural openings, penetrations, loads, movements, tolerances, buildability and design responsibilities.",
                    ),
                ),
                ConsistencySection(
                    key="deliverables",
                    scope_items=(
                        "Coordinate structural openings, penetrations, loads, movements, tolerances, buildability, interfaces and design responsibilities.",
                    ),
                ),
            ),
        )
    )

    assert [issue.code for issue in report.deterministic_issues] == ["duplicate_scope"]
    assert report.semantic_candidates == ()


def test_ambiguous_duplicates_are_resolved_in_one_bounded_batch() -> None:
    resolver_calls = 0
    received_candidates = ()

    async def resolver(brief, candidates):
        nonlocal resolver_calls, received_candidates
        del brief
        resolver_calls += 1
        received_candidates = candidates
        return {candidates[0].id}

    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="scope",
                    scope_items=(
                        "Review the structural design basis, existing conditions, footing capacity and loads.",
                        "Document the fire strategy, egress paths and essential service interfaces.",
                    ),
                    risk_items=(
                        "Programme delay may affect tender issue and consultant coordination activities.",
                    ),
                ),
                ConsistencySection(
                    key="review",
                    scope_items=(
                        "Review the structural design basis, existing conditions, seismic capacity and loads.",
                        "Confirm the acoustic criteria, facade ratings and plant noise limits.",
                    ),
                    risk_items=(
                        "Programme delay may affect tender release and consultant coordination activities.",
                    ),
                ),
            ),
            resolver=resolver,
        )
    )

    assert report.deterministic_issues == ()
    assert len(received_candidates) == 2
    assert resolver_calls == 1
    assert report.ai_call_count == 1
    assert report.semantic_conflicts == (received_candidates[0].id,)
    assert not report.is_consistent
    assert received_candidates[0].excerpts[0] in format_consistency_failures(report)


def test_semantic_candidates_are_bounded_before_one_resolver_call() -> None:
    resolver_calls = 0
    received_count = 0

    async def resolver(brief, candidates):
        nonlocal resolver_calls, received_count
        del brief
        resolver_calls += 1
        received_count = len(candidates)
        return set()

    items = tuple(
        f"Review structural design basis existing conditions and loads option{index}."
        for index in range(8)
    )
    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (ConsistencySection(key="scope", scope_items=items),),
            resolver=resolver,
        )
    )

    assert report.deterministic_issues == ()
    assert len(report.semantic_candidates) == 12
    assert received_count == 12
    assert resolver_calls == 1
    assert report.ai_call_count == 1
    assert report.is_consistent


def test_deterministic_conflict_skips_resolver_even_with_ambiguous_candidates() -> None:
    resolver_calls = 0

    async def resolver(brief, candidates):
        nonlocal resolver_calls
        del brief, candidates
        resolver_calls += 1
        return set()

    report = asyncio.run(
        run_generation_consistency_gate(
            _brief(),
            (
                ConsistencySection(
                    key="background",
                    text=("Project: Chen Residence",),
                    scope_items=(
                        "Review the structural design basis, existing conditions, footing capacity and loads.",
                    ),
                ),
                ConsistencySection(
                    key="scope",
                    scope_items=(
                        "Review the structural design basis, existing conditions, seismic capacity and loads.",
                    ),
                ),
            ),
            resolver=resolver,
        )
    )

    assert report.deterministic_issues
    assert report.semantic_candidates
    assert resolver_calls == 0
    assert report.ai_call_count == 0
