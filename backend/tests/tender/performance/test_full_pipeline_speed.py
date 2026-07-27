"""Full-pipeline speed fixture harness (Packet A2 / Sprint S0).

Cold/warm ODL package timings are always measurable from the three-quote PDFs.
LLM stage rows are recorded through the telemetry helpers so a ledger can show
non-zero ``llm_calls`` without requiring a live worker in unit CI.

Set ``TENDER_PERF_WRITE_REPORT=1`` to write markdown under
``docs/performance/tender/``.
"""

from __future__ import annotations

import os
import hashlib
import time
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.project import Project
from app.database.user import User
from app.database.workspace_file import WorkspaceFile
from app.projects.document_selections import replace_selection
from app.schemas.document_selections import QuoteCandidateInput
from tender import worker
from tender.models import TenderComparison, TenderJob
from tender.schemas import TenderIntakeRequest
from tender.seeds.load import DatabaseSeedStore, load_tender_seeds
from tender.services import ingestion, telemetry
from tender.services.intake import create_immutable_intake
from tender.services.pdf import extract_pages
from tender.services.telemetry import (
    StageTiming,
    begin_stage_usage,
    end_stage_usage,
    record_llm_usage,
    write_stage_ledger,
)
from tender.performance.full_pipeline import (
    rank_bottlenecks,
    summarize_pipeline_run,
    write_pipeline_report,
)
from tests.conftest import run_async

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PDFS = ["Enmore.pdf", "Kaposi.pdf", "NexusBuilt.pdf"]
REPORT_DIR = REPO_ROOT / "docs" / "performance" / "tender"


def test_full_pipeline_summary_names_slowest_stage_and_covers_pipeline() -> None:
    rows = [
        StageTiming(
            stage="ingest_document",
            duration_ms=100,
            status="done",
            metadata={"queue_wait_ms": 5},
        ),
        StageTiming(
            stage="classify_document",
            duration_ms=200,
            status="done",
            llm_calls=1,
            input_tokens=10,
            output_tokens=2,
        ),
        StageTiming(
            stage="extract_line_items",
            duration_ms=700,
            status="done",
            llm_calls=1,
            input_tokens=30,
            output_tokens=5,
        ),
        StageTiming(
            stage="map_items",
            duration_ms=400,
            status="done",
            llm_calls=1,
            input_tokens=20,
            output_tokens=4,
        ),
        StageTiming(stage="run_expectations", duration_ms=30, status="done"),
        StageTiming(
            stage="infer_silence_batch",
            duration_ms=80,
            status="done",
            llm_calls=1,
            input_tokens=8,
            output_tokens=2,
        ),
        StageTiming(stage="run_analysis", duration_ms=40, status="done"),
        StageTiming(stage="generate_flags", duration_ms=20, status="done"),
        StageTiming(stage="assemble_report_draft", duration_ms=60, status="done"),
    ]

    summary = summarize_pipeline_run(
        mode="cold",
        intake_duration_ms=25,
        wall_duration_ms=1_400,
        terminal_state="report_ready",
        rows=rows,
    )

    assert summary.total_duration_ms == 1_400
    assert summary.missing_stages == ()
    assert summary.slowest_stage == "extraction"
    assert summary.stage_duration_ms == {
        "intake": 25,
        "queue": 5,
        "extraction": 800,
        "classification": 200,
        "mapping": 400,
        "expectations": 30,
        "silence": 80,
        "analysis": 40,
        "flags": 20,
        "report": 60,
    }


def test_bottleneck_ranking_uses_contribution_and_variance() -> None:
    def run(extraction: int, mapping: int):
        rows = [
            StageTiming(
                stage="extract_line_items", duration_ms=extraction, status="done"
            ),
            StageTiming(stage="classify_document", duration_ms=10, status="done"),
            StageTiming(stage="map_items", duration_ms=mapping, status="done"),
            StageTiming(stage="run_expectations", duration_ms=10, status="done"),
            StageTiming(stage="infer_silence_batch", duration_ms=10, status="done"),
            StageTiming(stage="run_analysis", duration_ms=10, status="done"),
            StageTiming(stage="generate_flags", duration_ms=10, status="done"),
            StageTiming(stage="assemble_report_draft", duration_ms=10, status="done"),
        ]
        return summarize_pipeline_run(
            mode="cold",
            intake_duration_ms=10,
            wall_duration_ms=extraction + mapping + 80,
            terminal_state="report_ready",
            rows=rows,
        )

    ranked = rank_bottlenecks([run(600, 200), run(900, 210), run(1200, 190)])

    assert ranked[0].stage == "extraction"
    assert ranked[0].median_ms == 900
    assert ranked[0].p95_ms == 1200
    assert ranked[0].variance_ms > ranked[1].variance_ms


def test_full_pipeline_ledger_includes_nonzero_llm_stats(tmp_path: Path) -> None:
    usage = begin_stage_usage()
    try:
        record_llm_usage(input_tokens=100, output_tokens=20)
        record_llm_usage(input_tokens=50, output_tokens=10, cache_hits=5)
    finally:
        end_stage_usage()

    rows = [
        StageTiming(
            stage="extract_line_items",
            duration_ms=800,
            status="done",
            llm_calls=usage.llm_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_hits=usage.cache_hits,
        ),
        StageTiming(
            stage="map_items",
            duration_ms=1200,
            status="done",
            llm_calls=2,
            input_tokens=400,
            output_tokens=60,
            metadata={"tiers": {"t0": 1, "t2": 1, "t0_ms": 5, "t2_ms": 40}},
        ),
    ]
    out = tmp_path / "warm-ledger.md"
    write_stage_ledger(out, title="Three-quote fixture", mode="warm", rows=rows)
    text = out.read_text(encoding="utf-8")
    assert "llm_calls: 4" in text or "llm_calls: 3" in text
    assert "extract_line_items | done | 800 | 2 | 150 | 30" in text
    assert "map_items | done | 1200 | 2 | 400 | 60" in text
    assert usage.llm_calls == 2
    assert usage.input_tokens == 150


@pytest.mark.integration
@pytest.mark.tender_eval
def test_three_quote_cold_warm_odl_micro_benchmark(tmp_path: Path) -> None:
    missing = [name for name in PDFS if not (FIXTURES / name).exists()]
    if missing:
        pytest.skip(f"fixture PDFs not present: {', '.join(missing)}")

    cold_rows = _measure_odl_package(mode="cold")
    warm_rows = _measure_odl_package(mode="warm")

    cold_path = tmp_path / "cold.md"
    warm_path = tmp_path / "warm.md"
    write_stage_ledger(
        cold_path,
        title="Three-quote ODL package",
        mode="cold",
        rows=cold_rows,
    )
    write_stage_ledger(
        warm_path,
        title="Three-quote ODL package",
        mode="warm",
        rows=warm_rows,
    )

    assert all(row.llm_calls == 0 for row in cold_rows)
    assert "llm_calls: 0" in cold_path.read_text(encoding="utf-8")

    if os.getenv("TENDER_PERF_WRITE_REPORT") == "1":
        stamp = date.today().isoformat()
        write_stage_ledger(
            REPORT_DIR / f"{stamp}-cold-odl.md",
            title="Three-quote ODL package",
            mode="cold",
            rows=cold_rows,
        )
        write_stage_ledger(
            REPORT_DIR / f"{stamp}-warm-odl.md",
            title="Three-quote ODL package",
            mode="warm",
            rows=warm_rows,
        )


@pytest.mark.integration
@pytest.mark.tender_eval
def test_three_quote_live_full_pipeline_cold_and_warm(monkeypatch) -> None:
    """Paid, explicit benchmark from atomic intake to report-ready/QA-required."""

    database_url = os.environ.get("TEST_DATABASE_URL")
    if (
        os.environ.get("TENDER_LIVE_EVAL") != "1"
        or os.environ.get("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1"
        or not database_url
    ):
        pytest.skip("requires TENDER_LIVE_EVAL=1 and an opted-in disposable database")

    missing = [name for name in PDFS if not (FIXTURES / name).exists()]
    if missing:
        pytest.skip(f"fixture PDFs not present: {', '.join(missing)}")

    fixture_bytes = {name: (FIXTURES / name).read_bytes() for name in PDFS}
    storage: dict[str, bytes] = {}

    def download(*, storage_key: str) -> bytes:
        return storage[storage_key]

    def upload(*, storage_key: str, content: bytes, filename: str) -> str:
        return storage_key

    monkeypatch.setattr(ingestion, "_default_downloader", download)
    monkeypatch.setattr(ingestion, "_default_uploader", upload)

    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    async def exercise() -> list:
        engine = create_async_engine(async_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        summaries = []
        sample_pairs = max(1, int(os.environ.get("TENDER_PERF_SAMPLE_PAIRS", "1")))
        try:
            async with factory() as session, session.begin():
                await load_tender_seeds(DatabaseSeedStore(session))

            for sample in range(sample_pairs):
                user_id, project_id = uuid.uuid4(), uuid.uuid4()
                file_ids: list[uuid.UUID] = []
                async with factory() as session, session.begin():
                    session.add(
                        User(id=user_id, email=f"tender-perf-{user_id}@example.com")
                    )
                    session.add(
                        Project(
                            id=project_id,
                            owner_user_id=user_id,
                            slug=f"tender-perf-{project_id}",
                            title="Tender full-pipeline benchmark",
                            workspace_path=f"projects/{project_id}",
                            phase="procurement",
                            building_class="residential",
                            work_type="refurb",
                            state="NSW",
                            status="active",
                            project_metadata={
                                "taxonomy": {
                                    "subclasses": ["house"],
                                    "scale": {"storeys": 2, "gfa_sqm": 240},
                                }
                            },
                        )
                    )
                    for name in PDFS:
                        content = fixture_bytes[name]
                        file_id = uuid.uuid4()
                        storage_key = f"{project_id}/quotes/{name}"
                        storage[storage_key] = content
                        file_ids.append(file_id)
                        session.add(
                            WorkspaceFile(
                                id=file_id,
                                project_id=project_id,
                                workspace_path=f"quotes/{name}",
                                filename=name,
                                storage_bucket="performance-fixture",
                                storage_key=storage_key,
                                content_hash=hashlib.sha256(content).hexdigest(),
                                size_bytes=len(content),
                                ingest_status="complete",
                            )
                        )
                async with factory() as session, session.begin():
                    selection = await replace_selection(
                        session,
                        project_id=project_id,
                        selected_by=user_id,
                        expected_revision=0,
                        quote_candidates=[
                            QuoteCandidateInput(
                                builder_name=Path(name).stem,
                                ordered_workspace_file_ids=[file_id],
                            )
                            for name, file_id in zip(PDFS, file_ids, strict=True)
                        ],
                        actor_source="performance_harness",
                    )

                for mode in ("cold", "warm"):
                    started = time.perf_counter()
                    async with factory() as session, session.begin():
                        created = await create_immutable_intake(
                            session,
                            request=TenderIntakeRequest(
                                project_id=project_id,
                                expected_profile_revision=1,
                                expected_selection_revision=selection.revision,
                                context_overrides={
                                    "region": "metro",
                                    "spec_level": "mid",
                                },
                                turn_id=f"perf-{sample}-{mode}-{uuid.uuid4()}",
                            ),
                            owner_user_id=user_id,
                        )
                        comparison_id = created.comparison.id
                    intake_ms = int((time.perf_counter() - started) * 1000)

                    while await worker.run_once(
                        factory, f"performance:{sample}:{mode}"
                    ):
                        pass

                    async with factory() as session:
                        comparison = await session.get(TenderComparison, comparison_id)
                        assert comparison is not None
                        jobs = list(
                            (
                                await session.execute(
                                    select(TenderJob).where(
                                        TenderJob.comparison_id == comparison_id
                                    )
                                )
                            )
                            .scalars()
                            .all()
                        )
                        incomplete = [job for job in jobs if job.status != "done"]
                        assert not incomplete, [
                            (job.kind, job.status, job.last_error) for job in incomplete
                        ]
                        rows = await telemetry.list_stage_timings(
                            session, comparison_id=comparison_id
                        )
                    terminal = (
                        "qa_required" if comparison.status == "qa" else "report_ready"
                    )
                    summary = summarize_pipeline_run(
                        mode=mode,
                        intake_duration_ms=intake_ms,
                        wall_duration_ms=int((time.perf_counter() - started) * 1000),
                        terminal_state=terminal,
                        rows=rows,
                    )
                    assert summary.missing_stages == ()
                    assert summary.llm_calls > 0
                    deterministic = {
                        "ingest_document",
                        "run_expectations",
                        "run_analysis",
                        "generate_flags",
                        "assemble_report_draft",
                    }
                    assert all(
                        row.llm_calls == 0 for row in rows if row.stage in deterministic
                    )
                    summaries.append(summary)
        finally:
            await engine.dispose()
        return summaries

    summaries = run_async(exercise())
    if os.environ.get("TENDER_PERF_WRITE_REPORT") == "1":
        write_pipeline_report(
            REPORT_DIR / f"{date.today().isoformat()}-full-pipeline.md",
            title="Three-quote full Tender pipeline",
            environment="docs/performance/environment.md",
            fixture_id="Enmore/Kaposi/NexusBuilt",
            runs=summaries,
        )
    if os.environ.get("TENDER_ENFORCE_90S") == "1":
        assert all(run.total_duration_ms <= 90_000 for run in summaries)


def _measure_odl_package(*, mode: str) -> list[StageTiming]:
    rows: list[StageTiming] = []
    package_started = time.perf_counter()
    for name in PDFS:
        pdf_path = FIXTURES / name
        started = time.perf_counter()
        pages = extract_pages(pdf_path.read_bytes())
        duration_ms = int((time.perf_counter() - started) * 1000)
        total_chars = sum(len(page.text) for page in pages)
        rows.append(
            StageTiming(
                stage=f"odl_extract:{name}",
                duration_ms=duration_ms,
                status="done",
                metadata={
                    "mode": mode,
                    "pages": len(pages),
                    "chars": total_chars,
                },
            )
        )
        assert pages, f"{name}: ODL returned no pages"
        assert total_chars > 0, f"{name}: ODL returned no text"

    rows.append(
        StageTiming(
            stage="package_total",
            duration_ms=int((time.perf_counter() - package_started) * 1000),
            status="done",
            metadata={"mode": mode},
        )
    )
    return rows
