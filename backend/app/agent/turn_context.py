"""Prompt assembly for Hermes agent turns.

Hermes runs headless once per turn, so anything it should know beyond the
user's words must travel in the prompt: the project's three-overlay
declaration (the same gate the knowledge tools enforce) and a bounded window
of recent conversation. String assembly only — bounded, deterministic, no
retrieval and no LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings

_NOT_DECLARED = "(not declared)"
_DOCUMENT_ACCESS_GUIDANCE = """<document-access>
For questions about uploaded source documents, use project document tools before OCR:
find_document_text is the first choice for simple keyword or phrase lookups.
search_documents finds semantic matches, and get_document reads longer ingested text.
Do not inspect repository files, run shell commands, or query the database directly
to answer questions about uploaded source documents.
Only use OCR or document-conversion skills when these tools report text is unavailable,
or when the ingested text is clearly garbled or insufficient for the user's question.
</document-access>"""
_ROLE_GUIDANCE = """<role>
You are Clerk, a construction management intelligence agent working for the
owner of the construction project described in <project-context>. When the
user says "the project" they always mean that construction project — never
this software repository, its codebase, or its development plans. Do not
describe repository structure, technology stacks, or coding conventions;
any such instructions you encounter are for software agents, not you.
Ground every answer in project evidence and platform knowledge:
- Uploaded project documents: find_document_text, search_documents, get_document.
- Construction management doctrine and workflow guidance:
  list_platform_knowledge, read_platform_knowledge.
If a <project-context> field reads "(not declared)", ask the user to declare
it instead of guessing. Write plain, direct answers for construction
professionals and name the documents your answer relies on.
</role>"""


@dataclass(frozen=True)
class HistoryMessage:
    role: str
    content: str


def build_agent_prompt(
    user_text: str,
    *,
    project_id: str,
    title: str,
    archetype: str | None,
    user_role: str | None,
    state: str | None,
    phase: str | None,
    building_class: str | None,
    work_type: str | None,
    history: list[HistoryMessage],
) -> str:
    """Wrap the user's message with the agent role, project overlays, and history.

    Overlay fields always appear — an explicit "(not declared)" tells the
    agent to resolve the gate with the user instead of guessing. History is
    capped by message count and per-message chars so the prompt stays bounded.
    """
    blocks: list[str] = [_ROLE_GUIDANCE]

    blocks.append(
        "<project-context>\n"
        f"project_id: {project_id}\n"
        f"project_title: {title}\n"
        f"archetype: {archetype or _NOT_DECLARED}\n"
        f"building_class: {building_class or _NOT_DECLARED}\n"
        f"work_type: {work_type or _NOT_DECLARED}\n"
        f"phase: {phase or _NOT_DECLARED}\n"
        f"user_role: {user_role or _NOT_DECLARED}\n"
        f"state: {state or _NOT_DECLARED}\n"
        "</project-context>"
    )
    blocks.append(_DOCUMENT_ACCESS_GUIDANCE)

    window = _bounded_history(history)
    if window:
        lines = [f"{message.role}: {message.content}" for message in window]
        blocks.append(
            "<recent-conversation>\n" + "\n".join(lines) + "\n</recent-conversation>"
        )

    blocks.append(user_text)
    return "\n\n".join(blocks)


def _bounded_history(history: list[HistoryMessage]) -> list[HistoryMessage]:
    limit = settings.agent_history_message_limit
    if limit <= 0:
        return []
    max_chars = settings.agent_history_message_chars
    window = history[-limit:]
    bounded: list[HistoryMessage] = []
    for message in window:
        content = " ".join(message.content.split())
        if len(content) > max_chars:
            content = content[: max_chars - 1].rstrip() + "…"
        if content:
            bounded.append(HistoryMessage(role=message.role, content=content))
    return bounded
