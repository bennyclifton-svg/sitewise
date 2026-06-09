"""Classify inbox files into known SiteWise lifecycle destination folders."""

from __future__ import annotations

import re
from urllib.parse import unquote

from ingest.document_metadata import (
    DISCIPLINE_FOLDER_LABELS,
    infer_discipline_from_file_name,
)

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

_FILENAME_DESTINATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^CC-A-", re.I), "03-design/architect"),
    (re.compile(r"^E\d{2}\b", re.I), "03-design/electrical"),
    (re.compile(r"^H-", re.I), "03-design/hydraulic"),
    (re.compile(r"^F-", re.I), "03-design/fire"),
    (re.compile(r"^S\d{3}", re.I), "03-design/structural"),
    (re.compile(r"\bctmp\b", re.I), "03-design/civil"),
    (re.compile(r"\b(tender|submission|procurement|quote)\b", re.I), "05-procurement"),
    (re.compile(r"\b(invoice|claim|estimate|budget|cost)\b", re.I), "01-cost"),
    (re.compile(r"\b(minutes|meeting)\b", re.I), "08-meetings-reporting"),
]

_BRIEF_FILENAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(owner[-_ ]?)?project[-_ ]?brief\b", re.I),
    re.compile(r"\bclient[-_ ]?brief\b", re.I),
    re.compile(r"\bpmp[-_ ]?(draft|brief)\b", re.I),
    re.compile(r"\brole[-_ ]?declaration\b", re.I),
    re.compile(r"\bbrief[-_ ]?sign[-_ ]?off\b", re.I),
    re.compile(r"\bemail[-_ ]?thread[-_ ].*\bbrief\b", re.I),
]

_CONSULTANT_COMMERCIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bfee[-_ ]?proposal\b", re.I),
    re.compile(r"\bengagement[-_ ]?letter\b", re.I),
    re.compile(r"\bletter[-_ ]?of[-_ ]?engagement\b", re.I),
    re.compile(r"\bconsultant[-_ ]?(appointment|agreement)\b", re.I),
    re.compile(r"\bscope[-_ ]?of[-_ ]?services\b", re.I),
    re.compile(r"\bappointment[-_ ]?letter\b", re.I),
]

_AUTHORITY_DESTINATION = "04-planning-and-authorities"

_AUTHORITY_FILENAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bplanning[-_ ]?pathway\b", re.I),
    re.compile(r"\bauthorit(y|ies)[-_ ]?pathway\b", re.I),
    re.compile(r"\bcdc[-_ ]?screening\b", re.I),
    re.compile(r"\bprincipal[-_ ]?certifier\b", re.I),
    re.compile(r"\bcertifier[-_ ]?appointment\b", re.I),
]

_PREVIEW_AUTHORITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*#\s*planning\s+pathway\s+memo\b", re.I | re.M),
    re.compile(r"\bDA\s*(?:\+|/)\s*CC\s+pathway\b", re.I),
    re.compile(r"\bComplying Development\s*\(CDC\)\b", re.I),
    re.compile(r"\bDevelopment Application\s*\(DA\)\b", re.I),
    re.compile(r"\bprincipal\s+certifier\s+appointed\b", re.I),
    re.compile(r"\bcertifier\s+engagement\s+on\s+file\b", re.I),
]

_PREVIEW_BRIEF_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*#\s*(owner[-_ ]?)?project[-_ ]?brief\b", re.I | re.M),
    re.compile(r"^\s*#\s*client[-_ ]?brief\b", re.I | re.M),
    re.compile(r"^\s*#\s*project[-_ ]?management[-_ ]?plan\b", re.I | re.M),
    re.compile(r"\bbrief formal sign[-_ ]?off\b", re.I),
    re.compile(r"Subject:\s*RE:.*\bowner brief\b", re.I),
]

_PREVIEW_CONSULTANT_COMMERCIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*#\s*fee[-_ ]?proposal\b", re.I | re.M),
    re.compile(r"^\s*#\s*letter[-_ ]?of[-_ ]?engagement\b", re.I | re.M),
    re.compile(r"^\s*#\s*engagement[-_ ]?letter\b", re.I | re.M),
]

_DUE_DILIGENCE_DESTINATION = "03-design/01-due-diligence"

_DUE_DILIGENCE_FILENAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bsurvey[-_ ]?report\b", re.I),
    re.compile(r"\b(feature|level)[-_ ]?survey\b", re.I),
    re.compile(r"\bgeotechnical[-_ ]?(investigation[-_ ]?)?report\b", re.I),
    re.compile(r"\bgeotech[-_ ]?report\b", re.I),
    re.compile(r"\bdilapidation[-_ ]?(condition[-_ ]?)?report\b", re.I),
    re.compile(r"\bdilapidation\b", re.I),
    re.compile(r"\bsydney[-_ ]?water\b", re.I),
    re.compile(r"\bsewer(age)?[-_ ]?(services[-_ ]?)?diagram\b", re.I),
    re.compile(r"\bbuild[-_ ]?over[-_ ]?sewer\b", re.I),
    re.compile(r"\bheritage[-_ ]?(advisor|desktop|assessment)\b", re.I),
    re.compile(r"\bdue[-_ ]?diligence\b", re.I),
]

_PREVIEW_DUE_DILIGENCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*#\s*(feature\s*[&]\s*)?level\s*survey\b", re.I | re.M),
    re.compile(r"^\s*#\s*geotechnical\s+investigation\s+report\b", re.I | re.M),
    re.compile(r"^\s*#\s*dilapidation\s+condition\s+report\b", re.I | re.M),
    re.compile(r"\bgeotechnical investigation report on file\b", re.I),
    re.compile(r"\bsewerage services diagram\b", re.I),
    re.compile(r"\bpre-demolition dilapidation\b", re.I),
]

_MANIFEST_PATTERN = re.compile(r"^intake_manifest_v\d+\.md$", re.I)


def is_intake_manifest(filename: str) -> bool:
    return bool(_MANIFEST_PATTERN.match(filename))


def inbox_package_folder(workspace_path: str, project_workspace_path: str) -> str | None:
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
    matches = [slug for slug, mapped in DISCIPLINE_FOLDER_LABELS.items() if mapped == label]
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


def _consultant_destination(*, stem: str, preview_snippet: str | None) -> str:
    discipline_slug = _infer_discipline_slug(stem=stem, preview_snippet=preview_snippet)
    if discipline_slug:
        return f"02-consultant/{discipline_slug}"
    return "02-consultant"


def _matches_any(patterns: list[re.Pattern[str]], *texts: str) -> bool:
    for text in texts:
        if not text:
            continue
        for pattern in patterns:
            if pattern.search(text):
                return True
    return False


def classify_inbox_destination(
    *,
    workspace_path: str,
    filename: str,
    project_workspace_path: str,
    preview_snippet: str | None = None,
) -> str | None:
    """Return a confident lifecycle destination folder or None when unresolved."""
    if is_intake_manifest(filename):
        return None

    package = inbox_package_folder(workspace_path, project_workspace_path)
    if package:
        decoded = unquote(package).upper()
        destination = INBOX_PACKAGE_DESTINATIONS.get(decoded) or INBOX_PACKAGE_DESTINATIONS.get(
            package.upper()
        )
        if destination:
            return destination

    stem = filename.rsplit(".", maxsplit=1)[0] if "." in filename else filename

    if _matches_any(_AUTHORITY_FILENAME_PATTERNS, stem, filename) or _matches_any(
        _PREVIEW_AUTHORITY_PATTERNS, preview_snippet or ""
    ):
        return _AUTHORITY_DESTINATION

    if _matches_any(_CONSULTANT_COMMERCIAL_PATTERNS, stem, filename) or _matches_any(
        _PREVIEW_CONSULTANT_COMMERCIAL_PATTERNS, preview_snippet or ""
    ):
        return _consultant_destination(stem=stem, preview_snippet=preview_snippet)

    if _matches_any(_BRIEF_FILENAME_PATTERNS, stem, filename) or _matches_any(
        _PREVIEW_BRIEF_PATTERNS, preview_snippet or ""
    ):
        return "00-brief-pmp"

    if _matches_any(_DUE_DILIGENCE_FILENAME_PATTERNS, stem, filename) or _matches_any(
        _PREVIEW_DUE_DILIGENCE_PATTERNS, preview_snippet or ""
    ):
        return _DUE_DILIGENCE_DESTINATION

    for pattern, destination in _FILENAME_DESTINATION_PATTERNS:
        if pattern.search(stem) or pattern.search(filename):
            return destination

    return None
