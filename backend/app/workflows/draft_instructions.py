"""Bounded LLM revision of a single draft section against user instructions."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.assistant.pmp_models import resolve_pmp_model
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.workflows.create_pmp import WorkflowValidationError

_INSTRUCTIONS_PATH = Path(__file__).with_name("draft_instructions_instructions.md")

_NUMERIC_RE = re.compile(r"\d[\d,.]*")
_DECISION_FENCE_RE = re.compile(r"```pmp-decision\n.*?\n```", re.DOTALL)

_MIN_LENGTH_RATIO = 0.5
_MAX_LENGTH_RATIO = 2.5

_HARD_CONSTRAINTS = (
    "Return the COMPLETE revised section, including its ## heading line unchanged.",
    "Do NOT change the ## heading line in any way.",
    "Do NOT alter, move, or remove any ```pmp-decision fenced block. "
    "Reproduce each one byte-for-byte.",
    "Do NOT introduce any number, date, quantity, percentage or currency amount "
    "that does not already appear in the section above or in the requested changes. "
    "You are not the calculator.",
    "Do NOT add new ## headings.",
    "Change only what the requested changes ask for. "
    "Leave every other sentence byte-identical.",
)


def _load_agent_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


class SliceInstruction(BaseModel):
    quoted_text: str = Field(min_length=1, max_length=4000)
    instruction: str = Field(min_length=1, max_length=1000)


class DraftInstructionSliceOutput(BaseModel):
    revised_markdown: str = Field(min_length=1)


draft_instruction_agent = Agent(
    f"openai-responses:{settings.pmp_model}",
    output_type=DraftInstructionSliceOutput,
    instructions=_load_agent_instructions(),
    defer_model_check=True,
)


def build_slice_prompt(
    *,
    section_markdown: str,
    instructions: list[SliceInstruction],
    project_title: str,
    validation_feedback: str | None = None,
) -> str:
    """Assemble the slice prompt. No doctrine, no seed, no retrieval — cheap and fast."""
    requested = "\n".join(
        f'{index}. Regarding this passage:\n   """{item.quoted_text}"""\n'
        f"   Requested change: {item.instruction}"
        for index, item in enumerate(instructions, start=1)
    )
    parts = [
        f"Project: {project_title}",
        "You are revising ONE section of an existing construction project document.",
        f"--- SECTION START ---\n{section_markdown}\n--- SECTION END ---",
        f"Requested changes:\n{requested}",
        "\n".join(_HARD_CONSTRAINTS),
    ]
    if validation_feedback:
        parts.append(
            "REVISION REQUIRED — your previous output failed validation:\n"
            f"{validation_feedback}\n"
            "Regenerate the section fixing every issue."
        )
    return "\n\n".join(parts)


def _numeric_tokens(text: str) -> set[str]:
    return {
        token
        for token in (match.group(0).rstrip(".,") for match in _NUMERIC_RE.finditer(text))
        if token
    }


def validate_slice_output(
    original: str,
    revised: str,
    *,
    instructions: list[SliceInstruction],
) -> None:
    """Raise WorkflowValidationError if the revision broke a document contract."""
    issues: list[str] = []

    if revised.split("\n", 1)[0] != original.split("\n", 1)[0]:
        issues.append("heading line was modified")

    if "\n## " in revised:
        issues.append("revision added a new ## heading")

    if _DECISION_FENCE_RE.findall(revised) != _DECISION_FENCE_RE.findall(original):
        issues.append("pmp-decision block was altered or removed")

    instruction_text = " ".join(
        f"{item.quoted_text} {item.instruction}" for item in instructions
    )
    allowed = _numeric_tokens(original) | _numeric_tokens(instruction_text)
    for token in sorted(_numeric_tokens(revised) - allowed):
        issues.append(
            f"revision introduced number {token!r} not present in the source or instructions"
        )

    if len(revised) < len(original) * _MIN_LENGTH_RATIO:
        issues.append("revision dropped more than half the section")

    if len(revised) > len(original) * _MAX_LENGTH_RATIO:
        issues.append("revision more than doubled the section")

    if issues:
        joined = "; ".join(issues)
        raise WorkflowValidationError(f"Draft instruction slice validation failed: {joined}")


async def run_slice_revision(
    *,
    section_markdown: str,
    instructions: list[SliceInstruction],
    project_title: str,
    chat_model: str | None = None,
    max_attempts: int = 3,
) -> str:
    """Revise one section. Returns revised markdown. Raises WorkflowValidationError."""
    resolved_model = chat_model.strip() if chat_model else resolve_pmp_model().execution_id
    validation_feedback: str | None = None

    for attempt in range(max_attempts):
        prompt = build_slice_prompt(
            section_markdown=section_markdown,
            instructions=instructions,
            project_title=project_title,
            validation_feedback=validation_feedback,
        )
        result = await run_agent_with_retry(
            draft_instruction_agent, prompt, model=resolved_model
        )
        revised = result.output.revised_markdown
        try:
            validate_slice_output(section_markdown, revised, instructions=instructions)
        except WorkflowValidationError as exc:
            if attempt >= max_attempts - 1:
                raise
            validation_feedback = str(exc)
            continue
        return revised

    raise WorkflowValidationError("Draft instruction slice produced no valid revision")
