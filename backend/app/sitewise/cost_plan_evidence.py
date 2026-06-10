"""Structured fact extraction for hybrid Create Cost Plan (mobilisation + budget evidence)."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.sitewise.mobilisation_evidence import (
    GAP_CERTIFIER,
    MobilisationEvidencePack,
    extract_mobilisation_evidence_pack,
    pack_has_gap,
)

_BUDGET_CEILING_PATTERN = re.compile(
    r"\*\*Working budget ceiling:\*\*\s*\$\s*([\d,]+)",
    re.IGNORECASE,
)
_CONTINGENCY_PATTERN = re.compile(
    r"\*\*\$([\d,]+)\s+contingency\*\*.*?\(approx\.?\s*([\d.]+)%\)",
    re.IGNORECASE,
)
_OWNER_SUPPLIED_PATTERN = re.compile(
    r"Owners will supply:\s*(.+?)(?:\n\n|\n##|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_BRIEF_SIGNED_PATTERN = re.compile(
    r"\*\*Signed:\*\*\s*(.+?)(?:\n\n|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_PROJECT_TITLE_PATTERN = re.compile(
    r"\*\*Project:\*\*\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
_ALLOWANCE_AMOUNT_PATTERN = re.compile(r"\$\s*([\d,]+)")
_CERTIFIER_NAME_PATTERN = re.compile(
    r"appointed\s+([A-Z][\w&.'\- ]+?Pty Ltd)\s+as principal certifier",
    re.IGNORECASE,
)
_CERTIFIER_FEE_PATTERN = re.compile(
    r"(?:principal certifier|certifier|PCA|fee)[^.\n]*?\$\s*([\d,]+)\s*\+?\s*GST",
    re.IGNORECASE,
)


class OwnerSuppliedItem(BaseModel):
    label: str
    amount_ex_gst: str | None = None


_GAP_RESOLVED_BY_OWNER_BRIEF = frozenset(
    {
        "Owner project brief formal sign-off",
        "Construction budget",
    }
)


class CostPlanEvidencePack(BaseModel):
    """Structured cost-plan facts from project evidence documents."""

    mobilisation: MobilisationEvidencePack
    project_name: str | None = None
    construction_budget_ceiling: str | None = None
    contingency_amount: str | None = None
    contingency_percent: str | None = None
    owner_supplied_items: list[OwnerSuppliedItem] = Field(default_factory=list)
    owner_brief_signed_date: str | None = None
    owner_brief_on_file: bool = False
    planning_pathway_summary: str | None = None
    planning_memo_on_file: bool = False
    certifier_name: str | None = None
    certifier_fee_ex_gst: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)

    @property
    def owners(self) -> str | None:
        return self.mobilisation.owners

    @property
    def site_address(self) -> str | None:
        return self.mobilisation.site_address

    @property
    def fee_total_ex_gst(self) -> str | None:
        return self.mobilisation.fee_total_ex_gst

    @property
    def gaps(self) -> list[str]:
        gaps = list(self.mobilisation.gaps)
        if self.owner_brief_on_file and self.construction_budget_ceiling:
            gaps = [gap for gap in gaps if gap not in _GAP_RESOLVED_BY_OWNER_BRIEF]
        elif self.owner_brief_on_file and self.owner_brief_signed_date:
            gaps = [gap for gap in gaps if gap != "Owner project brief formal sign-off"]
        return gaps


def _markdown_section(markdown: str, heading: str) -> str:
    target = heading.strip().lower()
    lines = markdown.splitlines()
    section_lines: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("## ") and stripped[3:].strip() == target:
            collecting = True
            continue
        if collecting and stripped.startswith("## "):
            break
        if collecting:
            section_lines.append(line)
    return "\n".join(section_lines)


def _split_document_texts(source_texts: list[str]) -> tuple[str, str, str]:
    owner_brief_parts: list[str] = []
    planning_parts: list[str] = []
    other_parts: list[str] = []
    for text in source_texts:
        lower = text.lower()
        if "owner project brief" in lower or "working budget ceiling" in lower:
            owner_brief_parts.append(text)
        elif "planning pathway memo" in lower or "cdc screening" in lower:
            planning_parts.append(text)
        else:
            other_parts.append(text)
    return (
        "\n\n".join(owner_brief_parts),
        "\n\n".join(planning_parts),
        "\n\n".join(other_parts),
    )


def _normalize_owner_supplied_label(raw: str) -> str:
    label = raw.strip().rstrip(".")
    label = re.sub(r"\(\s*allowance\s*\)?\s*$", "", label, flags=re.IGNORECASE).strip()
    label = label.rstrip("(").strip()
    return label or raw.strip()


def _parse_owner_supplied(raw: str) -> list[OwnerSuppliedItem]:
    items: list[OwnerSuppliedItem] = []
    for part in re.split(r",\s*(?=[A-Za-z])", raw.strip()):
        cleaned = part.strip().rstrip(".")
        if not cleaned:
            continue
        amount_match = _ALLOWANCE_AMOUNT_PATTERN.search(cleaned)
        amount = amount_match.group(1) if amount_match else None
        label = _normalize_owner_supplied_label(_ALLOWANCE_AMOUNT_PATTERN.sub("", cleaned).strip("() "))
        items.append(OwnerSuppliedItem(label=label or cleaned, amount_ex_gst=amount))
    return items


def _extract_owner_brief_fields(owner_brief_text: str) -> dict[str, object]:
    if not owner_brief_text.strip():
        return {
            "owner_brief_on_file": False,
            "owner_supplied_items": [],
        }

    ceiling_match = _BUDGET_CEILING_PATTERN.search(owner_brief_text)
    contingency_match = _CONTINGENCY_PATTERN.search(owner_brief_text)
    supplied_match = _OWNER_SUPPLIED_PATTERN.search(owner_brief_text)
    signed_match = _BRIEF_SIGNED_PATTERN.search(owner_brief_text)
    project_match = _PROJECT_TITLE_PATTERN.search(owner_brief_text)

    owner_supplied: list[OwnerSuppliedItem] = []
    if supplied_match:
        owner_supplied = _parse_owner_supplied(supplied_match.group(1))

    signed_date = None
    if signed_match:
        signed_date = " ".join(signed_match.group(1).splitlines()[0].split())

    return {
        "project_name": project_match.group(1).strip() if project_match else None,
        "construction_budget_ceiling": ceiling_match.group(1) if ceiling_match else None,
        "contingency_amount": contingency_match.group(1) if contingency_match else None,
        "contingency_percent": contingency_match.group(2) if contingency_match else None,
        "owner_supplied_items": owner_supplied,
        "owner_brief_signed_date": signed_date,
        "owner_brief_on_file": True,
    }


def _extract_planning_pathway_summary(planning_text: str) -> str | None:
    if not planning_text.strip():
        return None
    recommendation = _markdown_section(planning_text, "Recommendation")
    haystack = (recommendation or planning_text).lower()
    if "da + cc" in haystack or "pursue da" in haystack:
        if "cdc" in haystack and "excluded" in haystack:
            return "DA + CC via Ku-ring-gai Council; CDC excluded (heritage conservation area)"
        return "DA + CC pathway recommended; CDC not supported at this stage"
    if "cdc" in haystack:
        return "CDC pathway under review — confirm with planning memo"
    return None


def extract_cost_plan_evidence_pack(
    source_texts: list[str],
    evidence_refs: list[str] | None = None,
) -> CostPlanEvidencePack:
    """Parse mobilisation, owner brief, and planning memo content into a cost evidence pack."""
    refs = list(evidence_refs or [])
    mobilisation = extract_mobilisation_evidence_pack(source_texts, refs)
    owner_brief_text, planning_text, _ = _split_document_texts(source_texts)
    owner_fields = _extract_owner_brief_fields(owner_brief_text)
    planning_summary = _extract_planning_pathway_summary(planning_text)

    project_name = owner_fields.get("project_name")
    if isinstance(project_name, str) and project_name.endswith(","):
        project_name = project_name.rstrip(",").strip()

    combined = "\n\n".join(source_texts)
    certifier_name = None
    certifier_fee = None
    if not pack_has_gap(mobilisation, GAP_CERTIFIER):
        name_match = _CERTIFIER_NAME_PATTERN.search(combined)
        fee_match = _CERTIFIER_FEE_PATTERN.search(combined)
        certifier_name = name_match.group(1).strip() if name_match else None
        certifier_fee = f"${fee_match.group(1)}" if fee_match else None

    return CostPlanEvidencePack(
        mobilisation=mobilisation,
        project_name=project_name if isinstance(project_name, str) else None,
        construction_budget_ceiling=owner_fields.get("construction_budget_ceiling"),  # type: ignore[arg-type]
        contingency_amount=owner_fields.get("contingency_amount"),  # type: ignore[arg-type]
        contingency_percent=owner_fields.get("contingency_percent"),  # type: ignore[arg-type]
        owner_supplied_items=owner_fields.get("owner_supplied_items") or [],  # type: ignore[arg-type]
        owner_brief_signed_date=owner_fields.get("owner_brief_signed_date"),  # type: ignore[arg-type]
        owner_brief_on_file=bool(owner_fields.get("owner_brief_on_file")),
        planning_pathway_summary=planning_summary,
        planning_memo_on_file=bool(planning_text.strip()),
        certifier_name=certifier_name,
        certifier_fee_ex_gst=certifier_fee,
        evidence_refs=refs,
    )
