from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from tender.models import Benchmark
from tender.schemas import ProjectContext


@dataclass(frozen=True)
class BenchmarkRow:
    id: str
    benchmark_key: str
    state: str
    region: str
    build_type: str
    spec_level: str
    metric: str
    p25: Decimal | None
    p50: Decimal | None
    p75: Decimal | None
    unit: str | None
    source: str
    provenance: str | None
    confidence: str
    effective_date: date | None
    superseded_by: str | None = None


@dataclass(frozen=True)
class PricedBenchmark:
    row: BenchmarkRow
    p25_cents: int | None
    p50_cents: int | None
    p75_cents: int | None
    skip_reason_key: str | None = None

    @property
    def can_price(self) -> bool:
        return self.skip_reason_key is None


def inherit_benchmark_key(
    anchor_cell_codes: Sequence[str],
    benchmark_key_by_cell: Mapping[str, str | None],
) -> str | None:
    """Single-anchor trades inherit the cell's benchmark_key; multi/unanchored skip (v1)."""
    if len(anchor_cell_codes) != 1:
        return None
    return benchmark_key_by_cell.get(anchor_cell_codes[0])


def benchmark_row_from_model(benchmark: Benchmark) -> BenchmarkRow:
    return BenchmarkRow(
        id=str(benchmark.id),
        benchmark_key=benchmark.benchmark_key,
        state=benchmark.state,
        region=benchmark.region,
        build_type=benchmark.build_type,
        spec_level=benchmark.spec_level,
        metric=benchmark.metric,
        p25=_decimal_or_none(benchmark.p25),
        p50=_decimal_or_none(benchmark.p50),
        p75=_decimal_or_none(benchmark.p75),
        unit=benchmark.unit,
        source=benchmark.source,
        provenance=benchmark.provenance,
        confidence=benchmark.confidence,
        effective_date=benchmark.effective_date,
        superseded_by=str(benchmark.superseded_by) if benchmark.superseded_by else None,
    )


def resolve_benchmark(
    rows: Sequence[BenchmarkRow],
    benchmark_key: str,
    context: ProjectContext,
    *,
    metric: str | None = None,
) -> BenchmarkRow | None:
    matches = [
        row
        for row in rows
        if row.benchmark_key == benchmark_key
        and row.state == context.state
        and row.region == context.region
        and row.build_type == context.build_type
        and row.spec_level == context.spec_level
        and row.superseded_by is None
        and (metric is None or row.metric == metric)
    ]
    if not matches:
        return None
    return max(matches, key=lambda row: row.effective_date or date.min)


def price_benchmark(
    row: BenchmarkRow,
    context: ProjectContext,
    *,
    stated_total_cents: int | None,
) -> PricedBenchmark:
    if row.metric == "ratio":
        return PricedBenchmark(row, None, None, None, "analysis.notes.ratio_not_priced")
    if row.metric == "per_m2" and context.floor_area_m2 is None:
        return PricedBenchmark(row, None, None, None, "analysis.notes.floor_area_required")
    if row.metric == "pct_of_build" and stated_total_cents is None:
        return PricedBenchmark(row, None, None, None, "analysis.notes.stated_total_required")

    return PricedBenchmark(
        row=row,
        p25_cents=_price_percentile(
            row.p25,
            row.metric,
            context,
            stated_total_cents=stated_total_cents,
        ),
        p50_cents=_price_percentile(
            row.p50,
            row.metric,
            context,
            stated_total_cents=stated_total_cents,
        ),
        p75_cents=_price_percentile(
            row.p75,
            row.metric,
            context,
            stated_total_cents=stated_total_cents,
        ),
    )


def _price_percentile(
    value: Decimal | None,
    metric: str,
    context: ProjectContext,
    *,
    stated_total_cents: int | None,
) -> int | None:
    if value is None:
        return None
    if metric == "absolute":
        return int(round(value))
    if metric == "per_m2":
        assert context.floor_area_m2 is not None
        return int(round(value * Decimal(str(context.floor_area_m2))))
    if metric == "pct_of_build":
        assert stated_total_cents is not None
        return int(round(Decimal(stated_total_cents) * value / Decimal("100")))
    return None


def _decimal_or_none(value: Any) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None
