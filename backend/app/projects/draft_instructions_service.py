"""Apply a batch of anchored, plain-English instructions to a generated draft.

Anchors are offsets into the *normalized* draft markdown (design decision D3).
Every anchor is verified before a single token is spent; instructions are then
grouped by `##` section and each touched section is revised by one bounded LLM
call. Untouched sections come back byte-identical.
"""

from __future__ import annotations

import asyncio
import difflib
import re
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.grounding.validator import normalize_match_text
from app.logging import get_logger
from app.projects.artefact_adapters import revise_workflow_artefact
from app.sitewise.markdown_sections import (
    MarkdownSection,
    normalize_draft_markdown,
    split_sections,
)
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.draft_instructions import SliceInstruction, run_slice_revision

logger = get_logger(__name__)

_FENCE_RE = re.compile(r"^(```|~~~)")
_PROVENANCE_QUOTE_LIMIT = 500


def _failure_reason(error: BaseException) -> str:
    """A reason the user can act on, for the tray."""
    if isinstance(error, WorkflowValidationError):
        return str(error)
    return (
        f"the model could not revise this section ({type(error).__name__}). "
        "Try again, or narrow the instruction."
    )


@dataclass(frozen=True)
class InstructionInput:
    anchor_start: int
    anchor_end: int
    quoted_text: str
    instruction: str


@dataclass(frozen=True)
class FailedInstruction:
    index: int
    reason: str


@dataclass(frozen=True)
class ApplyResult:
    revision: DraftArtifact
    applied_count: int
    failed: list[FailedInstruction]


class StaleAnchorError(ValueError):
    """An anchor no longer addresses the text the user selected."""


class AllInstructionsFailedError(RuntimeError):
    """Every instruction failed, so no revision was published."""

    def __init__(self, failed: list[FailedInstruction]) -> None:
        super().__init__("; ".join(f"{item.index}: {item.reason}" for item in failed))
        self.failed = failed


def _split_blocks(text: str) -> list[tuple[str, int, int]]:
    """Blank-line-delimited blocks as (text, start, end), fences kept whole."""
    blocks: list[tuple[str, int, int]] = []
    offset = 0
    in_fence = False
    start: int | None = None
    current: list[str] = []

    for line in text.splitlines(keepends=True):
        is_fence = bool(_FENCE_RE.match(line))
        if not line.strip() and not in_fence:
            if current and start is not None:
                blocks.append(("".join(current), start, offset))
            current = []
            start = None
        else:
            if start is None:
                start = offset
            current.append(line)
            if is_fence:
                in_fence = not in_fence
        offset += len(line)

    if current and start is not None:
        blocks.append(("".join(current), start, offset))
    return blocks


def changed_block_ranges(original: str, revised: str, *, offset: int) -> list[dict[str, int]]:
    """Offsets of blocks in `revised` that differ from `original`, shifted by `offset`."""
    old_blocks = _split_blocks(original)
    new_blocks = _split_blocks(revised)
    matcher = difflib.SequenceMatcher(
        a=[block[0] for block in old_blocks],
        b=[block[0] for block in new_blocks],
        autojunk=False,
    )
    ranges: list[dict[str, int]] = []
    for tag, _, _, j1, j2 in matcher.get_opcodes():
        if tag in {"replace", "insert"}:
            for _, start, end in new_blocks[j1:j2]:
                ranges.append({"start": start + offset, "end": end + offset})
    return ranges


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else f"{text}\n"


def _verify_anchors(source: str, instructions: list[InstructionInput]) -> None:
    for index, item in enumerate(instructions):
        if not 0 <= item.anchor_start < item.anchor_end <= len(source):
            raise StaleAnchorError(
                f"Instruction {index + 1} points outside the draft "
                f"[{item.anchor_start}, {item.anchor_end}) — reselect the text."
            )
        sliced = source[item.anchor_start : item.anchor_end]
        if normalize_match_text(sliced) != normalize_match_text(item.quoted_text):
            raise StaleAnchorError(
                f"Instruction {index + 1} no longer matches the draft text it was "
                "attached to — the draft has changed since it was queued."
            )


def _group_by_section(
    source: str, instructions: list[InstructionInput]
) -> tuple[list[MarkdownSection], dict[int, list[int]], list[FailedInstruction]]:
    """Map each instruction onto the level-2 section that contains its anchor.

    Level-1 sections span the whole document and would swallow every anchor, so
    only `##` sections are addressable — matching the slice agent's heading
    contract. Grouping is keyed on the section's index, which duplicate headings
    cannot collide on.
    """
    sections = [section for section in split_sections(source) if section.level == 2]
    grouped: dict[int, list[int]] = {}
    failed: list[FailedInstruction] = []

    for index, item in enumerate(instructions):
        position = next(
            (
                number
                for number, section in enumerate(sections)
                if section.start <= item.anchor_start < section.end
            ),
            None,
        )
        if position is None:
            failed.append(
                FailedInstruction(index=index, reason="selection is outside any section")
            )
            continue
        grouped.setdefault(position, []).append(index)

    return sections, grouped, failed


async def apply_draft_instructions(
    session: AsyncSession,
    *,
    project: Project,
    draft: DraftArtifact,
    expected_base_version: int,
    author_user_id: uuid.UUID,
    instructions: list[InstructionInput],
    chat_model: str | None = None,
) -> ApplyResult:
    source = normalize_draft_markdown(draft.content_markdown)

    _verify_anchors(source, instructions)
    sections, grouped, failed = _group_by_section(source, instructions)
    if not grouped:
        raise AllInstructionsFailedError(failed)

    # Release the read transaction before the model calls.
    #
    # `get_db` opens one session per request and commits it after the handler
    # returns. Loading the project and draft starts a transaction, and the slice
    # calls below take 1-3 minutes — so without this the connection sits
    # idle-in-transaction for the whole batch and Postgres (behind the Supabase
    # pooler) terminates it. The failure then surfaces on `session.commit()`
    # during dependency teardown, outside every exception handler, as a bare 500
    # with no body. Nothing has been written yet, so this commit is a no-op on
    # data; `expire_on_commit=False` keeps `project` and `draft` usable, and
    # `revise_workflow_artefact` opens a fresh transaction for the writes.
    await session.commit()

    positions = list(grouped)
    results = await asyncio.gather(
        *(
            run_slice_revision(
                section_markdown=sections[position].content,
                instructions=[
                    SliceInstruction(
                        quoted_text=instructions[index].quoted_text,
                        instruction=instructions[index].instruction,
                    )
                    for index in grouped[position]
                ],
                project_title=project.title,
                chat_model=chat_model,
            )
            for position in positions
        ),
        return_exceptions=True,
    )

    applied: list[tuple[int, str]] = []
    for position, result in zip(positions, results, strict=True):
        if isinstance(result, BaseException):
            if isinstance(result, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                raise result
            # One section's slice blowing up must not lose the sections that
            # succeeded. A model timeout or a malformed structured response is
            # reported against its own instructions, exactly like a validation
            # failure, and the rest of the batch still publishes.
            if not isinstance(result, WorkflowValidationError):
                logger.exception(
                    "draft_instruction_slice_error",
                    project_id=str(project.id),
                    draft_id=str(draft.id),
                    section_id=sections[position].section_id,
                    exc_info=result,
                )
            failed.extend(
                FailedInstruction(index=index, reason=_failure_reason(result))
                for index in grouped[position]
            )
            continue
        applied.append((position, result))

    if not applied:
        raise AllInstructionsFailedError(sorted(failed, key=lambda item: item.index))

    assembled = source
    for position, revised in sorted(applied, key=lambda pair: sections[pair[0]].start, reverse=True):
        section = sections[position]
        assembled = (
            assembled[: section.start]
            + _ensure_trailing_newline(revised)
            + assembled[section.end :]
        )

    # Final offsets are computed from the splice arithmetic, not by re-parsing
    # the assembled markdown and matching by index. Re-parsing assumes the
    # revised text yields exactly the same section count and order; a single
    # stray ``` fence in one revision flips `split_sections`'s fence state and
    # swallows every heading after it, which would silently mis-target the
    # highlights or raise IndexError.
    changed_ranges: list[dict[str, int]] = []
    shift = 0
    for position, revised in sorted(applied, key=lambda pair: sections[pair[0]].start):
        section = sections[position]
        replacement = _ensure_trailing_newline(revised)
        changed_ranges.extend(
            changed_block_ranges(
                section.content, replacement, offset=section.start + shift
            )
        )
        shift += len(replacement) - (section.end - section.start)

    revision = await revise_workflow_artefact(
        session,
        project=project,
        draft=draft,
        expected_base_version=expected_base_version,
        author_user_id=author_user_id,
        content_markdown=assembled,
        actor_source="agent_instruction",
    )

    applied_indices = sorted(index for position, _ in applied for index in grouped[position])
    applied_records = [
        {
            "section_id": sections[position].section_id,
            "anchor": {
                "start": instructions[index].anchor_start,
                "end": instructions[index].anchor_end,
            },
            "quoted_text": instructions[index].quoted_text[:_PROVENANCE_QUOTE_LIMIT],
            "instruction": instructions[index].instruction,
        }
        for position, _ in applied
        for index in grouped[position]
    ]
    revision.provenance_metadata = {
        **(revision.provenance_metadata or {}),
        "applied_instructions": applied_records,
        "changed_ranges": changed_ranges,
        "sections_changed": [sections[position].heading for position, _ in applied],
    }
    await session.flush()
    # ``updated_at`` is generated by Postgres on UPDATE and SQLAlchemy expires it
    # during the flush above.  FastAPI/Pydantic serializes the returned ORM row
    # synchronously, so leaving that attribute expired triggers an implicit async
    # load and raises MissingGreenlet while the endpoint builds its response.
    await session.refresh(revision)

    return ApplyResult(
        revision=revision,
        applied_count=len(applied_indices),
        failed=sorted(failed, key=lambda item: item.index),
    )
