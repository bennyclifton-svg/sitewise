"""Project identity helpers for RFPs, EOIs, and agent profile updates."""

from __future__ import annotations

from typing import Any

from app.database.project import Project
from app.projects.profile import read_profile
from app.sitewise.mobilisation_evidence import (
    _extract_owners,
    _extract_site_address,
)
from app.sitewise.pmp_evidence_validation import extract_project_grounding_facts


def identity_from_project(project: Project) -> dict[str, str | None]:
    profile = read_profile(project)
    return {
        "site_address": profile.site_address,
        "client": profile.client,
    }


def identity_from_evidence_texts(texts: list[str]) -> dict[str, str | None]:
    cleaned = [text for text in texts if isinstance(text, str) and text.strip()]
    if not cleaned:
        return {"site_address": None, "client": None}
    grounding = extract_project_grounding_facts(cleaned)
    site = _extract_site_address(cleaned)
    if not site:
        site_value = grounding.get("site")
        site = site_value.strip() if isinstance(site_value, str) and site_value.strip() else None
    owners = _extract_owners(cleaned, grounding)
    if not owners:
        owners_value = grounding.get("owners")
        owners = (
            owners_value.strip()
            if isinstance(owners_value, str) and owners_value.strip()
            else None
        )
    return {"site_address": site, "client": owners}


def identity_from_evidence_items(
    evidence: list[dict[str, Any]],
) -> dict[str, str | None]:
    texts = [
        str(item.get("snippet") or item.get("content") or "")
        for item in evidence
        if isinstance(item, dict)
    ]
    return identity_from_evidence_texts(texts)


def resolve_project_identity(
    project: Project,
    *,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prefer confirmed profile identity; fall back to evidence extraction."""
    profile_identity = identity_from_project(project)
    evidence_identity = identity_from_evidence_items(evidence or [])
    site = profile_identity["site_address"] or evidence_identity["site_address"]
    client = profile_identity["client"] or evidence_identity["client"]
    return {
        "site_address": site,
        "client": client,
        "site_address_source": (
            "profile"
            if profile_identity["site_address"]
            else "evidence"
            if evidence_identity["site_address"]
            else None
        ),
        "client_source": (
            "profile"
            if profile_identity["client"]
            else "evidence"
            if evidence_identity["client"]
            else None
        ),
    }


def classification_summary(project: Project) -> str | None:
    profile = read_profile(project)
    parts: list[str] = []
    if profile.building_class:
        parts.append(profile.building_class.replace("_", " "))
    if profile.work_type:
        parts.append(profile.work_type.replace("_", " "))
    subclasses = [
        item if isinstance(item, str) else getattr(item, "value", None)
        for item in profile.subclasses
    ]
    subclass_labels = [value for value in subclasses if isinstance(value, str) and value]
    if subclass_labels:
        parts.append(", ".join(subclass_labels[:2]))
    scale = profile.scale
    if isinstance(scale.get("site_sqm"), (int, float)):
        parts.append(f"{scale['site_sqm']:g} m² site")
    if isinstance(scale.get("gfa_sqm"), (int, float)):
        parts.append(f"{scale['gfa_sqm']:g} m² GFA")
    if isinstance(scale.get("storeys"), int):
        storeys = scale["storeys"]
        parts.append(f"{storeys} storey" if storeys == 1 else f"{storeys} storeys")
    if isinstance(scale.get("bedrooms"), int):
        parts.append(f"{scale['bedrooms']} bedrooms")
    if not parts:
        return None
    return " / ".join(parts)
