"""Promote issuing-firm document metadata into shared consultant facts."""

from __future__ import annotations

import re
from typing import Any

from app.database.project import Project
from app.database.source_document import SourceDocument
from app.projects.project_knowledge import (
    SharedProjectObject,
    SharedProjectObjectConflict,
    SharedProjectObjectUpdate,
    get_shared_project_object,
    list_shared_project_objects,
    upsert_shared_project_object,
    write_shared_project_object,
)
from ingest.consultant_firm import (
    extract_issuing_firm_from_text,
    is_noise_firm_candidate,
)

# Map document discipline labels / folder cues onto PMP register rows.
_DISCIPLINE_TO_REGISTER: dict[str, str] = {
    "architect": "Architect",
    "architectural": "Architect",
    "structural": "Structural Engineer",
    "civil": "Civil Engineer",
    "geotechnical": "Geotechnical Engineer",
    "hydraulic": "Services Engineer (Hydraulic)",
    "electrical": "Services Engineer (Electrical)",
    "mechanical": "Services Engineer (Mechanical)",
    "services": "Services Engineer",
    "fire": "Fire Engineer",
    "facade": "Facade Engineer",
    "landscape": "Landscape Architect",
    "landscape architectural": "Landscape Architect",
    "acoustic": "Acoustic Consultant",
    "access": "Access Consultant",
    "traffic": "Traffic Engineer",
    "vertical transportation": "Vertical Transport Consultant",
    "vertical transport": "Vertical Transport Consultant",
    "waterproofing": "Waterproofing Consultant",
    "demolition": "Demolition Consultant",
    "hazmat": "Hazmat Consultant",
}

_STATUS_RANK = {
    "Report/drawings on file; appointment unverified": 1,
    "Certificate/DCD on file; appointment unverified": 2,
    "Engagement evidenced": 3,
}

_FIRM_PREFERENCE = {
    "fire engineer": (
        "Fire Safety Studio Pty Ltd",
        "TDL Engineering Consulting Pty Ltd",
    ),
    "architect": ("Roda Architects Pty Ltd",),
    "services engineer (hydraulic)": ("TDL Engineering Consulting Pty Ltd",),
    "structural engineer": ("Zait Engineering Solutions Pty Ltd",),
    "landscape architect": ("Sulphurcrest Enterprises Pty Ltd",),
    "acoustic consultant": ("Acoustic Logic Pty Ltd",),
    "access consultant": ("Vista Access Architects Pty Ltd",),
}


def _prefer_firm(discipline: str, current: str | None, candidate: str) -> str:
    prefs = _FIRM_PREFERENCE.get(discipline.strip().lower(), ())
    for preferred in prefs:
        if candidate.casefold() == preferred.casefold():
            return preferred
        if current and current.casefold() == preferred.casefold():
            return preferred
    return candidate or (current or "")

_CERT_HINT = re.compile(r"(?i)\b(?:certificate|dcd|design\s+compliance)\b")


def map_discipline_to_register_label(discipline: str | None) -> str | None:
    if not discipline:
        return None
    key = re.sub(r"\s+", " ", discipline).strip().lower()
    if key in _DISCIPLINE_TO_REGISTER:
        return _DISCIPLINE_TO_REGISTER[key]
    # Already a taxonomy register label.
    if "engineer" in key or "consultant" in key or key == "architect":
        return discipline.strip()
    return None


def evidence_status_for_kind(document_class: str | None, *, filename: str = "") -> str:
    blob = f"{document_class or ''} {filename}"
    if _CERT_HINT.search(blob) or (document_class or "").lower() == "certificate":
        return "Certificate/DCD on file; appointment unverified"
    return "Report/drawings on file; appointment unverified"


def _object_id_for_discipline(register_label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", register_label.lower()).strip("-")
    return slug or "consultant"


def _firm_from_document(document: SourceDocument) -> str | None:
    metadata = document.document_metadata if isinstance(document.document_metadata, dict) else {}
    firm = str(metadata.get("issuing_firm") or "").strip()
    if firm and not is_noise_firm_candidate(firm):
        return firm
    return extract_issuing_firm_from_text(document.normalized_content or "")


def _discipline_from_document(document: SourceDocument) -> str | None:
    metadata = document.document_metadata if isinstance(document.document_metadata, dict) else {}
    mapped = map_discipline_to_register_label(str(metadata.get("discipline") or "") or None)
    if mapped:
        return mapped
    path = (document.relative_path or "").replace("\\", "/")
    match = re.search(r"/(?:02-consultant|03-design)/([^/]+)", path, re.I)
    if match:
        return map_discipline_to_register_label(match.group(1).replace("-", " "))
    return None


def upsert_consultant_fact_from_document(
    project: Project,
    document: SourceDocument,
) -> SharedProjectObject | None:
    firm = _firm_from_document(document)
    discipline = _discipline_from_document(document)
    if not firm or not discipline or is_noise_firm_candidate(firm):
        return None

    object_id = _object_id_for_discipline(discipline)
    existing = get_shared_project_object(
        project, kind="consultant", object_id=object_id
    )
    evidence_kind = evidence_status_for_kind(
        document.document_class, filename=document.filename or ""
    )
    paths: list[str] = []
    if existing and isinstance(existing.value.get("evidence_paths"), list):
        paths = [str(p) for p in existing.value["evidence_paths"]]
    if document.relative_path and document.relative_path not in paths:
        paths.append(document.relative_path)

    previous_status = (
        str(existing.value.get("status") or "") if existing else ""
    )
    status = evidence_kind
    if _STATUS_RANK.get(previous_status, 0) > _STATUS_RANK.get(status, 0):
        status = previous_status

    existing_firm = (
        str(existing.value.get("firm") or "") if existing else ""
    )
    if existing_firm and is_noise_firm_candidate(existing_firm):
        existing_firm = ""
    chosen_firm = _prefer_firm(discipline, existing_firm or None, firm)
    if _STATUS_RANK.get(evidence_kind, 0) >= _STATUS_RANK.get(previous_status, 0):
        chosen_firm = _prefer_firm(discipline, existing_firm or None, firm)
    elif existing_firm:
        chosen_firm = _prefer_firm(discipline, existing_firm, firm)

    value: dict[str, Any] = {
        "discipline": discipline,
        "firm": chosen_firm,
        "status": status,
        "evidence_paths": paths,
        "evidence_kind": "design_document",
        "name": chosen_firm,
    }

    expected = existing.revision if existing else 0
    try:
        return upsert_shared_project_object(
            project,
            kind="consultant",
            object_id=object_id,
            update=SharedProjectObjectUpdate(expected_revision=expected, value=value),
            source="evidence",
        )
    except SharedProjectObjectConflict:
        return existing


def reconcile_consultant_facts_from_documents(
    project: Project,
    documents: list[SourceDocument],
) -> list[SharedProjectObject]:
    touched: dict[str, SharedProjectObject] = {}
    for document in documents:
        fact = upsert_consultant_fact_from_document(project, document)
        if fact is not None:
            touched[fact.id] = fact
    return list(touched.values())


async def reconcile_project_consultant_facts(
    session,
    *,
    project: Project,
    documents: list[SourceDocument],
) -> list[SharedProjectObject]:
    """Persist reconciled consultant facts under the project lock."""
    # Mutate a working copy of metadata, then write each changed object once.
    working = Project(project_metadata=dict(project.project_metadata or {}))
    reconcile_consultant_facts_from_documents(working, documents)
    results: list[SharedProjectObject] = []
    for fact in list_shared_project_objects(working, kind="consultant"):
        current = get_shared_project_object(
            project, kind="consultant", object_id=fact.id
        )
        expected = current.revision if current else 0
        if current and current.value == fact.value:
            results.append(current)
            continue
        try:
            results.append(
                await write_shared_project_object(
                    session,
                    project=project,
                    kind="consultant",
                    object_id=fact.id,
                    update=SharedProjectObjectUpdate(
                        expected_revision=expected,
                        value=fact.value,
                    ),
                    source="evidence",
                )
            )
        except SharedProjectObjectConflict:
            if current is not None:
                results.append(current)
    return results
