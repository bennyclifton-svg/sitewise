from pathlib import Path

from app.sitewise.mobilisation_evidence import (
    GAP_CONSTRUCTION_BUDGET,
    GAP_OWNER_BRIEF,
    MobilisationEvidencePack,
    extract_mobilisation_evidence_pack,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "data" / "synthetic-mobilisation-evidence" / "chen-residence"
ENGAGEMENT_FIXTURE = FIXTURE_DIR / "01-engagement-letter-harrison-clarke-studio.md"
FEE_FIXTURE = FIXTURE_DIR / "02-fee-proposal-harrison-clarke-studio.md"

ENGAGEMENT_REF = (
    "project_evidence:04-projects/test/02-consultant/architect/"
    "01-engagement-letter-harrison-clarke-studio.md#chunk=abc"
)
FEE_REF = (
    "project_evidence:04-projects/test/02-consultant/architect/"
    "02-fee-proposal-harrison-clarke-studio.md#chunk=def"
)


def _harrison_clarke_source_texts() -> list[str]:
    return [
        ENGAGEMENT_FIXTURE.read_text(encoding="utf-8"),
        FEE_FIXTURE.read_text(encoding="utf-8"),
    ]


def _harrison_clarke_refs() -> list[str]:
    return [ENGAGEMENT_REF, FEE_REF]


def test_extract_mobilisation_evidence_pack_harrison_clarke_identity_and_site() -> None:
    pack = extract_mobilisation_evidence_pack(
        _harrison_clarke_source_texts(),
        _harrison_clarke_refs(),
    )

    assert pack.owners == "Michael and Sarah Chen"
    assert pack.site_address == "14 Wattle Grove, Lindfield NSW 2070"
    assert pack.dwelling_summary is not None
    assert "knockdown-rebuild" in pack.dwelling_summary.lower()
    assert "285" in pack.dwelling_summary
    assert pack.site_constraints is not None
    assert "2.1" in pack.site_constraints
    assert "ku-ring-gai" in pack.site_constraints.lower()


def test_extract_mobilisation_evidence_pack_harrison_clarke_engagement() -> None:
    pack = extract_mobilisation_evidence_pack(
        _harrison_clarke_source_texts(),
        _harrison_clarke_refs(),
    )

    assert pack.engagement_letter_date == "14 May 2026"
    assert pack.engagement_executed_date == "16/05/2026"
    assert pack.appointee == "Harrison Clarke Studio Pty Ltd"
    assert pack.roles is not None
    assert "architect and project manager" in pack.roles.lower()
    assert "superintendent" in pack.roles.lower()
    assert len(pack.scope_bullets) == 7
    assert any("da lodgement" in bullet.lower() for bullet in pack.scope_bullets)
    assert pack.service_exclusions is not None
    assert "interior design" in pack.service_exclusions.lower()
    assert pack.disbursements == "cost + 10%"
    assert pack.owner_approval_rule is not None
    assert "written approval" in pack.owner_approval_rule.lower()


def test_extract_mobilisation_evidence_pack_harrison_clarke_fee_and_programme() -> None:
    pack = extract_mobilisation_evidence_pack(
        _harrison_clarke_source_texts(),
        _harrison_clarke_refs(),
    )

    assert pack.fee_total_ex_gst == "$148,500"
    assert pack.fee_proposal_date == "28 April 2026"
    assert len(pack.fee_stages) == 6
    assert pack.fee_stages[0].stage == "Mobilisation & concept"
    assert pack.fee_stages[0].fee_ex_gst == "$22,000"
    assert pack.fee_stages[-1].stage == "Construction administration"
    assert pack.fee_stages[-1].trigger.lower().startswith("monthly")
    assert "12 months" in pack.fee_stages[-1].trigger.lower()
    assert pack.reporting_cadence == "Monthly owner progress reporting and milestone advice"
    assert pack.target_da_lodgement == "September 2026"


def test_extract_mobilisation_evidence_pack_harrison_clarke_pi_and_procurement() -> None:
    pack = extract_mobilisation_evidence_pack(
        _harrison_clarke_source_texts(),
        _harrison_clarke_refs(),
    )

    assert pack.pi_insurer == "QBE Australia Ltd"
    assert pack.pi_policy_ref == "PI-NSW-2026-44821"
    assert pack.pi_limit == "$5,000,000 any one claim"
    assert "2025" in (pack.pi_period or "")
    assert pack.pi_holder == "HCS"
    assert pack.planning_pathway is not None
    assert "cdc not assumed" in pack.planning_pathway.lower()
    assert pack.invited_builder_count == 3
    assert pack.formal_tender_count == 1
    assert pack.ca_months_assumed == 12
    assert pack.conflict_disclosure is not None
    assert "linden constructions" in pack.conflict_disclosure.lower()


def test_extract_mobilisation_evidence_pack_harrison_clarke_gaps() -> None:
    pack = extract_mobilisation_evidence_pack(
        _harrison_clarke_source_texts(),
        _harrison_clarke_refs(),
    )

    assert "Owner project brief formal sign-off" in pack.gaps
    assert "Construction budget" in pack.gaps
    assert "Geotechnical report" in pack.gaps
    assert "Certifier appointment" in pack.gaps
    assert "Master programme on file" in pack.gaps
    assert pack.evidence_refs == _harrison_clarke_refs()


def test_extract_mobilisation_evidence_pack_empty_source_texts() -> None:
    pack = extract_mobilisation_evidence_pack([], [ENGAGEMENT_REF])

    assert isinstance(pack, MobilisationEvidencePack)
    assert pack.owners is None
    assert len(pack.gaps) == 5
    assert pack.evidence_refs == [ENGAGEMENT_REF]


def test_extract_mobilisation_evidence_pack_chen_stage1_brief_and_budget() -> None:
    texts = _harrison_clarke_source_texts() + [
        (FIXTURE_DIR / "03-owner-project-brief-chen-residence.md").read_text(encoding="utf-8"),
        (FIXTURE_DIR / "04-email-thread-brief-signoff.md").read_text(encoding="utf-8"),
    ]
    pack = extract_mobilisation_evidence_pack(texts, _harrison_clarke_refs())

    assert pack.owner_brief_on_file is True
    assert pack.owner_brief_signed_date is not None
    assert pack.construction_budget_ceiling == "$1,850,000"
    assert GAP_OWNER_BRIEF not in pack.gaps
    assert GAP_CONSTRUCTION_BUDGET not in pack.gaps
    assert pack.ca_months_assumed == 12


def test_normalize_text_fragment_collapses_internal_double_periods() -> None:
    from app.sitewise.mobilisation_evidence import _normalize_text_fragment

    assert _normalize_text_fragment("double garage..") == "double garage."
    assert _normalize_text_fragment("item on title..") == "item on title."
