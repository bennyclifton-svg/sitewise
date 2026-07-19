"""Unit tests for deterministic quote ledger reconciliation (I2)."""

from __future__ import annotations

from tender.schemas import ExtractedLineItem
from tender.services.reconciliation import reconcile_quote

TOL = 0.01


def _item(
    *,
    figure_key: str,
    description_raw: str,
    amount_cents: int,
    role: str = "contract_component",
    gst_basis: str = "inc",
    is_rollup: bool = False,
    parent_figure_key: str | None = None,
    printed_text: str | None = None,
    page_no: int = 1,
    section_path: list[str] | None = None,
) -> ExtractedLineItem:
    return ExtractedLineItem(
        page_no=page_no,
        description_raw=description_raw,
        amount_cents=amount_cents,
        figure_key=figure_key,
        parent_figure_key=parent_figure_key,
        role=role,  # type: ignore[arg-type]
        gst_basis=gst_basis,  # type: ignore[arg-type]
        is_rollup=is_rollup,
        printed_text=printed_text or f"${amount_cents / 100:,.2f}",
        section_path=section_path or [],
    )


def _by_key(result):
    return {f.figure_key: f for f in result.figures}


def _coastal_figures(*, drop_category: str | None = None) -> list[ExtractedLineItem]:
    cats = {
        "cat-a": 11_000_00,
        "cat-b": 22_000_00,
        "cat-c": 33_000_00,
    }
    figures = []
    for key, cents in cats.items():
        if key == drop_category:
            continue
        figures.append(
            _item(
                figure_key=key,
                description_raw=f"Category {key[-1].upper()}",
                amount_cents=cents,
                gst_basis="inc",
                is_rollup=True,
            )
        )
    if drop_category != "cat-b":
        figures.append(
            _item(
                figure_key="ps-1",
                description_raw="PS: Contingency",
                amount_cents=5_000_00,
                role="ps_allowance",
                gst_basis="inc",
                parent_figure_key="cat-b",
            )
        )
    return figures


def test_coastal_shape_counts_category_rollups() -> None:
    figures = _coastal_figures()
    stated = 11_000_00 + 22_000_00 + 33_000_00
    result = reconcile_quote(
        figures,
        stated_total_cents=stated,
        gst_treatment="inclusive",
        tol_ratio=TOL,
    )
    by_key = _by_key(result)

    assert by_key["cat-a"].counted_in_total is True
    assert by_key["cat-b"].counted_in_total is True
    assert by_key["cat-c"].counted_in_total is True
    assert by_key["ps-1"].counted_in_total is False
    assert result.residual_cents == 0
    assert result.status == "reconciled"
    assert by_key["cat-a"].amount_ex_gst_cents == round(11_000_00 / 1.1)
    assert by_key["cat-b"].amount_ex_gst_cents == round(22_000_00 / 1.1)
    assert by_key["cat-c"].amount_ex_gst_cents == round(33_000_00 / 1.1)
    assert result.stated_basis == "inc"


def test_toussaint_shape_marks_summary_duplicates_and_counts_items() -> None:
    figures = [
        _item(
            figure_key="s1",
            description_raw="1. Preliminaries",
            amount_cents=30_000_00,
            gst_basis="ex",
            is_rollup=True,
        ),
        _item(
            figure_key="s1-a",
            description_raw="1.1 Site establishment",
            amount_cents=10_000_00,
            gst_basis="ex",
            parent_figure_key="s1",
        ),
        _item(
            figure_key="s1-b",
            description_raw="1.2 Temporary works",
            amount_cents=20_000_00,
            gst_basis="ex",
            parent_figure_key="s1",
        ),
        _item(
            figure_key="s2",
            description_raw="2. Structure",
            amount_cents=70_000_00,
            gst_basis="ex",
            is_rollup=True,
        ),
        _item(
            figure_key="s2-a",
            description_raw="2.1 Concrete",
            amount_cents=30_000_00,
            gst_basis="ex",
            parent_figure_key="s2",
        ),
        _item(
            figure_key="s2-b",
            description_raw="2.2 Steel",
            amount_cents=40_000_00,
            gst_basis="ex",
            parent_figure_key="s2",
        ),
        _item(
            figure_key="sum-head",
            description_raw="SUMMARY",
            amount_cents=100_000_00,
            role="informational",
            gst_basis="ex",
            is_rollup=True,
        ),
        _item(
            figure_key="sum-s1",
            description_raw="1. Preliminaries",
            amount_cents=30_000_00,
            gst_basis="ex",
            parent_figure_key="sum-head",
            section_path=["SUMMARY"],
        ),
        _item(
            figure_key="sum-s2",
            description_raw="2. Structure",
            amount_cents=70_000_00,
            gst_basis="ex",
            parent_figure_key="sum-head",
            section_path=["SUMMARY"],
        ),
    ]
    gst_line = 10_000_00
    stated = 100_000_00 + gst_line
    result = reconcile_quote(
        figures,
        stated_total_cents=stated,
        gst_treatment="inclusive",
        tol_ratio=TOL,
        gst_line_cents=gst_line,
    )
    by_key = _by_key(result)

    assert by_key["sum-s1"].duplicate_of_figure_key == "s1"
    assert by_key["sum-s2"].duplicate_of_figure_key == "s2"
    assert by_key["sum-s1"].counted_in_total is False
    assert by_key["sum-s2"].counted_in_total is False
    assert by_key["s1"].counted_in_total is False
    assert by_key["s2"].counted_in_total is False
    assert by_key["s1-a"].counted_in_total is True
    assert by_key["s1-b"].counted_in_total is True
    assert by_key["s2-a"].counted_in_total is True
    assert by_key["s2-b"].counted_in_total is True
    assert result.residual_cents == 0
    assert result.status == "reconciled"


def test_montique_shape_counts_lump_not_ps_children() -> None:
    figures = [
        _item(
            figure_key="lump",
            description_raw="Lump sum contract price",
            amount_cents=500_000_00,
            gst_basis="inc",
            is_rollup=True,
        ),
        _item(
            figure_key="ps-a",
            description_raw="PS: Tiles",
            amount_cents=10_000_00,
            role="ps_allowance",
            gst_basis="inc",
            parent_figure_key="lump",
        ),
        _item(
            figure_key="ps-b",
            description_raw="PS: Appliances",
            amount_cents=20_000_00,
            role="ps_allowance",
            gst_basis="inc",
            parent_figure_key="lump",
        ),
        _item(
            figure_key="ps-c",
            description_raw="PS: Landscaping",
            amount_cents=30_000_00,
            role="ps_allowance",
            gst_basis="inc",
            parent_figure_key="lump",
        ),
    ]
    result = reconcile_quote(
        figures,
        stated_total_cents=500_000_00,
        gst_treatment="inclusive",
        tol_ratio=TOL,
    )
    by_key = _by_key(result)

    assert by_key["lump"].counted_in_total is True
    assert by_key["ps-a"].counted_in_total is False
    assert by_key["ps-b"].counted_in_total is False
    assert by_key["ps-c"].counted_in_total is False
    assert result.residual_cents == 0
    assert result.status == "reconciled"


def test_coastal_residual_when_category_dropped() -> None:
    missing = 33_000_00
    figures = _coastal_figures(drop_category="cat-c")
    stated = 11_000_00 + 22_000_00 + missing
    result = reconcile_quote(
        figures,
        stated_total_cents=stated,
        gst_treatment="inclusive",
        tol_ratio=TOL,
    )

    assert result.status == "residual"
    assert abs(result.residual_cents) == missing
