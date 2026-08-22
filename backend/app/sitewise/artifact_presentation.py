"""Deterministic issue-document and web-only QA presentation helpers."""

from __future__ import annotations

import re
from typing import TypedDict
from typing import TypedDict

from app.projects.artefact_blocks import detach_block_marker, strip_block_markers
from app.sitewise.taxonomy import DESIGN_LEAD_UNCONFIRMED_LABEL

_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_INTERNAL_PREFIXES = (
    "scaffold status:",
    "profile emphasis:",
    "loaded seed sections:",
)
_AUDIT_LABEL_RE = re.compile(r"^-\s+\*\*(.+?)\*\*\s*$")
_REVIEW_AUDIT_GROUPS = frozenset({"assumptions", "judgements", "workflow warnings"})
_CONFIRM_RE = re.compile(r"\bconfirm\b", re.IGNORECASE)
_TO_BE_CONFIRMED_RE = re.compile(r"\bto be confirmed\b", re.IGNORECASE)
_DESIGN_LEAD_TBC_RE = re.compile(re.escape(DESIGN_LEAD_UNCONFIRMED_LABEL), re.IGNORECASE)
_DESIGN_LEAD_PLACEHOLDER = "\x00DESIGN_LEAD_TBC\x00"
_TBC_RE = re.compile(r"\bTBC\b", re.IGNORECASE)
_OWNER_BRIEF_LEAD_IN_RE = re.compile(
    r"^\s*\*{0,2}draft owner project brief\*{0,2}\s*(?:—|–|-|:)\s*"
    r"\*{0,2}formal sign[- ]off pending(?:\*{0,2})?\.?(?:\*{0,2})?\s*",
    re.IGNORECASE | re.MULTILINE,
)
_EVIDENCE_ON_FILE_ONLY_RE = re.compile(
    r"^\s*\*{0,2}Evidence on file\*{0,2}\s*:?\s*\*{0,2}\s*\.?\s*$",
    re.IGNORECASE,
)
_EVIDENCE_ON_FILE_LEADING_RE = re.compile(
    r"^\s*\*{0,2}Evidence on file\*{0,2}\s*:\s*\*{0,2}\s*",
    re.IGNORECASE,
)
_EVIDENCE_ON_FILE_LABEL_RE = re.compile(
    r"\s*(?:(?:—|–|-|/|;|,)\s*)?\*{0,2}\bEvidence on file\b\*{0,2}\s*:?\s*\*{0,2}\s*\.?",
    re.IGNORECASE,
)
_USER_PROVIDED_AFTER_SEPARATOR_RE = re.compile(
    r"\s*(?:—|–|-|/|;|,)\s*(?:is\s+)?\*{0,2}user[- ]provided\*{0,2}"
    r"(?:\s*/\s*(?:assumption|not evidenced))?\.?",
    re.IGNORECASE,
)
_USER_PROVIDED_AFTER_COLON_RE = re.compile(
    r"(:\s*)\*{0,2}user[- ]provided\*{0,2}\s*",
    re.IGNORECASE,
)
_USER_PROVIDED_IS_RE = re.compile(
    r"\s*,?\s*is\s+\*{0,2}user[- ]provided\*{0,2}\.?",
    re.IGNORECASE,
)
_USER_PROVIDED_ONLY_RE = re.compile(
    r"^\s*\*{0,2}user[- ]provided\*{0,2}"
    r"(?:\s*/\s*(?:assumption|not evidenced))?\.?\s*$",
    re.IGNORECASE,
)
_SUMMARY_ADDRESS_LABELS = frozenset(
    {"site / asset", "site/asset", "site / address", "site", "address"}
)
_SUMMARY_OWNER_LABELS = frozenset(
    {"client / owner", "client/owner", "owners", "owner", "client"}
)
_COMBINED_IDENTITY_LABEL_RE = re.compile(
    r"^project\s*/\s*(?:owners?|clients?)\s*/\s*(?:site|address)$",
    re.IGNORECASE,
)
_CONFIRMED_PREFIX_RE = re.compile(
    r"^\s*\*?Confirmed\b[:\s,—–-]*",
    re.IGNORECASE,
)
_REQUIRING_RESOLUTION_RE = re.compile(
    r"\s*(?:,\s*)?\brequiring resolution\b\.?",
    re.IGNORECASE,
)
_CONFLICT_STATUS_ONLY_RE = re.compile(
    r"^\s*\*{0,2}Conflict\*{0,2}\s*$",
    re.IGNORECASE,
)
_CONFLICT_TRAILING_RE = re.compile(
    r"\s*\*{0,2}Conflict\*{0,2}(?:\s+requiring resolution)?\.?\s*$",
    re.IGNORECASE,
)
_ADDRESS_SCOPE_TERMS = ("upper metal roof", "stormwater drainage")
_PROPOSAL_ADDRESSEE_RE = re.compile(
    r"\s*(?:\.\s*)?Proposal addressed to\s+[^.]+\.?",
    re.IGNORECASE,
)
_SUMMARY_IDENTITY_ORDER = ("project", "address", "owner", "description")


def _split_row_cells(visible: str) -> list[str]:
    """Split a GFM row on unescaped pipes.

    ``\\|`` is a pipe inside a cell, not a column boundary, and ``\\\\`` is a
    literal backslash. A plain ``split("|")`` turns a three-column row into
    four and silently corrupts the table, so walk the characters instead.
    Inverse of :func:`_escape_cell_text`.
    """
    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(visible):
        char = visible[index]
        if char == "\\" and index + 1 < len(visible) and visible[index + 1] in "|\\":
            current.append(visible[index + 1])
            index += 2
            continue
        if char == "|":
            cells.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    cells.append("".join(current))
    return cells


def _escape_cell_text(cell: str) -> str:
    """Escape a cell so it survives as one column. Inverse of :func:`_split_row_cells`."""
    return cell.replace("\\", "\\\\").replace("|", "\\|")


def _split_table_row(line: str) -> tuple[list[str], str | None]:
    visible, marker = detach_block_marker(line)
    raw = [cell.strip() for cell in _split_row_cells(visible.strip())]
    if len(raw) >= 2 and raw[0] == "" and raw[-1] == "":
        return raw[1:-1], marker
    return [cell for index, cell in enumerate(raw) if not (index == 0 and cell == "")], marker


def _join_table_row(cells: list[str], marker: str | None = None) -> str:
    row = "| " + " | ".join(_escape_cell_text(cell) for cell in cells) + " |"
    return f"{row}{marker or ''}"


def _strip_pmp_disclaimer(markdown: str) -> str:
    blocks = re.split(r"(\r?\n\s*\r?\n)", markdown)
    kept: list[str] = []
    for block in blocks:
        normalized = " ".join(block.split()).casefold().replace("owner-side", "owner side")
        is_disclaimer = (
            "owner side review and governance plan" in normalized
            and "not an instruction" in normalized
            and "statutory submission" in normalized
            and "construction management plan" in normalized
        )
        if not is_disclaimer:
            kept.append(block)
    return "".join(kept)


def clean_issue_language(value: str) -> str:
    """Remove unresolved-workflow shorthand from issued prose without model work."""

    cleaned = _OWNER_BRIEF_LEAD_IN_RE.sub("", value)
    cleaned = _strip_evidence_on_file_label(cleaned)
    cleaned = _strip_user_provided_label(cleaned)
    cleaned = _REQUIRING_RESOLUTION_RE.sub("", cleaned)
    if _CONFLICT_STATUS_ONLY_RE.fullmatch(cleaned):
        return ""
    cleaned = _CONFLICT_TRAILING_RE.sub("", cleaned)
    held_lead = _DESIGN_LEAD_TBC_RE.search(cleaned)
    if held_lead:
        cleaned = _DESIGN_LEAD_TBC_RE.sub(_DESIGN_LEAD_PLACEHOLDER, cleaned)
    cleaned = _TO_BE_CONFIRMED_RE.sub("not stated", cleaned)

    def replace_confirm(match: re.Match[str]) -> str:
        return "State" if match.group(0)[0].isupper() else "state"

    cleaned = _CONFIRM_RE.sub(replace_confirm, cleaned)
    cleaned = _TBC_RE.sub("—", cleaned)
    if held_lead:
        cleaned = cleaned.replace(_DESIGN_LEAD_PLACEHOLDER, held_lead.group(0))
    return cleaned.strip()


def _strip_evidence_on_file_label(value: str) -> str:
    """Drop redundant evidence-status prose; citations already carry that signal."""

    if _EVIDENCE_ON_FILE_ONLY_RE.fullmatch(value):
        return ""
    cleaned = _EVIDENCE_ON_FILE_LEADING_RE.sub("", value)
    cleaned = _EVIDENCE_ON_FILE_LABEL_RE.sub("", cleaned)
    return cleaned.strip()


def _strip_user_provided_label(value: str) -> str:
    if _USER_PROVIDED_ONLY_RE.fullmatch(value):
        return "—"
    cleaned = _USER_PROVIDED_AFTER_SEPARATOR_RE.sub("", value)
    cleaned = _USER_PROVIDED_AFTER_COLON_RE.sub(r"\1", cleaned)
    return _USER_PROVIDED_IS_RE.sub("", cleaned)


def prepare_issue_markdown(markdown: str, *, project_title: str | None = None) -> str:
    """Move review machinery to one final web-only Trace & QA section.

    The transform is deterministic and runs after grounding validation, so it
    adds no model work and cannot change cited customer-facing claims.
    """
    markdown = _strip_pmp_disclaimer(markdown)
    markdown = _strip_coverage_register_section(markdown)
    primary_parts: list[str] = []
    qa_items: list[str] = []
    unresolved_fields: list[str] = []

    for heading, section in _h2_sections(markdown):
        normalized_heading = heading.casefold()
        if normalized_heading == "internal audit layer":
            body = _section_body(section)
            if body:
                qa_items.extend(_audit_review_items(body))
            continue
        if normalized_heading == "trace & qa":
            items, unresolved = _existing_trace_items(_section_body(section))
            qa_items.extend(items)
            unresolved_fields.extend(unresolved)
            continue
        if _is_coverage_register_heading(normalized_heading):
            continue
        cleaned, internal, unresolved = _clean_primary_section(
            section,
            project_title=project_title,
        )
        if normalized_heading == "citation key":
            cleaned = _clean_citation_key_section(cleaned)
        if cleaned.strip():
            primary_parts.append(cleaned.strip())
        qa_items.extend(internal)
        unresolved_fields.extend(unresolved)

    primary = "\n\n".join(primary_parts).strip()
    qa_lines = _dedupe_nonempty(qa_items)
    unresolved = _dedupe_nonempty(unresolved_fields)
    if not qa_lines and not unresolved:
        return primary + "\n"

    trace = [
        "## Trace & QA",
        "",
        "This review-only section is excluded from Word and PDF exports.",
    ]
    if unresolved:
        trace.extend(["", "**Inputs to resolve**"])
        trace.extend(f"- {item}" for item in unresolved)
    if qa_lines:
        trace.extend(["", "**Generation trace**"])
        trace.extend(f"- {item}" for item in qa_lines)
    return f"{primary}\n\n" + "\n".join(trace).rstrip() + "\n"


def issue_export_markdown(
    markdown: str,
    *,
    project_title: str | None = None,
) -> str:
    """Remove the final web-only Trace & QA section from an export."""
    markdown = strip_block_markers(markdown)
    markdown = _strip_pmp_disclaimer(markdown)
    markdown = _strip_coverage_register_section(markdown)
    markdown = _OWNER_BRIEF_LEAD_IN_RE.sub("", markdown)
    export_lines: list[str] = []
    for line in markdown.splitlines():
        cleaned = _strip_user_provided_label(_strip_evidence_on_file_label(line))
        if cleaned.strip() or not line.strip():
            export_lines.append(cleaned)
    markdown = "\n".join(export_lines)
    sections = _h2_sections(markdown)
    kept: list[str] = []
    for heading, section in sections:
        normalized_heading = heading.casefold()
        if normalized_heading == "trace & qa":
            continue
        if _is_coverage_register_heading(normalized_heading):
            continue
        if normalized_heading == "project summary":
            section, _, _ = _clean_primary_section(
                section,
                project_title=project_title,
            )
        elif normalized_heading == "citation key":
            section = _clean_citation_key_section(section)
        else:
            section = _normalise_register_citation_columns(section)
        kept.append(section)
    return "\n\n".join(section.strip() for section in kept if section.strip()).rstrip() + "\n"


def _is_coverage_register_heading(heading: str) -> bool:
    normalized = heading.casefold().replace("—", "-").replace("–", "-")
    return "evidence coverage register" in normalized


def _strip_coverage_register_section(markdown: str) -> str:
    kept: list[str] = []
    for heading, section in _h2_sections(markdown):
        if heading and _is_coverage_register_heading(heading):
            continue
        kept.append(section)
    if not kept:
        return markdown
    return (
        "\n\n".join(section.strip() for section in kept if section.strip()).rstrip()
        + "\n"
    )


_SECTION_EVIDENCE_TABLE_HEADER_RE = re.compile(
    r"^\|\s*section\s*\|\s*evidence status\s*\|\s*(?:citation|ref)\s*\|\s*$",
    re.IGNORECASE,
)


def _clean_citation_key_section(section: str) -> str:
    """Keep Citation key as a numbered document list; drop section-status tables."""

    lines = section.splitlines()
    kept: list[str] = []
    skipping_table = False
    for line in lines:
        stripped = line.strip()
        if _SECTION_EVIDENCE_TABLE_HEADER_RE.match(stripped):
            skipping_table = True
            continue
        if skipping_table:
            if stripped.startswith("|"):
                continue
            skipping_table = False
        if stripped.casefold() in {"**documents cited:**", "documents cited:"}:
            continue
        if re.fullmatch(r"\[\d+\]\s+.+", stripped):
            kept.append(f"- {stripped}")
            continue
        kept.append(line)
    # Collapse excess blank lines after table removal.
    cleaned: list[str] = []
    blank_run = 0
    for line in kept:
        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                continue
        else:
            blank_run = 0
        cleaned.append(line)
    return "\n".join(cleaned).rstrip() + "\n"


def _h2_sections(markdown: str) -> list[tuple[str, str]]:
    matches = list(_H2_RE.finditer(markdown))
    if not matches:
        return [("", markdown)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("", markdown[: matches[0].start()]))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections.append((match.group(1).strip(), markdown[match.start() : end]))
    return sections


def _section_body(section: str) -> str:
    lines = section.splitlines()
    return "\n".join(lines[1:]).strip() if lines else ""


def _clean_primary_section(
    section: str,
    *,
    project_title: str | None = None,
) -> tuple[str, list[str], list[str]]:
    kept: list[str] = []
    internal: list[str] = []
    unresolved: list[str] = []
    is_project_summary = section.lstrip().casefold().startswith("## project summary")
    for line in section.splitlines():
        stripped = line.strip()
        lowered = stripped.casefold()
        if is_project_summary and _is_critical_current_position_line(stripped):
            continue
        if is_project_summary and _is_summary_column_header(stripped):
            continue
        if is_project_summary and stripped and not stripped.startswith("|"):
            # Project Summary is table-only; bridge paragraphs move out of the issued body.
            if lowered.startswith("## "):
                kept.append(line)
            elif lowered.startswith(_INTERNAL_PREFIXES):
                internal.append(stripped)
            continue
        if lowered.startswith(_INTERNAL_PREFIXES):
            internal.append(stripped)
            continue
        if "TBC" not in line:
            cleaned_line = clean_issue_language(line)
            if is_project_summary and stripped.startswith("|"):
                kept.extend(
                    _expand_and_clean_summary_rows(
                        cleaned_line,
                        project_title=project_title,
                    )
                )
            elif cleaned_line.strip():
                kept.append(cleaned_line)
            continue
        if stripped.startswith("|"):
            cells, _ = _split_table_row(stripped)
            if cells and cells[0] and set(cells[0]) != {"-"}:
                unresolved.append(cells[0].replace("**", ""))
            cleaned_line = clean_issue_language(line)
            if is_project_summary:
                kept.extend(
                    _expand_and_clean_summary_rows(
                        cleaned_line,
                        project_title=project_title,
                    )
                )
            elif cleaned_line.strip():
                kept.append(cleaned_line)
        else:
            unresolved.append(stripped.replace("TBC", "unresolved"))
    cleaned_section = "\n".join(kept)
    if is_project_summary:
        cleaned_section = _order_project_summary_rows(
            cleaned_section,
            project_title=project_title,
        )
        cleaned_section = _rebuild_summary_table_without_column_header(cleaned_section)
    cleaned_section = _drop_consultants_scope_column(cleaned_section)
    cleaned_section = _blank_consultants_fee_not_evidenced(cleaned_section)
    cleaned_section = _normalise_register_citation_columns(cleaned_section)
    return cleaned_section, internal, unresolved


_CITATION_TOKEN_RE = re.compile(r"\[(\d+)\]")


def _extract_citation_tokens(text: str) -> str:
    seen: set[str] = set()
    tokens: list[str] = []
    for match in _CITATION_TOKEN_RE.finditer(text):
        token = f"[{match.group(1)}]"
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return " ".join(tokens)


def _strip_citation_tokens(text: str) -> str:
    return re.sub(r"\s+", " ", _CITATION_TOKEN_RE.sub(" ", text)).strip()


def _citation_column_index(labels: list[str]) -> int | None:
    for index, label in enumerate(labels):
        if label in {"citation", "ref"}:
            return index
    if labels and labels[-1] == "":
        return len(labels) - 1
    return None


class _RegisterCitationLayout(TypedDict):
    drop: list[int]
    citation_index: int | None
    append: bool


def _brief_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "item" not in labels or "position" not in labels:
        return None
    if "location" in labels and "finish" in labels:
        return None
    drop: list[int] = []
    basis_index = next(
        (
            index
            for index, label in enumerate(labels)
            if label in {"basis / source", "basis/source", "source"}
        ),
        None,
    )
    has_owner = "owner" in labels
    has_action = any("verification" in label or label == "next action" for label in labels)
    if basis_index is not None and has_owner and has_action and len(labels) >= 5:
        drop.append(basis_index)
    citation_index = _citation_column_index(labels)
    return {
        "drop": drop,
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _ffe_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "item" not in labels or "finish" not in labels or "location" not in labels:
        return None
    drop = [
        index
        for index, label in enumerate(labels)
        if label in {"qty", "quantity", "status"}
    ]
    citation_index = _citation_column_index(labels)
    return {
        "drop": drop,
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _planning_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "discipline" in labels and "firm" in labels:
        return None
    if "item" in labels and "position" in labels:
        return None
    if "item" in labels and "location" in labels and "finish" in labels:
        return None
    looks_named = (
        any(
            token in " ".join(labels)
            for token in ("compliance", "approval", "authority")
        )
        and "status" in labels
    )
    looks_due_diligence = (
        "item" in labels
        and "status" in labels
        and any("next" in label or "verification" in label for label in labels)
    )
    if not (looks_named or looks_due_diligence):
        return None
    citation_index = _citation_column_index(labels)
    return {
        "drop": [],
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _programme_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if not any("milestone" in label for label in labels):
        return None
    citation_index = _citation_column_index(labels)
    return {
        "drop": [],
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _risks_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "risk" not in labels:
        return None
    citation_index = _citation_column_index(labels)
    return {
        "drop": [],
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _actions_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "item" in labels and "position" in labels:
        return None
    if "item" in labels and "location" in labels and "finish" in labels:
        return None
    if "item" not in labels:
        return None
    has_owner_or_status = "owner" in labels or "status" in labels
    has_action = any(
        "next" in label or label in {"due", "due basis"} for label in labels
    )
    if not (has_owner_or_status and has_action):
        return None
    citation_index = _citation_column_index(labels)
    return {
        "drop": [],
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _register_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    return (
        _brief_citation_layout(labels)
        or _ffe_citation_layout(labels)
        or _planning_citation_layout(labels)
        or _programme_citation_layout(labels)
        or _risks_citation_layout(labels)
        or _actions_citation_layout(labels)
    )


def _apply_register_citation_layout(
    cells: list[str],
    layout: _RegisterCitationLayout,
    *,
    is_header: bool,
    is_separator: bool,
) -> list[str]:
    drop = set(layout["drop"])
    citation_index = layout["citation_index"]
    harvested = "" if is_header or is_separator else _extract_citation_tokens(" ".join(cells))
    remaining = [cell for index, cell in enumerate(cells) if index not in drop]
    remaining_indexes = [index for index, _ in enumerate(cells) if index not in drop]
    out: list[str] = []
    for display_index, cell in enumerate(remaining):
        source_index = remaining_indexes[display_index]
        if is_separator:
            out.append(cell)
            continue
        if source_index == citation_index:
            out.append("" if is_header else harvested)
            continue
        if is_header:
            label = cell.casefold()
            out.append("Comment" if label == "notes" else cell)
            continue
        out.append(_strip_citation_tokens(cell))
    if layout["append"]:
        if is_separator:
            out.append("---")
        elif is_header:
            out.append("")
        else:
            out.append(harvested)
    return out


def _normalise_register_citation_columns(section: str) -> str:
    """Give Brief, FFE, planning, programme, risks, and actions tables a trailing citation column.

    Drops the Brief exclusions `Basis / source` column and lifts inline `[n]`
    markers into the citation cell so registers match Project Summary / Consultants.
    """

    lines = section.splitlines()
    out: list[str] = []
    layout: _RegisterCitationLayout | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            layout = None
            out.append(line)
            continue
        cells, marker = _split_table_row(stripped)
        labels = [cell.casefold() for cell in cells]
        if cells and cells[0] and set(cells[0]) != {"-"}:
            detected = _register_citation_layout(labels)
            if detected is not None:
                layout = detected
                cells = _apply_register_citation_layout(
                    cells, layout, is_header=True, is_separator=False
                )
                out.append(_join_table_row(cells, marker))
                continue
        if layout is None:
            out.append(line)
            continue
        if cells and set(cells[0]) == {"-"}:
            cells = _apply_register_citation_layout(
                cells, layout, is_header=False, is_separator=True
            )
            out.append(_join_table_row(cells, marker))
            continue
        cells = _apply_register_citation_layout(
            cells, layout, is_header=False, is_separator=False
        )
        out.append(_join_table_row(cells, marker))
    return "\n".join(out)


_CITATION_TOKEN_RE = re.compile(r"\[(\d+)\]")


def _extract_citation_tokens(text: str) -> str:
    seen: set[str] = set()
    tokens: list[str] = []
    for match in _CITATION_TOKEN_RE.finditer(text):
        token = f"[{match.group(1)}]"
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return " ".join(tokens)


def _strip_citation_tokens(text: str) -> str:
    return re.sub(r"\s+", " ", _CITATION_TOKEN_RE.sub(" ", text)).strip()


def _citation_column_index(labels: list[str]) -> int | None:
    for index, label in enumerate(labels):
        if label in {"citation", "ref"}:
            return index
    if labels and labels[-1] == "":
        return len(labels) - 1
    return None


class _RegisterCitationLayout(TypedDict):
    drop: list[int]
    citation_index: int | None
    append: bool


def _brief_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "item" not in labels or "position" not in labels:
        return None
    if "location" in labels and "finish" in labels:
        return None
    drop: list[int] = []
    basis_index = next(
        (
            index
            for index, label in enumerate(labels)
            if label in {"basis / source", "basis/source", "source"}
        ),
        None,
    )
    has_owner = "owner" in labels
    has_action = any("verification" in label or label == "next action" for label in labels)
    if basis_index is not None and has_owner and has_action and len(labels) >= 5:
        drop.append(basis_index)
    citation_index = _citation_column_index(labels)
    return {
        "drop": drop,
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _ffe_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "item" not in labels or "finish" not in labels or "location" not in labels:
        return None
    drop = [
        index
        for index, label in enumerate(labels)
        if label in {"qty", "quantity", "status"}
    ]
    citation_index = _citation_column_index(labels)
    return {
        "drop": drop,
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _planning_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "discipline" in labels and "firm" in labels:
        return None
    if "item" in labels and "position" in labels:
        return None
    if "item" in labels and "location" in labels and "finish" in labels:
        return None
    looks_named = (
        any(
            token in " ".join(labels)
            for token in ("compliance", "approval", "authority")
        )
        and "status" in labels
    )
    looks_due_diligence = (
        "item" in labels
        and "status" in labels
        and any("next" in label or "verification" in label for label in labels)
    )
    if not (looks_named or looks_due_diligence):
        return None
    citation_index = _citation_column_index(labels)
    return {
        "drop": [],
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _programme_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if not any("milestone" in label for label in labels):
        return None
    citation_index = _citation_column_index(labels)
    return {
        "drop": [],
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _risks_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "risk" not in labels:
        return None
    citation_index = _citation_column_index(labels)
    return {
        "drop": [],
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _actions_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    if "item" in labels and "position" in labels:
        return None
    if "item" in labels and "location" in labels and "finish" in labels:
        return None
    if "item" not in labels:
        return None
    has_owner_or_status = "owner" in labels or "status" in labels
    has_action = any(
        "next" in label or label in {"due", "due basis"} for label in labels
    )
    if not (has_owner_or_status and has_action):
        return None
    citation_index = _citation_column_index(labels)
    return {
        "drop": [],
        "citation_index": citation_index,
        "append": citation_index is None,
    }


def _register_citation_layout(labels: list[str]) -> _RegisterCitationLayout | None:
    return (
        _brief_citation_layout(labels)
        or _ffe_citation_layout(labels)
        or _planning_citation_layout(labels)
        or _programme_citation_layout(labels)
        or _risks_citation_layout(labels)
        or _actions_citation_layout(labels)
    )


def _apply_register_citation_layout(
    cells: list[str],
    layout: _RegisterCitationLayout,
    *,
    is_header: bool,
    is_separator: bool,
) -> list[str]:
    drop = set(layout["drop"])
    citation_index = layout["citation_index"]
    harvested = "" if is_header or is_separator else _extract_citation_tokens(" ".join(cells))
    remaining = [cell for index, cell in enumerate(cells) if index not in drop]
    remaining_indexes = [index for index, _ in enumerate(cells) if index not in drop]
    out: list[str] = []
    for display_index, cell in enumerate(remaining):
        source_index = remaining_indexes[display_index]
        if is_separator:
            out.append(cell)
            continue
        if source_index == citation_index:
            out.append("" if is_header else harvested)
            continue
        if is_header:
            label = cell.casefold()
            out.append("Comment" if label == "notes" else cell)
            continue
        out.append(_strip_citation_tokens(cell))
    if layout["append"]:
        if is_separator:
            out.append("---")
        elif is_header:
            out.append("")
        else:
            out.append(harvested)
    return out


def _normalise_register_citation_columns(section: str) -> str:
    """Give Brief, FFE, planning, programme, risks, and actions tables a trailing citation column.

    Drops the Brief exclusions `Basis / source` column and lifts inline `[n]`
    markers into the citation cell so registers match Project Summary / Consultants.
    """

    lines = section.splitlines()
    out: list[str] = []
    layout: _RegisterCitationLayout | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            layout = None
            out.append(line)
            continue
        cells, marker = _split_table_row(stripped)
        labels = [cell.casefold() for cell in cells]
        if cells and cells[0] and set(cells[0]) != {"-"}:
            detected = _register_citation_layout(labels)
            if detected is not None:
                layout = detected
                cells = _apply_register_citation_layout(
                    cells, layout, is_header=True, is_separator=False
                )
                out.append(_join_table_row(cells, marker))
                continue
        if layout is None:
            out.append(line)
            continue
        if cells and set(cells[0]) == {"-"}:
            cells = _apply_register_citation_layout(
                cells, layout, is_header=False, is_separator=True
            )
            out.append(_join_table_row(cells, marker))
            continue
        cells = _apply_register_citation_layout(
            cells, layout, is_header=False, is_separator=False
        )
        out.append(_join_table_row(cells, marker))
    return "\n".join(out)


def _drop_consultants_scope_column(section: str) -> str:
    """Drop legacy Scope / services from the Consultants appointment register."""

    lines = section.splitlines()
    out: list[str] = []
    scope_index: int | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            scope_index = None
            out.append(line)
            continue
        cells, marker = _split_table_row(stripped)
        labels = [cell.casefold() for cell in cells]
        if (
            "discipline" in labels
            and "firm" in labels
            and "fee" in labels
            and "status" in labels
            and "citation" in labels
        ):
            scope_index = next(
                (index for index, label in enumerate(labels) if "scope" in label),
                None,
            )
            if scope_index is None:
                out.append(line)
                continue
            cells = [cell for index, cell in enumerate(cells) if index != scope_index]
            out.append(_join_table_row(cells, marker))
            continue
        if scope_index is None:
            out.append(line)
            continue
        if cells and set(cells[0]) == {"-"}:
            cells = [cell for index, cell in enumerate(cells) if index != scope_index]
            out.append(_join_table_row(cells, marker))
            continue
        if len(cells) > scope_index:
            cells = [cell for index, cell in enumerate(cells) if index != scope_index]
            out.append(_join_table_row(cells, marker))
            continue
        out.append(line)
    return "\n".join(out)


def _blank_consultants_fee_not_evidenced(section: str) -> str:
    """Leave Fee blank when the appointment register has no fee evidence.

    Status already carries Not evidenced; repeating it in Fee is too loud in the
    issued sheet and exports.
    """

    lines = section.splitlines()
    out: list[str] = []
    fee_index: int | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            fee_index = None
            out.append(line)
            continue
        cells, marker = _split_table_row(stripped)
        labels = [cell.casefold() for cell in cells]
        if (
            len(cells) >= 5
            and "discipline" in labels
            and "firm" in labels
            and "fee" in labels
            and "status" in labels
            and "citation" in labels
        ):
            fee_index = labels.index("fee")
            out.append(line)
            continue
        if fee_index is None:
            out.append(line)
            continue
        if cells and set(cells[0]) == {"-"}:
            out.append(line)
            continue
        if len(cells) > fee_index and cells[fee_index].casefold() == "not evidenced":
            cells[fee_index] = ""
            out.append(_join_table_row(cells, marker))
            continue
        out.append(line)
    return "\n".join(out)


def _expand_and_clean_summary_rows(
    line: str,
    *,
    project_title: str | None,
) -> list[str]:
    expanded = _expand_combined_identity_row(line, project_title=project_title)
    return [
        cleaned
        for raw in expanded
        if (cleaned := _clean_project_summary_row(raw, project_title=project_title)).strip()
    ]


def _expand_combined_identity_row(
    line: str,
    *,
    project_title: str | None,
) -> list[str]:
    """Split LLM-combined Project/Owners/Site rows into three identity rows."""

    cells, marker = _split_table_row(line)
    if len(cells) < 2 or not cells[0] or set(cells[0]) == {"-"}:
        return [line]
    label = re.sub(r"\s+", " ", cells[0]).casefold()
    if not _COMBINED_IDENTITY_LABEL_RE.fullmatch(label):
        return [line]

    parts = [part.strip(" .") for part in re.split(r"\s*/\s*", cells[1]) if part.strip()]
    while len(parts) < 3:
        parts.append("")
    project_value = project_title or _strip_confirmed_prefix(parts[0])
    owner_value = _strip_confirmed_prefix(parts[1])
    address_value = _strip_confirmed_prefix(parts[2])
    citation = cells[-1] if len(cells) >= 3 else ""
    if citation.strip() in {"—", "-", "–"}:
        citation = ""
    return [
        _join_table_row(["Project", project_value, ""], marker),
        _join_table_row(["Address", address_value, citation]),
        _join_table_row(["Owner", owner_value, citation]),
    ]


def _strip_confirmed_prefix(value: str) -> str:
    return _CONFIRMED_PREFIX_RE.sub("", value).strip(" .")


def _clean_project_summary_row(
    line: str,
    *,
    project_title: str | None,
) -> str:
    """Keep summary identity rows compact and free of evidence-status prose."""

    cells, marker = _split_table_row(line)
    if len(cells) < 2 or not cells[0] or set(cells[0]) == {"-"}:
        return line

    label = re.sub(r"\s+", " ", cells[0]).casefold()
    cells[1] = _strip_confirmed_prefix(_strip_evidence_on_file_label(cells[1]))
    if label in {"project", "project title"}:
        if project_title and cells[1].casefold() != project_title.casefold():
            cells[0] = "Description"
        else:
            cells[0] = "Project"
            if project_title:
                cells[1] = project_title
        if cells[0] == "Project" and len(cells) >= 3:
            cells[-1] = ""
    elif label in _SUMMARY_OWNER_LABELS:
        cells[0] = "Owner"
        cells[1] = _PROPOSAL_ADDRESSEE_RE.sub("", cells[1]).rstrip(" .")
    elif label in _SUMMARY_ADDRESS_LABELS:
        cells[0] = "Address"
        cells[1] = _address_detail(cells[1])
    elif label in {"description", "project description"}:
        cells[0] = "Description"

    if len(cells) >= 3 and cells[-1].strip() in {"—", "-", "–"}:
        cells[-1] = ""
    return _join_table_row(cells, marker)


def _address_detail(detail: str) -> str:
    sentences = re.split(r"(?<=\.)\s+", detail.strip())
    without_scope = " ".join(
        sentence
        for sentence in sentences
        if not any(term in sentence.casefold() for term in _ADDRESS_SCOPE_TERMS)
    ).strip()
    return _strip_confirmed_prefix(without_scope).rstrip(" .")


def _order_project_summary_rows(
    section: str,
    *,
    project_title: str | None,
) -> str:
    desired_order = _SUMMARY_IDENTITY_ORDER
    lines = section.splitlines()
    rows_by_label: dict[str, str] = {}
    row_indexes: list[int] = []
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells, marker = _split_table_row(line)
        if not cells:
            continue
        label = cells[0].casefold()
        if label == "client":
            label = "owner"
            line = _join_table_row(["Owner", *cells[1:]], marker)
        if label in desired_order and label not in rows_by_label:
            rows_by_label[label] = line
            row_indexes.append(index)
    if project_title and "project" not in rows_by_label and row_indexes:
        insert_at = min(row_indexes)
        lines.insert(insert_at, f"| Project | {project_title} |  |")
        return _order_project_summary_rows("\n".join(lines), project_title=None)
    ordered_rows = [rows_by_label[label] for label in desired_order if label in rows_by_label]
    for index, row in zip(row_indexes, ordered_rows, strict=True):
        lines[index] = row
    return "\n".join(lines)


def _rebuild_summary_table_without_column_header(section: str) -> str:
    """Keep GFM valid after dropping Field/... headers: first data row + separator."""

    lines = section.splitlines()
    table_indexes = [
        index for index, line in enumerate(lines) if line.strip().startswith("|")
    ]
    if not table_indexes:
        return section
    data_rows: list[tuple[list[str], str | None]] = []
    for index in table_indexes:
        cells, marker = _split_table_row(lines[index])
        if not cells or not cells[0] or set(cells[0]) == {"-"}:
            continue
        data_rows.append((cells, marker))
    if not data_rows:
        return section
    column_count = max(len(cells) for cells, _ in data_rows)
    normalized_rows = [
        _join_table_row(
            [*cells, *([""] * (column_count - len(cells)))],
            marker if index else None,
        )
        for index, (cells, marker) in enumerate(data_rows)
    ]
    separator = "| " + " | ".join(["---"] * column_count) + " |"
    rebuilt = [normalized_rows[0], separator, *normalized_rows[1:]]
    start, end = table_indexes[0], table_indexes[-1]
    return "\n".join([*lines[:start], *rebuilt, *lines[end + 1 :]])


def _is_summary_column_header(line: str) -> bool:
    if not line.startswith("|"):
        return False
    cells = [cell.casefold() for cell in _split_table_row(line)[0]]
    if not cells or not cells[0]:
        return False
    if cells[0] == "field":
        return True
    joined = " | ".join(cells)
    return joined in {
        "field | current pmp position | citation",
        "field | project detail | citation",
        "field | project detail | source",
    }


def _is_critical_current_position_line(line: str) -> bool:
    visible, _ = detach_block_marker(line)
    normalized = visible.strip("|#* :").casefold()
    if normalized == "critical current position":
        return True
    if line.startswith("|"):
        first_cell = visible.strip("|").split("|", maxsplit=1)[0].strip().casefold()
        return first_cell == "critical current position"
    return False


def _dedupe_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        value = " ".join(item.split()).strip(" -")
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _audit_review_items(body: str) -> list[str]:
    group: str | None = None
    items: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        label = _AUDIT_LABEL_RE.match(stripped)
        if label:
            group = label.group(1).strip().casefold()
            continue
        if group not in _REVIEW_AUDIT_GROUPS or not stripped:
            continue
        value = stripped.removeprefix("- ").strip()
        if not value or value.casefold() in {"tbc", "none", "none identified."}:
            continue
        items.append(f"{group.title()}: {value.replace('TBC', 'Unresolved')}")
    return items


def _existing_trace_items(body: str) -> tuple[list[str], list[str]]:
    mode = "trace"
    items: list[str] = []
    unresolved: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        lowered = stripped.casefold()
        if not stripped or lowered.startswith("this review-only section"):
            continue
        if lowered == "**inputs to resolve**":
            mode = "inputs"
            continue
        if lowered == "**generation trace**":
            mode = "trace"
            continue
        value = stripped.removeprefix("- ").strip()
        if not value:
            continue
        (unresolved if mode == "inputs" else items).append(value)
    return items, unresolved
