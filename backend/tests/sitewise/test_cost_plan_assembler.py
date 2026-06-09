from app.sitewise.cost_plan_assembler import assemble_cost_plan_markdown
from app.sitewise.cost_plan_renderer import render_cost_plan_scaffold
from tests.sitewise.test_pmp_renderer import _harrison_clarke_project
from tests.sitewise.test_cost_plan_renderer import _pack
from tests.workflows.hybrid_cost_plan_fixtures import harrison_clarke_cost_narrative


def test_assemble_cost_plan_markdown_replaces_narrative_placeholders() -> None:
    scaffold = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    markdown = assemble_cost_plan_markdown(
        scaffold,
        harrison_clarke_cost_narrative(),
        provenance={"compiler": "hybrid"},
    )
    lower = markdown.lower()
    assert "[pending cost plan narrative generation]" not in lower
    assert "- **judgements**" in lower
    assert "2026-06-28" in markdown
    assert "| risk | owner | status | next action | due |" in lower
    assert "## recommended next steps" in lower
    assert "1. 1." not in markdown


def test_assemble_cost_plan_markdown_strips_existing_step_numbers() -> None:
    scaffold = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    narrative = harrison_clarke_cost_narrative()
    narrative.next_steps = [
        "1. Owner to confirm owner-supplied allowances by 2026-06-28.",
        "2. Architect-PM to prepare head-builder tender package by 2026-07-05.",
        "3. Architect-PM to reconcile tender pricing to owner brief ceiling by 2026-07-12.",
    ]
    markdown = assemble_cost_plan_markdown(scaffold, narrative)
    assert "1. Owner to confirm owner-supplied allowances by 2026-06-28." in markdown
    assert "1. 1." not in markdown
