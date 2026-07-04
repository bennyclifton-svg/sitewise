from collections import Counter
from collections.abc import Callable
from pathlib import Path

import structlog

from ingest.chunk import chunk_document
from ingest.classify import classify_entry
from ingest.discover import discover_corpus
from ingest.embed import embed_texts
from ingest.extract import extract_document
from ingest.metadata import infer_project_context
from ingest.persist import persist_ingest
from ingest.router import build_ingest_plan, should_persist_chunks
from ingest.types import FolderSummary, IngestPlan, ManifestEntry

logger = structlog.get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TraceCallback = Callable[[str, str, str, dict[str, object]], None]


def _emit_trace(
    trace_callback: TraceCallback | None,
    step: str,
    status: str,
    message: str,
    **metadata: object,
) -> None:
    if trace_callback is None:
        return
    trace_callback(
        step,
        status,
        message,
        {key: value for key, value in metadata.items() if value is not None},
    )


def _manifest_from_file(file_path: Path, data_dir: Path) -> ManifestEntry | None:
    resolved = file_path.resolve()
    data_root = data_dir.resolve()
    repo_root = _REPO_ROOT.resolve()

    if resolved.is_relative_to(data_root):
        relative_path = resolved.relative_to(data_root).as_posix()
        project = relative_path.split("/", maxsplit=1)[0]
    elif resolved.is_relative_to(repo_root):
        relative_path = resolved.relative_to(repo_root).as_posix()
        project = relative_path.split("/", maxsplit=1)[0]
    else:
        return None

    if resolved.stat().st_size == 0:
        return None

    return ManifestEntry(
        absolute_path=resolved,
        relative_path=relative_path,
        project=project,
        filename=resolved.name,
        extension=resolved.suffix.lower(),
        size_bytes=resolved.stat().st_size,
    )


def plan_entry(entry: ManifestEntry) -> IngestPlan:
    context = infer_project_context(entry.relative_path)
    classification = classify_entry(entry)
    return build_ingest_plan(entry, context, classification)


def plan_folder(
    folder: str,
    *,
    data_dir: Path | None = None,
    limit: int | None = None,
) -> list[IngestPlan]:
    entries = discover_corpus(data_dir=data_dir, folder=folder)
    if limit is not None:
        entries = entries[:limit]

    plans = [plan_entry(entry) for entry in entries]
    for plan in plans:
        logger.debug(
            "ingest_planned",
            relative_path=plan.entry.relative_path,
            document_class=plan.classification.document_class,
            ingest_mode=plan.classification.ingest_mode,
            extractor=plan.extractor,
            chunker=plan.chunker,
            metadata=plan.classification.document_metadata,
        )
    return plans


def ingest_plan(
    plan: IngestPlan,
    *,
    skip_if_unchanged: bool = True,
    trace_callback: TraceCallback | None = None,
) -> bool:
    extracted = extract_document(plan)
    if extracted is None:
        _emit_trace(
            trace_callback,
            "extract",
            "skipped",
            "No extractable content found.",
            extractor=plan.extractor,
        )
        return False
    _emit_trace(
        trace_callback,
        "extract",
        "complete",
        "Extracted document text.",
        extractor=plan.extractor,
        page_count=len(extracted.pages),
        character_count=len(extracted.normalized_content),
    )

    if should_persist_chunks(plan):
        chunks = chunk_document(extracted, plan)
        if not chunks:
            logger.warning("chunk_empty", relative_path=plan.entry.relative_path)
            _emit_trace(
                trace_callback,
                "chunk",
                "failed",
                "Chunking returned no retrieval chunks.",
                chunker=plan.chunker,
            )
            return False
        _emit_trace(
            trace_callback,
            "chunk",
            "complete",
            "Chunked document for retrieval.",
            chunker=plan.chunker,
            chunk_count=len(chunks),
        )
        embeddings = embed_texts([chunk.content for chunk in chunks])
        _emit_trace(
            trace_callback,
            "embed",
            "complete",
            "Embedded retrieval chunks.",
            embedding_count=len(embeddings),
        )
    else:
        chunks = []
        embeddings = []
        _emit_trace(
            trace_callback,
            "chunk",
            "skipped",
            "Document class does not use retrieval chunks.",
            chunker=plan.chunker,
        )

    persisted = persist_ingest(
        plan,
        extracted,
        chunks,
        embeddings,
        skip_if_unchanged=skip_if_unchanged,
    )
    _emit_trace(
        trace_callback,
        "persist",
        "complete" if persisted else "skipped",
        (
            "Persisted document and retrieval data."
            if persisted
            else "Ingest skipped because content is unchanged."
        ),
        chunk_count=len(chunks),
    )
    return persisted


def summarize_folder(folder: str, *, data_dir: Path | None = None, limit: int | None = None) -> FolderSummary:
    plans = plan_folder(folder, data_dir=data_dir, limit=limit)
    by_class = Counter(plan.classification.document_class for plan in plans)
    return FolderSummary(
        folder=folder,
        discovered=len(plans),
        planned=len(plans),
        skipped=0,
        by_class=dict(by_class),
    )


def ingest_folder(
    folder: str,
    *,
    dry_run: bool = True,
    data_dir: Path | None = None,
    limit: int | None = None,
    skip_if_unchanged: bool = True,
) -> FolderSummary:
    plans = plan_folder(folder, data_dir=data_dir, limit=limit)
    persisted = 0
    skipped = 0
    failed = 0

    if dry_run:
        summary = FolderSummary(
            folder=folder,
            discovered=len(plans),
            planned=len(plans),
            skipped=0,
            by_class=Counter(plan.classification.document_class for plan in plans),
        )
        logger.info(
            "ingest_folder_complete",
            folder=folder,
            dry_run=True,
            planned=summary.planned,
            by_class=dict(summary.by_class),
        )
        return summary

    for plan in plans:
        try:
            if ingest_plan(plan, skip_if_unchanged=skip_if_unchanged):
                persisted += 1
            else:
                skipped += 1
        except Exception as exc:
            failed += 1
            logger.error(
                "ingest_file_failed",
                relative_path=plan.entry.relative_path,
                error=str(exc),
            )

    by_class = Counter(plan.classification.document_class for plan in plans)
    summary = FolderSummary(
        folder=folder,
        discovered=len(plans),
        planned=persisted,
        skipped=skipped + failed,
        by_class=dict(by_class),
    )
    logger.info(
        "ingest_folder_complete",
        folder=folder,
        dry_run=False,
        persisted=persisted,
        skipped=skipped,
        failed=failed,
        by_class=summary.by_class,
    )
    return summary


def ingest_file(
    file_path: Path,
    *,
    data_dir: Path | None = None,
    dry_run: bool = True,
    skip_if_unchanged: bool = True,
) -> bool:
    from app.config import settings

    root = data_dir or settings.data_dir
    entry = _manifest_from_file(file_path, root)
    if entry is None:
        logger.error("ingest_file_outside_corpus", file_path=str(file_path))
        return False

    plan = plan_entry(entry)
    if dry_run:
        logger.info("ingest_file_planned", relative_path=plan.entry.relative_path, extractor=plan.extractor)
        return True
    return ingest_plan(plan, skip_if_unchanged=skip_if_unchanged)
