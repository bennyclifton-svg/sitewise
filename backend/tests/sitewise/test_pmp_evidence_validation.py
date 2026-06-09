from app.sitewise.pmp_evidence_validation import (
    _audit_label_items,
    evidence_grounded_violations,
    evidence_refs_include_engagement_letter,
    evidence_refs_include_fee_proposal,
    extract_grounding_anchors,
    extract_project_grounding_facts,
    sanitize_evidence_grounded_markdown,
    sync_document_control_version,
)
from tests.workflows.test_create_pmp import (
    _project_source_texts,
    _replace_pmp_section,
    _valid_evidence_grounded_pmp_markdown,
)


ENGAGEMENT_REF = (
    "project_evidence:04-projects/test/02-consultant/architect/"
    "01-engagement-letter-harrison-clarke-studio.md#chunk=abc"
)
FEE_REF = (
    "project_evidence:04-projects/test/02-consultant/architect/"
    "02-fee-proposal-harrison-clarke-studio.md#chunk=def"
)


def test_evidence_ref_helpers_detect_mobilisation_documents() -> None:
    refs = [ENGAGEMENT_REF, FEE_REF]
    assert evidence_refs_include_engagement_letter(refs)
    assert evidence_refs_include_fee_proposal(refs)


def test_evidence_grounded_violations_accepts_faithful_draft() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    refs = [ENGAGEMENT_REF, FEE_REF]
    assert (
        evidence_grounded_violations(
            markdown,
            refs,
            source_texts=_project_source_texts(),
        )
        == []
    )


def test_extract_grounding_anchors_finds_site_and_owners() -> None:
    anchors = extract_grounding_anchors(_project_source_texts())
    assert any("wattle grove" in anchor for anchor in anchors)
    assert any("michael" in anchor for anchor in anchors)


def test_extract_grounding_anchors_ignores_date_contaminated_spans() -> None:
    anchors = extract_grounding_anchors(
        [
            "14 May 2026 Michael and Sarah Chen 14 Wattle Grove Lindfield NSW 2070",
            "Dear Michael and Sarah Chen,\nRe: 14 Wattle Grove, Lindfield NSW 2070",
        ]
    )
    assert all("14 may 2026" not in anchor for anchor in anchors)
    assert any("wattle grove" in anchor for anchor in anchors)


def test_extract_project_grounding_facts_structures_site_and_owners() -> None:
    facts = extract_project_grounding_facts(_project_source_texts())
    assert "wattle grove" in facts["site"].lower()
    assert "michael" in facts["owners"].lower()


def test_evidence_grounded_violations_rejects_missing_site_in_overview() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    markdown = _replace_pmp_section(
        markdown,
        "Project overview",
        "## Project overview\n\nAssumption: site and owner details pending.\n",
    )
    violations = evidence_grounded_violations(
        markdown,
        [ENGAGEMENT_REF],
        source_texts=_project_source_texts(),
    )
    assert any("Project overview must ground site" in issue for issue in violations)


def test_evidence_grounded_violations_rejects_none_yet_contradiction() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown().replace(
        "Evidence on file:",
        "Source hierarchy: project evidence (none yet). Evidence on file:",
    )
    violations = evidence_grounded_violations(markdown, [ENGAGEMENT_REF])
    assert any("none yet" in issue for issue in violations)


def test_evidence_grounded_violations_rejects_missing_engagement_status() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown().replace("executed", "pending")
    markdown = markdown.replace("signed", "pending")
    markdown = markdown.replace("on file", "pending")
    violations = evidence_grounded_violations(markdown, [ENGAGEMENT_REF])
    assert any("grounded appointment status" in issue for issue in violations)


def test_evidence_grounded_violations_rejects_false_workflow_warning() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown() + "\n- No engagement letter found.\n"
    violations = evidence_grounded_violations(markdown, [ENGAGEMENT_REF])
    assert any("no engagement letter" in issue for issue in violations)


def test_evidence_grounded_violations_rejects_pre_engagement_mobilisation() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown().replace(
        "Post-engagement mobilisation posture; master programme required before September 2026 DA target.",
        "Current mobilisation phase: Assumption: pre-brief / pre-engagement.",
    )
    violations = evidence_grounded_violations(markdown, [ENGAGEMENT_REF])
    assert any("pre-brief / pre-engagement" in issue for issue in violations)


def test_evidence_grounded_violations_requires_evidence_map_table() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    markdown = markdown.replace("| Section | Evidence status | Ref |", "| Item | Status |")
    violations = evidence_grounded_violations(markdown, [ENGAGEMENT_REF])
    assert any("evidence map table" in issue for issue in violations)


def test_evidence_grounded_violations_requires_two_facts() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    markdown = markdown.replace(
        "- HCS engaged as architect-PM; engagement executed 16/05/2026.\n"
        "- Fixed fee $148,500 ex GST on staged triggers per engagement letter.\n"
        "- DA pathway assumed (not CDC) per fee proposal.\n",
        "- Assumption: project facts pending.\n",
    )
    violations = evidence_grounded_violations(markdown, [ENGAGEMENT_REF])
    assert any("at least 2 evidenced project facts" in issue for issue in violations)


def test_audit_label_items_supports_colon_headings_and_nested_bullets() -> None:
    markdown = """## Internal audit layer

- **Facts:**
  - Engagement executed 16/05/2026.
  - Fixed fee $148,500 ex GST per engagement letter.
- **Assumptions:**
  - Construction budget not evidenced.
"""
    facts = _audit_label_items(markdown, "Facts")
    assert len(facts) == 2
    assert all("budget not evidenced" not in item for item in facts)


def test_sanitize_evidence_grounded_markdown_strips_false_workflow_warnings() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    markdown = markdown.replace(
        "- Geotech and certifier not yet on file.\n",
        "- Geotech and certifier not yet on file.\n- No engagement letter found.\n",
    )
    refs = [ENGAGEMENT_REF, FEE_REF]
    cleaned = sanitize_evidence_grounded_markdown(markdown, refs)
    assert "no engagement letter found" not in cleaned.lower()
    assert evidence_grounded_violations(cleaned, refs) == []


def test_sanitize_evidence_grounded_markdown_repairs_project_overview() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    markdown = markdown.replace(
        "Owners: Michael and Sarah Chen.\n"
        "Site: 14 Wattle Grove, Lindfield NSW 2070.\n",
        "- **Assumption**: site address, dwelling type, budget, and owner identity not yet evidenced.\n",
    )
    refs = [ENGAGEMENT_REF, FEE_REF]
    cleaned = sanitize_evidence_grounded_markdown(
        markdown,
        refs,
        source_texts=_project_source_texts(),
    )
    assert "not yet evidenced" not in cleaned.lower()
    assert "wattle grove" in cleaned.lower()
    assert "michael" in cleaned.lower()
    assert (
        evidence_grounded_violations(
            cleaned,
            refs,
            source_texts=_project_source_texts(),
        )
        == []
    )


def test_evidence_grounded_violations_rejects_body_section_filing_contradictions() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    appointment = """## Architect-PM role and appointment

Engagement instruments: fee proposal, executed engagement letter, scope of services — all Assumption: not yet filed.
"""
    markdown = _replace_pmp_section(markdown, "Architect-PM role and appointment", appointment)
    refs = [ENGAGEMENT_REF, FEE_REF]
    violations = evidence_grounded_violations(markdown, refs)
    assert any("not yet filed" in issue for issue in violations)


def test_sanitize_evidence_grounded_markdown_strips_appointment_contradictions() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    appointment = """## Architect-PM role and appointment

Engagement instruments: fee proposal, executed engagement letter — all Assumption: not yet filed.
PI insurance grounded from engagement letter.
"""
    markdown = _replace_pmp_section(markdown, "Architect-PM role and appointment", appointment)
    refs = [ENGAGEMENT_REF, FEE_REF]
    cleaned = sanitize_evidence_grounded_markdown(
        markdown,
        refs,
        source_texts=_project_source_texts(),
    )
    assert "not yet filed" not in cleaned.lower()


def test_sync_document_control_version_aligns_with_draft_version() -> None:
    markdown = _valid_evidence_grounded_pmp_markdown()
    synced = sync_document_control_version(markdown, 8)
    assert "Version v08" in synced
    assert "Version v01" not in synced


GEOTECH_REF = (
    "project_evidence:04-projects/test/03-design/01-due-diligence/"
    "06-geotechnical-report-terratech.md#chunk=geo"
)


def _chen_stage1_markdown_snippet() -> str:
    return """## Evidence basis and document control

**Evidence on file:**
- Geotechnical report — issued 22 May 2026.

| Section | Evidence status | Ref |
| --- | --- | --- |
| Geotechnical report | Grounded | geotechnical report |

## Programme and staging regime

| Sub-milestone | Maps to stage | Status | Note |
| --- | --- | --- | --- |
| Planning pathway confirmed | Stage 1 | Grounded | CDC / DA / exempt |

Planning pathway (fee proposal): Single DA pathway (CDC not assumed at this stage)

## Risks, decisions and next actions
| Risk | Owner | Status | Next action | Due |
| --- | --- | --- | --- | --- |
| Reactive soil / footing type unknown | Architect-PM | Assumption | Certify footing design | TBC |

## Internal audit layer

- **Facts**
  - Geotechnical report on file confirms H1 site classification.
- **Workflow warnings**
  - Geotechnical report is required for determining site-specific conditions.
"""


def test_sanitize_strips_false_geotech_workflow_warning_when_geotech_on_file() -> None:
    markdown = _chen_stage1_markdown_snippet()
    refs = [ENGAGEMENT_REF, GEOTECH_REF]
    cleaned = sanitize_evidence_grounded_markdown(markdown, refs)
    assert "geotechnical report is required" not in cleaned.lower()
    violations = evidence_grounded_violations(cleaned, refs)
    assert not any("geotechnical report is required" in issue for issue in violations)


def test_sanitize_repairs_reactive_soil_risk_when_h1_on_file() -> None:
    markdown = _chen_stage1_markdown_snippet()
    refs = [ENGAGEMENT_REF, GEOTECH_REF]
    cleaned = sanitize_evidence_grounded_markdown(markdown, refs)
    assert "footing type unknown" not in cleaned.lower()
    assert "h1 on file" in cleaned.lower()
    assert "| Partial |" in cleaned


def test_sanitize_repairs_planning_pathway_submilestone_note() -> None:
    markdown = _chen_stage1_markdown_snippet()
    refs = [ENGAGEMENT_REF, FEE_REF]
    cleaned = sanitize_evidence_grounded_markdown(markdown, refs)
    assert "CDC / DA / exempt" not in cleaned
    assert "Single DA (CDC not assumed)" in cleaned


def test_sanitize_collapses_duplicate_periods() -> None:
    markdown = "Knockdown-rebuild.. Proposed dwelling.."
    cleaned = sanitize_evidence_grounded_markdown(
        markdown,
        [ENGAGEMENT_REF],
    )
    assert ".." not in cleaned


def test_evidence_grounded_violations_rejects_false_geotech_workflow_warning() -> None:
    markdown = _chen_stage1_markdown_snippet()
    violations = evidence_grounded_violations(markdown, [ENGAGEMENT_REF, GEOTECH_REF])
    assert any("geotechnical report is required" in issue for issue in violations)


def test_evidence_grounded_violations_allows_geotech_action_when_not_evidenced() -> None:
    markdown = """## Evidence basis and document control

**Evidence on file:**
- Engagement letter executed 16/05/2026.

| Section | Evidence status | Ref |
| --- | --- | --- |
| Appointment & fee | Grounded | engagement letter |
| Geotechnical report | Not evidenced | — |

## Internal audit layer

- **Facts**
  - Engagement letter executed 16/05/2026.
  - Fixed fee $148,500 ex GST per engagement letter.
- **Workflow warnings**
  - Commission geotechnical report before scheme lock.
"""
    violations = evidence_grounded_violations(markdown, [ENGAGEMENT_REF])
    assert not any("commission geotechnical report" in issue for issue in violations)


def test_sanitize_repairs_v15_like_draft_without_evidence_refs() -> None:
    markdown = _chen_stage1_markdown_snippet()
    cleaned = sanitize_evidence_grounded_markdown(
        markdown,
        [],
        source_texts=["AS 2870-2011 Site Classification: H1 (highly reactive clay)"],
    )
    assert "geotechnical report is required" not in cleaned.lower()
    assert "CDC / DA / exempt" not in cleaned
    assert "footing type unknown" not in cleaned.lower()
    assert evidence_grounded_violations(
        cleaned,
        [],
        source_texts=["AS 2870-2011 Site Classification: H1 (highly reactive clay)"],
    ) == []
