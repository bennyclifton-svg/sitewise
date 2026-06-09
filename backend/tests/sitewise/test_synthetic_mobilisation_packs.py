"""Parametrized extraction checks for synthetic mobilisation evidence packs."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.sitewise.mobilisation_evidence import (
    build_evidence_on_file_lines,
    extract_mobilisation_evidence_pack,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_ROOT = REPO_ROOT / "data" / "synthetic-mobilisation-evidence"


def _read_paths(*relative_paths: str) -> list[str]:
    return [(EVIDENCE_ROOT / rel).read_text(encoding="utf-8") for rel in relative_paths]


def _read_numbered_dir(subdir: str) -> list[str]:
    folder = EVIDENCE_ROOT / subdir
    return [path.read_text(encoding="utf-8") for path in sorted(folder.glob("[0-9]*.md"))]


@pytest.mark.parametrize(
    ("label", "texts", "expected_gaps", "extra_checks"),
    [
        (
            "chen-baseline",
            _read_paths(
                "chen-residence/01-engagement-letter-harrison-clarke-studio.md",
                "chen-residence/02-fee-proposal-harrison-clarke-studio.md",
            ),
            {
                "Owner project brief formal sign-off",
                "Construction budget",
                "Geotechnical report",
                "Certifier appointment",
                "Master programme on file",
            },
            {"conflict": True, "da_target": "September 2026"},
        ),
        (
            "chen-stage1",
            _read_paths(
                "chen-residence/01-engagement-letter-harrison-clarke-studio.md",
                "chen-residence/02-fee-proposal-harrison-clarke-studio.md",
                "chen-residence/03-owner-project-brief-chen-residence.md",
                "chen-residence/04-email-thread-brief-signoff.md",
            ),
            {
                "Geotechnical report",
                "Certifier appointment",
                "Master programme on file",
            },
            {"conflict": True, "da_target": "September 2026", "budget": "$1,850,000"},
        ),
        (
            "chen-full",
            [p.read_text(encoding="utf-8") for p in sorted((EVIDENCE_ROOT / "chen-residence").glob("[0-9]*.md"))],
            set(),
            {"conflict": True, "da_target": "September 2026"},
        ),
        (
            "walsh-renovation",
            _read_numbered_dir("walsh-renovation"),
            {
                "Geotechnical report",
                "Certifier appointment",
                "Master programme on file",
            },
            {"conflict": False, "da_target": "July 2026"},
        ),
        (
            "nguyen-dual-occ",
            _read_numbered_dir("nguyen-dual-occ"),
            {
                "Geotechnical report",
                "Certifier appointment",
                "Master programme on file",
            },
            {"conflict": False, "cdc": True},
        ),
        (
            "engagement-only",
            _read_paths("engagement-only/01-engagement-letter-harbour-design.md"),
            {
                "Owner project brief formal sign-off",
                "Construction budget",
                "Geotechnical report",
                "Certifier appointment",
                "Master programme on file",
            },
            {"conflict": False, "fee": "$24,500"},
        ),
    ],
)
def test_synthetic_pack_gap_profiles(
    label: str,
    texts: list[str],
    expected_gaps: set[str],
    extra_checks: dict[str, object],
) -> None:
    _ = label
    pack = extract_mobilisation_evidence_pack(texts)
    assert set(pack.gaps) == expected_gaps

    if extra_checks.get("conflict"):
        assert pack.conflict_disclosure
    else:
        assert not pack.conflict_disclosure

    if da_target := extra_checks.get("da_target"):
        assert pack.target_da_lodgement == da_target

    if extra_checks.get("cdc"):
        assert pack.planning_pathway
        assert "cdc" in (pack.planning_pathway or "").lower()

    if fee := extra_checks.get("fee"):
        assert pack.fee_total_ex_gst == fee

    if budget := extra_checks.get("budget"):
        assert pack.construction_budget_ceiling == budget
        assert pack.owner_brief_on_file is True


@pytest.mark.parametrize(
    ("texts", "expected_appointee", "expected_pi_holder"),
    [
        (
            _read_numbered_dir("walsh-renovation"),
            "Atelier North Pty Ltd",
            "Atelier North",
        ),
        (
            _read_paths(
                "chen-residence/01-engagement-letter-harrison-clarke-studio.md",
                "chen-residence/02-fee-proposal-harrison-clarke-studio.md",
            ),
            "Harrison Clarke Studio Pty Ltd",
            "HCS",
        ),
    ],
)
def test_pack_extracts_firm_identity(
    texts: list[str],
    expected_appointee: str,
    expected_pi_holder: str,
) -> None:
    """Appointee and PI holder must be read from evidence, not defaulted to a sample firm."""
    pack = extract_mobilisation_evidence_pack(texts)
    assert pack.appointee == expected_appointee
    assert pack.pi_holder == expected_pi_holder


def test_walsh_pack_captures_builder_rom_and_heritage_advice() -> None:
    """Builder ROM and heritage advice are evidence on file — they must not be dropped."""
    pack = extract_mobilisation_evidence_pack(_read_numbered_dir("walsh-renovation"))

    assert pack.builder_rom is not None
    assert "880,000" in pack.builder_rom and "980,000" in pack.builder_rom
    # ROM must be flagged as not a formal budget (PACK test).
    assert "not a tender" in pack.builder_rom.lower()

    assert pack.heritage_advice is not None
    assert "heritage" in pack.heritage_advice.lower()


def test_walsh_evidence_on_file_lists_every_supplied_document() -> None:
    """All five Walsh evidence documents appear in the document-control inventory."""
    pack = extract_mobilisation_evidence_pack(_read_numbered_dir("walsh-renovation"))
    inventory = " ".join(build_evidence_on_file_lines(pack)).lower()

    assert "engagement letter" in inventory
    assert "fee proposal" in inventory
    assert "owner project brief" in inventory
    assert "cost advice" in inventory  # builder ROM email
    assert "heritage" in inventory  # heritage desktop advice


def test_walsh_reporting_cadence_is_fortnightly() -> None:
    """Cadence must come from evidence (fortnightly), not the monthly default."""
    pack = extract_mobilisation_evidence_pack(_read_numbered_dir("walsh-renovation"))
    assert pack.reporting_cadence is not None
    assert "fortnightly" in pack.reporting_cadence.lower()
