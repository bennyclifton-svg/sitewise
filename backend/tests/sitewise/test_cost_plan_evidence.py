from pathlib import Path

from app.sitewise.cost_plan_evidence import extract_cost_plan_evidence_pack, _parse_owner_supplied

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic-mobilisation-evidence" / "chen-residence"


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_extract_cost_plan_pack_includes_owner_brief_budget() -> None:
    texts = [
        _read("01-engagement-letter-harrison-clarke-studio.md"),
        _read("02-fee-proposal-harrison-clarke-studio.md"),
        _read("03-owner-project-brief-chen-residence.md"),
        _read("09-planning-pathway-memo-harrison-clarke.md"),
    ]
    pack = extract_cost_plan_evidence_pack(texts, ["ref:engagement", "ref:brief"])

    assert pack.construction_budget_ceiling == "1,850,000"
    assert pack.contingency_amount == "120,000"
    assert pack.contingency_percent == "6.5"
    assert pack.owner_brief_on_file is True
    assert pack.fee_total_ex_gst in {"148,500", "$148,500"}
    assert pack.planning_pathway_summary is not None
    assert "cdc not supported" in pack.planning_pathway_summary.lower()
    assert len(pack.owner_supplied_items) == 2


def test_extract_cost_plan_pack_mobilisation_only_has_no_ceiling() -> None:
    texts = [
        _read("01-engagement-letter-harrison-clarke-studio.md"),
        _read("02-fee-proposal-harrison-clarke-studio.md"),
    ]
    pack = extract_cost_plan_evidence_pack(texts, [])

    assert pack.construction_budget_ceiling is None
    assert pack.owner_brief_on_file is False
    assert pack.fee_total_ex_gst in {"148,500", "$148,500"}
    assert "Owner project brief formal sign-off" in pack.gaps
    assert "Construction budget" in pack.gaps


def test_parse_owner_supplied_normalizes_allowance_labels() -> None:
    items = _parse_owner_supplied("pendant lights (allowance $8,000), appliances package (allowance $22,000).")
    assert len(items) == 2
    assert items[0].label == "pendant lights"
    assert items[0].amount_ex_gst == "8,000"
    assert items[1].label == "appliances package"
    assert items[1].amount_ex_gst == "22,000"


def test_extract_cost_plan_pack_full_chen_residence_clears_standard_gaps() -> None:
    texts = [
        _read("01-engagement-letter-harrison-clarke-studio.md"),
        _read("02-fee-proposal-harrison-clarke-studio.md"),
        _read("03-owner-project-brief-chen-residence.md"),
        _read("09-planning-pathway-memo-harrison-clarke.md"),
        _read("06-geotechnical-report-terratech.md"),
        _read("11-master-programme-chen-residence.md"),
        _read("12-certifier-appointment-chen-residence.md"),
    ]
    pack = extract_cost_plan_evidence_pack(texts, [])

    assert pack.planning_memo_on_file is True
    assert pack.planning_pathway_summary is not None
    assert "da + cc" in pack.planning_pathway_summary.lower()
    assert pack.gaps == []


def test_extract_cost_plan_pack_resolves_brief_gaps_when_brief_present() -> None:
    texts = [
        _read("01-engagement-letter-harrison-clarke-studio.md"),
        _read("02-fee-proposal-harrison-clarke-studio.md"),
        _read("03-owner-project-brief-chen-residence.md"),
    ]
    pack = extract_cost_plan_evidence_pack(texts, [])

    assert pack.owner_brief_on_file is True
    assert pack.construction_budget_ceiling == "1,850,000"
    assert "Owner project brief formal sign-off" not in pack.gaps
    assert "Construction budget" not in pack.gaps
    assert "Geotechnical report" in pack.gaps
