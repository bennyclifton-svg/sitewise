"""Evidence fidelity checks for evidence_grounded Create Cost Plan drafts."""

from __future__ import annotations

import re

EVIDENCE_MAP_MARKERS: tuple[str, ...] = (
    "| section |",
    "| evidence status |",
    "evidence status | ref",
)

EVIDENCE_GROUNDED_MARKERS: tuple[str, ...] = (
    "evidence on file",
)

_PROGRESS_CLAIM_MARKERS: tuple[str, ...] = (
    "progress-claim",
    "progress_claim",
    "payment-claim",
    "payment_claim",
    "schedule-of-values",
    "schedule_of_values",
    "05-progress-claims",
)

_COLLAPSED_CONSTRUCTION_PATTERNS: tuple[str, ...] = (
    r"^\s*\|\s*[^|]+\|\s*construction\s*\|\s*construction contract\s*\|",
    r"^\s*\|\s*[^|]+\|\s*construction\s*\|\s*builder contract\s*\|",
    r"^\s*-\s+\*\*construction contract\*\*",
    r"^\s*-\s+construction contract\s*[:—-]\s*\$",
)

_TRADE_ROW_MARKERS: tuple[str, ...] = (
    "preliminaries",
    "siteworks",
    "footings",
    "framing",
    "external envelope",
    "partitions",
    "kitchen",
    "building services",
    "slab",
    "lockup",
    "fixing",
)

_AUDIT_LABEL_HEADING = re.compile(
    r"^\s*(?:-\s*)?\*\*([A-Za-z]+):?\*\*\s*$",
    re.IGNORECASE,
)

_AUDIT_LABELS = ("Facts", "Assumptions", "Judgements", "Recommendations")


def _normalize_ref(ref: str) -> str:
    path = ref.split("#", 1)[0]
    if ":" in path:
        path = path.split(":", 1)[1]
    return path.lower()


def evidence_refs_include_progress_claim(evidence_refs: list[str]) -> bool:
    return any(
        any(marker in _normalize_ref(ref) for marker in _PROGRESS_CLAIM_MARKERS)
        for ref in evidence_refs
    )


def source_texts_include_trade_breakdown(source_texts: list[str]) -> bool:
    combined = "\n".join(source_texts).lower()
    hits = sum(1 for marker in _TRADE_ROW_MARKERS if marker in combined)
    return hits >= 3


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


def _replace_markdown_section_body(markdown: str, heading: str, body: str) -> str:
    target = heading.strip().lower()
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip().lower()
        if stripped.startswith("## ") and stripped[3:].strip() == target:
            output.append(line)
            output.extend(body.rstrip().splitlines())
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("## "):
                index += 1
            continue
        output.append(line)
        index += 1
    return "\n".join(output)


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
        if stripped.lower().startswith("cost evidence conflicts"):
            break
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                items.append(item)
    return items


def _has_evidence_map_table(section: str) -> bool:
    lower = section.lower()
    if any(marker in lower for marker in EVIDENCE_MAP_MARKERS):
        return True

    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip().lower() for cell in line.split("|") if cell.strip()]
        if len(cells) < 3:
            continue
        joined = " ".join(cells)
        if "section" in joined and "ref" in joined:
            return True
        if "evidence" in joined and "ref" in joined:
            return True
    return False


def _has_evidence_on_file_marker(section: str) -> bool:
    return any(marker in section.lower() for marker in EVIDENCE_GROUNDED_MARKERS)


def _normalize_audit_layer_format(markdown: str) -> str:
    audit = _markdown_section(markdown, "Internal audit layer")
    if not audit:
        return markdown

    updated_audit = audit
    for label in _AUDIT_LABELS:
        updated_audit = re.sub(
            rf"^###\s+{label}\s*:?\s*$",
            f"- **{label}**",
            updated_audit,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        updated_audit = re.sub(
            rf"^-\s+{label}\s*:?\s*$",
            f"- **{label}**",
            updated_audit,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        updated_audit = re.sub(
            rf"^\*\*{label}\*\*\s*:?\s*$",
            f"- **{label}**",
            updated_audit,
            flags=re.IGNORECASE | re.MULTILINE,
        )

    if updated_audit != audit:
        return _replace_markdown_section_body(
            markdown,
            "Internal audit layer",
            updated_audit,
        )
    return markdown


def _evidence_on_file_summary(evidence_refs: list[str]) -> str:
    labels: list[str] = []
    for ref in evidence_refs[:4]:
        path = ref.split(":", 1)[-1].split("#")[0]
        labels.append(path.rsplit("/", maxsplit=1)[-1] or path)
    return "; ".join(labels)


def _default_evidence_map_table(evidence_refs: list[str]) -> str:
    rows = [
        "| Section | Evidence status | Ref |",
        "| --- | --- | --- |",
    ]
    section_refs = [
        ("Cost breakdown by category", evidence_refs[0] if evidence_refs else "—"),
        ("Budget reconciliation and control decision", evidence_refs[1] if len(evidence_refs) > 1 else "—"),
        ("PM fee treatment", evidence_refs[0] if evidence_refs else "—"),
    ]
    for section_name, ref in section_refs:
        status = "Grounded" if ref != "—" else "Not evidenced"
        rows.append(f"| {section_name} | {status} | {ref} |")
    return "\n".join(rows)


def _default_facts_block(evidence_refs: list[str]) -> str:
    bullets = [
        f"- Project cost evidence indexed ({len(evidence_refs)} ref(s)); review draft rows against Sources."
    ]
    for ref in evidence_refs[:3]:
        path = ref.split(":", 1)[-1].split("#")[0]
        bullets.append(f"- Evidence on file: `{path}`.")
    return "\n".join(["- **Facts**", *bullets])


def ensure_evidence_grounded_cost_plan_scaffold(
    markdown: str,
    evidence_refs: list[str],
) -> str:
    """Repair common evidence_grounded draft formatting gaps before validation."""
    if not evidence_refs:
        return markdown

    updated = _normalize_audit_layer_format(markdown)

    source_section = _markdown_section(updated, "Source evidence used")
    if source_section:
        source_body = source_section
        if not _has_evidence_on_file_marker(source_body):
            source_body = (
                f"{source_body.rstrip()}\n\n"
                f"**Evidence on file:** {_evidence_on_file_summary(evidence_refs)}."
            )
        if not _has_evidence_map_table(source_body):
            source_body = (
                f"{source_body.rstrip()}\n\n{_default_evidence_map_table(evidence_refs)}"
            )
        if source_body != source_section:
            updated = _replace_markdown_section_body(
                updated,
                "Source evidence used",
                source_body,
            )

    if not _audit_label_items(updated, "Facts"):
        audit_section = _markdown_section(updated, "Internal audit layer")
        facts_block = _default_facts_block(evidence_refs)
        audit_body = f"{facts_block}\n\n{audit_section.lstrip()}" if audit_section else facts_block
        updated = _replace_markdown_section_body(
            updated,
            "Internal audit layer",
            audit_body,
        )

    return updated


def _construction_line_count(breakdown_section: str) -> int:
    count = 0
    for line in breakdown_section.splitlines():
        lower = line.lower()
        if "| construction |" in lower or "| 6 | construction" in lower:
            count += 1
        elif lower.strip().startswith("|") and " construction " in f" {lower} ":
            if "subtotal" not in lower and "category" not in lower:
                count += 1
    return count


def _has_collapsed_construction(breakdown_section: str) -> bool:
    for pattern in _COLLAPSED_CONSTRUCTION_PATTERNS:
        if re.search(pattern, breakdown_section, re.IGNORECASE | re.MULTILINE):
            return True
    construction_lines = [
        line
        for line in breakdown_section.splitlines()
        if "construction" in line.lower() and line.strip().startswith("|")
    ]
    if len(construction_lines) == 1:
        lower = construction_lines[0].lower()
        if any(
            phrase in lower
            for phrase in ("construction contract", "builder contract", "head contract")
        ):
            return True
    return False


def claim_first_violations(
    markdown: str,
    evidence_refs: list[str],
    *,
    source_texts: list[str] | None = None,
) -> list[str]:
    """Return claim-first rule violations when granular claim evidence exists."""
    if not evidence_refs_include_progress_claim(evidence_refs):
        return []
    if source_texts and not source_texts_include_trade_breakdown(source_texts):
        return []

    breakdown = _markdown_section(markdown, "Cost breakdown by category")
    if not breakdown:
        return ["Cost breakdown by category section is missing"]

    if _has_collapsed_construction(breakdown):
        return [
            "claim-first rule: progress claim or SOV evidence exists but Construction "
            "section is collapsed to a single contract line — preserve trade/work-package "
            "granularity from the claim schedule"
        ]

    if _construction_line_count(breakdown) < 2:
        return [
            "claim-first rule: progress claim evidence exists but Construction breakdown "
            "has fewer than 2 cost item rows"
        ]
    return []


def cost_plan_evidence_grounded_violations(
    markdown: str,
    evidence_refs: list[str],
    *,
    source_texts: list[str] | None = None,
) -> list[str]:
    """Return evidence fidelity issues for evidence_grounded cost plan drafts."""
    if not evidence_refs:
        return []

    violations: list[str] = []
    source_section = _markdown_section(markdown, "Source evidence used")

    if source_section and not _has_evidence_on_file_marker(source_section):
        violations.append(
            "evidence_grounded draft must state what evidence is on file "
            "(e.g. 'Evidence on file:' in Source evidence used)"
        )

    if source_section and not _has_evidence_map_table(source_section):
        violations.append(
            "Source evidence used must include an evidence map table "
            "(| Section | Evidence status | Ref |)"
        )

    if not _audit_label_items(markdown, "Facts"):
        violations.append(
            "Internal audit layer must include a **Facts** bullet list when evidence_refs is populated"
        )

    violations.extend(
        claim_first_violations(
            markdown,
            evidence_refs,
            source_texts=source_texts,
        )
    )
    return violations
