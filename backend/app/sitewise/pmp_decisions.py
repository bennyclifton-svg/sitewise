"""Parse, validate, and rewrite embedded ``pmp-decision`` fenced blocks in PMP markdown."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterator

from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context
from app.sitewise.taxonomy import complexity_dimensions_for

_FENCE_RE = re.compile(r"^(```|~~~)([^\s]*)")
_REQUIRED_KEYS = frozenset({"id", "label", "options", "selected"})

PMP_CORE_DECISIONS: dict[str, dict[str, Any]] = {
    "approval-pathway": {
        "label": "Approvals pathway",
        "section": "Compliance & approvals",
        "options": [
            {"value": "da", "label": "Development Application (DA)"},
            {"value": "cdc", "label": "Complying Development Certificate (CDC)"},
            {"value": "exempt", "label": "Exempt / No approval required"},
        ],
    },
    "contract-form": {
        "label": "Contract form",
        "section": "Procurement & delivery",
        "options": [
            {"value": "as4000", "label": "AS 4000"},
            {"value": "hia", "label": "HIA"},
            {"value": "design_construct", "label": "Design & Construct"},
            {"value": "cost_plus", "label": "Cost Plus"},
        ],
    },
    "staging-strategy": {
        "label": "Staging strategy",
        "section": "Programme & milestones",
        "options": [
            {"value": "single_stage", "label": "Single stage delivery"},
            {"value": "staged_oc", "label": "Staged OC / partial handover"},
            {"value": "phased_occupation", "label": "Phased occupation"},
        ],
    },
}


@dataclass(frozen=True, slots=True)
class PmpDecision:
    id: str
    section: str
    label: str
    options: tuple[dict[str, str], ...]
    selected: str
    source: str
    rationale: str | None = None
    evidence_conflict: bool = False
    agent_suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class _DecisionFence:
    start: int
    end: int
    fence: str
    info: str
    body: str


def _kebab_case(value: str) -> str:
    return value.strip().replace("_", "-")


def _iter_decision_fences(markdown: str) -> Iterator[_DecisionFence]:
    lines = markdown.splitlines(keepends=True)
    offset = 0
    index = 0
    while index < len(lines):
        match = _FENCE_RE.match(lines[index])
        if match is None:
            offset += len(lines[index])
            index += 1
            continue
        fence = match.group(1)
        info = match.group(2)
        start = offset
        offset += len(lines[index])
        index += 1
        body_lines: list[str] = []
        while index < len(lines) and not lines[index].strip().startswith(fence):
            body_lines.append(lines[index])
            offset += len(lines[index])
            index += 1
        if index < len(lines):
            offset += len(lines[index])
            index += 1
        if info == "pmp-decision":
            yield _DecisionFence(
                start=start,
                end=offset,
                fence=fence,
                info=info,
                body="".join(body_lines),
            )


def _parse_payload(body: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _normalise_options(raw_options: object) -> tuple[dict[str, str], ...]:
    if not isinstance(raw_options, list):
        return ()
    options: list[dict[str, str]] = []
    for item in raw_options:
        if not isinstance(item, dict):
            continue
        value = item.get("value") or item.get("id")
        label = item.get("label") or item.get("title")
        if not isinstance(value, str) or not value.strip():
            continue
        options.append(
            {
                "value": value.strip(),
                "label": str(label).strip() if label else value.strip(),
            }
        )
    return tuple(options)


def _option_values(options: tuple[dict[str, str], ...]) -> set[str]:
    return {option["value"] for option in options}


def _selected_label(decision: PmpDecision) -> str:
    for option in decision.options:
        if option["value"] == decision.selected:
            return option["label"]
    return decision.selected


def _decision_from_payload(payload: dict[str, Any]) -> PmpDecision | None:
    decision_id = payload.get("id")
    label = payload.get("label")
    selected = payload.get("selected")
    if not isinstance(decision_id, str) or not isinstance(label, str) or not isinstance(selected, str):
        return None
    options = _normalise_options(payload.get("options"))
    source = payload.get("source")
    rationale = payload.get("rationale")
    section = payload.get("section")
    agent_suggestion = payload.get("agent_suggestion")
    evidence_conflict = payload.get("evidence_conflict")
    return PmpDecision(
        id=decision_id.strip(),
        section=str(section).strip() if isinstance(section, str) else "",
        label=label.strip(),
        options=options,
        selected=selected.strip(),
        source=str(source).strip() if isinstance(source, str) else "agent",
        rationale=str(rationale).strip() if isinstance(rationale, str) and rationale.strip() else None,
        evidence_conflict=bool(evidence_conflict),
        agent_suggestion=(
            str(agent_suggestion).strip()
            if isinstance(agent_suggestion, str) and agent_suggestion.strip()
            else None
        ),
    )


def extract_decisions(markdown: str) -> list[PmpDecision]:
    decisions: list[PmpDecision] = []
    for block in _iter_decision_fences(markdown):
        payload = _parse_payload(block.body)
        if payload is None:
            continue
        decision = _decision_from_payload(payload)
        if decision is not None:
            decisions.append(decision)
    return decisions


def decision_violations(markdown: str) -> list[str]:
    violations: list[str] = []
    seen_ids: set[str] = set()
    for block in _iter_decision_fences(markdown):
        payload = _parse_payload(block.body)
        if payload is None:
            violations.append("Malformed pmp-decision JSON block.")
            continue
        missing = sorted(key for key in _REQUIRED_KEYS if key not in payload)
        if missing:
            violations.append(
                f"Decision block missing required keys ({', '.join(missing)})."
            )
            continue
        decision = _decision_from_payload(payload)
        if decision is None:
            violations.append("Decision block has invalid field types.")
            continue
        if decision.id in seen_ids:
            violations.append(f"Duplicate decision id: {decision.id}.")
        seen_ids.add(decision.id)
        if not decision.options:
            violations.append(f"Decision '{decision.id}' has no options.")
            continue
        if decision.selected not in _option_values(decision.options):
            violations.append(
                f"Decision '{decision.id}' selected value is not in options."
            )
    return violations


def missing_locked_decisions(markdown: str, locked_ids: set[str]) -> list[str]:
    present = {decision.id for decision in extract_decisions(markdown)}
    return sorted(decision_id for decision_id in locked_ids if decision_id not in present)


def _render_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def restamp_decisions(markdown: str, locked: dict[str, str]) -> str:
    if not locked:
        return markdown

    pieces: list[str] = []
    cursor = 0
    for block in _iter_decision_fences(markdown):
        pieces.append(markdown[cursor : block.start])
        payload = _parse_payload(block.body)
        if payload is not None and payload.get("id") in locked:
            locked_value = locked[str(payload["id"])]
            current_selected = payload.get("selected")
            if (
                isinstance(current_selected, str)
                and current_selected.strip()
                and current_selected.strip() != locked_value
            ):
                payload["agent_suggestion"] = current_selected.strip()
                payload["evidence_conflict"] = True
            payload["selected"] = locked_value
            payload["source"] = "user"
        if payload is not None:
            body = _render_payload(payload)
            pieces.append(f"{block.fence}{block.info}\n{body}\n{block.fence}\n")
        else:
            pieces.append(markdown[block.start : block.end])
        cursor = block.end
    pieces.append(markdown[cursor:])
    return "".join(pieces)


def render_decisions_static(markdown: str) -> str:
    pieces: list[str] = []
    cursor = 0
    for block in _iter_decision_fences(markdown):
        pieces.append(markdown[cursor : block.start])
        payload = _parse_payload(block.body)
        if payload is None:
            pieces.append(markdown[block.start : block.end])
        else:
            decision = _decision_from_payload(payload)
            if decision is None:
                pieces.append(markdown[block.start : block.end])
            else:
                pieces.append(f"**{decision.label}:** {_selected_label(decision)}\n")
        cursor = block.end
    pieces.append(markdown[cursor:])
    return "".join(pieces)


def decision_option_sets_for_project(project: object | None) -> dict[str, dict[str, Any]]:
    sets = {key: dict(value) for key, value in PMP_CORE_DECISIONS.items()}
    context = pmp_taxonomy_context(project) if project is not None else None
    if context is None:
        return sets
    for dimension in complexity_dimensions_for(context.building_class, context.subclasses):
        decision_id = _kebab_case(dimension.key)
        sets[decision_id] = {
            "label": dimension.label,
            "section": "Project snapshot",
            "options": [
                {"value": option.value, "label": option.label}
                for option in dimension.options
            ],
        }
    return sets


def format_decision_option_sets(project: object | None) -> str:
    lines = ["Available decision option sets (use only these values in pmp-decision blocks):"]
    for decision_id, spec in sorted(decision_option_sets_for_project(project).items()):
        options = ", ".join(
            f"{option['value']}={option['label']}" for option in spec["options"]
        )
        lines.append(f"- {decision_id} ({spec['label']}): {options}")
    return "\n".join(lines)


def format_locked_decisions(locked: dict[str, str]) -> str:
    if not locked:
        return "User-locked decisions: none."
    lines = ["User-locked decisions (must be preserved with source=user):"]
    for decision_id, selected in sorted(locked.items()):
        lines.append(f"- {decision_id}: {selected}")
    return "\n".join(lines)
