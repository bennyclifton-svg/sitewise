"""Unit tests for consultant-procurement evidence handling.

Covers three generator fixes:
- Fix 1: label "Information to review" by the document's own identity, not the
  retrieval query bucket that surfaced it.
- Fix 2: exclude consultant fee proposals from RFP evidence (leakage guard).
- Fix 4: reconcile the parametric fee benchmark against a received
  same-discipline fee proposal already in the corpus.
"""

from types import SimpleNamespace
from typing import Any

from app.workflows import consultant_procurement as workflow


def _overlay_project(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "archetype": "renovation",
        "user_role": "architect-pm",
        "building_class": None,
        "work_type": None,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


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


# --- Fix 1: label by document identity ------------------------------------


def test_document_kind_labels_engagement_letter() -> None:
    # Real regression: this was misfiled under /hydraulic/ and labelled
    # "Project brief" because the project-brief query bucket surfaced it.
    item = _item(
        filename="01-engagement-letter-atelier-north.md",
        relative_path="04-projects/walsh/02-consultant/hydraulic/01-engagement-letter-atelier-north.md",
        role_label="Project brief",
    )
    assert workflow._document_kind(item) == "Engagement letter"


def test_document_kind_none_for_ambiguous_document() -> None:
    item = _item(filename="pathway.pdf", relative_path="04-projects/walsh/02-planning/pathway.pdf")
    assert workflow._document_kind(item) is None


def test_information_to_review_excludes_fee_proposals() -> None:
    evidence = [
        _item(
            filename="03-owner-project-brief-walsh-house.md",
            relative_path="a/03-owner-project-brief-walsh-house.md",
            role_label="Project brief",
        ),
        _item(
            filename="p02-02-fee-proposal-cascade-hydraulic.md",
            relative_path="a/p02-02-fee-proposal-cascade-hydraulic.md",
            role_label="Project brief",
        ),
    ]

    lines = workflow._information_to_review(evidence)

    assert not any("fee-proposal" in line for line in lines)
    assert any("03-owner-project-brief-walsh-house.md" in line for line in lines)


def test_information_to_review_relabels_by_document_identity() -> None:
    evidence = [
        _item(
            filename="01-engagement-letter-atelier-north.md",
            relative_path="a/01-engagement-letter-atelier-north.md",
            role_label="Project brief",
        )
    ]

    lines = workflow._information_to_review(evidence)

    assert lines == ["Engagement letter: a/01-engagement-letter-atelier-north.md"]


def test_information_to_review_falls_back_to_role_label_when_unknown() -> None:
    evidence = [
        _item(
            filename="pathway.pdf",
            relative_path="a/pathway.pdf",
            role_label="Planning pathway",
        )
    ]

    lines = workflow._information_to_review(evidence)

    assert lines == ["Planning pathway: a/pathway.pdf"]


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


# --- Fix 5: resolve mandatory guidance from the knowledge catalog ----------


def test_required_guidance_paths_returns_consultant_procurement_doctrine() -> None:
    # A residential renovation run by an architect-PM (the Walsh shape).
    project = _overlay_project()

    paths = workflow._required_guidance_paths(project)

    assert "seed/procurement-quoting-guide.md" in paths
    # Doctrine core / archetype / role scaffolding is not presented as
    # consultant-procurement guidance.
    assert "docs/clerk-brief.md" not in paths


def test_required_guidance_paths_empty_without_overlays() -> None:
    project = _overlay_project(archetype=None, user_role=None)

    assert workflow._required_guidance_paths(project) == []


def test_merge_required_guidance_surfaces_doctrine_when_semantic_empty() -> None:
    project = _overlay_project()

    merged = workflow._merge_required_guidance([], project)

    assert any(item["path"] == "seed/procurement-quoting-guide.md" for item in merged)
    assert any(item.get("source_type") == "required-doctrine" for item in merged)


def test_merge_required_guidance_does_not_duplicate_semantic_hit() -> None:
    project = _overlay_project()
    existing = [
        {
            "path": "seed/procurement-quoting-guide.md",
            "title": "Procurement guide",
            "source_type": "reference",
        }
    ]

    merged = workflow._merge_required_guidance(existing, project)

    quoting = [i for i in merged if i["path"] == "seed/procurement-quoting-guide.md"]
    assert len(quoting) == 1
