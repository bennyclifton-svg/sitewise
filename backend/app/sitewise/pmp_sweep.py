"""Current-corpus sweep helpers for Update PMP."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.project import Project
from app.retrieval.schemas import SourcePassage
from app.schemas.projects import WorkflowTraceEvent
from app.sitewise.mobilisation_evidence import (
    MobilisationEvidencePack,
    extract_mobilisation_evidence_pack,
    merge_evidence_packs,
)
from app.sitewise.pmp_corpus import CorpusListingResult, list_current_pmp_corpus_documents
from app.sitewise.pmp_evidence_validation import apply_corpus_evidence_downgrades

CREATE_PMP_EVIDENCE_DOC_CHARS = 8_000
CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS = 8


def _trace(step: str, status: str, message: str, **metadata) -> WorkflowTraceEvent:
    return WorkflowTraceEvent(
        step=step,
        status=status,
        message=message,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )


def _source_ref(passage: SourcePassage) -> str:
    return f"{passage.source_type or 'source'}:{passage.relative_path}#chunk={passage.chunk_id}"


@dataclass(frozen=True, slots=True)
class CorpusSweepResult:
    passages: tuple[SourcePassage, ...]
    merged_pack: MobilisationEvidencePack
    evidence_refs: tuple[str, ...]
    listing: CorpusListingResult
    evidence_changed: dict[str, list[str]]
    trace_events: tuple[WorkflowTraceEvent, ...]


def evidence_ref_path(ref: str) -> str:
    body = ref.split(":", 1)[-1]
    return body.split("#", 1)[0].replace("\\", "/")


def compute_evidence_changed(
    *,
    previous_refs: list[str],
    current_refs: list[str],
    previous_paths: set[str] | None = None,
    current_paths: set[str] | None = None,
    downgraded_sections: list[str] | None = None,
    conflicted_sections: list[str] | None = None,
) -> dict[str, list[str]]:
    prev_paths = previous_paths or {evidence_ref_path(ref) for ref in previous_refs}
    curr_paths = current_paths or {evidence_ref_path(ref) for ref in current_refs}
    superseded = sorted(prev_paths - curr_paths)
    return {
        "added": sorted(curr_paths - prev_paths),
        "removed": sorted(prev_paths - curr_paths),
        "superseded": superseded,
        "downgraded": list(downgraded_sections or []),
        "conflicted": list(conflicted_sections or []),
    }


def compute_sections_changed(
    baseline_markdown: str,
    output_markdown: str,
) -> list[str]:
    """Return section headings whose body changed between baseline and output."""
    baseline_sections = _section_bodies(baseline_markdown)
    output_sections = _section_bodies(output_markdown)
    changed: list[str] = []
    for heading, baseline_body in baseline_sections.items():
        output_body = output_sections.get(heading)
        if output_body is None:
            continue
        if _normalise_section_body(baseline_body) != _normalise_section_body(output_body):
            changed.append(heading)
    for heading in output_sections:
        if heading not in baseline_sections:
            changed.append(heading)
    return changed


def _section_bodies(markdown: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = stripped[3:].strip()
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()
    return sections


def _normalise_section_body(body: str) -> str:
    return re.sub(r"\s+", " ", body.strip().lower())


def _document_passage(document) -> SourcePassage:
    content = document.normalized_content[:CREATE_PMP_EVIDENCE_DOC_CHARS]
    return SourcePassage(
        chunk_id=document.id,
        document_id=document.id,
        chunk_index=0,
        content=content,
        page_or_section=None,
        project=document.project,
        project_id=getattr(document, "project_id", None),
        phase=document.phase,
        source_type=document.source_type or "project_evidence",
        document_class=document.document_class,
        filename=document.filename,
        relative_path=document.relative_path,
        document_metadata=document.document_metadata,
        chunk_metadata={"evidence_sweep": True, "whole_document": True},
        score=1.0,
    )


def _chunk_documents(documents: tuple, batch_size: int) -> list[tuple[int, tuple]]:
    batches: list[tuple[int, tuple]] = []
    for index in range(0, len(documents), batch_size):
        batches.append((len(batches), tuple(documents[index : index + batch_size])))
    return batches


async def sweep_current_pmp_corpus(
    session: AsyncSession,
    *,
    project: Project,
    previous_evidence_refs: list[str] | None = None,
) -> CorpusSweepResult:
    listing = await list_current_pmp_corpus_documents(
        session,
        project_id=project.id,
        max_documents=settings.pmp_sweep_max_documents,
    )
    trace_events: list[WorkflowTraceEvent] = []
    if listing.capped:
        trace_events.append(
            _trace(
                "evidence_sweep",
                "warning",
                (
                    f"Active corpus exceeds sweep cap ({settings.pmp_sweep_max_documents}); "
                    "only the first capped documents were swept."
                ),
                active_documents=len(listing.documents),
                cap=settings.pmp_sweep_max_documents,
            )
        )

    batches = _chunk_documents(
        listing.documents,
        CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS,
    )
    merged_pack = MobilisationEvidencePack()
    passages: list[SourcePassage] = []
    for batch_index, batch in batches:
        texts = [document.normalized_content for document in batch]
        refs = [_source_ref(_document_passage(document)) for document in batch]
        labels = [document.filename for document in batch]
        pack = extract_mobilisation_evidence_pack(texts, refs, labels)
        merged_pack = merge_evidence_packs(merged_pack, pack) if passages else pack
        passages.extend(_document_passage(document) for document in batch)
        trace_events.append(
            _trace(
                "evidence_sweep",
                "complete",
                f"Swept evidence batch {batch_index + 1} of {max(len(batches), 1)}.",
                batch_index=batch_index,
                batch_count=len(batch),
                active_document_names=[document.filename for document in batch],
                skipped_superseded=listing.skipped_superseded,
                skipped_revision_duplicates=listing.skipped_revision_duplicate,
            )
        )

    if not batches:
        trace_events.append(
            _trace(
                "evidence_sweep",
                "complete",
                "Active corpus is empty; no project evidence documents to sweep.",
                batch_index=0,
                batch_count=0,
                active_document_names=[],
                skipped_superseded=listing.skipped_superseded,
                skipped_revision_duplicates=listing.skipped_revision_duplicate,
            )
        )

    evidence_refs = tuple(merged_pack.evidence_refs)
    evidence_changed = compute_evidence_changed(
        previous_refs=list(previous_evidence_refs or []),
        current_refs=list(evidence_refs),
    )
    return CorpusSweepResult(
        passages=tuple(passages),
        merged_pack=merged_pack,
        evidence_refs=evidence_refs,
        listing=listing,
        evidence_changed=evidence_changed,
        trace_events=tuple(trace_events),
    )


def apply_sweep_downgrades(
    markdown: str,
    *,
    previous_evidence_refs: list[str],
    current_evidence_refs: list[str],
    current_source_texts: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    removed_paths = {
        evidence_ref_path(ref)
        for ref in previous_evidence_refs
        if evidence_ref_path(ref) not in {evidence_ref_path(r) for r in current_evidence_refs}
    }
    if not removed_paths:
        return markdown, {"downgraded": [], "conflicted": []}
    return apply_corpus_evidence_downgrades(
        markdown,
        removed_paths=removed_paths,
        current_source_texts=current_source_texts,
    )
