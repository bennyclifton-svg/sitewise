"""Route classified documents into known SiteWise lifecycle destination folders."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from ingest.classify import classify_entry
from ingest.document_metadata import (
    DISCIPLINE_FOLDER_LABELS,
    infer_discipline_from_file_name,
)
from ingest.types import Classification, ManifestEntry

# Top-level `_inbox/<package>/` folder → destination path relative to project workspace.
INBOX_PACKAGE_DESTINATIONS: dict[str, str] = {
    "ACCESS": "03-design/architect",
    "ACOUSTIC": "03-design/architect",
    "ARCHITECTURE": "03-design/architect",
    "ASP3": "04-planning-and-authorities",
    "BASIX": "04-planning-and-authorities",
    "CIVIL": "03-design/civil",
    "DA, MODS & STAMPED PLANS": "04-planning-and-authorities",
    "ELEC": "03-design/electrical",
    "ELECTRICAL": "03-design/electrical",
    "FACADE REPORT": "03-design/architect",
    "FER - PRIMARY": "03-design/fire",
    "FER - RITEK": "03-design/fire",
    "FIRE MATRIX": "03-design/fire",
    "FIRE WET & DRY": "03-design/fire",
    "HYDRAULIC": "03-design/hydraulic",
    "LANDSCAPE": "03-design/landscape-architect",
    "LIFT": "03-design/mechanical",
    "MECH": "03-design/mechanical",
    "NBN": "03-design/electrical",
    "ROOF ACCESS": "03-design/architect",
    "SECTION J": "03-design/energy-assessor",
    "SITE INVESTIGATION": "03-design/geotechnical",
    "STORMWATER": "03-design/civil",
    "STRUCTURAL": "03-design/structural",
    "STRUCTURAL BALUSTRADE DESIGN": "03-design/structural",
    "TRAFFIC": "03-design/civil",
    "WASTE MGT PLAN": "07-construction/site-management",
    "WATERPROOFING": "03-design/architect",
    "s73 NOR DEVELOPER DEED & MLIM": "04-planning-and-authorities",
}

# Discipline sheet prefixes — routing, not semantic (Stage 6.1 split).
_FILENAME_ROUTING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^CC-A-", re.I), "03-design/architect"),
    (
        re.compile(r"^(?:\d{3,6}[\s_-]+)?M-?\d{2,4}\b", re.I),
        "03-design/mechanical",
    ),
    (
        re.compile(r"^(?:\d{3,6}[\s_-]+)?E-?\d{2,4}\b", re.I),
        "03-design/electrical",
    ),
    (re.compile(r"^H-", re.I), "03-design/hydraulic"),
    (re.compile(r"^F-", re.I), "03-design/fire"),
    (re.compile(r"^S\d{3}", re.I), "03-design/structural"),
    (re.compile(r"\bctmp\b", re.I), "03-design/civil"),
]

_ROUTES: dict[tuple[str, str], str] = {
    ("commercial", "cost"): "01-cost",
    ("commercial", "contract_admin"): "01-cost/variations",
    ("report", "structural"): "03-design/structural",
    ("report", "geotechnical"): "03-design/01-due-diligence",
    ("report", "survey"): "03-design/01-due-diligence",
    ("report", "heritage"): "03-design/01-due-diligence",
    ("report", "planning"): "04-planning-and-authorities",
    ("certificate", "planning"): "04-planning-and-authorities",
    ("schedule", "programme"): "06-programme",
    ("schedule", "cost"): "01-cost",
}

_ROUTES_BY_CLASS: dict[str, str | None] = {
    "statutory_instrument": "04-planning-and-authorities",
    "certificate": "04-planning-and-authorities",
    "contract": "02-consultant",
    "correspondence": "08-meetings-reporting",
    "photo": "07-construction/photos",
    "drawing": None,
    "specification": None,
    "commercial": None,
    "schedule": None,
    "unknown": None,
}

_MANIFEST_PATTERN = re.compile(r"^intake_manifest_v\d+\.md$", re.I)


def is_intake_manifest(filename: str) -> bool:
    return bool(_MANIFEST_PATTERN.match(filename))


def inbox_package_folder(
    workspace_path: str, project_workspace_path: str
) -> str | None:
    """Return the top-level inbox package folder name, if any."""
    prefix = f"{project_workspace_path.rstrip('/')}/_inbox/"
    normalised = workspace_path.replace("\\", "/")
    if not normalised.startswith(prefix):
        return None
    remainder = normalised[len(prefix) :]
    if not remainder or "/" not in remainder:
        return None
    return unquote(remainder.split("/", maxsplit=1)[0])


def _slug_for_discipline_label(label: str) -> str | None:
    matches = [
        slug for slug, mapped in DISCIPLINE_FOLDER_LABELS.items() if mapped == label
    ]
    if not matches:
        return None
    canonical = [slug for slug in matches if "-engineer" not in slug]
    return (canonical or matches)[0]


def _infer_discipline_slug(*, stem: str, preview_snippet: str | None) -> str | None:
    for text in (stem, preview_snippet or ""):
        label = infer_discipline_from_file_name(text)
        if label:
            slug = _slug_for_discipline_label(label)
            if slug:
                return slug
    return None


def _consultant_destination(discipline_slug: str | None) -> str:
    if discipline_slug:
        return f"02-consultant/{discipline_slug}"
    return "02-consultant"


def _discipline_for(
    classification: Classification, *, filename: str
) -> str | None:
    slug = classification.document_metadata.get("discipline")
    if slug:
        return slug
    stem = filename.rsplit(".", maxsplit=1)[0] if "." in filename else filename
    return _infer_discipline_slug(stem=stem, preview_snippet=None)


def _filename_routing(filename: str) -> str | None:
    stem = filename.rsplit(".", maxsplit=1)[0] if "." in filename else filename
    for pattern, destination in _FILENAME_ROUTING_PATTERNS:
        if pattern.search(stem) or pattern.search(filename):
            return destination
    return None


def filing_destination(
    classification: Classification,
    *,
    workspace_path: str,
    filename: str,
    project_workspace_path: str,
) -> str | None:
    """Route a classified document to a lifecycle folder. Makes no semantic
    judgement — it only reads the canonical Classification."""

    package = inbox_package_folder(workspace_path, project_workspace_path)
    if package and (dest := INBOX_PACKAGE_DESTINATIONS.get(unquote(package).upper())):
        return dest

    metadata = classification.document_metadata
    if metadata.get("procurement_stage"):
        return "05-procurement"

    commercial_type = metadata.get("commercial_type")
    if commercial_type == "fee_proposal":
        return _consultant_destination(
            _discipline_for(classification, filename=filename)
        )
    if commercial_type == "quote":
        return "05-procurement/quotes"
    if metadata.get("brief_kind"):
        return "00-brief-pmp"
    if metadata.get("due_diligence"):
        return "03-design/01-due-diligence"

    pair = _ROUTES.get((classification.document_class, classification.document_subject))
    if pair is not None:
        return pair
    by_class = _ROUTES_BY_CLASS.get(classification.document_class)
    if by_class is not None:
        return by_class

    routed = _filename_routing(filename)
    if routed is not None:
        return routed

    discipline_slug = _discipline_for(classification, filename=filename)
    if discipline_slug:
        return f"03-design/{discipline_slug}"

    return None


def classify_inbox_destination(
    *,
    workspace_path: str,
    filename: str,
    project_workspace_path: str,
    preview_snippet: str | None = None,
) -> str | None:
    """Shim: classify then route. Stage 7 wires sort_service to filing_destination."""
    if is_intake_manifest(filename):
        return None

    extension = ""
    if "." in filename:
        extension = "." + filename.rsplit(".", maxsplit=1)[-1]
    entry = ManifestEntry(
        absolute_path=Path(workspace_path),
        relative_path=workspace_path,
        project=project_workspace_path.split("/", maxsplit=1)[0],
        filename=filename,
        extension=extension,
        size_bytes=0,
    )
    classification = classify_entry(entry, extracted_text=preview_snippet)
    return filing_destination(
        classification,
        workspace_path=workspace_path,
        filename=filename,
        project_workspace_path=project_workspace_path,
    )
