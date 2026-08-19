"""Canonical document category list.

Kind (document_class) says what the file is. Category says which domain it
belongs to. Category is also the consultant roster: Architect, Hydraulic, BCA.
Programme / cost / defects sit on the same list but are not appointments.
"""

from __future__ import annotations

import re
from typing import get_args

from ingest.types import DocumentSubject

# Display labels — short, industry-known. Order is the user-facing menu.
CATEGORY_LABELS: dict[str, str] = {
    "architect": "Architect",
    "landscape": "Landscape",
    "interior_design": "Interior Design",
    "structural": "Structural",
    "civil": "Civil",
    "geotechnical": "Geotechnical",
    "mechanical": "Mechanical",
    "electrical": "Electrical",
    "hydraulic": "Hydraulic",
    "fire_engineer": "Fire Engineer",
    "fire_services": "Fire Services",
    "town_planner": "Town Planner",
    "heritage": "Heritage",
    "archaeology": "Archaeology",
    "surveyor": "Surveyor",
    "quantity_surveyor": "Quantity Surveyor",
    "certifier": "Certifier",
    "basix": "BASIX",
    "esd": "ESD",
    "acoustic": "Acoustic",
    "access": "Access",
    "roof_access": "Roof Access",
    "facade": "Facade",
    "traffic": "Traffic",
    "bca": "BCA",
    "arborist": "Arborist",
    "ecology": "Ecology",
    "bushfire": "Bushfire",
    "cost": "Cost",
    "programme": "Programme",
    "contract_admin": "Contract Admin",
    "defects": "Defects",
    "none": "None",
}

CONSULTANT_CATEGORIES: frozenset[str] = frozenset(
    slug
    for slug in CATEGORY_LABELS
    if slug not in {"cost", "programme", "contract_admin", "defects", "none"}
)

# Incoming labels / leftover subject values → canonical slug.
_CATEGORY_ALIASES: dict[str, str] = {
    "architecture": "architect",
    "architectural": "architect",
    "architectural services": "architect",
    "landscape architect": "landscape",
    "landscape architectural": "landscape",
    "structural engineer": "structural",
    "structural engineering": "structural",
    "civil engineer": "civil",
    "civil engineering": "civil",
    "civil stormwater": "civil",
    "civil / stormwater": "civil",
    "civil and stormwater": "civil",
    "stormwater": "civil",
    "geotech": "geotechnical",
    "geotechnical engineer": "geotechnical",
    "geotechnical engineering": "geotechnical",
    "mechanical engineer": "mechanical",
    "mechanical services": "mechanical",
    "services engineer mechanical": "mechanical",
    "electrical engineer": "electrical",
    "electrical services": "electrical",
    "services engineer electrical": "electrical",
    "hydraulic engineer": "hydraulic",
    "hydraulic services": "hydraulic",
    "services engineer hydraulic": "hydraulic",
    "services": "none",
    "fire": "fire_engineer",
    "fire engineer": "fire_engineer",
    "fire engineering": "fire_engineer",
    "fire services": "fire_services",
    "fire protection": "fire_services",
    "planning": "town_planner",
    "town planning": "town_planner",
    "town planner": "town_planner",
    "heritage consultant": "heritage",
    "survey": "surveyor",
    "quantity surveyor": "quantity_surveyor",
    "building certifier": "certifier",
    "certification": "certifier",
    "principal certifier": "certifier",
    "energy": "basix",
    "energy assessor": "basix",
    "energy assessment": "basix",
    "interior designer": "interior_design",
    "interior design": "interior_design",
    "archaeological": "archaeology",
    "archaeologist": "archaeology",
    "esd consultant": "esd",
    "sustainability": "esd",
    "sustainability consultant": "esd",
    "ecologically sustainable": "esd",
    "acoustic consultant": "acoustic",
    "access consultant": "access",
    "roof access consultant": "roof_access",
    "facade engineer": "facade",
    "traffic engineer": "traffic",
    "ecologist": "ecology",
    "ecological": "ecology",
    "bca consultant": "bca",
    "ncc": "bca",
    "building code": "bca",
    "bushfire consultant": "bushfire",
    "unassigned": "none",
}

_TOKEN = re.compile(r"[^a-z0-9]+")


def _key(value: str) -> str:
    return _TOKEN.sub(" ", value.casefold()).strip()


def canonical_category(value: str | None) -> DocumentSubject:
    """Map any stored subject, discipline label, or alias onto the closed set."""
    if value is None:
        return "none"
    raw = str(value).strip()
    if not raw:
        return "none"
    key = _key(raw)
    if not key:
        return "none"
    slug = key.replace(" ", "_")
    allowed = get_args(DocumentSubject)
    if slug in allowed:
        return slug  # type: ignore[return-value]
    aliased = _CATEGORY_ALIASES.get(key)
    if aliased in allowed:
        return aliased  # type: ignore[return-value]
    return "none"


def category_label(value: str | None) -> str:
    slug = canonical_category(value)
    if slug == "none":
        return ""
    return CATEGORY_LABELS.get(slug, slug.replace("_", " ").title())


def resolve_category(
    *,
    document_subject: str | None = None,
    discipline: str | None = None,
) -> DocumentSubject:
    """Prefer an explicit subject; otherwise use filing discipline."""
    subject = canonical_category(document_subject)
    if subject != "none":
        return subject
    return canonical_category(discipline)
