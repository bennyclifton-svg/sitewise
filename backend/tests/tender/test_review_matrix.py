from datetime import date

import pytest

from tender.review_schemas import ReviewSelection
from tender.services.review_facts import numbered_facts, reconcile_submission
from tender.services.review_matrix import build_price_matrix


def fact(
    label, amount=None, *, kind="component", parent=None, basis="ex", currency="AUD"
):
    return dict(
        label=label,
        amount_printed=amount,
        kind=kind,
        parent_label=parent,
        tax_basis=basis,
        currency=currency,
        page_no=1,
        excerpt=label,
    )


def matrix(source, selected):
    facts = numbered_facts([dict(id="doc", quote_id="q", facts=source)])
    selection = ReviewSelection(
        conclusion="single_quote",
        findings=[dict(issue="scope", fact_ids=["f1:0"])],
        matrix=[
            dict(
                label=label,
                cells=[dict(quote_id="q", fact_ids=[f"f1:{i}" for i in ids])],
            )
            for label, ids in selected
        ],
    )
    calculations = {"q": reconcile_submission(facts, review_date=date(2026, 9, 16))}
    return build_price_matrix(
        selection,
        facts,
        [dict(id="q", name="Firm")],
        calculations,
        other_label="Other quoted items",
    )


def test_combined_lines_and_unselected_components_all_count_once():
    result = matrix(
        [
            fact("Supply", "$120.00"),
            fact("Install", "$80.00"),
            fact("Completion", "$30.00"),
            fact("Total", "$230.00", kind="total"),
        ],
        [("Electrical", [0, 1])],
    )
    assert result.labels == ["Electrical", "Other quoted items"]
    assert [row[0].amount_cents for row in result.rows] == [20000, 3000]
    assert result.rows[0][0].counted_ids == ["f1:0", "f1:1"]
    assert result.columns[0].difference_cents == 0


def test_bundle_owns_its_price_even_when_the_child_row_comes_first():
    result = matrix(
        [
            fact("Supply and install", "$200.00"),
            fact("Installation", "$80.00", parent="Supply and install"),
            fact("Included labour", kind="included", parent="Supply and install"),
            fact("Total", "$200.00", kind="total"),
        ],
        [("Installation", [1, 2]), ("Electrical package", [0])],
    )
    assert result.rows[0][0].amount_cents is None
    assert result.rows[0][0].bundled_rows == ["Electrical package"]
    assert result.rows[1][0].amount_cents == 20000
    assert result.columns[0].item_total_cents == 20000


def test_selected_subtotal_keeps_its_explicit_children_in_the_selected_group():
    result = matrix(
        [
            fact("Electrical", "$200.00", kind="subtotal"),
            fact("Supply", "$120.00", parent="Electrical"),
            fact("Installation", "$80.00", parent="Electrical"),
            fact("Total", "$200.00", kind="total"),
        ],
        [("Electrical package", [0]), ("Installation", [2])],
    )
    assert result.labels == ["Electrical package", "Installation"]
    assert result.rows[0][0].amount_cents == 20000
    assert result.rows[1][0].amount_cents is None
    assert result.rows[1][0].bundled_rows == ["Electrical package"]


def test_options_rates_and_embedded_allowances_are_reference_only():
    result = matrix(
        [
            fact("Package", "$200.00"),
            fact("Tiles", "$40.00", kind="allowance", parent="Package"),
            fact("Extra work", "$20.00", kind="rate"),
            fact("Upgrade", "$50.00", kind="option"),
            fact("Total", "$200.00", kind="total"),
        ],
        [("Package", [0]), ("Tiles", [1]), ("Extras", [2, 3])],
    )
    assert [row[0].amount_cents for row in result.rows] == [20000, None, None]
    assert result.rows[1][0].bundled_rows == ["Package"]
    assert result.columns[0].difference_cents == 0


def test_duplicate_prices_credits_and_real_zero_remain_distinct_from_missing():
    result = matrix(
        [
            fact("Supply", "$200.00"),
            fact("Supply", "$200.00"),
            fact("Credit", "($20.00)"),
            fact("Included attendance", "$0.00"),
            fact("Total", "$180.00", kind="total"),
        ],
        [
            ("Work", [0]),
            ("Repeated price", [1]),
            ("Credit", [2]),
            ("Attendance", [3]),
            ("Unknown", []),
        ],
    )
    assert [row[0].amount_cents for row in result.rows] == [20000, None, -2000, 0, None]
    assert result.rows[1][0].bundled_rows == ["Work"]
    assert result.columns[0].difference_cents == 0


def test_difference_is_exposed_not_filled_with_an_invented_adjustment():
    result = matrix(
        [fact("Work", "$200.00"), fact("Total", "$250.00", kind="total")],
        [("Work", [0])],
    )
    assert result.labels == ["Work"]
    assert result.columns[0].difference_cents == 5000


@pytest.mark.parametrize("extra", [dict(basis="inc"), dict(currency="USD")])
def test_incompatible_bases_stay_in_notes_without_a_spurious_sum(extra):
    result = matrix(
        [
            fact("Work", "$200.00"),
            fact("Other work", "$100.00", **extra),
            fact("Total", "$300.00", kind="total"),
        ],
        [("Work", [0]), ("Other work", [1])],
    )
    assert all(row[0].amount_cents is None for row in result.rows)
    assert result.columns[0].mixed_bases
    assert result.columns[0].item_total_cents is None
    assert result.columns[0].difference_cents is None


def test_tax_conversion_and_conflicting_totals_do_not_create_false_matches():
    result = matrix(
        [fact("Work", "$200.00"), fact("Total", "$220.00", kind="total", basis="inc")],
        [("Work", [0])],
    )
    assert result.columns[0].quoted_total_cents == 20000
    assert result.columns[0].converted_total
    assert result.columns[0].difference_cents == 0
    conflict = matrix(
        [
            fact("Work", "$200.00"),
            fact("Total", "$200.00", kind="total"),
            fact("Revised total", "$230.00", kind="total"),
        ],
        [("Work", [0])],
    )
    assert conflict.columns[0].quoted_total_cents is None
    assert conflict.columns[0].difference_cents is None


def test_unknown_tax_malformed_and_missing_prices_never_become_zero():
    result = matrix(
        [
            fact("Work", "$200.00", basis="unknown"),
            fact("Handrail", "$9,5556.80"),
            fact("Total", "$200.00", kind="total", basis="unknown"),
        ],
        [("Work", [0]), ("Handrail", [1])],
    )
    assert result.rows[1][0].amount_cents is None
    assert result.columns[0].quoted_total_cents is None
    empty = matrix([fact("Unknown", kind="included")], [("Unknown", [0])])
    assert empty.columns[0].item_total_cents is None


def test_allowance_only_quote_preserves_numeric_partial_schedule_without_guessing_tax():
    result = matrix(
        [
            fact(
                "Windows",
                "$100.00",
                kind="allowance",
                basis="unknown",
                parent="Provisional sums",
            ),
            fact(
                "Doors",
                "$50.00",
                kind="allowance",
                basis="unknown",
                parent="Provisional sums",
            ),
            fact("Pool", "$30.00", kind="allowance", basis="unknown"),
            fact("Total", "$1000.00", kind="total", basis="inc"),
        ],
        [("Openings", [0, 1])],
    )
    assert [row[0].amount_cents for row in result.rows] == [15000, 3000]
    assert result.columns[0].partial_schedule
    assert result.columns[0].item_total_cents == 18000
    assert result.columns[0].difference_cents is None


def test_stage_subtotals_without_component_breakdowns_are_still_prices():
    result = matrix(
        [
            fact("Design", "$100.00", kind="subtotal"),
            fact("Documentation", "$200.00", kind="subtotal"),
            fact("Total", "$300.00", kind="total"),
        ],
        [("Design", [0]), ("Documentation", [1])],
    )
    assert [row[0].amount_cents for row in result.rows] == [10000, 20000]
    assert result.columns[0].difference_cents == 0


def test_partial_exclusive_schedule_does_not_compare_to_a_gross_total():
    result = matrix(
        [
            fact("Design", "$100.00", kind="subtotal"),
            fact("Total", "$110.00", kind="total", basis="inc"),
        ],
        [("Design", [0])],
    )
    assert result.columns[0].partial_schedule
    assert result.columns[0].quoted_total_cents == 10000
    assert result.columns[0].converted_total
    assert result.columns[0].difference_cents == 0
