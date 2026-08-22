"""Canonical SiteWise consultant, trade, and supplier identities."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

ParticipantType = Literal["consultant", "trade", "supplier"]
ProcurementRequestKind = Literal[
    "consultant_rfp", "trade_rft", "trade_rfq", "contractor_eoi"
]

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "data" / "taxonomy" / "disciplines.json"


@dataclass(frozen=True, slots=True)
class Discipline:
    code: str
    label: str
    participant_type: ParticipantType
    request_kind: ProcurementRequestKind
    aliases: tuple[str, ...]
    workspace_slug: str
    pmp_label: str


@dataclass(frozen=True, slots=True)
class RequiredProjectDiscipline:
    code: str | None
    label: str
    participant_type: ParticipantType
    request_kind: ProcurementRequestKind
    sources: tuple[str, ...]


def _normalise(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


@lru_cache(maxsize=1)
def discipline_catalog() -> tuple[Discipline, ...]:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    entries = tuple(_discipline(item) for item in raw.get("disciplines", []))
    _validate(entries)
    return entries


def _discipline(raw: object) -> Discipline:
    if not isinstance(raw, dict):
        raise ValueError("discipline entries must be objects")
    return Discipline(
        code=str(raw["code"]),
        label=str(raw["label"]),
        participant_type=str(raw["participant_type"]),  # type: ignore[arg-type]
        request_kind=str(raw["request_kind"]),  # type: ignore[arg-type]
        aliases=tuple(str(value) for value in raw.get("aliases", [])),
        workspace_slug=str(raw["workspace_slug"]),
        pmp_label=str(raw.get("pmp_label") or raw["label"]),
    )


def _validate(entries: tuple[Discipline, ...]) -> None:
    if not entries:
        raise ValueError("discipline catalogue is empty")
    codes: set[str] = set()
    aliases_by_type: dict[ParticipantType, dict[str, str]] = {
        "consultant": {},
        "trade": {},
        "supplier": {},
    }
    valid_kinds = {"consultant_rfp", "trade_rft", "trade_rfq", "contractor_eoi"}
    for entry in entries:
        if entry.code in codes:
            raise ValueError(f"duplicate discipline code: {entry.code}")
        codes.add(entry.code)
        if entry.participant_type not in aliases_by_type:
            raise ValueError(f"invalid participant type for {entry.code}")
        if entry.request_kind not in valid_kinds:
            raise ValueError(f"invalid request kind for {entry.code}")
        for value in (entry.code, entry.label, entry.pmp_label, *entry.aliases):
            key = _normalise(value)
            owner = aliases_by_type[entry.participant_type].get(key)
            if owner is not None and owner != entry.code:
                raise ValueError(
                    f"ambiguous {entry.participant_type} discipline alias {value!r}: "
                    f"{owner} and {entry.code}"
                )
            aliases_by_type[entry.participant_type][key] = entry.code


@lru_cache(maxsize=1)
def _by_code() -> dict[str, Discipline]:
    return {entry.code: entry for entry in discipline_catalog()}


def discipline_by_code(code: str) -> Discipline:
    try:
        return _by_code()[code]
    except KeyError as exc:
        raise ValueError(f"unknown discipline code: {code}") from exc


def resolve_discipline(
    value: str,
    *,
    participant_type: ParticipantType | None = None,
) -> Discipline:
    key = _normalise(value)
    matches = [
        entry
        for entry in discipline_catalog()
        if (participant_type is None or entry.participant_type == participant_type)
        and key
        in {
            _normalise(entry.code),
            _normalise(entry.label),
            _normalise(entry.pmp_label),
            *(_normalise(alias) for alias in entry.aliases),
        }
    ]
    if not matches:
        raise ValueError(f"unknown discipline: {value}")
    if len(matches) > 1:
        codes = ", ".join(entry.code for entry in matches)
        raise ValueError(f"ambiguous discipline {value!r}: {codes}")
    return matches[0]


def disciplines_for(
    participant_type: ParticipantType | None = None,
) -> tuple[Discipline, ...]:
    return tuple(
        entry
        for entry in discipline_catalog()
        if participant_type is None or entry.participant_type == participant_type
    )


def required_project_disciplines(project: object) -> tuple[RequiredProjectDiscipline, ...]:
    """Return the deterministic project roster shared by PMP and Procurement.

    Database-backed procurement requests and manual strategy rows are merged by the
    strategy service because this resolver deliberately performs no I/O.
    """
    from app.sitewise.consultant_register import consultant_appointment_rows
    from app.sitewise.consultant_typical import (
        removed_consultant_labels,
        typical_consultant_labels,
    )
    from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context
    from app.sitewise.taxonomy import work_scope_items_for

    context = pmp_taxonomy_context(project)
    collected: list[tuple[Discipline, str]] = []
    if context is not None:
        for item in work_scope_items_for(context.work_type, context.work_scope):
            for label in item.consultants:
                collected.append((resolve_discipline(label), "work_scope"))
        for label in typical_consultant_labels(
            work_type=context.work_type,
            subclasses=context.subclasses,
        ):
            collected.append(
                (resolve_discipline(label, participant_type="consultant"), "typical")
            )

    removed = removed_consultant_labels(project)
    for row in consultant_appointment_rows(project):
        try:
            discipline = resolve_discipline(
                str(row["discipline"]), participant_type="consultant"
            )
        except ValueError:
            continue
        collected.append((discipline, "appointment"))

    order: list[str] = []
    merged: dict[str, tuple[Discipline, list[str]]] = {}
    for discipline, source in collected:
        if discipline.label.casefold() in removed or discipline.pmp_label.casefold() in removed:
            continue
        if discipline.code not in merged:
            order.append(discipline.code)
            merged[discipline.code] = (discipline, [])
        sources = merged[discipline.code][1]
        if source not in sources:
            sources.append(source)
    return tuple(
        RequiredProjectDiscipline(
            code=code,
            label=merged[code][0].pmp_label,
            participant_type=merged[code][0].participant_type,
            request_kind=merged[code][0].request_kind,
            sources=tuple(merged[code][1]),
        )
        for code in order
    )
