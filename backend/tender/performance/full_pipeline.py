from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from tender.services.telemetry import StageTiming

STAGE_GROUPS: dict[str, frozenset[str]] = {
    "extraction": frozenset({"ingest_document", "extract_line_items", "embed_items"}),
    "classification": frozenset({"classify_document"}),
    "mapping": frozenset({"map_items"}),
    "expectations": frozenset({"run_expectations"}),
    "silence": frozenset({"infer_silence", "infer_silence_batch"}),
    "analysis": frozenset({"run_analysis"}),
    "flags": frozenset({"generate_flags"}),
    "report": frozenset({"assemble_report_draft"}),
}


@dataclass(frozen=True, slots=True)
class PipelineRunSummary:
    mode: str
    terminal_state: str
    wall_duration_ms: int
    stage_duration_ms: dict[str, int]
    missing_stages: tuple[str, ...]
    slowest_stage: str
    llm_calls: int
    input_tokens: int
    output_tokens: int

    @property
    def total_duration_ms(self) -> int:
        return self.wall_duration_ms


@dataclass(frozen=True, slots=True)
class StageBottleneck:
    stage: str
    median_ms: int
    p95_ms: int
    contribution: float
    variance_ms: float


def summarize_pipeline_run(
    *,
    mode: str,
    intake_duration_ms: int,
    wall_duration_ms: int,
    terminal_state: str,
    rows: list[StageTiming],
) -> PipelineRunSummary:
    durations = {
        "intake": max(0, intake_duration_ms),
        "queue": sum(_metadata_int(row, "queue_wait_ms") for row in rows),
        **{
            group: sum(
                max(0, row.duration_ms) for row in rows if row.stage in stage_names
            )
            for group, stage_names in STAGE_GROUPS.items()
        },
    }
    missing = tuple(
        group
        for group in STAGE_GROUPS
        if durations[group] == 0
        and not (terminal_state == "qa_required" and group == "report")
    )
    slowest = max(
        (stage for stage in durations if stage != "queue"),
        key=lambda stage: durations[stage],
    )
    return PipelineRunSummary(
        mode=mode,
        terminal_state=terminal_state,
        wall_duration_ms=max(0, wall_duration_ms),
        stage_duration_ms=durations,
        missing_stages=missing,
        slowest_stage=slowest,
        llm_calls=sum(max(0, row.llm_calls) for row in rows),
        input_tokens=sum(max(0, row.input_tokens) for row in rows),
        output_tokens=sum(max(0, row.output_tokens) for row in rows),
    )


def rank_bottlenecks(
    runs: list[PipelineRunSummary],
) -> list[StageBottleneck]:
    if not runs:
        return []
    total_median = statistics.median(run.total_duration_ms for run in runs)
    ranked: list[StageBottleneck] = []
    for stage in runs[0].stage_duration_ms:
        samples = [run.stage_duration_ms[stage] for run in runs]
        median_ms = int(statistics.median(samples))
        ranked.append(
            StageBottleneck(
                stage=stage,
                median_ms=median_ms,
                p95_ms=_nearest_rank(samples, 0.95),
                contribution=(median_ms / total_median) if total_median else 0.0,
                variance_ms=statistics.pstdev(samples),
            )
        )
    return sorted(
        ranked,
        key=lambda item: (item.contribution, item.variance_ms),
        reverse=True,
    )


def write_pipeline_report(
    path: Path,
    *,
    title: str,
    environment: str,
    fixture_id: str,
    runs: list[PipelineRunSummary],
) -> None:
    if not runs:
        raise ValueError("at least one full-pipeline run is required")
    bottlenecks = rank_bottlenecks(runs)
    sections = [
        f"# {title}",
        "",
        f"- Environment: {environment}",
        f"- Fixture: {fixture_id}",
        f"- Samples: {len(runs)}",
        "",
        "## Raw run totals",
        "",
        "sample | mode | terminal | total_ms | llm_calls | input_tokens | output_tokens | missing",
        "---: | --- | --- | ---: | ---: | ---: | ---: | ---",
    ]
    for index, run in enumerate(runs, start=1):
        sections.append(
            " | ".join(
                (
                    str(index),
                    run.mode,
                    run.terminal_state,
                    str(run.total_duration_ms),
                    str(run.llm_calls),
                    str(run.input_tokens),
                    str(run.output_tokens),
                    ", ".join(run.missing_stages) or "none",
                )
            )
        )
    sections.extend(
        [
            "",
            "## Stage contribution and variance",
            "",
            "rank | stage | median_ms | p95_ms | contribution | population_sd_ms",
            "---: | --- | ---: | ---: | ---: | ---:",
        ]
    )
    for index, item in enumerate(bottlenecks, start=1):
        sections.append(
            f"{index} | {item.stage} | {item.median_ms} | {item.p95_ms} | "
            f"{item.contribution:.3f} | {item.variance_ms:.1f}"
        )
    sections.extend(["", "## Per-run stage ledger", ""])
    stage_order = list(runs[0].stage_duration_ms)
    sections.extend(
        [
            "sample | " + " | ".join(stage_order),
            "---: | " + " | ".join("---:" for _ in stage_order),
        ]
    )
    for index, run in enumerate(runs, start=1):
        sections.append(
            f"{index} | "
            + " | ".join(str(run.stage_duration_ms[stage]) for stage in stage_order)
        )
    sections.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sections), encoding="utf-8")


def _metadata_int(row: StageTiming, key: str) -> int:
    value = (row.metadata or {}).get(key, 0)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _nearest_rank(samples: list[int], percentile: float) -> int:
    ordered = sorted(samples)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]
