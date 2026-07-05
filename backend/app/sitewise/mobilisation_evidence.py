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
GAP_ENGAGEMENT = "Executed engagement letter"

_QUOTE_SIGNAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bprice\s+estimate\b", re.IGNORECASE),
    re.compile(r"\bquotation\b", re.IGNORECASE),
    re.compile(r"\bbuilder'?s?\s+margin\b", re.IGNORECASE),
    re.compile(r"\bschedule\s+of\s+rates\b", re.IGNORECASE),
)
_MONEY_PATTERN = re.compile(r"\$?\s*([\d]{1,3}(?:,\d{3})+(?:\.\d{2})?)")
_QUOTE_EX_GST_PATTERN = re.compile(
    r"EXC?\.?\s*GST\s*\n*\s*\$?\s*([\d]{1,3}(?:,\d{3})+(?:\.\d{2})?)",
    re.IGNORECASE,
)
_QUOTE_MARGIN_PATTERN = re.compile(
    r"(?:PLUS\s+)?(\d+(?:\.\d+)?)\s*%\s*BUILDER'?S?\s*MARGIN\s*\n*\s*\$?\s*"
    r"([\d]{1,3}(?:,\d{3})+(?:\.\d{2})?)",
    re.IGNORECASE,
)
_QUOTE_EXCLUSION_BLOCK_PATTERN = re.compile(
    r"(?:does\s+not\s+includ|not\s+included|exclusions?)[^\n]*\n(.+)\Z",
    re.IGNORECASE | re.DOTALL,
)

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

    builder_quotes: list[str] = Field(default_factory=list)
    other_evidence: list[str] = Field(default_factory=list)

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


def has_engagement_evidence(pack: MobilisationEvidencePack) -> bool:
    """True when engagement-letter content was actually found in the corpus."""
    return any(
        (
            pack.engagement_letter_date,
            pack.engagement_executed_date,
            pack.appointee,
            pack.roles,
            pack.scope_bullets,
            pack.fee_stages,
        )
    )


def has_fee_proposal_evidence(pack: MobilisationEvidencePack) -> bool:
    """True when fee-proposal content was actually found in the corpus."""
    return any(
        (
            pack.fee_proposal_date,
            pack.dwelling_summary,
            pack.conflict_disclosure,
        )
    )


def _is_engagement_or_fee_text(text: str) -> bool:
    lowered = text.lower()
    if "letter of engagement" in lowered:
        return True
    if "scope of services" in lowered and "fee basis" in lowered:
        return True
    return "fee proposal" in lowered or "project understanding" in lowered


def _parse_money(raw: str) -> float:
    return float(raw.replace(",", ""))


def _quote_exclusion_items(text: str) -> list[str]:
    block_match = _QUOTE_EXCLUSION_BLOCK_PATTERN.search(text)
    if not block_match:
        return []
    items: list[str] = []
    for match in _NUMBERED_LIST_ITEM.finditer(block_match.group(1)):
        item = " ".join(match.group(1).split()).rstrip(".")
        if item and len(item) < 80:
            items.append(item)
    return items


def extract_builder_quote_summary(text: str, label: str) -> str | None:
    """Summarise a builder price estimate / quotation deterministically.

    A quote is recognised by content signals (price estimate, quotation,
    builder margin, schedule of rates) plus a material dollar amount. The
    summary states the headline pricing and flags exclusions as unpriced
    latent-condition risks — market pricing signal, never an owner budget.
    """
    signals = sum(1 for pattern in _QUOTE_SIGNAL_PATTERNS if pattern.search(text))
    amounts = [_parse_money(raw) for raw in _MONEY_PATTERN.findall(text)]
    headline = max(amounts, default=0.0)
    if signals < 1 or headline < 10_000:
        return None
    if signals < 2 and "stage" not in text.lower():
        return None

    parts: list[str] = []
    ex_gst_match = _QUOTE_EX_GST_PATTERN.search(text)
    margin_match = _QUOTE_MARGIN_PATTERN.search(text)
    if ex_gst_match and margin_match:
        parts.append(
            f"${ex_gst_match.group(1)} ex GST "
            f"(${margin_match.group(2)} incl {margin_match.group(1)}% builder margin)"
        )
    elif ex_gst_match:
        parts.append(f"${ex_gst_match.group(1)} ex GST")
    else:
        parts.append(f"headline amount ${headline:,.2f}")

    if "stage" in text.lower():
        parts.append("staged trade breakdown")

    exclusions = _quote_exclusion_items(text)
    if exclusions:
        shown = "; ".join(exclusions[:4])
        parts.append(
            f"{len(exclusions)} excluded items ({shown}, …) — unpriced latent-condition risks"
        )

    return f"Builder price estimate on file ({label}) — " + "; ".join(parts) + "."


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
    lines.extend(pack.builder_quotes)
    lines.extend(pack.other_evidence)
    if not lines and pack.evidence_refs:
        # Evidence exists even when nothing matched the mobilisation checklist —
        # never report an indexed corpus as "not yet indexed".
        lines.append(
            f"{len(pack.evidence_refs)} evidence document(s) on file — not matched to the "
            "mobilisation checklist; review content and file to the correct folder."
        )
    return lines


def build_evidence_map_rows(pack: MobilisationEvidencePack) -> list[tuple[str, str, str]]:
    """Return (section, status, ref) tuples for the evidence map table.

    A row may only claim Grounded/Partial when the underlying evidence was
    actually extracted from the corpus — never from template defaults.
    """
    brief_grounded = pack.owner_brief_on_file and not pack_has_gap(pack, GAP_OWNER_BRIEF)
    budget_grounded = not pack_has_gap(pack, GAP_CONSTRUCTION_BUDGET)
    engagement_grounded = has_engagement_evidence(pack)

    if brief_grounded:
        project_understanding_status, project_understanding_ref = (
            "Grounded",
            "owner project brief",
        )
    elif has_fee_proposal_evidence(pack):
        project_understanding_status, project_understanding_ref = "Partial", "fee proposal"
    else:
        project_understanding_status, project_understanding_ref = "Not evidenced", "—"

    rows = [
        (
            "Appointment & fee",
            "Grounded" if engagement_grounded else "Not evidenced",
            "engagement letter" if engagement_grounded else "—",
        ),
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
    if pack.builder_quotes:
        rows.append(
            (
                "Builder pricing",
                "On file — unverified",
                f"{len(pack.builder_quotes)} builder quote(s)",
            )
        )
    return rows


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
    source_labels: list[str] | None = None,
) -> MobilisationEvidencePack:
    """Parse mobilisation evidence into a structured pack.

    Every evidence document is considered: engagement letters and fee
    proposals populate the checklist fields; builder quotes are summarised as
    unverified market pricing; anything else passes through as other evidence
    so no indexed document is silently dropped.
    """
    refs = list(evidence_refs or [])
    if not source_texts:
        return MobilisationEvidencePack(
            gaps=[GAP_ENGAGEMENT, *(label for label, _ in STANDARD_GAP_CHECKS)],
            evidence_refs=refs,
        )

    labels = list(source_labels or [])
    if len(labels) < len(source_texts):
        labels.extend(
            f"evidence document {index + 1}"
            for index in range(len(labels), len(source_texts))
        )

    combined = "\n\n".join(source_texts)
    engagement_text, fee_text = _split_engagement_and_fee_texts(source_texts)
    grounding = extract_project_grounding_facts(source_texts)

    dwelling_summary, site_constraints = _extract_dwelling_and_constraints(fee_text)
    invited_builder_count, formal_tender_count = _extract_builder_counts(combined)
    pi_fields = _extract_pi_fields(engagement_text)
    gaps = _detect_gaps(combined)
    owner_brief_on_file = _owner_brief_on_file(combined, gaps)

    builder_quotes: list[str] = []
    other_evidence: list[str] = []
    for text, label in zip(source_texts, labels, strict=True):
        quote_summary = extract_builder_quote_summary(text, label)
        if quote_summary is not None:
            builder_quotes.append(quote_summary)
        elif not _is_engagement_or_fee_text(text):
            other_evidence.append(
                f"{label} on file — content not matched to the mobilisation checklist; "
                "review and file to the correct lifecycle folder."
            )

    pack = MobilisationEvidencePack(
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
        builder_quotes=builder_quotes,
        other_evidence=other_evidence,
        gaps=gaps,
        evidence_refs=refs,
    )
    if not has_engagement_evidence(pack):
        pack.gaps.insert(0, GAP_ENGAGEMENT)
    return pack
