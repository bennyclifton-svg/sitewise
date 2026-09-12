from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from app.sitewise.cost_plan_evidence import extract_cost_plan_evidence_pack
from app.workflows.create_cost_plan import (
    run_create_cost_plan_typed,
    WorkflowValidationError,
)
from tests.conftest import run_async
from tests.workflows.hybrid_cost_plan_fixtures import (
    harrison_clarke_cost_project,
    platform_passages_for_cost_plan,
)
from tests.workflows.hybrid_pmp_fixtures import evidence_passage

CORPUS = (
    Path(__file__).resolve().parents[3]
    / "docs/demo-corpus/seven-hills/01-briefing-and-planning"
)
BRIEF = (CORPUS / "01-client-development-brief.md").read_text(encoding="utf-8")
ADVICE = (CORPUS / "08-feasibility-cost-and-programme-advice.md").read_text(
    encoding="utf-8"
)


def compile_baseline(advice=ADVICE, extra_passages=()):
    project = harrison_clarke_cost_project(
        title="Seven Hills",
        building_class="residential",
        work_type="new",
    )
    passages = [
        evidence_passage(
            f"{project.slug}/{name}.md", content, project_slug=project.slug
        )
        for name, content in [("brief", BRIEF), ("advice", advice)]
    ]
    return run_async(
        run_create_cost_plan_typed(
            project=project,
            passages=passages
            + list(extra_passages)
            + platform_passages_for_cost_plan(project),
            draft_mode="evidence_grounded",
            chat_model="unused",
            project_source_texts=[BRIEF, advice],
            trace=[],
        )
    )


def test_client_budget_does_not_imply_brief_signoff():
    pack = extract_cost_plan_evidence_pack([ADVICE, BRIEF])
    assert pack.owner_brief_on_file
    assert pack.construction_budget_ceiling == "9,800,000"
    assert "Construction budget" not in pack.gaps
    assert "Owner project brief formal sign-off" in pack.gaps


def test_seven_hills_compiler_preserves_qs_forecast_and_uncertainty():
    output = compile_baseline()
    construction = [
        item for item in output._cost_items if item.category == "Construction"
    ]
    assert len(construction) == 10
    assert sum(item.budget for item in construction) == Decimal("10070000")
    assert [item.budget for item in construction] == [
        Decimal(amount)
        for amount in [
            "845000",
            "610000",
            "920000",
            "1530000",
            "1410000",
            "1870000",
            "1255000",
            "900000",
            "350000",
            "380000",
        ]
    ]
    osd = next(item for item in construction if "OSD" in item.item)
    assert osd.budget == Decimal("350000")
    assert "scope not defined" in osd.item
    assert all(
        item.committed == 0 and item.status == "proposed" for item in construction
    )
    assert all(item.source_refs[0]["document_id"] for item in construction)
    assert not any(item.category == "PC allowances" for item in output._cost_items)
    assert "$9,800,000" in output.markdown
    assert "$10,070,000" in output.markdown
    assert "$270,000" in output.markdown
    assert "indicative allocation" not in output.markdown


@pytest.mark.parametrize(
    "advice",
    [
        ADVICE.replace("$10,070,000", "$10,080,000"),
        ADVICE.replace("Allowance excl GST", "Allowance"),
        ADVICE.replace("$350,000", "TBC"),
    ],
    ids=["mismatched-total", "missing-gst-basis", "unpriced-element"],
)
def test_invalid_forecast_does_not_silently_fall_back_to_allowances(advice):
    with pytest.raises(WorkflowValidationError, match="forecast"):
        compile_baseline(advice)


def test_multiple_forecasts_require_selection():
    project = harrison_clarke_cost_project()
    other = evidence_passage(
        f"{project.slug}/other.md", ADVICE, project_slug=project.slug
    )
    with pytest.raises(
        WorkflowValidationError, match="Multiple construction forecasts"
    ):
        compile_baseline(extra_passages=[other])


def test_foreign_project_forecast_cannot_override_project_evidence():
    other = evidence_passage(
        "another-project/advice.md", ADVICE, project_slug="another-project"
    )
    other = other.model_copy(update={"project_id": uuid4()})
    output = compile_baseline(extra_passages=[other])
    assert not any(
        ref.get("document_id") == str(other.document_id)
        for item in output._cost_items
        for ref in item.source_refs
    )


def test_qs_advice_alone_is_not_a_client_brief():
    pack = extract_cost_plan_evidence_pack([ADVICE])
    assert not pack.owner_brief_on_file
    assert pack.construction_budget_ceiling is None
