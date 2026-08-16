"""Addressable Markdown block mutations with stable identity and provenance."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Sequence

from pydantic import BaseModel, Field, model_validator


BlockType = Literal["paragraph", "list_item", "table_row"]
BlockOperationType = Literal[
    "ADD",
    "UPDATE",
    "DELETE",
    "MOVE",
    "DUPLICATE",
    "PROTECT",
    "UNPROTECT",
    "KEEP",
    "CONFIRM_DELETE",
]
BlockPlacement = Literal["before", "after"]
BlockSource = Literal["user", "ai", "import", "system"]

_MARKER_RE = re.compile(
    r"<!--\s*clerk:block\s+id=(?P<id>blk_[a-f0-9]{32})\s*-->",
    re.IGNORECASE,
)
_VISIBLE_MARKER_RE = re.compile(
    r"<!--\s*clerk:block\b[^>]*-->",
    re.IGNORECASE,
)
_VISIBLE_MARKER_LINE_RE = re.compile(
    rf"^[ \t]*{_VISIBLE_MARKER_RE.pattern}[ \t]*(?:\r?\n|$)",
    re.IGNORECASE | re.MULTILINE,
)
_VISIBLE_END_MARKER_RE = re.compile(
    rf" ?{_VISIBLE_MARKER_RE.pattern}(?=[ \t]*(?:\r?$))",
    re.IGNORECASE | re.MULTILINE,
)
_LIST_RE = re.compile(r"^(?P<indent>\s*)(?:[-*+]|\d+[.)])\s+\S")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")


class ArtefactBlockTarget(BaseModel):
    id: str | None = Field(default=None, pattern=r"^blk_[a-f0-9]{32}$")
    type: BlockType
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_address(self) -> "ArtefactBlockTarget":
        if self.id is None and (self.start is None or self.end is None):
            raise ValueError("target requires id or start/end")
        if self.start is not None and self.end is not None and self.start >= self.end:
            raise ValueError("target start must be before end")
        return self


class ArtefactBlockOperation(BaseModel):
    operation: BlockOperationType
    target: ArtefactBlockTarget
    content: str | None = Field(default=None, max_length=20_000)
    placement: BlockPlacement | None = None
    reference_id: str | None = Field(default=None, pattern=r"^blk_[a-f0-9]{32}$")

    @model_validator(mode="after")
    def validate_payload(self) -> "ArtefactBlockOperation":
        if self.operation in {"ADD", "UPDATE"} and not (self.content or "").strip():
            raise ValueError(f"{self.operation} requires content")
        if self.operation == "ADD" and self.placement is None:
            raise ValueError("ADD requires placement")
        if self.operation == "MOVE" and (
            self.reference_id is None or self.placement is None
        ):
            raise ValueError("MOVE requires reference_id and placement")
        if self.operation in {
            "PROTECT",
            "UNPROTECT",
            "KEEP",
            "CONFIRM_DELETE",
        } and self.target.id is None:
            raise ValueError(f"{self.operation} requires target.id")
        return self


class BlockProvenance(BaseModel):
    id: str
    type: BlockType
    created_by: BlockSource
    last_modified_by: BlockSource
    created_at: datetime
    updated_at: datetime
    source_refs: tuple[str, ...] = ()
    user_protected: bool = False
    status: Literal["active", "propose_delete", "conflict"] = "active"
    baseline_content_hash: str
    input_hash: str | None = None
    generation_version: str | None = None
    context_version: int | None = None
    source_version: str | None = None
    seed_version: str | None = None


@dataclass(frozen=True, slots=True)
class MarkdownBlock:
    id: str | None
    type: BlockType
    start: int
    end: int
    content: str
    marker_start: int | None = None
    marker_end: int | None = None


@dataclass(frozen=True, slots=True)
class BlockMutationResult:
    markdown: str
    metadata: dict[str, dict[str, Any]]
    changed_block_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IncrementalBlockProposal:
    block_id: str
    content: str | None
    input_hash: str


@dataclass(frozen=True, slots=True)
class IncrementalMergeResult:
    markdown: str
    metadata: dict[str, dict[str, Any]]
    updated: tuple[str, ...]
    preserved: tuple[str, ...]
    conflicts: tuple[str, ...]


def strip_block_markers(markdown: str) -> str:
    """Remove internal provenance syntax from presentation/export Markdown."""
    without_marker_lines = _VISIBLE_MARKER_LINE_RE.sub("", markdown)
    without_end_markers = _VISIBLE_END_MARKER_RE.sub("", without_marker_lines)
    return _VISIBLE_MARKER_RE.sub("", without_end_markers)


def detach_block_marker(value: str) -> tuple[str, str | None]:
    """Separate one block's visible Markdown from its opaque identity marker."""
    marker = _MARKER_RE.search(value)
    return _MARKER_RE.sub("", value), marker.group(0) if marker else None


def markdown_blocks(markdown: str) -> list[MarkdownBlock]:
    """Parse the first supported addressable units without a Markdown dependency."""
    lines = list(_lines_with_offsets(markdown))
    blocks: list[MarkdownBlock] = []
    pending_marker: tuple[str, int, int] | None = None
    paragraph_start: int | None = None
    paragraph_end: int | None = None
    in_fence = False

    def finish_paragraph() -> None:
        nonlocal paragraph_start, paragraph_end, pending_marker
        if paragraph_start is None or paragraph_end is None:
            return
        blocks.append(
            _block(
                markdown,
                "paragraph",
                paragraph_start,
                paragraph_end,
                pending_marker,
            )
        )
        paragraph_start = paragraph_end = None
        pending_marker = None

    for line_index, (line, start, content_end, line_end) in enumerate(lines):
        stripped = line.strip()
        marker = _MARKER_RE.search(stripped)
        if marker and marker.group(0) == stripped:
            finish_paragraph()
            pending_marker = (marker.group("id").lower(), start, line_end)
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            finish_paragraph()
            in_fence = not in_fence
            pending_marker = None
            continue
        if in_fence or not stripped:
            finish_paragraph()
            if not stripped and pending_marker is not None:
                # A marker may be separated from its block by one blank line.
                continue
            pending_marker = None
            continue
        visible_line = _MARKER_RE.sub("", line).rstrip()
        visible_stripped = visible_line.strip()
        embedded_marker = (
            (marker.group("id").lower(), start, content_end)
            if marker is not None
            else pending_marker
        )
        if _is_table_row(visible_stripped):
            finish_paragraph()
            next_visible = (
                _MARKER_RE.sub("", lines[line_index + 1][0]).strip()
                if line_index + 1 < len(lines)
                else ""
            )
            is_header = bool(_TABLE_SEPARATOR_RE.fullmatch(next_visible))
            if not _TABLE_SEPARATOR_RE.fullmatch(visible_stripped) and not is_header:
                blocks.append(
                    _block(
                        markdown,
                        "table_row",
                        start,
                        content_end,
                        embedded_marker,
                        content=visible_line,
                        embedded=marker is not None,
                    )
                )
            pending_marker = None
            continue
        if _LIST_RE.match(visible_line):
            finish_paragraph()
            blocks.append(
                _block(
                    markdown,
                    "list_item",
                    start,
                    content_end,
                    embedded_marker,
                    content=visible_line,
                    embedded=marker is not None,
                )
            )
            pending_marker = None
            continue
        if stripped.startswith("#") or stripped.startswith(">") or stripped == "---":
            finish_paragraph()
            pending_marker = None
            continue
        paragraph_start = start if paragraph_start is None else paragraph_start
        paragraph_end = content_end
    finish_paragraph()
    return blocks


def apply_block_operations(
    markdown: str,
    operations: Sequence[ArtefactBlockOperation],
    *,
    existing_metadata: dict[str, Any] | None,
    actor_source: BlockSource,
    now: datetime | None = None,
) -> BlockMutationResult:
    if not operations:
        return BlockMutationResult(markdown, dict(existing_metadata or {}), ())
    current = markdown
    metadata = {
        key: dict(value)
        for key, value in (existing_metadata or {}).items()
        if isinstance(key, str) and isinstance(value, dict)
    }
    changed: list[str] = []
    timestamp = now or datetime.now(UTC)

    for operation in operations:
        blocks = markdown_blocks(current)
        target = _resolve_target(blocks, operation.target)
        if target.type != operation.target.type:
            raise ValueError("target block type does not match the addressed Markdown")

        if operation.operation in {"PROTECT", "UNPROTECT"}:
            block_id = target.id
            if block_id is None:
                raise ValueError(f"{operation.operation} requires target.id")
            existing = metadata.get(block_id)
            provenance = _updated_provenance(
                existing,
                block_id=block_id,
                block_type=target.type,
                content=target.content,
                actor_source=actor_source,
                timestamp=timestamp,
            )
            # Protection is metadata-only: keep the existing baseline hash.
            if existing and isinstance(existing.get("baseline_content_hash"), str):
                provenance["baseline_content_hash"] = existing["baseline_content_hash"]
            provenance["user_protected"] = operation.operation == "PROTECT"
            metadata[block_id] = provenance
            changed.append(block_id)
            continue

        if operation.operation == "KEEP":
            block_id = target.id
            if block_id is None:
                raise ValueError("KEEP requires target.id")
            existing = metadata.get(block_id)
            provenance = _updated_provenance(
                existing,
                block_id=block_id,
                block_type=target.type,
                content=target.content,
                actor_source=actor_source,
                timestamp=timestamp,
            )
            provenance["status"] = "active"
            provenance["baseline_content_hash"] = _content_hash(target.content)
            if existing:
                for key in (
                    "input_hash",
                    "generation_version",
                    "context_version",
                    "source_version",
                    "seed_version",
                    "user_protected",
                ):
                    if key in existing:
                        provenance[key] = existing[key]
            metadata[block_id] = provenance
            changed.append(block_id)
            continue

        if operation.operation == "CONFIRM_DELETE":
            block_id = target.id
            if block_id is None:
                raise ValueError("CONFIRM_DELETE requires target.id")
            status = (metadata.get(block_id) or {}).get("status")
            if status != "propose_delete":
                raise ValueError("CONFIRM_DELETE requires a propose_delete block")
            delete_start = _address_start(target)
            current = _delete_with_spacing(current, delete_start, target.end)
            metadata.pop(block_id, None)
            changed.append(block_id)
            continue

        if (
            operation.operation in {"UPDATE", "DELETE"}
            and actor_source == "ai"
            and target.id
            and bool(metadata.get(target.id, {}).get("user_protected"))
        ):
            raise ValueError("protected block rejects AI overwrite and deletion")

        if operation.operation == "UPDATE":
            block_id = target.id or _new_block_id()
            replacement = _marked(
                block_id,
                _normalise_content(operation.content or ""),
                target.type,
            )
            replace_start = _address_start(target)
            current = _replace(current, replace_start, target.end, replacement)
            metadata[block_id] = _updated_provenance(
                metadata.get(block_id),
                block_id=block_id,
                block_type=target.type,
                content=operation.content or "",
                actor_source=actor_source,
                timestamp=timestamp,
            )
            changed.append(block_id)
            continue

        if operation.operation == "DELETE":
            block_id = target.id
            delete_start = _address_start(target)
            current = _delete_with_spacing(current, delete_start, target.end)
            if block_id:
                metadata.pop(block_id, None)
                changed.append(block_id)
            continue

        if operation.operation == "DUPLICATE":
            block_id = _new_block_id()
            insertion = _sibling_separator(target.type) + _marked(
                block_id, target.content, target.type
            )
            current = _replace(current, target.end, target.end, insertion)
            metadata[block_id] = _updated_provenance(
                None,
                block_id=block_id,
                block_type=target.type,
                content=target.content,
                actor_source=actor_source,
                timestamp=timestamp,
            )
            changed.append(block_id)
            continue

        if operation.operation == "ADD":
            block_id = _new_block_id()
            content = _normalise_content(operation.content or "")
            insertion = _marked(block_id, content, target.type)
            gap = _sibling_separator(target.type)
            if operation.placement == "after":
                current = _replace(current, target.end, target.end, gap + insertion)
            else:
                offset = _address_start(target)
                current = _replace(current, offset, offset, insertion + gap)
            metadata[block_id] = _updated_provenance(
                None,
                block_id=block_id,
                block_type=target.type,
                content=content,
                actor_source=actor_source,
                timestamp=timestamp,
            )
            changed.append(block_id)
            continue

        reference = _resolve_id(blocks, operation.reference_id or "")
        if reference.id == target.id:
            continue
        extracted_start = _address_start(target)
        extracted = current[extracted_start : target.end]
        without = _delete_with_spacing(current, extracted_start, target.end)
        remaining = markdown_blocks(without)
        reference_after_delete = _resolve_id(remaining, reference.id or "")
        offset = (
            _address_start(reference_after_delete)
            if operation.placement == "before"
            else reference_after_delete.end
        )
        insertion = (
            f"{extracted.rstrip()}\n"
            if operation.placement == "before"
            else f"\n{extracted.lstrip()}"
        )
        current = _replace(without, offset, offset, insertion)
        if target.id:
            existing = metadata.get(target.id)
            metadata[target.id] = _updated_provenance(
                existing,
                block_id=target.id,
                block_type=target.type,
                content=target.content,
                actor_source=actor_source,
                timestamp=timestamp,
            )
            if existing and isinstance(existing.get("baseline_content_hash"), str):
                metadata[target.id]["baseline_content_hash"] = existing[
                    "baseline_content_hash"
                ]
            if existing:
                metadata[target.id]["user_protected"] = bool(
                    existing.get("user_protected", False)
                )
            changed.append(target.id)

    return BlockMutationResult(current, metadata, tuple(dict.fromkeys(changed)))


def materialize_block_identity(
    markdown: str,
    *,
    actor_source: BlockSource,
    generation_input_hash: str | None = None,
    generation_version: str | None = None,
    now: datetime | None = None,
) -> BlockMutationResult:
    """Stamp generated blocks once so later text movement cannot change identity."""
    current = markdown
    metadata: dict[str, dict[str, Any]] = {}
    changed: list[str] = []
    timestamp = now or datetime.now(UTC)
    blocks = markdown_blocks(markdown)
    occurrences: dict[str, int] = {}
    assignments: list[tuple[MarkdownBlock, str]] = []
    for block in blocks:
        if block.id is not None:
            continue
        semantic_key = "\0".join(
            (
                _section_heading_at(markdown, block.start) or "document",
                block.type,
                block.content.strip(),
            )
        )
        occurrence = occurrences.get(semantic_key, 0) + 1
        occurrences[semantic_key] = occurrence
        block_id = _stable_generated_block_id(semantic_key, occurrence)
        assignments.append((block, block_id))

    for block, block_id in reversed(assignments):
        current = _replace(
            current,
            block.start,
            block.end,
            _marked(block_id, block.content, block.type),
        )
        provenance = _updated_provenance(
            None,
            block_id=block_id,
            block_type=block.type,
            content=block.content,
            actor_source=actor_source,
            timestamp=timestamp,
        )
        provenance["input_hash"] = (
            _generated_block_input_hash(generation_input_hash, block)
            if generation_input_hash
            else None
        )
        provenance["generation_version"] = generation_version
        metadata[block_id] = provenance
        changed.append(block_id)
    return BlockMutationResult(
        markdown=current,
        metadata=metadata,
        changed_block_ids=tuple(reversed(changed)),
    )


def block_input_hash(
    *,
    context_version: int,
    source_version: str,
    seed_version: str,
    inputs: dict[str, Any],
) -> str:
    import json

    payload = {
        "context_version": context_version,
        "source_version": source_version,
        "seed_version": seed_version,
        "inputs": inputs,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def merge_incremental_block_updates(
    markdown: str,
    metadata: dict[str, Any],
    proposals: Sequence[IncrementalBlockProposal],
    *,
    now: datetime | None = None,
) -> IncrementalMergeResult:
    """Update untouched AI blocks; preserve or flag human-controlled content."""
    current = markdown
    copied = {
        key: dict(value) for key, value in metadata.items() if isinstance(value, dict)
    }
    updated: list[str] = []
    preserved: list[str] = []
    conflicts: list[str] = []
    timestamp = now or datetime.now(UTC)

    for proposal in proposals:
        raw = copied.get(proposal.block_id)
        if raw is None:
            conflicts.append(proposal.block_id)
            continue
        provenance = BlockProvenance.model_validate(raw)
        if provenance.input_hash == proposal.input_hash:
            preserved.append(proposal.block_id)
            continue
        block = _resolve_id(markdown_blocks(current), proposal.block_id)
        current_hash = _content_hash(block.content)
        human_controlled = (
            provenance.user_protected
            or provenance.created_by == "user"
            or provenance.last_modified_by == "user"
            or current_hash != provenance.baseline_content_hash
        )
        if proposal.content is None:
            if human_controlled:
                copied[proposal.block_id]["status"] = "propose_delete"
                preserved.append(proposal.block_id)
            else:
                current = _delete_with_spacing(
                    current, _address_start(block), block.end
                )
                copied.pop(proposal.block_id, None)
                updated.append(proposal.block_id)
            continue
        if human_controlled:
            copied[proposal.block_id]["status"] = "conflict"
            conflicts.append(proposal.block_id)
            continue
        replacement = _marked(
            proposal.block_id,
            _normalise_content(proposal.content),
            block.type,
        )
        current = _replace(
            current,
            _address_start(block),
            block.end,
            replacement,
        )
        copied[proposal.block_id].update(
            {
                "updated_at": timestamp.isoformat(),
                "baseline_content_hash": _content_hash(proposal.content),
                "input_hash": proposal.input_hash,
                "status": "active",
            }
        )
        updated.append(proposal.block_id)

    return IncrementalMergeResult(
        current,
        copied,
        tuple(updated),
        tuple(preserved),
        tuple(conflicts),
    )


def reconcile_regenerated_blocks(
    baseline_markdown: str,
    baseline_metadata: dict[str, Any],
    regenerated_markdown: str,
    *,
    generation_input_hash: str,
    generation_version: str,
    now: datetime | None = None,
) -> IncrementalMergeResult:
    """Adopt regenerated AI blocks while retaining human-controlled baseline blocks.

    A generator is expected to carry stable marker IDs forward. New unmarked
    blocks receive IDs here. If a human-controlled block is omitted, it is
    restored beside its closest surviving neighbour and marked propose_delete.
    """
    timestamp = now or datetime.now(UTC)
    baseline_blocks = markdown_blocks(baseline_markdown)
    baseline_by_id = {block.id: block for block in baseline_blocks if block.id}
    generated = materialize_block_identity(
        regenerated_markdown,
        actor_source="ai",
        generation_input_hash=generation_input_hash,
        generation_version=generation_version,
        now=timestamp,
    )
    current = generated.markdown
    metadata = dict(generated.metadata)
    updated: list[str] = list(generated.changed_block_ids)
    preserved: list[str] = []
    conflicts: list[str] = []

    for block in markdown_blocks(current):
        if block.id is None:
            continue
        existing = baseline_metadata.get(block.id)
        provenance = _updated_provenance(
            existing if isinstance(existing, dict) else None,
            block_id=block.id,
            block_type=block.type,
            content=block.content,
            actor_source="ai",
            timestamp=timestamp,
        )
        provenance["input_hash"] = _generated_block_input_hash(
            generation_input_hash, block
        )
        provenance["generation_version"] = generation_version
        metadata[block.id] = provenance
        baseline_block = baseline_by_id.get(block.id)
        if baseline_block is not None and baseline_block.content != block.content:
            updated.append(block.id)

    for index, baseline_block in enumerate(baseline_blocks):
        block_id = baseline_block.id
        if block_id is None:
            continue
        raw = baseline_metadata.get(block_id)
        if not isinstance(raw, dict):
            continue
        human_controlled = (
            bool(raw.get("user_protected"))
            or raw.get("created_by") == "user"
            or raw.get("last_modified_by") == "user"
            or _content_hash(baseline_block.content) != raw.get("baseline_content_hash")
        )
        if not human_controlled:
            continue

        proposed = next(
            (block for block in markdown_blocks(current) if block.id == block_id),
            None,
        )
        status: Literal["active", "propose_delete", "conflict"] = "active"
        if proposed is None:
            status = "propose_delete"
            marked = _marked(block_id, baseline_block.content, baseline_block.type)
            current = _insert_near_baseline_neighbour(
                current,
                baseline_markdown,
                baseline_blocks,
                index,
                marked,
            )
        elif proposed.content != baseline_block.content:
            status = "conflict"
            current = _replace(
                current,
                _address_start(proposed),
                proposed.end,
                _marked(block_id, baseline_block.content, baseline_block.type),
            )
            conflicts.append(block_id)

        retained = dict(raw)
        retained["status"] = status
        metadata[block_id] = retained
        preserved.append(block_id)

    return IncrementalMergeResult(
        markdown=current,
        metadata=metadata,
        updated=tuple(dict.fromkeys(updated)),
        preserved=tuple(dict.fromkeys(preserved)),
        conflicts=tuple(dict.fromkeys(conflicts)),
    )


def _lines_with_offsets(markdown: str):
    offset = 0
    for line_with_end in markdown.splitlines(keepends=True):
        line = line_with_end.rstrip("\r\n")
        content_end = offset + len(line)
        line_end = offset + len(line_with_end)
        yield line, offset, content_end, line_end
        offset = line_end
    if markdown and offset < len(markdown):
        yield markdown[offset:], offset, len(markdown), len(markdown)


def _block(
    markdown: str,
    block_type: BlockType,
    start: int,
    end: int,
    marker: tuple[str, int, int] | None,
    *,
    content: str | None = None,
    embedded: bool = False,
) -> MarkdownBlock:
    return MarkdownBlock(
        id=marker[0] if marker else None,
        type=block_type,
        start=start,
        end=end,
        content=content if content is not None else markdown[start:end],
        marker_start=marker[1] if marker and not embedded else None,
        marker_end=marker[2] if marker and not embedded else None,
    )


def _is_table_row(stripped: str) -> bool:
    return stripped.count("|") >= 2 and (
        stripped.startswith("|") or stripped.endswith("|")
    )


def _resolve_target(
    blocks: Sequence[MarkdownBlock], target: ArtefactBlockTarget
) -> MarkdownBlock:
    if target.id is not None:
        return _resolve_id(blocks, target.id)
    if target.start is None or target.end is None:
        raise ValueError("target range is stale or is not an addressable Markdown block")
    for block in blocks:
        if block.start == target.start and block.end == target.end:
            return block
    # Clients often address the visible row/paragraph and omit an embedded
    # trailing provenance marker that still belongs to the same block.
    for block in blocks:
        if block.start == target.start and target.start < target.end <= block.end:
            return block
    raise ValueError("target range is stale or is not an addressable Markdown block")


def _resolve_id(blocks: Sequence[MarkdownBlock], block_id: str) -> MarkdownBlock:
    for block in blocks:
        if block.id == block_id:
            return block
    raise ValueError(f"block {block_id!r} was not found")


def _address_start(block: MarkdownBlock) -> int:
    return block.marker_start if block.marker_start is not None else block.start


def _new_block_id() -> str:
    return f"blk_{uuid.uuid4().hex}"


def _stable_generated_block_id(semantic_key: str, occurrence: int) -> str:
    digest = hashlib.sha256(f"{semantic_key}\0{occurrence}".encode()).hexdigest()
    return f"blk_{digest[:32]}"


def _marked(block_id: str, content: str, block_type: BlockType) -> str:
    marker = f"<!-- clerk:block id={block_id} -->"
    if block_type == "table_row":
        # Keep the visible row byte-identical. Presentation boundaries mask or
        # strip the marker before GFM parsing, so the comment stays metadata
        # instead of becoming part of the final cell's canonical content.
        return f"{content.rstrip()}{marker}"
    if block_type == "list_item":
        # Inline markers keep a list contiguous while preserving its visible
        # Markdown prefix for exports and range-based clients.
        return f"{content.rstrip()} {marker}"
    return f"{marker}\n{content}"


def _normalise_content(content: str) -> str:
    return content.strip("\r\n")


def _sibling_separator(block_type: BlockType) -> str:
    # Paragraphs need a blank line or CommonMark merges them into one block.
    return "\n\n" if block_type == "paragraph" else "\n"


def _replace(source: str, start: int, end: int, replacement: str) -> str:
    return source[:start] + replacement + source[end:]


def _delete_with_spacing(source: str, start: int, end: int) -> str:
    # Block ranges end at content (not the line terminator). Consume one
    # trailing newline so table/list deletes do not leave a blank line that
    # splits a GFM table or CommonMark list.
    if end < len(source) and source[end] == "\n":
        end += 1
    elif start > 0 and source[start - 1] == "\n":
        start -= 1
    result = _replace(source, start, end, "")
    return re.sub(r"\n{3,}", "\n\n", result)


def _generated_block_input_hash(
    generation_input_hash: str,
    block: MarkdownBlock,
) -> str:
    return _content_hash(
        f"{generation_input_hash}:{block.type}:{block.content.strip()}"
    )


def _insert_near_baseline_neighbour(
    current: str,
    baseline: str,
    baseline_blocks: Sequence[MarkdownBlock],
    index: int,
    marked: str,
) -> str:
    target_type = baseline_blocks[index].type
    for positions, placement in (
        (range(index - 1, -1, -1), "after"),
        (range(index + 1, len(baseline_blocks)), "before"),
    ):
        for position in positions:
            neighbour = baseline_blocks[position]
            if neighbour.type != target_type or neighbour.id is None:
                continue
            live = next(
                (
                    block
                    for block in markdown_blocks(current)
                    if block.id == neighbour.id
                ),
                None,
            )
            if live is None:
                continue
            if placement == "after":
                return _replace(current, live.end, live.end, f"\n{marked}")
            offset = _address_start(live)
            return _replace(current, offset, offset, f"{marked}\n")

    heading = _section_heading_at(baseline, baseline_blocks[index].start)
    offset = _section_end(current, heading) if heading else len(current)
    prefix = "" if offset == 0 or current[:offset].endswith("\n\n") else "\n\n"
    suffix = "" if offset == len(current) or current[offset:].startswith("\n") else "\n"
    return _replace(current, offset, offset, f"{prefix}{marked}{suffix}")


def _section_heading_at(markdown: str, offset: int) -> str | None:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", markdown[:offset]))
    return matches[-1].group(1).strip() if matches else None


def _section_end(markdown: str, heading: str) -> int:
    headings = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", markdown))
    for index, match in enumerate(headings):
        if match.group(1).strip().casefold() != heading.casefold():
            continue
        return (
            headings[index + 1].start() if index + 1 < len(headings) else len(markdown)
        )
    return len(markdown)


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.strip().encode()).hexdigest()


def _updated_provenance(
    existing: dict[str, Any] | None,
    *,
    block_id: str,
    block_type: BlockType,
    content: str,
    actor_source: BlockSource,
    timestamp: datetime,
) -> dict[str, Any]:
    created_at = (
        existing.get("created_at")
        if existing and isinstance(existing.get("created_at"), str)
        else timestamp.isoformat()
    )
    created_by = (
        existing.get("created_by")
        if existing and existing.get("created_by") in {"user", "ai", "import", "system"}
        else actor_source
    )
    return BlockProvenance(
        id=block_id,
        type=block_type,
        created_by=created_by,
        last_modified_by=actor_source,
        created_at=created_at,
        updated_at=timestamp,
        source_refs=tuple(existing.get("source_refs", ())) if existing else (),
        user_protected=bool(existing.get("user_protected", False))
        if existing
        else False,
        status="active",
        baseline_content_hash=_content_hash(content),
        input_hash=existing.get("input_hash") if existing else None,
        generation_version=existing.get("generation_version") if existing else None,
        context_version=existing.get("context_version") if existing else None,
        source_version=existing.get("source_version") if existing else None,
        seed_version=existing.get("seed_version") if existing else None,
    ).model_dump(mode="json")
