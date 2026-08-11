"""Bounded LLM revision of a single draft section against user instructions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.assistant.pmp_models import resolve_pmp_model
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.schemas.projects import ProjectProfileView
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
    "that does not already appear in the section above, the project profile, "
    "or the requested changes. "
    "You are not the calculator.",
    "When a requested change needs a project fact (address, client, state, "
    "classification, scale, etc.), use the PROJECT PROFILE values below. "
    "Do not invent placeholders such as 'to be confirmed' for facts the "
    "profile already supplies.",
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


def format_project_profile(profile: ProjectProfileView | None) -> str:
    """Render profile facts for the slice prompt. Empty when nothing is set."""
    if profile is None:
        return ""
    payload = profile.model_dump(
        mode="json",
        exclude={"project_id", "profile_revision"},
        exclude_none=True,
    )
    lines: list[str] = []
    for key, value in payload.items():
        rendered = _format_profile_value(value)
        if rendered is None:
            continue
        lines.append(f"- {key}: {rendered}")
    return "\n".join(lines)


def _format_profile_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        items = [_format_profile_value(item) for item in value]
        compact = [item for item in items if item]
        return ", ".join(compact) if compact else None
    if isinstance(value, dict):
        if not value:
            return None
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    text = str(value).strip()
    return text or None


def build_slice_prompt(
    *,
    section_markdown: str,
    instructions: list[SliceInstruction],
    project_title: str,
    project_profile: ProjectProfileView | None = None,
    validation_feedback: str | None = None,
) -> str:
    """Assemble the slice prompt with project profile facts, no retrieval."""
    requested = "\n".join(
        f'{index}. Regarding this passage:\n   """{item.quoted_text}"""\n'
        f"   Requested change: {item.instruction}"
        for index, item in enumerate(instructions, start=1)
    )
    profile_block = format_project_profile(project_profile)
    parts = [
        f"Project: {project_title}",
        "You are revising ONE section of an existing construction project document.",
        f"--- SECTION START ---\n{section_markdown}\n--- SECTION END ---",
    ]
    if profile_block:
        parts.append(f"--- PROJECT PROFILE ---\n{profile_block}\n--- END PROJECT PROFILE ---")
    else:
        parts.append(
            "--- PROJECT PROFILE ---\n(no profile fields set)\n--- END PROJECT PROFILE ---"
        )
    parts.extend(
        [
            f"Requested changes:\n{requested}",
            "\n".join(_HARD_CONSTRAINTS),
        ]
    )
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
    project_profile: ProjectProfileView | None = None,
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
    profile_text = format_project_profile(project_profile)
    allowed = (
        _numeric_tokens(original)
        | _numeric_tokens(instruction_text)
        | _numeric_tokens(profile_text)
    )
    for token in sorted(_numeric_tokens(revised) - allowed):
        issues.append(
            f"revision introduced number {token!r} not present in the source, "
            "project profile, or instructions"
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
    project_profile: ProjectProfileView | None = None,
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
            project_profile=project_profile,
            validation_feedback=validation_feedback,
        )
        result = await run_agent_with_retry(
            draft_instruction_agent, prompt, model=resolved_model
        )
        revised = result.output.revised_markdown
        try:
            validate_slice_output(
                section_markdown,
                revised,
                instructions=instructions,
                project_profile=project_profile,
            )
        except WorkflowValidationError as exc:
            if attempt >= max_attempts - 1:
                raise
            validation_feedback = str(exc)
            continue
        return revised

    raise WorkflowValidationError("Draft instruction slice produced no valid revision")
