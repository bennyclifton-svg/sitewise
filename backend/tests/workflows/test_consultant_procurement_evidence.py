"""Unit tests for consultant-procurement evidence handling.

Covers two generator fixes:
- Exclude consultant fee proposals from RFP evidence (leakage guard).
- Reconcile the parametric fee benchmark against a received
  same-discipline fee proposal already in the corpus.
"""

from typing import Any

from app.workflows import consultant_procurement as workflow
def _item(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "role": "cost_plan_pmp",
        "role_label": "Cost plan / PMP",
        "document_id": "doc",
        "chunk_id": "chunk",
        "filename": "document.md",
        "relative_path": "04-projects/walsh/document.md",
        "page_or_section": None,
        "snippet": "",
        "score": 0.1,
    }
    base.update(overrides)
    return base


# --- Fix 2: leakage guard -------------------------------------------------


def test_is_consultant_fee_proposal_detects_by_filename() -> None:
    item = _item(
        filename="p02-01-fee-proposal-southline-structural.md",
        relative_path="04-projects/walsh/_inbox/p02-01-fee-proposal-southline-structural.md",
    )
    assert workflow._is_consultant_fee_proposal(item) is True


def test_is_consultant_fee_proposal_false_for_owner_brief() -> None:
    item = _item(
        filename="03-owner-project-brief-walsh-house.md",
        relative_path="04-projects/walsh/00-brief-pmp/03-owner-project-brief-walsh-house.md",
    )
    assert workflow._is_consultant_fee_proposal(item) is False


# --- Fix 4: reconcile benchmark with received proposal --------------------


def test_reconcile_forecast_flags_received_structural_proposal() -> None:
    profile = workflow.normalise_discipline("structural engineer")
    forecast = {
        "used": True,
        "label": (
            "$16,500 ex GST judgement allowance for internal budget checking "
            "only; not a received fee proposal."
        ),
    }
    evidence = [
        _item(
            filename="p02-01-fee-proposal-southline-structural.md",
            relative_path="a/p02-01-fee-proposal-southline-structural.md",
            snippet="FEE PROPOSAL - STRUCTURAL ENGINEERING. Total professional fee $20,150.",
        )
    ]

    updated = workflow._reconcile_forecast_with_received(forecast, evidence, profile)

    assert updated["received_proposal_on_file"] is True
    assert updated["received_proposal_amount"] == 20150


def test_reconcile_forecast_ignores_other_discipline_proposal() -> None:
    profile = workflow.normalise_discipline("structural engineer")
    forecast = {"used": True, "label": "benchmark"}
    evidence = [
        _item(
            filename="p02-02-fee-proposal-cascade-hydraulic.md",
            relative_path="a/p02-02-fee-proposal-cascade-hydraulic.md",
            snippet="Total professional fee $11,750.",
        )
    ]

    updated = workflow._reconcile_forecast_with_received(forecast, evidence, profile)

    assert "received_proposal_on_file" not in updated
def test_reconcile_forecast_noop_without_received_proposal() -> None:
    profile = workflow.normalise_discipline("structural engineer")
    forecast = {"used": True, "label": "benchmark"}

    updated = workflow._reconcile_forecast_with_received(forecast, [], profile)

    assert "received_proposal_on_file" not in updated


