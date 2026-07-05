"""Evidence fidelity checks for evidence_grounded Create/Update PMP drafts."""

from __future__ import annotations

import re

# Narrative phrases that contradict indexed project evidence.
GLOBAL_EVIDENCE_CONTRADICTIONS: tuple[str, ...] = (
    "project evidence (none yet)",
    "project evidence: none",
    "project evidence — none",
    "project evidence - none",
    "mobilisation evidence not yet indexed",
)

PROJECT_OVERVIEW_CONTRADICTIONS: tuple[str, ...] = (
    "site address, dwelling type, budget, and owner identity not yet evidenced",
    "owner identity not yet evidenced",
    "site address not yet evidenced",
    "neither brief filed yet",
)

ENGAGEMENT_LETTER_CONTRADICTIONS: tuple[str, ...] = (
    "no engagement letter found",
    "no engagement letter on file",
    "no engagement letter available",
    "engagement letter — not yet filed",
    "engagement letter - not yet filed",
    "engagement instruments gap: fee proposal, executed engagement letter",
)

FEE_PROPOSAL_CONTRADICTIONS: tuple[str, ...] = (
    "fee proposal — not yet filed",
    "fee proposal - not yet filed",
    "fee proposal, executed engagement letter, scope of services — all assumption: not yet filed",
)

GEOTECH_REQUIRED_CONTRADICTIONS: tuple[str, ...] = (
    "geotechnical report is required",
    "geotech report is required",
    "geotechnical report required",
    "commission geotechnical report",
    "geotech not yet on file",
)

POST_ENGAGEMENT_CONTRADICTIONS: tuple[str, ...] = (
    "pre-brief / pre-engagement",
    "mobilisation phase: assumption: pre-brief",
    "current mobilisation phase: assumption: pre-brief",
)

ENGAGEMENT_FILING_CONTRADICTIONS: tuple[str, ...] = (
    "all assumption: not yet filed",
    "neither brief filed yet",
    "engagement letter gap",
)

EVIDENCE_GROUNDED_MARKERS: tuple[str, ...] = (
    "evidence on file",
)

ENGAGEMENT_STATUS_MARKERS: tuple[str, ...] = (
    "executed",
    "signed",
    "on file",
)

EVIDENCE_MAP_MARKERS: tuple[str, ...] = (
    "| section |",
    "| evidence status |",
    "evidence status | ref",
)

# Sections where contradictory filing/mobilisation language is stripped during sanitize.
EVIDENCE_SANITIZE_SECTION_HEADINGS: tuple[str, ...] = (
    "Evidence basis and document control",
    "Project overview",
    "Architect-PM role and appointment",
    "Two-brief discipline",
    "Consultant coordination",
    "Internal audit layer",
)

_VERSION_PATTERN = re.compile(r"\bVersion v\d+\b", re.IGNORECASE)

_STREET_ADDRESS_PATTERN = re.compile(
    r"\d+\s+[A-Za-z][\w\s\-']{2,48}"
    r"(?:,\s*)?(?:[A-Za-z][\w\s\-']{2,24})?\s*(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4}",
    re.IGNORECASE,
)
_DEAR_OWNERS_PATTERN = re.compile(r"Dear\s+(.+?),", re.IGNORECASE)
_PROJECT_HEADING_PATTERN = re.compile(r"^\*\*Project:\*\*\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_DATE_PREFIX_PATTERN = re.compile(
    r"^\d{1,2}\s+"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.IGNORECASE,
)


def _normalize_ref(ref: str) -> str:
    path = ref.split("#", 1)[0]
    if ":" in path:
        path = path.split(":", 1)[1]
    return path.lower()


def evidence_refs_include_engagement_letter(evidence_refs: list[str]) -> bool:
    return any(
        "engagement-letter" in _normalize_ref(ref)
        or "engagement_letter" in _normalize_ref(ref)
        or "/engagement-letter" in _normalize_ref(ref)
        for ref in evidence_refs
    )


def evidence_refs_include_fee_proposal(evidence_refs: list[str]) -> bool:
    return any(
        "fee-proposal" in _normalize_ref(ref)
        or "fee_proposal" in _normalize_ref(ref)
        or "/fee-proposal" in _normalize_ref(ref)
        for ref in evidence_refs
    )


def evidence_refs_include_geotechnical_report(evidence_refs: list[str]) -> bool:
    return any(
        "geotechnical" in _normalize_ref(ref) or "geotech" in _normalize_ref(ref)
        for ref in evidence_refs
    )


def _is_valid_grounding_anchor(anchor: str) -> bool:
    cleaned = " ".join(anchor.split()).strip()
    if len(cleaned) < 4:
        return False
    if len(cleaned) > 72:
        return False
    if _DATE_PREFIX_PATTERN.search(cleaned):
        return False
    if re.search(r"\b(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+\d{4}\b", cleaned, re.IGNORECASE):
        return True
    return len(cleaned.split()) <= 6


def extract_project_grounding_facts(source_texts: list[str]) -> dict[str, str]:
    """Extract structured site/owner/project labels from mobilisation evidence."""
    if not source_texts:
        return {}

    combined = "\n".join(source_texts)
    facts: dict[str, str] = {}

    addresses: list[str] = []
    for match in _STREET_ADDRESS_PATTERN.finditer(combined):
        address = " ".join(match.group(0).split())
        if len(address) >= 10 and _is_valid_grounding_anchor(address.lower()):
            addresses.append(address)
    if addresses:
        facts["site"] = addresses[0]

    dear_match = _DEAR_OWNERS_PATTERN.search(combined)
    if dear_match:
        owners = dear_match.group(1).strip()
        if owners:
            facts["owners"] = owners

    project_match = _PROJECT_HEADING_PATTERN.search(combined)
    if project_match:
        project_name = project_match.group(1).strip()
        if project_name and _is_valid_grounding_anchor(project_name.lower()):
            facts["project_name"] = project_name

    return facts


def extract_grounding_anchors(source_texts: list[str]) -> list[str]:
    """Return distinctive phrases from mobilisation evidence for overview grounding checks."""
    facts = extract_project_grounding_facts(source_texts)
    anchors: list[str] = []
    for key in ("site", "owners", "project_name"):
        value = facts.get(key)
        if value:
            anchors.append(value.lower())

    if anchors:
        return anchors[:6]

    if not source_texts:
        return []

    combined = "\n".join(source_texts)
    for match in _STREET_ADDRESS_PATTERN.finditer(combined):
        anchor = " ".join(match.group(0).split()).lower()
        if len(anchor) >= 10 and _is_valid_grounding_anchor(anchor):
            anchors.append(anchor)

    dear_match = _DEAR_OWNERS_PATTERN.search(combined)
    if dear_match:
        owners = dear_match.group(1).strip().lower()
        if _is_valid_grounding_anchor(owners):
            anchors.append(owners)

    deduped: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        if anchor in seen:
            continue
        seen.add(anchor)
        deduped.append(anchor)
    return deduped[:6]


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


_AUDIT_LABEL_HEADING = re.compile(
    r"^\s*(?:-\s*)?\*\*([A-Za-z]+):?\*\*\s*$",
    re.IGNORECASE,
)


def _audit_label_items(markdown: str, label: str) -> list[str]:
    """Return non-empty bullet lines under a **Label** marker in Internal audit layer."""
    audit = _markdown_section(markdown, "Internal audit layer")
    if not audit:
        return []

    target = label.strip().lower()
    label_pattern = re.compile(
        rf"\*\*{re.escape(label)}:?\*\*",
        re.IGNORECASE,
    )
    lines = audit.splitlines()
    items: list[str] = []
    in_section = False
    for line in lines:
        if not in_section:
            if label_pattern.search(line):
                in_section = True
            continue

        heading = _AUDIT_LABEL_HEADING.match(line.strip())
        if heading and heading.group(1).lower() != target:
            break

        stripped = line.strip()
        if stripped.lower().startswith("workflow warnings"):
            break
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                items.append(item)
    return items


def _audit_subsection(markdown: str, subsection: str) -> str:
    """Return lines under a Workflow warnings / **Assumptions** marker in Internal audit layer."""
    audit = _markdown_section(markdown, "Internal audit layer")
    if not audit:
        return ""

    target = subsection.strip().lower()
    lines = audit.splitlines()
    section_lines: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if not collecting:
            heading = _AUDIT_LABEL_HEADING.match(stripped)
            if heading and heading.group(1).lower() == target:
                collecting = True
                continue
            lowered = stripped.lower().rstrip(":")
            if lowered in {target, f"- {target}"} or lowered.endswith(target):
                collecting = True
            continue
        heading = _AUDIT_LABEL_HEADING.match(stripped)
        if heading:
            break
        if stripped.startswith("## "):
            break
        section_lines.append(line)
    return "\n".join(section_lines)


def markdown_is_evidence_grounded(markdown: str, evidence_refs: list[str]) -> bool:
    """True when refs are populated or the draft already states evidence on file."""
    if evidence_refs:
        return True
    evidence_basis = _markdown_section(
        markdown, "Evidence basis and document control"
    )
    return _contains_any(evidence_basis.lower(), EVIDENCE_GROUNDED_MARKERS)


def _geotechnical_evidenced(markdown: str, evidence_refs: list[str]) -> bool:
    if evidence_refs_include_geotechnical_report(evidence_refs):
        return True

    evidence_basis = _markdown_section(
        markdown, "Evidence basis and document control"
    ).lower()
    for line in evidence_basis.splitlines():
        lower = line.lower()
        if "geotechnical" not in lower:
            continue
        if _contains_any(lower, ("not evidenced", "not on file", "required")):
            continue
        if _contains_any(lower, ("on file", "grounded", "issued")):
            return True
    return False


def _geotechnical_site_class_known(
    markdown: str,
    source_texts: list[str] | None,
) -> bool:
    haystack = markdown.lower()
    if "site classification" in haystack and re.search(r"\bh1\b", haystack):
        return True
    if not source_texts:
        return False
    combined = "\n".join(source_texts).lower()
    return "site classification" in combined and re.search(r"\bh1\b", combined) is not None


def _contradiction_phrases_for_refs(
    evidence_refs: list[str],
    *,
    markdown: str = "",
) -> tuple[str, ...]:
    phrases: list[str] = []
    if evidence_refs_include_engagement_letter(evidence_refs):
        phrases.extend(ENGAGEMENT_LETTER_CONTRADICTIONS)
        phrases.extend(POST_ENGAGEMENT_CONTRADICTIONS)
        phrases.extend(ENGAGEMENT_FILING_CONTRADICTIONS)
    if evidence_refs_include_fee_proposal(evidence_refs):
        phrases.extend(FEE_PROPOSAL_CONTRADICTIONS)
    if markdown and _geotechnical_evidenced(markdown, evidence_refs):
        phrases.extend(GEOTECH_REQUIRED_CONTRADICTIONS)
    return tuple(phrases)


def _full_body_contradiction_phrases(
    evidence_refs: list[str],
    *,
    markdown: str = "",
) -> tuple[str, ...]:
    """All phrases that must not appear anywhere in evidence_grounded markdown."""
    phrases: list[str] = []
    phrases.extend(GLOBAL_EVIDENCE_CONTRADICTIONS)
    phrases.extend(PROJECT_OVERVIEW_CONTRADICTIONS)
    phrases.extend(_contradiction_phrases_for_refs(evidence_refs, markdown=markdown))
    deduped: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(phrase)
    return tuple(deduped)


def _strip_contradictory_lines(section: str, phrases: tuple[str, ...]) -> str:
    if not section or not phrases:
        return section

    kept: list[str] = []
    for line in section.splitlines():
        lower = line.lower()
        if any(phrase.lower() in lower for phrase in phrases):
            continue
        kept.append(line)
    return "\n".join(kept)


def _strip_contradictory_bullets(section: str, phrases: tuple[str, ...]) -> str:
    if not section or not phrases:
        return section

    kept: list[str] = []
    for line in section.splitlines():
        lower = line.lower()
        if line.strip().startswith(("-", "*")) and any(phrase.lower() in lower for phrase in phrases):
            continue
        kept.append(line)
    return "\n".join(kept)


def _strip_overview_contradictions(section: str) -> str:
    if not section:
        return section

    kept: list[str] = []
    for line in section.splitlines():
        lower = line.lower()
        if any(phrase.lower() in lower for phrase in PROJECT_OVERVIEW_CONTRADICTIONS):
            continue
        if "not yet evidenced" in lower and any(
            token in lower for token in ("site address", "owner identity", "dwelling type", "budget")
        ):
            continue
        if "pre-brief / pre-engagement" in lower:
            continue
        kept.append(line)
    return "\n".join(kept)


def _replace_markdown_section(markdown: str, heading: str, replacement: str) -> str:
    target = heading.strip().lower()
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip().lower()
        if stripped.startswith("## ") and stripped[3:].strip() == target:
            output.append(line)
            output.extend(replacement.rstrip().splitlines())
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("## "):
                index += 1
            continue
        output.append(line)
        index += 1
    return "\n".join(output)


def _inject_project_overview_grounding(section: str, source_texts: list[str]) -> str:
    cleaned = _strip_overview_contradictions(section)
    anchors = extract_grounding_anchors(source_texts)
    if anchors and any(_anchor_present(anchor, cleaned) for anchor in anchors):
        return cleaned

    facts = extract_project_grounding_facts(source_texts)
    if not facts:
        return cleaned

    additions: list[str] = []
    if owners := facts.get("owners"):
        additions.append(f"- Owners (evidence): {owners}.")
    if site := facts.get("site"):
        additions.append(f"- Site (evidence): {site}.")
    if project_name := facts.get("project_name"):
        if project_name.lower() not in cleaned.lower():
            additions.append(f"- Project (evidence): {project_name}.")

    if not additions:
        return cleaned

    body = cleaned.rstrip()
    if body:
        body = f"{body}\n"
    return f"{body}{chr(10).join(additions)}\n"


def _repair_geotech_workflow_bullet(line: str) -> str | None:
    lower = line.lower()
    if not line.strip().startswith(("-", "*")):
        return line
    if any(phrase in lower for phrase in GEOTECH_REQUIRED_CONTRADICTIONS):
        return None
    if "geotech and certifier not yet on file" in lower:
        return line.replace(
            "Geotech and certifier not yet on file",
            "Certifier not yet on file",
        ).replace(
            "geotech and certifier not yet on file",
            "certifier not yet on file",
        )
    return line


def _repair_planning_pathway_submilestone(markdown: str) -> str:
    if "single da pathway" not in markdown.lower():
        return markdown
    return markdown.replace(
        "CDC / DA / exempt",
        "Single DA (CDC not assumed)",
    )


def _repair_reactive_soil_risk_row(
    markdown: str,
    evidence_refs: list[str],
    source_texts: list[str] | None,
) -> str:
    if not _geotechnical_evidenced(markdown, evidence_refs):
        return markdown
    if not _geotechnical_site_class_known(markdown, source_texts):
        return markdown

    section = _markdown_section(markdown, "Risks, decisions and next actions")
    if not section:
        return markdown

    repaired_lines: list[str] = []
    changed = False
    for line in section.splitlines():
        lower = line.lower()
        if (
            "|" in line
            and "reactive" in lower
            and ("unknown" in lower or "footing type unknown" in lower)
        ):
            repaired = re.sub(
                r"Reactive soil / footing type unknown",
                "Reactive soil (H1 on file); footing design pending structural engineer",
                line,
                flags=re.IGNORECASE,
            )
            repaired = re.sub(
                r"footing type unknown",
                "footing design pending structural engineer (H1 on file)",
                repaired,
                flags=re.IGNORECASE,
            )
            repaired = re.sub(
                r"\|\s*Assumption\s*\|",
                "| Partial |",
                repaired,
                count=1,
            )
            if repaired != line:
                changed = True
            repaired_lines.append(repaired)
            continue
        repaired_lines.append(line)

    if not changed:
        return markdown
    return _replace_markdown_section(
        markdown,
        "Risks, decisions and next actions",
        "\n".join(repaired_lines),
    )


def _collapse_duplicate_periods(markdown: str) -> str:
    return re.sub(r"(?<=[a-z0-9])\.\.(?=\s|$|[A-Za-z])", ".", markdown)


def sync_document_control_version(markdown: str, version: int) -> str:
    """Align Evidence basis version label with the saved draft artefact version."""
    section = _markdown_section(markdown, "Evidence basis and document control")
    if not section:
        return markdown

    updated = _VERSION_PATTERN.sub(f"Version v{version:02d}", section)
    if updated == section:
        return markdown
    return _replace_markdown_section(
        markdown,
        "Evidence basis and document control",
        updated,
    )


def sanitize_evidence_grounded_markdown(
    markdown: str,
    evidence_refs: list[str],
    *,
    source_texts: list[str] | None = None,
) -> str:
    """Repair common evidence_grounded draft issues before validation."""
    if not markdown_is_evidence_grounded(markdown, evidence_refs):
        return markdown

    phrases = _full_body_contradiction_phrases(evidence_refs, markdown=markdown)
    updated = markdown

    for heading in EVIDENCE_SANITIZE_SECTION_HEADINGS:
        section = _markdown_section(updated, heading)
        if not section or not phrases:
            continue
        if heading == "Project overview":
            cleaned = _strip_overview_contradictions(section)
            cleaned = _strip_contradictory_lines(cleaned, phrases)
        elif heading == "Internal audit layer":
            cleaned = section
            for label in ("Assumptions", "Workflow warnings"):
                subsection = _audit_subsection(section, label.lower())
                if not subsection:
                    continue
                stripped = _strip_contradictory_bullets(subsection, phrases)
                if label.lower() == "workflow warnings" and _geotechnical_evidenced(
                    updated, evidence_refs
                ):
                    warning_lines: list[str] = []
                    for warning_line in stripped.splitlines():
                        repaired = _repair_geotech_workflow_bullet(warning_line)
                        if repaired is not None:
                            warning_lines.append(repaired)
                    stripped = "\n".join(warning_lines)
                if stripped != subsection:
                    cleaned = cleaned.replace(subsection, stripped, 1)
            cleaned = _strip_contradictory_lines(cleaned, phrases)
        else:
            cleaned = _strip_contradictory_lines(section, phrases)
        if cleaned != section:
            updated = _replace_markdown_section(updated, heading, cleaned)

    overview = _markdown_section(updated, "Project overview")
    if overview and source_texts:
        repaired_overview = _inject_project_overview_grounding(overview, source_texts)
        if repaired_overview != overview:
            updated = _replace_markdown_section(updated, "Project overview", repaired_overview)
    elif overview:
        cleaned_overview = _strip_overview_contradictions(overview)
        if cleaned_overview != overview:
            updated = _replace_markdown_section(updated, "Project overview", cleaned_overview)

    updated = _repair_planning_pathway_submilestone(updated)
    updated = _repair_reactive_soil_risk_row(updated, evidence_refs, source_texts)
    updated = _collapse_duplicate_periods(updated)
    return updated


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    lower = haystack.lower()
    return any(needle.lower() in lower for needle in needles)


def _anchor_present(anchor: str, haystack: str) -> bool:
    anchor = anchor.lower().strip()
    if not anchor:
        return False
    haystack_lower = haystack.lower()
    if anchor in haystack_lower:
        return True
    # Accept partial street match when suburb/postcode present in anchor.
    tokens = [token for token in re.split(r"[\s,]+", anchor) if len(token) >= 4]
    if len(tokens) >= 2:
        return tokens[0] in haystack_lower and tokens[1] in haystack_lower
    return False


# Evidence-map refs that name a document type must be corroborated by the
# corpus text — a "Grounded" claim citing a document nobody uploaded is the
# §evidence-discipline failure this validator exists to catch.
_EVIDENCE_MAP_REF_MARKERS: dict[str, tuple[str, ...]] = {
    "engagement letter": ("letter of engagement", "engagement letter"),
    "fee proposal": ("fee proposal", "project understanding"),
    "owner project brief": ("project brief", "owner brief"),
    "geotechnical report": ("geotech", "site classification", "soil classification", "as 2870"),
    "certifier appointment": ("certifier",),
    "master programme": ("master programme", "master program"),
}

_EVIDENCE_MAP_ROW_PATTERN = re.compile(
    r"^\|\s*(?P<section>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|\s*(?P<ref>[^|]+?)\s*\|\s*$",
    re.MULTILINE,
)


def evidence_map_claim_violations(
    markdown: str,
    source_texts: list[str],
) -> list[str]:
    """Flag evidence-map rows whose Grounded/Partial claim cites an absent document."""
    evidence_basis = _markdown_section(markdown, "Evidence basis and document control")
    if not evidence_basis:
        return []
    corpus_lower = "\n".join(source_texts).lower()
    violations: list[str] = []
    for match in _EVIDENCE_MAP_ROW_PATTERN.finditer(evidence_basis):
        status = match.group("status").strip().lower()
        ref = match.group("ref").strip().lower()
        if status in {"evidence status", "---", "not evidenced"}:
            continue
        markers = _EVIDENCE_MAP_REF_MARKERS.get(ref)
        if markers is None:
            continue
        if not any(marker in corpus_lower for marker in markers):
            violations.append(
                f"evidence map row {match.group('section').strip()!r} claims "
                f"{match.group('status').strip()!r} via {ref!r} but no such document "
                "is in the indexed evidence"
            )
    return violations


def evidence_grounded_violations(
    markdown: str,
    evidence_refs: list[str],
    *,
    source_texts: list[str] | None = None,
) -> list[str]:
    """Return evidence fidelity issues for evidence_grounded drafts."""
    if not markdown_is_evidence_grounded(markdown, evidence_refs):
        return []

    violations: list[str] = []
    evidence_basis = _markdown_section(markdown, "Evidence basis and document control")
    workflow_warnings = _audit_subsection(markdown, "workflow warnings")
    body_lower = markdown.lower()

    for phrase in _full_body_contradiction_phrases(evidence_refs, markdown=markdown):
        if phrase.lower() in body_lower:
            violations.append(
                f"evidence contradiction: {phrase!r} conflicts with indexed project evidence"
            )

    for phrase in GLOBAL_EVIDENCE_CONTRADICTIONS:
        if phrase.lower() in evidence_basis.lower():
            violations.append(
                f"evidence basis contradiction: must not claim missing evidence when "
                f"evidence_refs is populated ({phrase!r})"
            )

    project_overview = _markdown_section(markdown, "Project overview")
    if project_overview:
        for phrase in PROJECT_OVERVIEW_CONTRADICTIONS:
            if phrase.lower() in project_overview.lower():
                violations.append(
                    f"project overview contradiction: {phrase!r} conflicts with "
                    "indexed project evidence"
                )

    if evidence_refs_include_engagement_letter(evidence_refs):
        appointment_scope = "\n".join(
            part
            for part in (evidence_basis, project_overview, _audit_subsection(markdown, "facts"))
            if part
        )
        if not _contains_any(appointment_scope, ENGAGEMENT_STATUS_MARKERS):
            violations.append(
                "engagement letter in evidence_refs but draft lacks grounded appointment "
                "status (executed, signed, or on file)"
            )

    if evidence_basis and not _contains_any(evidence_basis, EVIDENCE_GROUNDED_MARKERS):
        violations.append(
            "evidence_grounded draft must state what evidence is on file "
            "(e.g. 'Evidence on file:' in document control)"
        )

    if evidence_basis and not _contains_any(evidence_basis.lower(), EVIDENCE_MAP_MARKERS):
        violations.append(
            "Evidence basis section must include an evidence map table "
            "(| Section | Evidence status | Ref |)"
        )

    if source_texts:
        violations.extend(evidence_map_claim_violations(markdown, source_texts))

    facts = _audit_label_items(markdown, "Facts")
    grounded_facts = [item for item in facts if "assumption" not in item.lower()]
    if len(grounded_facts) < 2:
        violations.append(
            "Internal audit Facts must list at least 2 evidenced project facts "
            "when evidence_refs is populated"
        )

    if evidence_refs_include_engagement_letter(evidence_refs):
        if workflow_warnings and "no engagement letter" in workflow_warnings.lower():
            violations.append(
                "Workflow warnings must not claim 'no engagement letter' when "
                "engagement letter is in evidence_refs"
            )

    if _geotechnical_evidenced(markdown, evidence_refs):
        if workflow_warnings and any(
            phrase in workflow_warnings.lower() for phrase in GEOTECH_REQUIRED_CONTRADICTIONS
        ):
            violations.append(
                "Workflow warnings must not claim geotechnical report is required when "
                "geotechnical report is on file"
            )

    if source_texts and project_overview:
        anchors = extract_grounding_anchors(source_texts)
        if anchors and not any(_anchor_present(anchor, project_overview) for anchor in anchors):
            violations.append(
                "Project overview must ground site and/or owner from project evidence "
                f"(expected one of: {', '.join(anchors[:3])})"
            )

    deduped: list[str] = []
    seen: set[str] = set()
    for issue in violations:
        if issue in seen:
            continue
        seen.add(issue)
        deduped.append(issue)
    return deduped
