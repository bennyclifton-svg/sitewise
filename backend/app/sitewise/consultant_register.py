"""Deterministic Consultants-register helpers from shared consultant facts."""

from __future__ import annotations

import re
from typing import Any

from app.database.project import Project
from app.projects.consultant_facts import map_discipline_to_register_label
from app.projects.project_knowledge import list_shared_project_objects
from ingest.consultant_firm import is_noise_firm_candidate

_CONSULTANTS_SECTION_RE = re.compile(
    r"(?ms)^(##\s+Consultants\s*\n)(.*?)(?=^##\s|\Z)"
)
_TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<discipline>[^|]+?)\s*\|\s*(?P<firm>[^|]*?)\s*\|\s*(?P<fee>[^|]*?)\s*\|\s*(?P<status>[^|]*?)\s*\|\s*(?P<citation>[^|]*?)\s*\|"
)

# Abbreviated tokens the narrative often uses inside slash-joined lumps.
_LUMP_TOKEN_ALIASES: dict[str, str] = {
    "geotech": "Geotechnical Engineer",
    "waterproof": "Waterproofing Consultant",
    "waterproofing": "Waterproofing Consultant",
    "facade": "Facade Engineer",
    "fire": "Fire Engineer",
    "structural": "Structural Engineer",
    "civil": "Civil Engineer",
    "landscape": "Landscape Architect",
    "traffic": "Traffic Engineer",
    "acoustic": "Acoustic Consultant",
    "access": "Access Consultant",
    "hydraulic": "Services Engineer (Hydraulic)",
    "electrical": "Services Engineer (Electrical)",
    "mechanical": "Services Engineer (Mechanical)",
    "vertical transport": "Vertical Transport Consultant",
    "vertical transportation": "Vertical Transport Consultant",
    "certifier": "Building Certifier",
    "building certifier": "Building Certifier",
}


def consultant_appointment_rows(project: Project) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in list_shared_project_objects(project, kind="consultant"):
        value = item.value if isinstance(item.value, dict) else {}
        discipline = str(value.get("discipline") or "").strip()
        firm = str(value.get("firm") or value.get("name") or "").strip()
        if not discipline or not firm or is_noise_firm_candidate(firm):
            continue
        paths = [
            str(path)
            for path in (value.get("evidence_paths") or [])
            if isinstance(path, str) and path
        ]
        rows.append(
            {
                "discipline": discipline,
                "firm": firm,
                "status": str(
                    value.get("status")
                    or "Report/drawings on file; appointment unverified"
                ),
                "evidence_paths": paths,
                "fee": str(value.get("fee") or ""),
            }
        )
    rows.sort(key=lambda row: row["discipline"].casefold())
    return rows


def citation_numbers_from_markdown(markdown: str) -> dict[str, int]:
    """Map citation-key filenames/paths to their [n] numbers."""
    numbers: dict[str, int] = {}
    for match in re.finditer(
        r"(?m)^\s*-\s*\[(\d+)\]\s+(.+?)(?:\s+—|\s+-|\s*$)",
        markdown,
    ):
        number = int(match.group(1))
        label = match.group(2).strip()
        numbers[label] = number
        filename = label.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
        numbers[filename] = number
    return numbers


def consultant_fact_constraints(project: Project) -> list[str]:
    rows = consultant_appointment_rows(project)
    if not rows:
        return []
    lines = [
        "Consultants register must use these evidenced firms when the discipline matches "
        "(or add the row if missing). Design drawings/certificates prove firm identity "
        "only — status stays appointment-unverified unless engagement evidence exists:"
    ]
    for row in rows:
        lines.append(
            f"- {row['discipline']}: {row['firm']} ({row['status']})"
        )
    return lines


def _discipline_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", label.casefold()).strip()


def _map_lump_token(token: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", token).strip()
    if not cleaned:
        return None
    alias = _LUMP_TOKEN_ALIASES.get(cleaned.casefold())
    if alias:
        return alias
    return map_discipline_to_register_label(cleaned)


def expand_discipline_lump(label: str) -> list[str] | None:
    """Split slash-joined discipline bundles into one register label each.

    Narrative drafts sometimes compress many TBC disciplines into one cell
    ("Structural / civil / geotech / facade / waterproof / fire"). The appointment
    register needs one row per discipline so firms/fees/status can be tracked.
    Returns None when the label is already a single discipline.
    """
    if "/" not in label:
        return None
    tokens = [part.strip() for part in re.split(r"\s*/\s*", label) if part.strip()]
    if len(tokens) < 2:
        return None

    mapped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        register = _map_lump_token(token)
        if register is None:
            continue
        key = _discipline_key(register)
        # Drop generic "Services Engineer" when specialist services rows exist.
        if key == "services engineer":
            continue
        if key in seen:
            continue
        seen.add(key)
        mapped.append(register)

    if len(mapped) < 2:
        return None
    return mapped


def _disciplines_match(row_label: str, fact_label: str) -> bool:
    left = _discipline_key(row_label)
    right = _discipline_key(fact_label)
    if not left or not right:
        return False
    if left == right:
        return True

    # Slash-joined lumps are expanded before matching; refuse firm fill if any remain.
    if "/" in row_label:
        return False

    if "hydraulic" in left and "hydraulic" in right:
        return True
    if "electrical" in left and "electrical" in right:
        return True
    if "mechanical" in left and "mechanical" in right:
        return True
    if "structural" in left and "structural" in right:
        return True
    if "fire" in left and "fire" in right:
        return True
    if (
        "architect" in left
        and "architect" in right
        and "landscape" not in left
        and "landscape" not in right
        and "access" not in left
        and "access" not in right
    ):
        return True
    if "acoustic" in left and "acoustic" in right:
        return True
    if "access" in left and "access" in right:
        return True
    if "landscape" in left and "landscape" in right:
        return True
    return False


def _citation_for(
    paths: list[str],
    citation_numbers: dict[str, int] | None,
) -> str:
    if not citation_numbers:
        return "—"
    for path in paths:
        number = citation_numbers.get(path)
        if number is not None:
            return f"[{number}]"
        # Allow filename-only keys.
        filename = path.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
        for key, value in citation_numbers.items():
            if key.endswith(filename) or key == filename:
                return f"[{value}]"
    return "—"


def _format_row(
    *,
    discipline: str,
    firm: str,
    fee: str,
    status: str,
    citation: str,
) -> str:
    return f"| {discipline} | {firm} | {fee} | {status} | {citation} |"


def _row_for_discipline(
    discipline: str,
    *,
    facts: list[dict[str, Any]],
    used_fact_indexes: set[int],
    citation_numbers: dict[str, int] | None,
    firm: str = "",
    fee: str = "",
    status: str = "Assumption / Not evidenced",
    citation: str = "—",
) -> str:
    matched_index = next(
        (
            index
            for index, fact in enumerate(facts)
            if index not in used_fact_indexes
            and _disciplines_match(discipline, fact["discipline"])
        ),
        None,
    )
    if matched_index is None:
        blank_firm = not firm or firm.upper() in {"TBC", "—", "-"}
        return _format_row(
            discipline=discipline,
            firm="TBC" if blank_firm else firm,
            fee=fee,
            status=status if not blank_firm else "Assumption / Not evidenced",
            citation=citation if not blank_firm else "—",
        )

    fact = facts[matched_index]
    used_fact_indexes.add(matched_index)
    if (
        not firm
        or firm.upper() in {"TBC", "—", "-"}
        or is_noise_firm_candidate(firm)
    ):
        firm = fact["firm"]
        status = fact["status"]
        citation = _citation_for(fact["evidence_paths"], citation_numbers)
    return _format_row(
        discipline=discipline,
        firm=firm,
        fee=fee,
        status=status,
        citation=citation,
    )


def apply_consultant_register_facts(
    markdown: str,
    *,
    project: Project,
    citation_numbers: dict[str, int] | None = None,
) -> str:
    """Fill, expand, or append Consultants rows from shared evidence-derived facts."""
    facts = consultant_appointment_rows(project)

    match = _CONSULTANTS_SECTION_RE.search(markdown)
    if match is None:
        return markdown

    header = match.group(1)
    body = match.group(2)
    lines = body.splitlines()
    used_fact_indexes: set[int] = set()
    rewritten: list[str] = []
    seen_disciplines: set[str] = set()

    for line in lines:
        row = _TABLE_ROW_RE.match(line.strip())
        if row is None or row.group("discipline").strip().lower() in {
            "discipline",
            "---",
        }:
            rewritten.append(line)
            continue
        if set(row.group("discipline").strip()) <= {"-"}:
            rewritten.append(line)
            continue

        discipline = row.group("discipline").strip()
        firm = row.group("firm").strip()
        fee = row.group("fee").strip()
        status = row.group("status").strip()
        citation = row.group("citation").strip()

        expanded = expand_discipline_lump(discipline)
        if expanded is not None:
            # Lumps are compression artifacts — never keep firm/fee/status from the
            # bundled cell; rebuild one clean row per discipline.
            for label in expanded:
                key = _discipline_key(label)
                if key in seen_disciplines:
                    continue
                seen_disciplines.add(key)
                rewritten.append(
                    _row_for_discipline(
                        label,
                        facts=facts,
                        used_fact_indexes=used_fact_indexes,
                        citation_numbers=citation_numbers,
                    )
                )
            continue

        key = _discipline_key(discipline)
        if key in seen_disciplines:
            continue
        seen_disciplines.add(key)
        rewritten.append(
            _row_for_discipline(
                discipline,
                facts=facts,
                used_fact_indexes=used_fact_indexes,
                citation_numbers=citation_numbers,
                firm=firm,
                fee=fee,
                status=status,
                citation=citation,
            )
        )

    # Append evidenced disciplines the draft omitted entirely.
    insert_at = len(rewritten)
    for index, fact in enumerate(facts):
        if index in used_fact_indexes:
            continue
        key = _discipline_key(str(fact["discipline"]))
        if key in seen_disciplines:
            continue
        seen_disciplines.add(key)
        citation = _citation_for(fact["evidence_paths"], citation_numbers)
        rewritten.insert(
            insert_at,
            _format_row(
                discipline=str(fact["discipline"]),
                firm=str(fact["firm"]),
                fee=str(fact.get("fee") or ""),
                status=str(fact["status"]),
                citation=citation,
            ),
        )
        insert_at += 1

    new_body = "\n".join(rewritten)
    if not new_body.endswith("\n"):
        new_body += "\n"
    return markdown[: match.start()] + header + new_body + markdown[match.end() :]
