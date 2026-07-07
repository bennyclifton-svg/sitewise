"""Critical corpus coverage checks for evidence-backed PMP drafts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class CoverageRequirement:
    source: str
    category: str
    fact: str
    alternatives: tuple[tuple[str, ...], ...]


def format_corpus_coverage_requirements(
    source_texts: Sequence[str],
    source_labels: Sequence[str] | None = None,
) -> str:
    """Return prompt-ready coverage requirements derived from current evidence."""
    requirements = build_corpus_coverage_requirements(source_texts, source_labels)
    if not requirements:
        return ""

    lines = [
        "Every active project evidence file is mandatory. The PMP must include each "
        "file in evidence_refs and carry these critical dates, values, quantities, "
        "scope items, and constraints into the relevant PMP sections:",
    ]
    current_source = ""
    for requirement in requirements:
        if requirement.source != current_source:
            current_source = requirement.source
            lines.append(f"- {current_source}")
        lines.append(f"  - {requirement.category}: {requirement.fact}")
    return "\n".join(lines)


def corpus_coverage_violations(
    markdown: str,
    *,
    output_evidence_refs: Sequence[str],
    required_evidence_refs: Sequence[str],
    source_texts: Sequence[str],
    source_labels: Sequence[str] | None = None,
) -> list[str]:
    """Return missing-file and missing-critical-fact coverage issues."""
    violations: list[str] = []
    output_paths = {_normalise_ref_path(ref) for ref in output_evidence_refs}
    for required_ref in required_evidence_refs:
        required_path = _normalise_ref_path(required_ref)
        if required_path and required_path not in output_paths:
            violations.append(
                "PMP evidence_refs is missing active project document: "
                f"{required_path}"
            )

    body = _normalise_text(markdown)
    for requirement in build_corpus_coverage_requirements(source_texts, source_labels):
        if _requirement_present(body, requirement):
            continue
        violations.append(
            f"PMP missing {requirement.category} from {requirement.source}: "
            f"{requirement.fact}"
        )

    return _dedupe(violations)


def build_corpus_coverage_requirements(
    source_texts: Sequence[str],
    source_labels: Sequence[str] | None = None,
) -> list[CoverageRequirement]:
    labels = list(source_labels or [])
    if len(labels) < len(source_texts):
        labels.extend(
            f"evidence document {index + 1}"
            for index in range(len(labels), len(source_texts))
        )

    requirements: list[CoverageRequirement] = []
    for text, label in zip(source_texts, labels, strict=True):
        lower = text.lower()
        if "tenant requirements brief" in lower or "functional requirements" in lower:
            requirements.extend(_tenant_brief_requirements(label, text))
        if "planning pathway advice" in lower or "pathway assessment" in lower:
            requirements.extend(_planning_requirements(label, text))
        if "letter of engagement" in lower:
            requirements.extend(_engagement_requirements(label, text))
        if "fee proposal" in lower:
            requirements.extend(_fee_proposal_requirements(label, text))
        if "base building information schedule" in lower or "landlord scope" in lower:
            requirements.extend(_landlord_requirements(label, text))
        if "preliminary cost advice" in lower or "programme rom" in lower:
            requirements.extend(_builder_rom_requirements(label, text))
    return _dedupe_requirements(requirements)


def _tenant_brief_requirements(source: str, text: str) -> list[CoverageRequirement]:
    requirements = [
        _req(source, "programme date", "target possession for fit-out: 1 November 2026", "1 November 2026"),
        _req(
            source,
            "programme date",
            "rent-free fit-out period: 1 February 2027 to 30 June 2027",
            ("1 February 2027", "30 June 2027"),
        ),
        _req(source, "programme date", "firm occupation from 1 July 2027", "1 July 2027"),
        _req(
            source,
            "live environment",
            "building partially occupied on Levels 2 and 5; after-hours access required",
            ("Levels 2 and 5", "after-hours"),
        ),
        _req(source, "scope quantity", "open-plan legal library about 180 m2", ("180", "legal library")),
        _req(source, "scope quantity", "42 workstations", "42 workstations"),
        _req(
            source,
            "scope quantity",
            "8 partner offices",
            "8 partner offices",
            "8 enclosed offices",
            "eight partner offices",
            "eight enclosed offices",
        ),
        _req(
            source,
            "scope quantity",
            "4 x 8-person meeting rooms",
            ("4 x 8-person", "meeting"),
            ("4 x 8 person", "meeting"),
            ("4", "8-person", "meeting"),
        ),
        _req(
            source,
            "scope quantity",
            "2 x 16-person meeting rooms",
            ("2 x 16-person", "meeting"),
            ("2 x 16 person", "meeting"),
            ("2", "16-person", "meeting"),
        ),
        _req(source, "scope quantity", "60-seat breakout / kitchen", "60-seat breakout", "60 seat breakout"),
        _req(source, "scope quantity", "secure records room and comms room", ("records room", "comms room")),
        _req(
            source,
            "scope quantity",
            "amenities: 2 male, 2 female, 1 accessible WC, shower on Level 4",
            ("2", "male", "2", "female", "accessible wc"),
            ("2 x male", "2 x female", "1 x accessible wc"),
        ),
        _req(
            source,
            "budget value",
            "tenant works budget aspiration $1.35M-$1.55M excluding furniture and IT licensing",
            ("$1.35m", "$1.55m"),
            ("1.35m", "1.55m"),
        ),
        _req(source, "services value", "minimum 500 kVA electrical supply to tenant switchboard", "500 kVA"),
    ]
    return [req for req in requirements if _source_supports(text, req)]


def _planning_requirements(source: str, text: str) -> list[CoverageRequirement]:
    requirements = [
        _req(source, "classification", "commercial office tower, BCA Class 5", "Class 5"),
        _req(source, "approval pathway", "SSD primary pathway; CDC not assumed", ("SSD", "primary"), ("CDC", "not")),
        _req(source, "occupancy value", "occupancy load increase from 98 to 142 persons", ("98", "142", "persons")),
        _req(source, "scope quantity", "Level 4 mezzanine insert about 185 m2", ("185", "mezzanine")),
        _req(source, "approval duration", "SSD assessment period 10-14 weeks", "10-14 weeks", "10 to 14 weeks"),
        _req(source, "approval duration", "Construction Certificate 4-6 weeks after SSD", "4-6 weeks", "4 to 6 weeks"),
        _req(source, "sustainability value", "NABERS Energy rating at least 4.5 stars", ("4.5", "NABERS")),
    ]
    return [req for req in requirements if _source_supports(text, req)]


def _engagement_requirements(source: str, text: str) -> list[CoverageRequirement]:
    requirements = [
        _req(source, "engagement date", "engagement letter dated 24 February 2026", "24 February 2026"),
        _req(source, "engagement date", "engagement accepted/executed 28/02/2026", "28/02/2026", "28 February 2026"),
        _req(source, "fee value", "fixed professional fee $118,500 ex GST", "$118,500", "118,500"),
        _req(source, "role boundary", "architect/PM is not Superintendent, Certifier, PCA, or builder", ("not", "Superintendent", "Certifier", "PCA", "builder")),
        _req(source, "reporting cadence", "fortnightly tenant progress reporting", "fortnightly"),
        _req(source, "programme date", "target SSD lodgement September 2026", "September 2026"),
        _req(source, "programme date", "tenant possession 1 November 2026", "1 November 2026"),
        _req(source, "programme date", "practical completion before 1 July 2027 occupation", "1 July 2027"),
        _req(source, "service value", "construction administration estimated 7 months", ("7", "months")),
    ]
    return [req for req in requirements if _source_supports(text, req)]


def _fee_proposal_requirements(source: str, text: str) -> list[CoverageRequirement]:
    requirements = [
        _req(source, "proposal date", "fee proposal dated 10 February 2026", "10 February 2026"),
        _req(source, "fee value", "total fixed fee $118,500 ex GST", "$118,500", "118,500"),
        _req(source, "scope quantity", "42 workstations", "42 workstations"),
        _req(source, "scope quantity", "8 partner offices and 6 meeting rooms", ("8", "partner offices", "6 meeting rooms"), ("8 partner offices", "6 meeting rooms")),
        _req(source, "scope quantity", "Level 4 mezzanine insert about 185 m2", ("185", "mezzanine")),
        _req(source, "approval pathway", "SSD primary pathway; CDC not assumed", ("SSD", "primary"), ("CDC", "not")),
        _req(source, "procurement value", "two experienced commercial fit-out builders to tender", "two", "2 invited builders", "two invited builders"),
        _req(source, "tender criterion", "tender evaluation includes after-hours methodology and services-capacity risk", ("after-hours", "services-capacity risk"), ("after-hours", "services capacity risk")),
    ]
    return [req for req in requirements if _source_supports(text, req)]


def _landlord_requirements(source: str, text: str) -> list[CoverageRequirement]:
    requirements = [
        _req(source, "landlord value", "landlord HVAC contribution $180,000 ex GST", "$180,000", "180,000"),
        _req(source, "scope boundary", "supplementary sprinklers for mezzanine and high-density areas are tenant scope", ("supplementary sprinklers", "tenant scope")),
        _req(source, "services value", "400 kVA existing switchboard; upgrade to 500 kVA shared cost", ("400 kVA", "500 kVA")),
        _req(source, "access constraint", "core drilling weekdays 7am-5pm unless after-hours permit granted", ("7am", "5pm"), ("7 am", "5 pm")),
        _req(source, "access constraint", "after-hours works 10:00 pm-6:00 am weekdays and Saturdays until 2:00 pm", ("10:00 pm", "6:00 am"), ("10 pm", "6 am")),
        _req(source, "access constraint", "no Sunday works", "no Sunday"),
        _req(source, "approval gate", "tenant works cannot commence until SSD consent and landlord fit-out consent deed", ("SSD consent", "fit-out consent deed")),
    ]
    return [req for req in requirements if _source_supports(text, req)]


def _builder_rom_requirements(source: str, text: str) -> list[CoverageRequirement]:
    requirements = [
        _req(source, "ROM value", "ROM tenant works range $1,280,000-$1,520,000 ex GST", ("$1,280,000", "$1,520,000"), ("1,280,000", "1,520,000")),
        _req(source, "programme duration", "programme ROM 22-26 weeks on site", "22-26 weeks", "22 to 26 weeks"),
        _req(source, "cost risk value", "after-hours labour and tenancy separation risk $180k-$240k", ("$180k", "$240k"), ("180k", "240k")),
        _req(source, "compliance risk", "fire engineering performance solution for open-plan library and egress changes", ("fire engineering", "performance solution")),
        _req(source, "scope risk", "supplementary sprinklers and smoke control to mezzanine", ("supplementary sprinklers", "smoke control")),
        _req(source, "scope risk", "acoustic partitions to adjoining tenancy", "acoustic partitions"),
        _req(source, "landlord risk", "landlord approval delays on slab penetrations", ("landlord approval", "slab penetrations")),
        _req(source, "conflict disclosure", "Apex is not a related party to Form & Function", ("not a related party", "Form & Function"), ("not related", "Form & Function")),
    ]
    return [req for req in requirements if _source_supports(text, req)]


def _req(
    source: str,
    category: str,
    fact: str,
    *alternatives: str | tuple[str, ...],
) -> CoverageRequirement:
    parsed: list[tuple[str, ...]] = []
    for alternative in alternatives:
        if isinstance(alternative, str):
            parsed.append((alternative,))
        else:
            parsed.append(tuple(alternative))
    return CoverageRequirement(
        source=source,
        category=category,
        fact=fact,
        alternatives=tuple(parsed),
    )


def _source_supports(text: str, requirement: CoverageRequirement) -> bool:
    body = _normalise_text(text)
    return _requirement_present(body, requirement)


def _requirement_present(normalised_body: str, requirement: CoverageRequirement) -> bool:
    for alternative in requirement.alternatives:
        if all(_normalise_text(term) in normalised_body for term in alternative):
            return True
    return False


def _normalise_ref_path(ref: str) -> str:
    path = str(ref).split("#", 1)[0].strip()
    if ":" in path:
        path = path.split(":", 1)[1]
    return path.replace("\\", "/").lower()


def _normalise_text(value: str) -> str:
    text = str(value).lower()
    replacements = {
        "\u00a0": " ",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00d7": "x",
        "\u2265": ">=",
        "m\u00b2": "m2",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _dedupe_requirements(
    requirements: list[CoverageRequirement],
) -> list[CoverageRequirement]:
    seen: set[tuple[str, str, str]] = set()
    result: list[CoverageRequirement] = []
    for requirement in requirements:
        key = (requirement.source, requirement.category, requirement.fact)
        if key in seen:
            continue
        seen.add(key)
        result.append(requirement)
    return result
