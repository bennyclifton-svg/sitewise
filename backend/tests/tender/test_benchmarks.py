from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from tender.schemas import ProjectContext
from tender.services.benchmarks import (
    BenchmarkRow,
    inherit_benchmark_key,
    price_benchmark,
    resolve_benchmark,
)


def test_inherit_benchmark_key_single_anchor_only() -> None:
    keys = {"03.05": "site.retaining", "18.01": "joinery.kitchen"}

    assert inherit_benchmark_key(("03.05",), keys) == "site.retaining"
    assert inherit_benchmark_key(("03.05", "18.01"), keys) is None
    assert inherit_benchmark_key((), keys) is None
    assert inherit_benchmark_key(("99.99",), keys) is None


def test_resolve_benchmark_uses_exact_non_superseded_latest_effective_date() -> None:
    rows = [
        _row(
            id="old",
            benchmark_key="site.cost",
            p50=Decimal("1000"),
            effective_date=date(2026, 1, 1),
        ),
        _row(
            id="latest",
            benchmark_key="site.cost",
            p50=Decimal("1200"),
            effective_date=date(2026, 6, 1),
        ),
        _row(
            id="superseded",
            benchmark_key="site.cost",
            p50=Decimal("9999"),
            effective_date=date(2026, 7, 1),
            superseded_by="latest",
        ),
        _row(
            id="wrong-region",
            benchmark_key="site.cost",
            region="regional",
            p50=Decimal("9000"),
            effective_date=date(2026, 8, 1),
        ),
    ]

    resolved = resolve_benchmark(rows, "site.cost", _context())

    assert resolved is not None
    assert resolved.id == "latest"
    assert resolved.p50 == Decimal("1200")


def test_resolve_benchmark_returns_none_for_missing_exact_key() -> None:
    assert resolve_benchmark([_row(benchmark_key="site.cost")], "site.other", _context()) is None
    assert (
        resolve_benchmark(
            [_row(benchmark_key="site.cost", spec_level="builder_base")],
            "site.cost",
            _context(spec_level="mid"),
        )
        is None
    )


@pytest.mark.parametrize(
    ("row_kwargs", "context_kwargs", "stated_total_cents", "expected"),
    [
        (
            {"metric": "absolute", "p25": Decimal("100"), "p50": Decimal("150"), "p75": Decimal("225")},
            {},
            1_000_000,
            (100, 150, 225, None),
        ),
        (
            {"metric": "per_m2", "p25": Decimal("1000"), "p50": Decimal("2000"), "p75": Decimal("3000")},
            {"floor_area_m2": 150},
            1_000_000,
            (150_000, 300_000, 450_000, None),
        ),
        (
            {"metric": "pct_of_build", "p25": Decimal("5"), "p50": Decimal("10"), "p75": Decimal("12.5")},
            {},
            1_000_000,
            (50_000, 100_000, 125_000, None),
        ),
        (
            {"metric": "ratio", "p25": Decimal("1.1"), "p50": Decimal("1.2"), "p75": Decimal("1.3")},
            {},
            1_000_000,
            (None, None, None, "analysis.notes.ratio_not_priced"),
        ),
        (
            {"metric": "per_m2", "p25": Decimal("1000"), "p50": Decimal("2000"), "p75": Decimal("3000")},
            {"floor_area_m2": None},
            1_000_000,
            (None, None, None, "analysis.notes.floor_area_required"),
        ),
        (
            {"metric": "pct_of_build", "p25": Decimal("5"), "p50": Decimal("10"), "p75": Decimal("12.5")},
            {},
            None,
            (None, None, None, "analysis.notes.stated_total_required"),
        ),
    ],
)
def test_price_benchmark_converts_each_metric_to_integer_cents(
    row_kwargs: dict[str, object],
    context_kwargs: dict[str, object],
    stated_total_cents: int | None,
    expected: tuple[int | None, int | None, int | None, str | None],
) -> None:
    row = _row(**row_kwargs)
    context = _context(**context_kwargs)
    priced = price_benchmark(row, context, stated_total_cents=stated_total_cents)

    assert (
        priced.p25_cents,
        priced.p50_cents,
        priced.p75_cents,
        priced.skip_reason_key,
    ) == expected


def _row(
    *,
    id: str = "bench",
    benchmark_key: str = "site.cost",
    state: str = "NSW",
    region: str = "metro",
    build_type: str = "new_build",
    spec_level: str = "mid",
    metric: str = "absolute",
    p25: Decimal | None = Decimal("1000"),
    p50: Decimal | None = Decimal("1200"),
    p75: Decimal | None = Decimal("1500"),
    confidence: str = "high",
    effective_date: date | None = date(2026, 1, 1),
    superseded_by: str | None = None,
) -> BenchmarkRow:
    return BenchmarkRow(
        id=id,
        benchmark_key=benchmark_key,
        state=state,
        region=region,
        build_type=build_type,
        spec_level=spec_level,
        metric=metric,
        p25=p25,
        p50=p50,
        p75=p75,
        unit="AUD",
        source="model_seed",
        provenance="fixture",
        confidence=confidence,
        effective_date=effective_date,
        superseded_by=superseded_by,
    )


def _context(**overrides: object) -> ProjectContext:
    data = {
        "state": "NSW",
        "region": "metro",
        "build_type": "new_build",
        "dwelling_class": "class_1a",
        "storeys": 1,
        "floor_area_m2": 200,
        "soil_class": "H2",
        "slope_class": "flat",
        "bal_rating": "none",
        "spec_level": "mid",
    }
    data.update(overrides)
    return ProjectContext.model_validate(data)
