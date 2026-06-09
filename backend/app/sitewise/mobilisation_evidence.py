"""Structured fact extraction from mobilisation evidence (engagement letter + fee proposal)."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.sitewise.pmp_evidence_validation import extract_project_grounding_facts

_DATE_LINE_PATTERN = re.compile(
    r"^\s*(\d{1,2}\s+"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4})\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_EXECUTED_DATE_PATTERN = re.compile(
    r"Date:\s*(\d{1,2}/\d{1,2}/\d{4})",
    re.IGNORECASE,
)
_FEE_TOTAL_PATTERN = re.compile(
    r"\$\s*([\d,]+)\s*(?:ex(?:cluding)?\.?\s*GST|excluding GST)",
    re.IGNORECASE,
)
_DA_TARGET_PATTERN = re.compile(
    r"Target\s+DA\s+lodgement:\s*\*\*([^*]+)\*\*",
    re.IGNORECASE,
)
_TO_OWNERS_PATTERN = re.compile(r"^\*\*To:\*\*\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_NAME_BEFORE_ADDRESS_PATTERN = re.compile(
    r"^([A-Za-z][\w\s\-']+?)\s*\n\d+\s+[A-Za-z][\w\s\-']{2,48}\s*(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4}\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_PI_SECTION_PATTERN = re.compile(
    r"professional indemnity insurance with\s+([^,]+),\s*policy\s+([^,]+),\s*"
    r"limit\s+(\$[\d,]+(?:\s+any one claim)?),\s*period\s+([^.\n]+)",
    re.IGNORECASE,
)
_NUMBERED_LIST_ITEM = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)
_TABLE_ROW_PATTERN = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
_INVITED_BUILDERS_PATTERN = re.compile(
    r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+invited\s+builders?",
    re.IGNORECASE,
)
_FORMAL_TENDER_PATTERN = re.compile(
    r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+formal\s+"
    r"(?:head[- ]builder\s+)?tenders?",
    re.IGNORECASE,
)
_CA_MONTHS_ENGAGEMENT_PATTERN = re.compile(
    r"monthly\s*[×x]\s*est\.?\s*(\d+)\s*[- ]month",
    re.IGNORECASE,
)
_FEE_PROPOSAL_DATE_PATTERN = re.compile(r"^\*\*Date:\*\*\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_BUDGET_CEILING_PATTERN = re.compile(
    r"(?:working budget ceiling|construction budget confirmed|construction budget ceiling)"
    r"[:\*\s]*\$?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_BRIEF_SIGNED_DATE_PATTERN = re.compile(
    r"owner project brief signed[^.\n]{0,80}?"
    r"(?:on\s+)?(\d{1,2}\s+"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})",
    re.IGNORECASE,
)
_BRIEF_FORMAL_SIGNOFF_DATE_PATTERN = re.compile(
    r"brief formal sign-off received[^.\n]{0,40}?"
    r"(?:—|-)?\s*(?:filed as owner project brief signed\s+)?(\d{1,2}\s+\w+\s+\d{4})",
    re.IGNORECASE,
)

GAP_OWNER_BRIEF = "Owner project brief formal sign-off"
GAP_CONSTRUCTION_BUDGET = "Construction budget"
GAP_GEOTECHNICAL = "Geotechnical report"
GAP_CERTIFIER = "Certifier appointment"
GAP_MASTER_PROGRAMME = "Master programme on file"

STANDARD_GAP_CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        GAP_OWNER_BRIEF,
        (
            "owner project brief signed",
            "brief formal sign-off",
            "brief signed by owner",
            "signed owner project brief",
        ),
    ),
    (
        GAP_CONSTRUCTION_BUDGET,
        (
            "construction budget",
            "project budget confirmed",
            "budget allowance",
            "working budget ceiling",
            "construction budget confirmed",
        ),
    ),
    (
        GAP_GEOTECHNICAL,
        (
            "geotechnical report on file",
            "geotech report on file",
            "geotechnical investigation report",
        ),
    ),
    (
        GAP_CERTIFIER,
        (
            "certifier appointed",
            "principal certifier appointed",
            "certifier engagement on file",
        ),
    ),
    (
        GAP_MASTER_PROGRAMME,
        (
            "master programme on file",
            "master program on file",
            "approved master programme",
        ),
    ),
)

_WORD_TO_INT = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


class FeeStage(BaseModel):
    stage: str
    trigger: str
    fee_ex_gst: str


class MobilisationEvidencePack(BaseModel):
    """Structured facts extracted from mobilisation evidence documents."""

    owners: str | None = None
    site_address: str | None = None
    dwelling_summary: str | None = None
    site_constraints: str | None = None

    engagement_letter_date: str | None = None
    fee_proposal_date: str | None = None
    engagement_executed_date: str | None = None
    appointee: str | None = None
    roles: str | None = None
    scope_bullets: list[str] = Field(default_factory=list)
    service_exclusions: str | None = None
    disbursements: str | None = None
    owner_approval_rule: str | None = None

    fee_total_ex_gst: str | None = None
    fee_stages: list[FeeStage] = Field(default_factory=list)
    reporting_cadence: str | None = None
    target_da_lodgement: str | None = None

    pi_insurer: str | None = None
    pi_policy_ref: str | None = None
    pi_limit: str | None = None
    pi_period: str | None = None
    pi_holder: str | None = None

    planning_pathway: str | None = None
    invited_builder_count: int | None = None
    formal_tender_count: int | None = None
    ca_months_assumed: int | None = None
    conflict_disclosure: str | None = None

    owner_brief_on_file: bool = False
    owner_brief_signed_date: str | None = None
    construction_budget_ceiling: str | None = None

    builder_rom: str | None = None
    heritage_advice: str | None = None

    gaps: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


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


def _split_engagement_and_fee_texts(source_texts: list[str]) -> tuple[str, str]:
    engagement_parts: list[str] = []
    fee_parts: list[str] = []
    for text in source_texts:
        lower = text.lower()
        if "letter of engagement" in lower or (
            "scope of services" in lower and "fee basis" in lower
        ):
            engagement_parts.append(text)
        elif "fee proposal" in lower or "project understanding" in lower:
            fee_parts.append(text)
    combined = "\n\n".join(source_texts)
    engagement = "\n\n".join(engagement_parts) if engagement_parts else combined
    fee = "\n\n".join(fee_parts) if fee_parts else combined
    return engagement, fee


def _parse_count(raw: str) -> int | None:
    cleaned = raw.strip().lower()
    if cleaned.isdigit():
        return int(cleaned)
    return _WORD_TO_INT.get(cleaned)


def _extract_letter_date(engagement_text: str) -> str | None:
    for match in _DATE_LINE_PATTERN.finditer(engagement_text):
        return " ".join(match.group(1).split())
    return None


def _extract_executed_date(engagement_text: str) -> str | None:
    accepted = engagement_text.split("ACCEPTED:", 1)
    search_text = accepted[1] if len(accepted) > 1 else engagement_text
    match = _EXECUTED_DATE_PATTERN.search(search_text)
    if match:
        return match.group(1)
    return None


def _extract_appointee(engagement_text: str) -> str | None:
    match = re.search(
        r"engagement of\s+(.+?)\s*\(\*\*[^*]+\*\*\)",
        engagement_text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return " ".join(match.group(1).split())
    match = re.search(
        r"^\*\*(.+?Pty Ltd)\*\*",
        engagement_text,
        re.IGNORECASE | re.MULTILINE,
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_roles(engagement_text: str) -> str | None:
    appointment = _markdown_section(engagement_text, "Appointment")
    if not appointment:
        return None
    role_match = re.search(
        r"appointed as\s+\*\*(.+?)\*\*",
        appointment,
        re.IGNORECASE | re.DOTALL,
    )
    exclusion_match = re.search(
        r"\*\*not\*\*\s+appointed as\s+([^.\n]+)",
        appointment,
        re.IGNORECASE,
    )
    if not role_match:
        return None
    roles = role_match.group(1).strip()
    if exclusion_match:
        excluded = exclusion_match.group(1).strip().rstrip(".")
        roles = f"{roles}; not {excluded}"
    return roles


def _extract_scope_bullets(engagement_text: str) -> list[str]:
    scope = _markdown_section(engagement_text, "Scope of services")
    if not scope:
        return []
    bullets: list[str] = []
    for match in _NUMBERED_LIST_ITEM.finditer(scope):
        item = " ".join(match.group(1).split())
        if item:
            bullets.append(item)
    return bullets


def _extract_service_exclusions(engagement_text: str) -> str | None:
    scope = _markdown_section(engagement_text, "Scope of services")
    match = re.search(
        r"\*\*Exclusions\*\*\s*(?:unless separately agreed)?:?\s*(.+?)(?:\n\n|\Z)",
        scope,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return " ".join(match.group(1).split()).strip()
    return None


def _extract_disbursements(engagement_text: str) -> str | None:
    fee_basis = _markdown_section(engagement_text, "Fee basis")
    match = re.search(
        r"Disbursements[^.\n]*billed at\s+(.+?)\.",
        fee_basis,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_owner_approval_rule(engagement_text: str) -> str | None:
    section = _markdown_section(engagement_text, "Authority and decisions")
    if not section:
        return None
    return " ".join(section.split())


def _extract_fee_total(text: str) -> str | None:
    match = _FEE_TOTAL_PATTERN.search(text)
    if match:
        return f"${match.group(1)}"
    return None


def _extract_fee_stages(engagement_text: str) -> list[FeeStage]:
    fee_basis = _markdown_section(engagement_text, "Fee basis")
    stages: list[FeeStage] = []
    for line in fee_basis.splitlines():
        row = _TABLE_ROW_PATTERN.match(line.strip())
        if not row:
            continue
        stage, trigger, fee = row.groups()
        if stage.strip().lower() in {"stage", "---"}:
            continue
        stages.append(
            FeeStage(
                stage=stage.strip(),
                trigger=trigger.strip(),
                fee_ex_gst=fee.strip(),
            )
        )
    return stages


def _extract_reporting_cadence(engagement_text: str) -> str | None:
    scope = _markdown_section(engagement_text, "Scope of services")
    match = re.search(
        r"(\d+\.\s*)?"
        r"((?:Fortnightly|Monthly|Weekly|Quarterly|Bi-weekly|Bi-monthly)\s+"
        r"owner progress reporting[^.\n]*)",
        scope,
        re.IGNORECASE,
    )
    if match:
        return " ".join(match.group(2).split())
    return None


def _extract_builder_rom(combined_text: str) -> str | None:
    """Capture builder preliminary cost advice (ROM) — explicitly not a formal budget."""
    lowered = combined_text.lower()
    if "preliminary cost advice" not in lowered and "rom construction range" not in lowered:
        return None
    range_match = re.search(
        r"ROM construction range:?\**\s*(\$[\d,]+\s*[–-]\s*\$?[\d,]+\s*ex\.?\s*GST)",
        combined_text,
        re.IGNORECASE,
    )
    if range_match:
        range_text = " ".join(range_match.group(1).split())
        return f"Builder preliminary cost advice (ROM, not a tender) — {range_text}."
    return "Builder preliminary cost advice (ROM, not a tender)."


def _extract_heritage_advice(combined_text: str) -> str | None:
    """Capture heritage desktop advice when supplied as evidence."""
    lowered = combined_text.lower()
    if "heritage desktop advice" not in lowered and "heritage impact statement" not in lowered:
        return None
    return (
        "Heritage desktop advice — conservation-area streetscape; "
        "DA pathway, heritage impact statement at schematic stage."
    )


def _extract_site_address(source_texts: list[str]) -> str | None:
    combined = "\n".join(source_texts)
    project_patterns = (
        r"\*\*Project:\*\*\s*.+?[—-]\s*(\d+\s+.+?(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4})",
        r"Re:[^\n]*?(\d+\s+.+?(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4})",
        r"proposed new dwelling at\s+(\d+\s+.+?(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4})",
    )
    for pattern in project_patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            return " ".join(match.group(1).split())

    block_match = re.search(
        r"(\d+\s+[A-Za-z][\w\s\-']+?)\s*\n"
        r"((?:[A-Za-z][\w\s\-']+?)\s*(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4})",
        combined,
        re.IGNORECASE,
    )
    if block_match:
        street = block_match.group(1).strip()
        locality = block_match.group(2).strip()
        if "pacific highway" not in street.lower():
            return f"{street}, {locality}"

    site = extract_project_grounding_facts(source_texts).get("site")
    if site and "pacific highway" not in site.lower():
        return site
    return None


def _extract_owners(source_texts: list[str], grounding: dict[str, str]) -> str | None:
    combined = "\n".join(source_texts)

    to_match = _TO_OWNERS_PATTERN.search(combined)
    if to_match:
        return to_match.group(1).strip()

    name_match = _NAME_BEFORE_ADDRESS_PATTERN.search(combined)
    if name_match:
        return " ".join(name_match.group(1).split())

    owners = grounding.get("owners")
    if owners:
        chen_match = re.search(
            rf"Dear\s+{re.escape(owners)}\s+Chen\b",
            combined,
            re.IGNORECASE,
        )
        if chen_match:
            return f"{owners} Chen"
    return owners


def _extract_target_da_lodgement(engagement_text: str) -> str | None:
    programme = _markdown_section(engagement_text, "Programme")
    search_text = programme or engagement_text
    match = _DA_TARGET_PATTERN.search(search_text)
    if match:
        return " ".join(match.group(1).split()).strip(" ,.")
    return None


def _extract_pi_fields(engagement_text: str) -> dict[str, str | None]:
    section = _markdown_section(engagement_text, "Professional indemnity")
    search_text = section or engagement_text
    match = _PI_SECTION_PATTERN.search(search_text)
    if not match:
        return {
            "pi_insurer": None,
            "pi_policy_ref": None,
            "pi_limit": None,
            "pi_period": None,
            "pi_holder": None,
        }
    holder_match = re.search(
        r"([A-Z][\w&.'\- ]+?)\s+holds professional indemnity insurance",
        search_text,
    )
    return {
        "pi_insurer": match.group(1).strip(),
        "pi_policy_ref": match.group(2).strip(),
        "pi_limit": match.group(3).strip(),
        "pi_period": match.group(4).strip(),
        "pi_holder": holder_match.group(1).strip() if holder_match else None,
    }


def _extract_dwelling_and_constraints(fee_text: str) -> tuple[str | None, str | None]:
    section = _markdown_section(fee_text, "Project understanding")
    if not section:
        return None, None
    sentences = [
        part.strip()
        for part in re.split(r"(?<=\.)\s+(?=[A-Z])", section)
        if part.strip()
    ]
    if not sentences:
        return None, None
    if len(sentences) >= 2:
        dwelling = f"{sentences[0]} {sentences[1]}"
        constraints = " ".join(sentences[2:]) if len(sentences) > 2 else None
    else:
        dwelling = sentences[0]
        constraints = None
    return _normalize_text_fragment(dwelling), _normalize_text_fragment(constraints)


def _extract_planning_pathway(fee_text: str) -> str | None:
    assumptions = _markdown_section(fee_text, "Assumptions")
    for line in assumptions.splitlines():
        stripped = line.strip().lstrip("-").strip()
        if "da" in stripped.lower() or "cdc" in stripped.lower():
            return stripped
    return None


def _extract_conflict_disclosure(fee_text: str) -> str | None:
    section = _markdown_section(fee_text, "Conflict disclosure")
    if not section:
        return None
    return " ".join(section.split())


def _extract_builder_counts(text: str) -> tuple[int | None, int | None]:
    invited = None
    formal = None
    invited_match = _INVITED_BUILDERS_PATTERN.search(text)
    if invited_match:
        invited = _parse_count(invited_match.group(1))
    formal_match = _FORMAL_TENDER_PATTERN.search(text)
    if formal_match:
        formal = _parse_count(formal_match.group(1))
    return invited, formal


def _extract_ca_months(engagement_text: str) -> int | None:
    """Prefer engagement-letter CA fee trigger; ignore owner overall programme ranges."""
    match = _CA_MONTHS_ENGAGEMENT_PATTERN.search(engagement_text)
    if match:
        return int(match.group(1))
    fee_basis = _markdown_section(engagement_text, "Fee basis")
    for line in fee_basis.splitlines():
        if "construction administration" in line.lower() and "month" in line.lower():
            row = _TABLE_ROW_PATTERN.match(line.strip())
            if row:
                trigger = row.group(2)
                month_match = re.search(r"(\d+)\s*[- ]month", trigger, re.IGNORECASE)
                if month_match:
                    return int(month_match.group(1))
    return None


def _extract_fee_proposal_date(fee_text: str) -> str | None:
    if "fee proposal" not in fee_text.lower():
        return None
    match = _FEE_PROPOSAL_DATE_PATTERN.search(fee_text)
    if match:
        return " ".join(match.group(1).split())
    return None


def _normalize_text_fragment(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = " ".join(text.split())
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    return cleaned.strip()


def _extract_construction_budget_ceiling(combined_text: str) -> str | None:
    match = _BUDGET_CEILING_PATTERN.search(combined_text)
    if match:
        return f"${match.group(1)}"
    return None


def _extract_owner_brief_signed_date(combined_text: str) -> str | None:
    for pattern in (_BRIEF_SIGNED_DATE_PATTERN, _BRIEF_FORMAL_SIGNOFF_DATE_PATTERN):
        match = pattern.search(combined_text)
        if match:
            return " ".join(match.group(1).split())
    return None


def _owner_brief_on_file(combined_text: str, gaps: list[str]) -> bool:
    if GAP_OWNER_BRIEF not in gaps:
        return True
    lowered = combined_text.lower()
    return any(
        marker in lowered
        for marker in (
            "owner project brief signed",
            "brief formal sign-off",
            "signed owner project brief",
        )
    )


def pack_has_gap(pack: MobilisationEvidencePack, gap_label: str) -> bool:
    """Return True when a standard mobilisation gap remains open."""
    return gap_label in pack.gaps


def build_evidence_on_file_lines(pack: MobilisationEvidencePack) -> list[str]:
    """Human-readable evidence inventory for document control."""
    lines: list[str] = []
    if pack.engagement_executed_date or pack.appointee:
        lines.append(
            f"Engagement letter ({pack.appointee or 'architect-PM'}) — executed "
            f"{pack.engagement_executed_date or 'date TBC'}."
        )
    if pack.fee_proposal_date or pack.fee_total_ex_gst:
        dated = pack.fee_proposal_date or "TBC"
        lines.append(f"Fee proposal — dated {dated}.")
    if pack.owner_brief_on_file:
        signed = (
            f" — signed {pack.owner_brief_signed_date}"
            if pack.owner_brief_signed_date
            else ""
        )
        lines.append(f"Owner project brief{signed}.")
    if pack.construction_budget_ceiling and not pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET):
        lines.append(
            f"Construction budget confirmed — {pack.construction_budget_ceiling} working ceiling."
        )
    if pack.builder_rom:
        lines.append(pack.builder_rom)
    if pack.heritage_advice:
        lines.append(pack.heritage_advice)
    if not pack_has_gap(pack, GAP_GEOTECHNICAL):
        lines.append("Geotechnical investigation report on file.")
    if not pack_has_gap(pack, GAP_CERTIFIER):
        lines.append("Principal certifier appointed.")
    if not pack_has_gap(pack, GAP_MASTER_PROGRAMME):
        lines.append("Master programme on file.")
    return lines


def build_evidence_map_rows(pack: MobilisationEvidencePack) -> list[tuple[str, str, str]]:
    """Return (section, status, ref) tuples for the evidence map table."""
    brief_grounded = pack.owner_brief_on_file and not pack_has_gap(pack, GAP_OWNER_BRIEF)
    budget_grounded = not pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET)
    project_understanding_status = "Grounded" if brief_grounded else "Partial"
    project_understanding_ref = "owner project brief" if brief_grounded else "fee proposal"

    return [
        ("Appointment & fee", "Grounded", "engagement letter"),
        ("Project understanding", project_understanding_status, project_understanding_ref),
        (
            "Construction budget",
            "Grounded" if budget_grounded else "Not evidenced",
            "owner project brief" if budget_grounded else "—",
        ),
        (
            "Owner project brief sign-off",
            "Grounded" if brief_grounded else "Not evidenced",
            "owner project brief" if brief_grounded else "—",
        ),
        (
            "Geotechnical report",
            "Grounded" if not pack_has_gap(pack, GAP_GEOTECHNICAL) else "Not evidenced",
            "geotechnical report" if not pack_has_gap(pack, GAP_GEOTECHNICAL) else "—",
        ),
        (
            "Certifier appointment",
            "Grounded" if not pack_has_gap(pack, GAP_CERTIFIER) else "Not evidenced",
            "certifier appointment" if not pack_has_gap(pack, GAP_CERTIFIER) else "—",
        ),
        (
            "Master programme",
            "Grounded" if not pack_has_gap(pack, GAP_MASTER_PROGRAMME) else "Not evidenced",
            "master programme" if not pack_has_gap(pack, GAP_MASTER_PROGRAMME) else "—",
        ),
    ]


def _detect_gaps(combined_text: str) -> list[str]:
    lowered = combined_text.lower()
    gaps: list[str] = []
    for label, markers in STANDARD_GAP_CHECKS:
        if any(marker in lowered for marker in markers):
            continue
        gaps.append(label)
    return gaps


def extract_mobilisation_evidence_pack(
    source_texts: list[str],
    evidence_refs: list[str] | None = None,
) -> MobilisationEvidencePack:
    """Parse engagement letter and fee proposal content into a structured evidence pack."""
    refs = list(evidence_refs or [])
    if not source_texts:
        return MobilisationEvidencePack(gaps=[label for label, _ in STANDARD_GAP_CHECKS], evidence_refs=refs)

    combined = "\n\n".join(source_texts)
    engagement_text, fee_text = _split_engagement_and_fee_texts(source_texts)
    grounding = extract_project_grounding_facts(source_texts)

    dwelling_summary, site_constraints = _extract_dwelling_and_constraints(fee_text)
    invited_builder_count, formal_tender_count = _extract_builder_counts(combined)
    pi_fields = _extract_pi_fields(engagement_text)
    gaps = _detect_gaps(combined)
    owner_brief_on_file = _owner_brief_on_file(combined, gaps)

    return MobilisationEvidencePack(
        owners=_extract_owners(source_texts, grounding),
        site_address=_extract_site_address(source_texts),
        dwelling_summary=dwelling_summary,
        site_constraints=site_constraints,
        engagement_letter_date=_extract_letter_date(engagement_text),
        fee_proposal_date=_extract_fee_proposal_date(fee_text),
        engagement_executed_date=_extract_executed_date(engagement_text),
        appointee=_extract_appointee(engagement_text),
        roles=_extract_roles(engagement_text),
        scope_bullets=_extract_scope_bullets(engagement_text),
        service_exclusions=_extract_service_exclusions(engagement_text),
        disbursements=_extract_disbursements(engagement_text),
        owner_approval_rule=_extract_owner_approval_rule(engagement_text),
        fee_total_ex_gst=_extract_fee_total(combined),
        fee_stages=_extract_fee_stages(engagement_text),
        reporting_cadence=_extract_reporting_cadence(engagement_text),
        target_da_lodgement=_extract_target_da_lodgement(engagement_text),
        pi_insurer=pi_fields["pi_insurer"],
        pi_policy_ref=pi_fields["pi_policy_ref"],
        pi_limit=pi_fields["pi_limit"],
        pi_period=pi_fields["pi_period"],
        pi_holder=pi_fields["pi_holder"],
        planning_pathway=_extract_planning_pathway(fee_text),
        invited_builder_count=invited_builder_count,
        formal_tender_count=formal_tender_count,
        ca_months_assumed=_extract_ca_months(engagement_text),
        conflict_disclosure=_extract_conflict_disclosure(fee_text),
        owner_brief_on_file=owner_brief_on_file,
        owner_brief_signed_date=_extract_owner_brief_signed_date(combined),
        construction_budget_ceiling=_extract_construction_budget_ceiling(combined),
        builder_rom=_extract_builder_rom(combined),
        heritage_advice=_extract_heritage_advice(combined),
        gaps=gaps,
        evidence_refs=refs,
    )
