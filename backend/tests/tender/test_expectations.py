from __future__ import annotations

from pathlib import Path
import uuid

import pytest

from tender.schemas import ProjectContext
from tender.seeds.load import read_expectations
from tender.services.expectations import (
    ExpectationRuleInput,
    FiredRule,
    MappedCellItem,
    PredicateValidationError,
    TradeExpectationTarget,
    build_cell_status_grid,
    evaluate_rules,
    expected_trades_from_fired_cells,
    validate_predicate,
)

CONCEPTS = {
    "cut_and_fill": ("cut and fill", "cut & fill", "benching", "earthworks"),
}


def test_evaluate_rules_supports_appendix_a_comparators() -> None:
    cases = [
        ({"field": "state", "eq": "NSW"}, {}, True),
        ({"field": "soil_class", "in": ["H2", "E", "P"]}, {"soil_class": "P"}, True),
        ({"field": "storeys", "gte": 2}, {"storeys": 2}, True),
        ({"field": "storeys", "lte": 1}, {"storeys": 2}, False),
        (
            {"field": "existing_dwelling_era", "before": "1990"},
            {"existing_dwelling_era": "1985"},
            True,
        ),
        ({"field": "target_budget_cents", "exists": False}, {}, True),
        (
            {"field": "notes", "contains_concept": "cut_and_fill"},
            {"notes": "The site needs cut & fill and benching."},
            True,
        ),
    ]

    for index, (predicate, overrides, should_fire) in enumerate(cases):
        fired = evaluate_rules(
            [_rule(f"RULE.{index}", predicate=predicate)],
            _context(**overrides),
            concepts=CONCEPTS,
        )
        assert [rule.rule_code for rule in fired] == ([f"RULE.{index}"] if should_fire else [])


def test_evaluate_rules_supports_nested_combinators() -> None:
    predicate = {
        "all": [
            {"field": "state", "eq": "NSW"},
            {
                "any": [
                    {"field": "soil_class", "eq": "P"},
                    {"field": "slope_class", "eq": "steep"},
                ]
            },
            {"not": {"field": "build_type", "eq": "renovation"}},
        ]
    }

    fired = evaluate_rules([_rule("NESTED", predicate=predicate)], _context(slope_class="steep"))

    assert [rule.rule_code for rule in fired] == ["NESTED"]


def test_evaluate_rules_filters_by_region_and_build_type_tags() -> None:
    rules = [
        _rule("STATE", region_tags=("QLD",)),
        _rule("STATE_REGION", region_tags=("QLD:regional",)),
        _rule("WRONG_REGION", region_tags=("QLD:metro",)),
        _rule("BUILD", build_type_tags=("new_build",)),
        _rule("WRONG_BUILD", build_type_tags=("renovation",)),
    ]

    fired = evaluate_rules(rules, _context(state="QLD", region="regional"))

    assert [rule.rule_code for rule in fired] == ["STATE", "STATE_REGION", "BUILD"]


def test_repository_selection_context_does_not_fake_rule_matches() -> None:
    rules = [
        _rule("STATE", predicate={"field": "state", "eq": "NSW"}, region_tags=("NSW",)),
        _rule("BUILD", predicate={"field": "build_type", "eq": "new_build"}, build_type_tags=("new_build",)),
        _rule("STOREYS", predicate={"field": "storeys", "gte": 2}),
    ]

    fired = evaluate_rules(
        rules,
        ProjectContext.model_validate({"context_source": "repository_selection"}),
    )

    assert fired == []


def test_appendix_a_example_rules_fire_verbatim() -> None:
    rules = [
        _rule(
            "SITE.PIERING.MUST",
            cell_code="03.02",
            severity="must",
            predicate={"field": "soil_class", "in": ["H2", "E", "P"]},
            rationale="Reactive/problem soils typically require engineered piering.",
        ),
        _rule(
            "SITE.RETAINING.SHOULD",
            cell_code="03.05",
            severity="should",
            predicate={"any": [{"field": "slope_class", "in": ["moderate", "steep"]}]},
            rationale="Sloping sites typically require retaining structures.",
        ),
        _rule(
            "STATUTORY.HOME_WARRANTY.NSW",
            cell_code="21.01",
            severity="must",
            predicate={"field": "state", "eq": "NSW"},
            rationale="NSW home-warranty (HBCF) cover must be evidenced before deposit.",
            region_tags=("NSW",),
        ),
        _rule(
            "DEMO.ASBESTOS.RENO",
            cell_code="02.03",
            severity="should",
            predicate={
                "all": [
                    {"field": "build_type", "in": ["renovation", "addition"]},
                    {"field": "existing_dwelling_era", "before": "1990"},
                ]
            },
            rationale="Pre-1990 dwellings carry material asbestos likelihood.",
            build_type_tags=("renovation", "addition"),
        ),
    ]

    fired = evaluate_rules(
        rules,
        _context(
            build_type="addition",
            existing_dwelling_era="1980",
            soil_class="P",
            slope_class="steep",
        ),
    )

    assert [rule.rule_code for rule in fired] == [
        "SITE.PIERING.MUST",
        "SITE.RETAINING.SHOULD",
        "STATUTORY.HOME_WARRANTY.NSW",
        "DEMO.ASBESTOS.RENO",
    ]


def test_validate_predicate_rejects_malformed_predicates() -> None:
    with pytest.raises(PredicateValidationError, match="unknown comparator"):
        validate_predicate({"field": "state", "matches": "NSW"})

    with pytest.raises(PredicateValidationError, match="all must be a non-empty list"):
        validate_predicate({"all": {"field": "state", "eq": "NSW"}})


def test_read_expectations_rejects_bad_predicate_at_load_time(tmp_path: Path) -> None:
    path = tmp_path / "expectations.yaml"
    path.write_text(
        """
meta: {version: 1}
rules:
  - rule: BAD.RULE
    cell: "01.01"
    severity: must
    predicate: {field: state, matches: NSW}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="BAD.RULE"):
        read_expectations(path)


def test_expected_trades_from_fired_cells_maps_via_anchors() -> None:
    trade_a = uuid.uuid4()
    trade_b = uuid.uuid4()
    trade_c = uuid.uuid4()
    fired = [
        FiredRule("SITE.RETAINING.SHOULD", "03.05", "should", None),
        FiredRule("SITE.PIERING.MUST", "03.02", "must", None),
    ]
    trades = [
        TradeExpectationTarget(trade_a, ("03.05", "03.01")),
        TradeExpectationTarget(trade_b, ("18.01",)),
        TradeExpectationTarget(trade_c, ()),
    ]

    expected = expected_trades_from_fired_cells(fired, trades)

    assert set(expected) == {trade_a}
    assert [rule.rule_code for rule in expected[trade_a]] == ["SITE.RETAINING.SHOULD"]


def test_trade_grid_expected_unmapped_is_silent_ambiguous() -> None:
    comparison_id = uuid.uuid4()
    q1 = uuid.uuid4()
    q2 = uuid.uuid4()
    trade_id = uuid.uuid4()

    drafts = build_cell_status_grid(
        comparison_id=comparison_id,
        quote_ids=[q1, q2],
        fired_rules=[
            FiredRule("SITE.RETAINING.SHOULD", "03.05", "should", "Need retaining"),
        ],
        mapped_items=[
            MappedCellItem(
                line_item_id=uuid.uuid4(),
                quote_id=q1,
                project_trade_id=trade_id,
                item_status="included",
                amount_ex_gst_cents=50_00,
            ),
        ],
        trades=[TradeExpectationTarget(trade_id, ("03.05",))],
    )

    by_key = {(d.quote_id, d.project_trade_id): d for d in drafts}
    assert by_key[(q1, trade_id)].status == "included"
    assert by_key[(q1, trade_id)].amount_cents == 50_00
    assert by_key[(q2, trade_id)].status == "silent_ambiguous"
    assert by_key[(q2, trade_id)].queue_silence
    assert by_key[(q2, trade_id)].cell_code is None
    assert by_key[(q2, trade_id)].evidence["expected_because"] == [
        "SITE.RETAINING.SHOULD"
    ]
    assert by_key[(q2, trade_id)].evidence["cross_quote_presence"] is True


def test_trade_grid_cross_quote_absence_without_anchors() -> None:
    """Trade priced in one quote and absent in another → silent even with no anchors."""
    comparison_id = uuid.uuid4()
    q1 = uuid.uuid4()
    q2 = uuid.uuid4()
    trade_id = uuid.uuid4()

    drafts = build_cell_status_grid(
        comparison_id=comparison_id,
        quote_ids=[q1, q2],
        fired_rules=[
            FiredRule("SITE.RETAINING.SHOULD", "03.05", "should", None),
        ],
        mapped_items=[
            MappedCellItem(
                line_item_id=uuid.uuid4(),
                quote_id=q1,
                project_trade_id=trade_id,
                item_status="included",
                amount_ex_gst_cents=10_00,
            ),
        ],
        trades=[TradeExpectationTarget(trade_id, ())],
    )

    by_key = {(d.quote_id, d.project_trade_id): d for d in drafts}
    assert by_key[(q1, trade_id)].status == "included"
    silent = by_key[(q2, trade_id)]
    assert silent.status == "silent_ambiguous"
    assert silent.queue_silence
    assert silent.evidence["expected_because"] == []
    assert silent.evidence["cross_quote_presence"] is True
    assert "absent here" in silent.evidence["cross_quote_note"]


def test_trade_grid_ignores_fired_cells_without_matching_anchors() -> None:
    comparison_id = uuid.uuid4()
    quote_id = uuid.uuid4()
    trade_id = uuid.uuid4()

    drafts = build_cell_status_grid(
        comparison_id=comparison_id,
        quote_ids=[quote_id],
        fired_rules=[FiredRule("SITE.RETAINING.SHOULD", "03.05", "should", None)],
        mapped_items=[],
        trades=[TradeExpectationTarget(trade_id, ("18.01",))],
    )

    assert drafts == []


def _rule(
    rule_code: str,
    *,
    cell_code: str = "03.05",
    severity: str = "should",
    predicate: dict | None = None,
    rationale: str | None = None,
    region_tags: tuple[str, ...] = (),
    build_type_tags: tuple[str, ...] = (),
) -> ExpectationRuleInput:
    return ExpectationRuleInput(
        rule_code=rule_code,
        cell_code=cell_code,
        severity=severity,
        predicate=predicate or {"field": "build_type", "exists": True},
        rationale=rationale,
        region_tags=region_tags,
        build_type_tags=build_type_tags,
    )


def _context(**overrides: object) -> ProjectContext:
    data = {
        "state": "NSW",
        "region": "metro",
        "build_type": "new_build",
        "dwelling_class": "class_1a",
        "storeys": 1,
        "soil_class": "M",
        "slope_class": "flat",
        "bal_rating": "none",
        "spec_level": "builder_base",
    }
    data.update(overrides)
    return ProjectContext.model_validate(data)
