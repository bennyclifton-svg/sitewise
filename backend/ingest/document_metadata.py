"""Document metadata extraction from filenames, paths, and preview snippets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import unquote

Confidence = Literal["high", "medium", "low"]

DISCIPLINE_FOLDER_LABELS: dict[str, str] = {
    "architect": "Architectural",
    "landscape-architect": "Landscape Architectural",
    "civil": "Civil",
    "structural": "Structural",
    "certifier": "Certifier",
    "town-planner": "Town Planning",
    "quantity-surveyor": "Quantity Surveyor",
    "surveyor": "Surveyor",
    "bushfire-consultant": "Bushfire",
    "geotechnical": "Geotechnical",
    "arborist": "Arborist",
    "energy-assessor": "Energy Assessment",
    "hydraulic": "Hydraulic",
    "mechanical": "Mechanical",
    "electrical": "Electrical",
    "fire": "Fire",
    "services": "Services",
    # Legacy slugs from pre-rename workspaces
    "civil-engineer": "Civil",
    "structural-engineer": "Structural",
    "geotechnical-engineer": "Geotechnical",
    "hydraulic-engineer": "Hydraulic",
    "mechanical-engineer": "Mechanical",
    "electrical-engineer": "Electrical",
    "fire-engineer": "Fire",
    "services-engineer": "Services",
}

INBOX_FOLDER_DISCIPLINE_LABELS: dict[str, str] = {
    "ACCESS": "Access",
    "ACOUSTIC": "Acoustic",
    "ARCHITECTURE": "Architectural",
    "ASP3": "Certification",
    "BASIX": "Energy Assessment",
    "CIVIL": "Civil",
    "DA, MODS & STAMPED PLANS": "Authorities",
    "ELEC": "Electrical",
    "FACADE REPORT": "Facade",
    "FER - PRIMARY": "Fire",
    "FER - RITEK": "Fire",
    "FIRE MATRIX": "Fire",
    "FIRE WET & DRY": "Fire",
    "HYDRAULIC": "Hydraulic",
    "LANDSCAPE": "Landscape Architectural",
    "LIFT": "Vertical Transportation",
    "MECH": "Mechanical",
    "NBN": "Communications",
    "ROOF ACCESS": "Architectural",
    "s73 NOR DEVELOPER DEED & MLIM": "Authorities",
    "SECTION J": "Energy Assessment",
    "SITE INVESTIGATION": "Geotechnical",
    "STORMWATER": "Civil",
    "STRUCTURAL": "Structural",
    "STRUCTURAL BALUSTRADE DESIGN": "Structural",
    "TRAFFIC": "Traffic",
    "WASTE MGT PLAN": "Construction",
    "WATERPROOFING": "Waterproofing",
}

LIFECYCLE_CATEGORY_BY_FOLDER: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"/00-brief-pmp/", re.I), "Brief"),
    (re.compile(r"/01-cost/", re.I), "Cost"),
    (re.compile(r"/02-consultant/", re.I), "Consultant"),
    (re.compile(r"/03-design/", re.I), "Design"),
    (re.compile(r"/04-planning-and-authorities/", re.I), "Authorities"),
    (re.compile(r"/05-procurement/", re.I), "Procurement"),
    (re.compile(r"/07-construction/", re.I), "Construction"),
    (re.compile(r"/08-meetings-reporting/", re.I), "Reporting"),
]

FILENAME_DISCIPLINE_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\belectrical\b", re.I), "Electrical"),
    (re.compile(r"\bhydraulic\b|\bhw\s*&\s*gas\b|\bsanitary\b|\bdrainage\b", re.I), "Hydraulic"),
    (re.compile(r"\bmechanical\b", re.I), "Mechanical"),
    (re.compile(r"\bstructural\b|^S\d{3}-", re.I), "Structural"),
    (re.compile(r"\barchitect", re.I), "Architectural"),
    (re.compile(r"\blandscape\b", re.I), "Landscape Architectural"),
    (re.compile(r"\bctmp\b|\bconstruction\s+traffic\s+management\b", re.I), "Traffic"),
    (re.compile(r"\bcivil\b|\bstorm\s*water\b|\bsewer\b", re.I), "Civil"),
    (re.compile(r"\bfire\b|\bfer\b|\bfas\d|\bfsp\d|\bfco\b|\bfyr", re.I), "Fire"),
    (re.compile(r"\bacoustic\b", re.I), "Acoustic"),
    (re.compile(r"\bwaterproof", re.I), "Waterproofing"),
    (re.compile(r"\bvertical\s+transport", re.I), "Vertical Transportation"),
    (re.compile(r"\bbasix\b|\benergy\b|\bsection\s+j\b", re.I), "Energy Assessment"),
    (re.compile(r"\bfacade\b", re.I), "Facade"),
    (re.compile(r"\bnbn\b|\bcommunications\b", re.I), "Communications"),
    (re.compile(r"\bcertif|\bdcd\b|\bdesign\s+certificate", re.I), "Certification"),
    (re.compile(r"^CC-A-", re.I), "Architectural"),
    (re.compile(r"^E\d{2}\s*-", re.I), "Electrical"),
    (re.compile(r"^H-", re.I), "Hydraulic"),
    (re.compile(r"^F-", re.I), "Fire"),
]


@dataclass
class DocumentMetadata:
    document_number: str
    title: str
    revision: str
    discipline: str
    canonical_file_name: str
    confidence: Confidence


@dataclass
class _ParsedFields:
    document_number: str
    title: str
    revision: str
    confidence: Confidence


def parse_document_metadata(
    *,
    file_name: str,
    filed_path: str,
    preview_snippet: str | None = None,
    source_path: str | None = None,
) -> DocumentMetadata:
    base_name = file_name.split("/")[-1] if "/" in file_name else file_name
    extension = _extract_extension(base_name)
    stem = base_name[: len(base_name) - (len(extension) + 1 if extension else 0)]

    if _is_unparseable_file_name(base_name):
        return _build_metadata(
            _ParsedFields(
                document_number="",
                title=_humanize_stem(stem),
                revision="Current",
                confidence="low",
            ),
            base_name,
            filed_path,
            extension,
            source_path,
        )

    from_preview = _parse_from_preview(preview_snippet) if preview_snippet else None
    from_file_name = _parse_from_file_name(stem)
    merged = _merge_parsed_fields(from_preview, from_file_name)

    return _build_metadata(merged, base_name, filed_path, extension, source_path)


def parse_from_title_block_text(text: str) -> dict[str, str | Confidence] | None:
    compact = re.sub(r"\s+", " ", text.replace("\x00", " "))
    line_fields = _parse_title_block_lines(text)
    document_number = (
        line_fields.get("document_number")
        or _extract_label_value(
            compact,
            [
                re.compile(
                    r"(?:drawing|drg|dwg|sheet)\s+(?:no|number|#)\.?\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*)",
                    re.I,
                ),
                re.compile(
                    r"(?:document|doc)\s+(?:no|number|#)\.?\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*)",
                    re.I,
                ),
                re.compile(
                    r"(?:reference|ref)\s+(?:no|number|#)\.?\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*)",
                    re.I,
                ),
                re.compile(
                    r"(?:project|job|report)\s+(?:no|number|ref)\.?\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*)",
                    re.I,
                ),
            ],
        )
    )
    title = line_fields.get("title") or _extract_label_value(
        compact,
        [
            re.compile(
                r"(?:drawing|document|report)\s+title\s+(?!block\b)(.{3,120}?)(?:\s+(?:revision|rev|drawn|scale|date|project|checked|approved)\b|$)",
                re.I,
            ),
            re.compile(
                r"\btitle\s+(?!block\b)(.{3,120}?)(?:\s+(?:revision|rev|drawn|scale|date|project|checked|approved)\b|$)",
                re.I,
            ),
            re.compile(
                r"\bdescription\s*[:.]?\s*(.{3,120}?)(?:\s+(?:revision|rev|drawn|scale|date|project|checked|approved)\b|$)",
                re.I,
            ),
        ],
    )
    revision = line_fields.get("revision") or _extract_label_value(
        compact,
        [
            re.compile(
                r"\b(?:revision|issue|version)\b\.?\s*[:.]?\s*([A-Z0-9]+(?:\s*[-–—]\s*[A-Z][A-Z0-9\s]+)?)",
                re.I,
            ),
            re.compile(
                r"\brev\b\.?\s*[:.]?\s*([A-Z0-9]+(?:\s*[-–—]\s*[A-Z][A-Z0-9\s]+)?)",
                re.I,
            ),
        ],
    )

    expanded_ctmp_title = _expand_ctmp_title_from_text(compact, title)
    resolved_title = expanded_ctmp_title if expanded_ctmp_title is not None else (title or "")
    resolved_document_number = document_number
    if not resolved_document_number and re.search(
        r"\bctmp\b|\bconstruction\s+traffic\s+management\s+plan\b", compact, re.I
    ):
        resolved_document_number = _extract_label_value(
            compact,
            [
                re.compile(
                    r"(?:reference|ref|project|document|report|job)\s+(?:no|number|#)\.?\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*)",
                    re.I,
                ),
            ],
        )

    if not resolved_document_number and not resolved_title and not revision:
        return None

    normalized_revision = "Current"
    if revision and _is_valid_revision(_normalize_revision(revision)):
        normalized_revision = _normalize_revision(revision)

    confidence: Confidence
    if resolved_document_number and resolved_title:
        confidence = "high"
    elif resolved_document_number or resolved_title:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "document_number": resolved_document_number
        if _is_valid_document_number(resolved_document_number or "")
        else "",
        "title": resolved_title,
        "revision": normalized_revision,
        "confidence": confidence,
    }


def infer_discipline_from_path(filed_path: str) -> str | None:
    normalised = filed_path.replace("\\", "/")
    match = re.search(r"/(?:02-consultant|03-design)/([^/]+)", normalised, re.I)
    if not match:
        return None
    return DISCIPLINE_FOLDER_LABELS.get(match.group(1).lower())


def infer_discipline_from_inbox_path(source_path: str) -> str | None:
    normalised = source_path.replace("\\", "/")
    inbox_match = re.search(r"/_inbox/([^/]+)", normalised, re.I)
    if not inbox_match:
        return None
    folder_key = inbox_match.group(1).upper()
    decoded_key = unquote(inbox_match.group(1)).upper()
    return INBOX_FOLDER_DISCIPLINE_LABELS.get(decoded_key) or INBOX_FOLDER_DISCIPLINE_LABELS.get(
        folder_key
    )


def infer_discipline_from_file_name(stem: str) -> str | None:
    for pattern, label in FILENAME_DISCIPLINE_KEYWORDS:
        if pattern.search(stem):
            return label
    return None


def infer_lifecycle_category(filed_path: str) -> str:
    normalised = filed_path.replace("\\", "/")
    for pattern, label in LIFECYCLE_CATEGORY_BY_FOLDER:
        if pattern.search(normalised):
            return label
    return "Project"


def build_canonical_file_name(
    fields: _ParsedFields,
    extension: str,
    original_file_name: str,
) -> str:
    if fields.confidence == "low":
        return original_file_name

    suffix = f".{extension.lstrip('.')}" if extension else ""
    safe_revision = (
        _sanitize_file_component(fields.revision)
        if fields.revision
        and fields.revision != "Current"
        and _is_valid_revision(fields.revision)
        else ""
    )
    revision_suffix = f" Rev {safe_revision}" if safe_revision else ""
    safe_title = _sanitize_file_component(
        _normalize_title_for_canonical(fields.title, fields.document_number)
    )
    safe_number = (
        _sanitize_file_component(fields.document_number)
        if _is_valid_document_number(fields.document_number)
        else ""
    )

    if safe_number and safe_title and safe_title.lower() != safe_number.lower():
        base = f"{safe_number} - {safe_title}{revision_suffix}"
    elif safe_number:
        base = f"{safe_number}{revision_suffix}"
    elif safe_title:
        base = f"{safe_title}{revision_suffix}"
    else:
        return original_file_name

    candidate = _truncate_file_name(f"{base}{suffix}", 180)
    return candidate if _is_safe_canonical_file_name(candidate) else original_file_name


def _build_metadata(
    fields: _ParsedFields,
    original_file_name: str,
    filed_path: str,
    extension: str,
    source_path: str | None = None,
) -> DocumentMetadata:
    discipline = _resolve_discipline(filed_path, source_path, original_file_name)
    canonical_file_name = (
        original_file_name
        if fields.confidence == "low"
        else build_canonical_file_name(fields, extension, original_file_name)
    )
    return DocumentMetadata(
        document_number=fields.document_number,
        title=fields.title,
        revision=fields.revision,
        discipline=discipline,
        canonical_file_name=canonical_file_name,
        confidence=fields.confidence,
    )


def _merge_parsed_fields(
    preview: dict[str, str | Confidence] | None,
    file_name: _ParsedFields,
) -> _ParsedFields:
    if not preview:
        return _normalize_parsed_fields(file_name)

    preview_doc = preview.get("document_number", "")
    preview_document_number = preview_doc if _is_valid_document_number(str(preview_doc)) else ""
    file_document_number = (
        file_name.document_number if _is_valid_document_number(file_name.document_number) else ""
    )
    # A high-confidence filename that already carries both a number and a title
    # is authored deliberately (e.g. "CC-A-182 RCP - LEVEL 1.pdf") and is more
    # reliable than a title block flattened from a 2D sheet — where labels and
    # values can land out of order. Trust it outright over a conflicting preview.
    strong_filename_identity = (
        file_name.confidence == "high"
        and bool(file_document_number)
        and bool(_clean_title(file_name.title))
    )
    if strong_filename_identity:
        document_number = file_document_number
    else:
        document_number = preview_document_number or file_document_number

    preview_title_raw = preview.get("title", "")
    preview_title = (
        _normalize_title_for_canonical(str(preview_title_raw), document_number)
        if preview_title_raw
        else ""
    )
    file_title = (
        _normalize_title_for_canonical(file_name.title, document_number) if file_name.title else ""
    )
    if strong_filename_identity:
        title = file_title
    else:
        title = _choose_best_title(preview_title, file_title, document_number)

    preview_rev = preview.get("revision", "")
    preview_revision = (
        str(preview_rev) if preview_rev and _is_valid_revision(str(preview_rev)) else "Current"
    )
    file_revision = (
        file_name.revision if file_name.revision and _is_valid_revision(file_name.revision) else "Current"
    )
    if strong_filename_identity:
        # Keep the filename's revision; only accept a clean single-token revision
        # from the title block (rejects noise like "FOR CONSTRUCTION").
        if file_revision != "Current":
            revision = file_revision
        elif preview_revision != "Current" and re.match(r"^[A-Z0-9]{1,4}$", preview_revision):
            revision = preview_revision
        else:
            revision = "Current"
    elif preview_revision != "Current":
        revision = preview_revision
    elif file_revision != "Current":
        revision = file_revision
    else:
        revision = "Current"

    preview_confidence = preview.get("confidence", "low")
    has_preview_identity = bool(preview.get("document_number") or preview_title)
    has_strong_preview = preview_confidence == "high" and has_preview_identity
    has_strong_file_name = file_name.confidence == "high" and bool(
        file_name.document_number or file_title
    )

    confidence: Confidence = "low"
    if has_strong_preview or (has_strong_file_name and title):
        confidence = "high"
    elif (
        file_name.confidence == "medium"
        or preview_confidence == "medium"
        or document_number
        or title
    ):
        confidence = "medium"

    return _normalize_parsed_fields(
        _ParsedFields(
            document_number=document_number,
            title=title,
            revision=revision,
            confidence=confidence,
        )
    )


def _choose_best_title(preview_title: str, file_title: str, document_number: str) -> str:
    preview_is_placeholder = _is_placeholder_title(preview_title, document_number)
    file_is_placeholder = _is_placeholder_title(file_title, document_number)
    preview_is_corrupted = _is_corrupted_extracted_title(preview_title, file_title)

    if preview_title and not preview_is_placeholder and not preview_is_corrupted:
        return preview_title
    if file_title and not file_is_placeholder:
        return file_title
    return preview_title or file_title


def _is_corrupted_extracted_title(preview_title: str, file_title: str) -> bool:
    if not preview_title:
        return False
    if re.match(r"^[\s\-–—]+", preview_title):
        return True
    if (
        file_title
        and len(file_title) > len(preview_title) + 8
        and preview_title.lower() in file_title.lower()
    ):
        return len(preview_title) < 16 or bool(
            re.search(r"\b(?:drawing\s+no|title|rev(?:ision)?)\b", preview_title, re.I)
        )
    return False


def _normalize_parsed_fields(fields: _ParsedFields) -> _ParsedFields:
    document_number = (
        fields.document_number.strip() if _is_valid_document_number(fields.document_number) else ""
    )
    title = _normalize_title_for_canonical(fields.title, document_number)
    revision = fields.revision if _is_valid_revision(fields.revision) else "Current"
    return _ParsedFields(
        document_number=document_number,
        title=title,
        revision=revision,
        confidence=fields.confidence,
    )


def _parse_from_preview(preview: str) -> dict[str, str | Confidence] | None:
    markdown = _parse_from_markdown_table(preview)
    if markdown and markdown.get("document_number") and markdown.get("title"):
        return markdown

    title_block = parse_from_title_block_text(preview)
    if not markdown and not title_block:
        return None

    document_number = (title_block or {}).get("document_number") or (markdown or {}).get(
        "document_number", ""
    )
    title = (title_block or {}).get("title") or (markdown or {}).get("title", "")
    revision = (title_block or {}).get("revision") or (markdown or {}).get("revision", "Current")
    md_conf = (markdown or {}).get("confidence")
    tb_conf = (title_block or {}).get("confidence")
    if md_conf == "high" or tb_conf == "high":
        confidence: Confidence = "high"
    elif markdown or title_block:
        confidence = "medium"
    else:
        confidence = "low"

    if not document_number and not title:
        return None

    return {
        "document_number": str(document_number),
        "title": str(title),
        "revision": str(revision),
        "confidence": confidence,
    }


def _parse_from_markdown_table(preview: str) -> dict[str, str | Confidence] | None:
    frontmatter_match = re.search(r"^title:\s*(.+)$", preview, re.M)
    frontmatter_title = frontmatter_match.group(1).strip() if frontmatter_match else None

    drawing_number_match = re.search(
        r"\*\*Drawing number\*\*\s*\|\s*(.+?)\s*\|", preview, re.I
    ) or re.search(r"\*\*Drawing No\.?\*\*\s*\|\s*(.+?)\s*\|", preview, re.I)
    drawing_number = drawing_number_match.group(1).strip() if drawing_number_match else None

    drawing_title_match = re.search(
        r"\*\*Drawing title\*\*\s*\|\s*(.+?)\s*\|", preview, re.I
    ) or re.search(r"\*\*Title\*\*\s*\|\s*(.+?)\s*\|", preview, re.I)
    drawing_title = drawing_title_match.group(1).strip() if drawing_title_match else None

    revision_match = re.search(
        r"\*\*Revision\*\*\s*\|\s*\*?\*?(.+?)\*?\*?\s*\|", preview, re.I
    ) or re.search(r"\*\*Rev(?:ision)?\*\*\s*\|\s*(.+?)\s*\|", preview, re.I)
    revision_raw = revision_match.group(1).strip() if revision_match else None

    if not drawing_number and not drawing_title and not frontmatter_title:
        return None

    return {
        "document_number": drawing_number or "",
        "title": drawing_title or frontmatter_title or "",
        "revision": _normalize_revision(revision_raw or ""),
        "confidence": "high" if drawing_number and drawing_title else "medium",
    }


def _parse_title_block_lines(text: str) -> dict[str, str]:
    lines = [line.strip() for line in re.split(r"\r?\n", text) if line.strip()]
    fields: dict[str, str] = {}

    label_matchers: list[tuple[str, list[re.Pattern[str]]]] = [
        (
            "document_number",
            [
                re.compile(r"^drawing\s*(?:no|number|#)\b", re.I),
                re.compile(r"^drg\s*no\b", re.I),
                re.compile(r"^document\s*(?:no|number|#)\b", re.I),
                re.compile(r"^reference\s*(?:no|number|#)\b", re.I),
                re.compile(r"^project\s*(?:no|number|ref)\b", re.I),
                re.compile(r"^report\s*(?:no|number|#)\b", re.I),
                re.compile(r"^job\s*(?:no|number|ref)\b", re.I),
            ],
        ),
        (
            "title",
            [
                re.compile(r"^drawing\s*title\b", re.I),
                re.compile(r"^document\s*title\b", re.I),
                re.compile(r"^report\s*title\b", re.I),
                re.compile(r"^title\b", re.I),
                re.compile(r"^description\b", re.I),
            ],
        ),
        (
            "revision",
            [
                re.compile(r"^revision\b", re.I),
                re.compile(r"^rev\b", re.I),
                re.compile(r"^issue\b", re.I),
                re.compile(r"^version\b", re.I),
            ],
        ),
    ]

    for index, line in enumerate(lines):
        for field_name, patterns in label_matchers:
            if not any(p.search(line) for p in patterns):
                continue
            if field_name == "title" and re.search(r"^drawing\s+title\s+block\b", line, re.I):
                continue

            next_line = lines[index + 1] if index + 1 < len(lines) else None
            value = _read_title_block_label_value(line, next_line)
            if not value:
                continue
            if field_name == "document_number" and fields.get("document_number"):
                continue
            if field_name == "title" and fields.get("title"):
                continue
            if field_name == "revision" and fields.get("revision"):
                continue

            if field_name == "revision":
                if _is_title_block_noise_value(value):
                    continue
                normalized_revision = _normalize_revision(value)
                if not _is_valid_revision(normalized_revision):
                    continue
                fields["revision"] = normalized_revision
            elif field_name == "document_number":
                if not _is_valid_document_number(value) or _is_title_block_noise_value(value):
                    continue
                fields["document_number"] = value
            else:
                if _is_title_block_noise_value(value):
                    continue
                fields["title"] = value

    return fields


def _read_title_block_label_value(line: str, next_line: str | None = None) -> str:
    inline_label = re.match(
        r"^(?:drawing\s*(?:no|number|#)|drg\s*no|document\s*(?:no|number|#)|reference\s*(?:no|number|#)|project\s*(?:no|number|ref)|report\s*(?:no|number|#)|job\s*(?:no|number|ref)|drawing\s*title|document\s*title|report\s*title|title|description|revision|rev|issue|version)\.?\s+(.+)$",
        line,
        re.I,
    )
    if inline_label:
        return _clean_title(inline_label.group(1))

    colon_separated = re.match(r"^[^:]+:\s*(.+)$", line)
    if colon_separated:
        return _clean_title(colon_separated.group(1))

    return _clean_title(next_line) if next_line else ""


def _extract_label_value(text: str, patterns: list[re.Pattern[str]]) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match and match.group(1):
            value = _clean_title(match.group(1))
            if len(value) >= 2 and not _is_title_block_noise_value(value):
                return value
    return None


def _is_title_block_noise_value(value: str) -> bool:
    cleaned = re.sub(r"[:.\s]+$", "", value).strip()
    return bool(
        re.match(
            r"^(?:scale|date|drawn|checked|approved|sheet|size|format|project|job|title|description"
            r"|status|stage|client|revision|rev|issue|version|notes?|drawing|document|report"
            r"|reference|number|consultant|contractor"
            r"|at|as|not|for|use|n/a|tbc|tba|nil|none)$",
            cleaned,
            re.I,
        )
    )


def _expand_ctmp_title_from_text(text: str, existing_title: str | None = None) -> str | None:
    if existing_title and not re.match(r"^ctmp\b", existing_title, re.I):
        return None
    if not re.search(r"\bctmp\b|\bconstruction\s+traffic\s+management\s+plan\b", text, re.I):
        return None

    status_match = None
    if existing_title:
        status_match = re.match(r"^ctmp\s*\(([^)]+)\)$", existing_title, re.I)
    if not status_match:
        status_match = re.search(
            r"\bconstruction\s+traffic\s+management\s+plan\s*\(([^)]+)\)", text, re.I
        )

    if status_match:
        return f"Construction Traffic Management Plan ({_clean_title(status_match.group(1))})"
    return "Construction Traffic Management Plan"


def _parse_from_file_name(stem: str) -> _ParsedFields:
    attempts = [
        _match_cc_architectural,
        _match_architect_number,
        _match_electrical_sheet,
        _match_nbn_sheet,
        _match_hydraulic_fire_layout,
        _match_cm_report,
        _match_ctmp_report,
        _match_for_construction,
        _match_cost_invoice,
        _match_vista_transmittal,
        _match_structural_sheet,
        _match_fco_revision,
        _match_rev_parenthetical,
        _match_bracket_revision,
        _match_job_reference,
        _match_leading_number_title,
        _match_generic_title,
    ]
    for attempt in attempts:
        result = attempt(stem)
        if result:
            return result
    return _ParsedFields(
        document_number="",
        title=_humanize_stem(stem),
        revision="Current",
        confidence="low",
    )


def _match_cc_architectural(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(CC-A-\d{3})\s+(.+)$", stem, re.I)
    if not match:
        return None
    return _ParsedFields(
        document_number=match.group(1).upper(),
        title=_clean_title(match.group(2)),
        revision="Current",
        confidence="high",
    )


def _match_architect_number(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(A\d{3,4})\s+(.+)$", stem, re.I)
    if not match:
        return None
    return _ParsedFields(
        document_number=match.group(1).upper(),
        title=_clean_title(match.group(2)),
        revision="Current",
        confidence="high",
    )


def _match_electrical_sheet(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(E\d{2})\s*-\s*([A-Z\s]+?)\s*-\s*(.+?)\s*-\s*\[([^\]]+)\]$", stem, re.I)
    if not match:
        return None
    title = _clean_title(
        _strip_redundant_discipline_prefix(
            f"{match.group(2).strip()} - {match.group(3).strip()}", match.group(1)
        )
    )
    return _ParsedFields(
        document_number=match.group(1).upper(),
        title=title,
        revision=_normalize_revision(match.group(4)),
        confidence="high",
    )


def _match_nbn_sheet(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(.+?\s*-\s*NBN\s*-\s*)([A-Z0-9]+)\[([^\]]+)\]$", stem, re.I)
    if not match:
        return None
    return _ParsedFields(
        document_number=match.group(2).upper(),
        title=_clean_title(f"NBN {match.group(2)}"),
        revision=_normalize_revision(match.group(3)),
        confidence="high",
    )


def _match_hydraulic_fire_layout(stem: str) -> _ParsedFields | None:
    match = re.match(r"^([FH]-\d{3})-(.+)-Layout1$", stem, re.I)
    if not match:
        return None
    return _ParsedFields(
        document_number=match.group(1).upper(),
        title=_clean_title(match.group(2)),
        revision="Current",
        confidence="medium",
    )


def _match_ctmp_report(stem: str) -> _ParsedFields | None:
    match = re.match(r"^CTMP(?:\s*\(([^)]+)\))?$", stem, re.I)
    if not match:
        return None
    status = match.group(1).strip() if match.group(1) else None
    title = (
        f"Construction Traffic Management Plan ({status})"
        if status
        else "Construction Traffic Management Plan"
    )
    return _ParsedFields(
        document_number="",
        title=_clean_title(title),
        revision="Current",
        confidence="medium",
    )


def _match_cm_report(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(CM\d+-I\d+-R\d+)\s*-\s*(.+)$", stem, re.I)
    if not match:
        return None
    revision_match = re.search(r"R(\d+)$", match.group(1), re.I)
    return _ParsedFields(
        document_number=match.group(1).upper(),
        title=_clean_title(match.group(2)),
        revision=revision_match.group(1) if revision_match else "Current",
        confidence="high",
    )


def _match_for_construction(stem: str) -> _ParsedFields | None:
    match = re.match(
        r"^FOR\s+CONSTRUCTION\s+\d{2}\.\d{2}\.\d{2}\s*\[([^\]]+)\]\s*([^-]+?)(?:\s*-\s*(.+?))?(?:\s*\[([^\]]+)\])?$",
        stem,
        re.I,
    )
    if not match:
        return None
    document_number = match.group(2).strip()
    title = _clean_title(match.group(3).strip() if match.group(3) else document_number)
    revision = _normalize_revision(match.group(4) or match.group(1))
    return _ParsedFields(
        document_number=document_number,
        title=title,
        revision=revision,
        confidence="high",
    )


def _match_cost_invoice(stem: str) -> _ParsedFields | None:
    if re.search(r"\bvar[-_]", stem, re.I):
        return None
    date_match = re.match(r"^(\d{4}-\d{2}(?:-\d{2})?)\s*-\s*(.+)$", stem)
    if not date_match:
        return None
    remainder = date_match.group(2)
    separator_index = remainder.rfind(" - ")
    if separator_index <= 0:
        return None
    return _ParsedFields(
        document_number=remainder[:separator_index].strip(),
        title=_clean_title(remainder[separator_index + 3 :]),
        revision="Current",
        confidence="medium",
    )


def _match_vista_transmittal(stem: str) -> _ParsedFields | None:
    match = re.match(
        r"^(\d{5})\s+(.+?)_(?:CC|PS\d)_(?:Issue\s+)?([A-Z0-9+]+)$", stem, re.I
    )
    if not match:
        return None
    return _ParsedFields(
        document_number=match.group(1),
        title=_clean_title(match.group(2).replace("_", " ")),
        revision=_normalize_revision(match.group(3)),
        confidence="medium",
    )


def _match_structural_sheet(stem: str) -> _ParsedFields | None:
    repeated = re.match(
        r"^(S\d{3})\s*-\s*(.+?)\s+Drawing\s+No\.?\s*[-–—]\s*\1\s+Rev\s+([A-Z0-9]+)$",
        stem,
        re.I,
    )
    if repeated:
        return _ParsedFields(
            document_number=repeated.group(1).upper(),
            title=_clean_title(repeated.group(2)),
            revision=_normalize_revision(repeated.group(3)),
            confidence="medium",
        )

    suffix = re.match(
        r"^(?:Drawing\s+No\.?\s+Rev\.?\s*[-–—]\s*)?(.+?)\s+Drawing\s+No\.?\s*[-–—]\s*(S\d{3})\s+Rev\s+([A-Z0-9]+)$",
        stem,
        re.I,
    )
    if suffix:
        return _ParsedFields(
            document_number=suffix.group(2).upper(),
            title=_clean_title(suffix.group(1)),
            revision=_normalize_revision(suffix.group(3)),
            confidence="medium",
        )

    match = re.match(r"^(S\d{3})-(\d{2})$", stem, re.I)
    if not match:
        return None
    return _ParsedFields(
        document_number=match.group(1).upper(),
        title="",
        revision=match.group(2),
        confidence="medium",
    )


def _match_fco_revision(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(FCO\s*\d+)\s+Rev\s+([A-Z0-9]+)$", stem, re.I) or re.match(
        r"^Short\s+form\s+(FCO-\d+)\s+Revision\s+([A-Z0-9]+)$", stem, re.I
    )
    if not match:
        return None
    doc_num = re.sub(r"\s+", " ", match.group(1)).upper()
    return _ParsedFields(
        document_number=doc_num,
        title=_clean_title(match.group(1)),
        revision=_normalize_revision(match.group(2)),
        confidence="medium",
    )


def _match_rev_parenthetical(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(.+?)\s*\(\s*Rev(?:ision)?\s*([^)]+)\)$", stem, re.I) or re.match(
        r"^(.+?)\s*\(\s*rev([^)]+)\)$", stem, re.I
    )
    if not match:
        return None
    title_part = _clean_title(match.group(1))
    number_match = re.match(r"^([A-Z0-9][A-Z0-9-]*)\s+(.+)$", title_part, re.I)
    return _ParsedFields(
        document_number=number_match.group(1) if number_match else "",
        title=number_match.group(2) if number_match else title_part,
        revision=_normalize_revision(match.group(2)),
        confidence="medium",
    )


def _match_bracket_revision(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(.+?)\s*\[([^\]]+)\]$", stem)
    if not match:
        return None
    left = match.group(1).strip()
    revision = _normalize_revision(match.group(2))
    dash_parts = re.split(r"\s*-\s*", left)

    if len(dash_parts) >= 2 and re.match(r"^[A-Z0-9][A-Z0-9-]*$", dash_parts[0], re.I):
        return _ParsedFields(
            document_number=dash_parts[0],
            title=_clean_title(" - ".join(dash_parts[1:])),
            revision=revision,
            confidence="medium",
        )

    spaced = re.match(r"^([A-Z0-9][A-Z0-9-]*)\s+(.+)$", left, re.I)
    if spaced:
        return _ParsedFields(
            document_number=spaced.group(1),
            title=_clean_title(spaced.group(2)),
            revision=revision,
            confidence="medium",
        )

    return _ParsedFields(
        document_number=re.sub(r"\s+", "-", left).upper(),
        title=_clean_title(left),
        revision=revision,
        confidence="medium",
    )


def _match_job_reference(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(J\d{4}-\d{3}-\d{3})\.\d{2}\.\d{2}\.\d{2}$", stem, re.I)
    if not match:
        return None
    return _ParsedFields(
        document_number=match.group(1).upper(),
        title=_clean_title(match.group(1)),
        revision="Current",
        confidence="medium",
    )


def _match_leading_number_title(stem: str) -> _ParsedFields | None:
    match = re.match(r"^(\d{4,})\s+(.+)$", stem)
    if not match:
        return None
    return _ParsedFields(
        document_number=match.group(1),
        title=_clean_title(match.group(2)),
        revision="Current",
        confidence="medium",
    )


def _match_generic_title(stem: str) -> _ParsedFields | None:
    if len(stem) < 2:
        return None

    rev_suffix = re.search(r"\bRev(?:ision)?\s+([A-Z0-9]+)$", stem, re.I)
    if rev_suffix:
        without_rev = stem[: rev_suffix.start()].strip()
        number_title = re.match(r"^([A-Z0-9][A-Z0-9-]*)\s+(.+)$", without_rev, re.I)
        return _ParsedFields(
            document_number=number_title.group(1) if number_title else "",
            title=_clean_title(number_title.group(2) if number_title else without_rev),
            revision=_normalize_revision(rev_suffix.group(1)),
            confidence="medium",
        )

    opaque_code = re.match(r"^[A-Z]?\d{1,4}$", stem, re.I)
    if opaque_code:
        return _ParsedFields(
            document_number=stem.upper(),
            title=_clean_title(stem),
            revision="Current",
            confidence="medium",
        )

    return _ParsedFields(
        document_number="",
        title=_clean_title(stem),
        revision="Current",
        confidence="low",
    )


def _resolve_discipline(
    filed_path: str,
    source_path: str | None,
    file_name: str,
) -> str:
    from_design_path = infer_discipline_from_path(filed_path)
    if from_design_path:
        return from_design_path

    from_inbox = infer_discipline_from_inbox_path(source_path or filed_path)
    from_lifecycle = _lifecycle_discipline(filed_path)
    from_file_name = infer_discipline_from_file_name(file_name)

    if from_inbox and from_lifecycle == "Construction" and from_inbox != "Construction":
        return from_inbox

    if from_lifecycle and re.search(
        r"/(?:01-cost|05-procurement|08-meetings-reporting|09-handover-dlp)/",
        filed_path,
        re.I,
    ):
        return from_lifecycle

    return (
        from_inbox
        or from_file_name
        or from_lifecycle
        or infer_lifecycle_category(filed_path)
    )


def _lifecycle_discipline(filed_path: str) -> str | None:
    category = infer_lifecycle_category(filed_path)
    return None if category == "Project" else category


def _is_unparseable_file_name(file_name: str) -> bool:
    return "~" in file_name or bool(re.search(r"\d{4}-\d{2}-\d{2}_.*VAR", file_name, re.I))


def _extract_extension(file_name: str) -> str:
    match = re.search(r"\.([^.]+)$", file_name)
    return match.group(1) if match else ""


def _normalize_revision(value: str) -> str:
    cleaned = re.sub(r"^rev(?:ision)?\s*", "", value, flags=re.I)
    cleaned = re.sub(r"\s*—.*$", "", cleaned)
    cleaned = re.sub(r"\s*-\s*.*$", "", cleaned)
    cleaned = re.sub(r"[:.\s]+$", "", cleaned).strip()

    if (
        not cleaned
        or re.match(r"^current$", cleaned, re.I)
        or _is_title_block_noise_value(cleaned)
        or re.match(r"^scale", cleaned, re.I)
    ):
        return "Current"
    return cleaned.upper()


def _is_valid_document_number(value: str | None) -> bool:
    cleaned = _clean_title(value or "")
    if not cleaned or len(cleaned) < 2:
        return False
    if not re.search(r"[A-Z0-9]", cleaned, re.I):
        return False
    if re.match(r"^[-–—./\s]+$", cleaned):
        return False
    return True


def _is_valid_revision(value: str | None) -> bool:
    if not value or value == "Current":
        return True
    cleaned = _sanitize_file_component(_normalize_revision(value))
    if not cleaned or cleaned == "Current":
        return False
    if _is_title_block_noise_value(cleaned) or re.match(r"^SCALE\b", cleaned, re.I):
        return False
    if re.search(r"[:/]", cleaned):
        return False
    if len(cleaned) > 24:
        return False
    return bool(re.match(r"^[A-Z0-9][A-Z0-9\s\-–—]*$", cleaned, re.I))


def _is_safe_canonical_file_name(file_name: str) -> bool:
    if not file_name.strip() or re.search(r'[<>:"/\\|?*]', file_name):
        return False
    if re.match(r"^[\s\-–—]+( - |$)", file_name):
        return False
    return True


def _clean_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    while re.match(r"^[\s\-–—]+", cleaned):
        cleaned = re.sub(r"^[\s\-–—]+", "", cleaned).strip()
    return re.sub(r"\s-\s$", "", cleaned).strip()


def _normalize_title_for_canonical(title: str, document_number: str) -> str:
    cleaned = _clean_title(title)
    cleaned = _strip_redundant_discipline_prefix(cleaned, document_number)
    cleaned = _dedupe_title_from_number(cleaned, document_number)
    return cleaned


def _strip_redundant_discipline_prefix(title: str, document_number: str) -> str:
    if not title:
        return title
    if re.match(r"^E\d{2}$", document_number, re.I):
        return re.sub(r"^ELECTRICAL\s*[-–—]\s*", "", title, flags=re.I).strip()
    if re.match(r"^H-", document_number, re.I):
        return re.sub(r"^HYDRAULIC\s*[-–—]\s*", "", title, flags=re.I).strip()
    if re.match(r"^S\d{3}$", document_number, re.I):
        return re.sub(r"^STRUCTURAL\s*[-–—]\s*", "", title, flags=re.I).strip()
    return title


def _dedupe_title_from_number(title: str, document_number: str) -> str:
    cleaned = _clean_title(title)
    if not cleaned:
        return ""
    if not document_number:
        return cleaned

    escaped = re.escape(document_number)
    if re.match(rf"^structural\s+drawing\s+{escaped}\s*$", cleaned, re.I):
        return ""
    cleaned = re.sub(rf"^{escaped}\s*[-–—:\s]+", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(rf"\s*[-–—]\s*{escaped}\s*$", "", cleaned, flags=re.I).strip()
    if cleaned.upper() == document_number.upper():
        return ""
    return cleaned


def _is_placeholder_title(title: str, document_number: str) -> bool:
    if not title:
        return True
    normalized_title = _clean_title(title)
    if not normalized_title:
        return True
    if document_number and normalized_title.upper() == document_number.upper():
        return True
    if re.match(r"^structural\s+drawing(\s+[A-Z0-9-]+)?$", normalized_title, re.I):
        return True
    if document_number:
        escaped = re.escape(document_number)
        if re.match(rf"^{escaped}\s*[-–—]?\s*$", normalized_title, re.I):
            return True
    return False


def _humanize_stem(stem: str) -> str:
    return _clean_title(re.sub(r"[-_]+", " ", stem))


def _sanitize_file_component(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r'[<>:"/\\|?*]', "-", value)).strip()


def _truncate_file_name(file_name: str, max_length: int) -> str:
    if len(file_name) <= max_length:
        return file_name
    extension = _extract_extension(file_name)
    stem = file_name[: len(file_name) - (len(extension) + 1 if extension else 0)]
    stem_max = max_length - (len(extension) + 1 if extension else 0)
    truncated_stem = stem[: max(stem_max, 20)].strip()
    return f"{truncated_stem}.{extension}" if extension else truncated_stem
