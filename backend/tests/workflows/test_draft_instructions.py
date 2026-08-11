import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.projects import ProjectProfileView
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.draft_instructions import (
    DraftInstructionSliceOutput,
    SliceInstruction,
    build_slice_prompt,
    format_project_profile,
    run_slice_revision,
    validate_slice_output,
)
from tests.conftest import run_async


def _profile(**overrides: object) -> ProjectProfileView:
    payload: dict[str, object] = {
        "project_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "profile_revision": 1,
        "state": "NSW",
        "site_address": "82 Queen Street, Petersham NSW 2049",
        "client": "Win Pty Ltd",
    }
    payload.update(overrides)
    return ProjectProfileView.model_validate(payload)

DECISION_FENCE = """\
```pmp-decision
{
  "id": "procurement-route",
  "section": "Procurement posture",
  "label": "Procurement route",
  "options": [
    {"value": "traditional", "label": "Traditional (Lump Sum)"},
    {"value": "design_construct", "label": "Design & Construct"}
  ],
  "selected": "traditional",
  "source": "agent",
  "rationale": "Documented single-stage design suits lump sum."
}
```"""

SECTION = f"""\
## Procurement posture

The head builder is procured through a single-stage invited tender.
Retention is held at 10% of each progress claim.

{DECISION_FENCE}

Tender list lock is scheduled before the DA determination.
"""


def _instruction(instruction: str, quoted: str = "Retention is held at 10%") -> SliceInstruction:
    return SliceInstruction(quoted_text=quoted, instruction=instruction)


def _result(markdown: str):
    class _Run:
        output = DraftInstructionSliceOutput(revised_markdown=markdown)

    return _Run()


def test_validator_accepts_a_faithful_revision() -> None:
    revised = SECTION.replace(
        "The head builder is procured through a single-stage invited tender.",
        "The head builder is procured by single-stage invited tender.",
    )
    validate_slice_output(SECTION, revised, instructions=[_instruction("tighten this")])


def test_validator_rejects_modified_heading() -> None:
    revised = SECTION.replace("## Procurement posture", "## Procurement approach")
    with pytest.raises(WorkflowValidationError) as exc:
        validate_slice_output(SECTION, revised, instructions=[_instruction("tighten this")])
    assert "heading line was modified" in str(exc.value)


def test_validator_rejects_new_heading() -> None:
    revised = SECTION + "\n## Extra section\n\nInvented content.\n"
    with pytest.raises(WorkflowValidationError) as exc:
        validate_slice_output(SECTION, revised, instructions=[_instruction("tighten this")])
    assert "revision added a new ## heading" in str(exc.value)


def test_validator_rejects_altered_decision_fence() -> None:
    revised = SECTION.replace('"selected": "traditional"', '"selected": "design_construct"')
    with pytest.raises(WorkflowValidationError) as exc:
        validate_slice_output(SECTION, revised, instructions=[_instruction("tighten this")])
    assert "pmp-decision block was altered or removed" in str(exc.value)


def test_validator_rejects_removed_decision_fence() -> None:
    revised = SECTION.replace(f"{DECISION_FENCE}\n\n", "")
    with pytest.raises(WorkflowValidationError) as exc:
        validate_slice_output(SECTION, revised, instructions=[_instruction("drop the fence")])
    assert "pmp-decision block was altered or removed" in str(exc.value)


def test_validator_rejects_invented_number() -> None:
    revised = SECTION.replace(
        "Tender list lock is scheduled before the DA determination.",
        "Tender list lock is scheduled before the DA determination. Budget is $450,000.",
    )
    with pytest.raises(WorkflowValidationError) as exc:
        validate_slice_output(SECTION, revised, instructions=[_instruction("add a budget line")])
    assert "450,000" in str(exc.value)
    assert "not present in the source, project profile, or instructions" in str(exc.value)


def test_validator_allows_numbers_from_project_profile() -> None:
    section = "## Project Summary\n\n| Field | Detail |\n| --- | --- |\n| Address | 82 Queen Street, Petersham |\n"
    revised = section.replace(
        "82 Queen Street, Petersham",
        "82 Queen Street, Petersham NSW 2049",
    )
    validate_slice_output(
        section,
        revised,
        instructions=[
            _instruction(
                "add state and postcode",
                quoted="82 Queen Street, Petersham",
            )
        ],
        project_profile=_profile(),
    )


def test_validator_allows_number_supplied_in_instruction() -> None:
    revised = SECTION.replace(
        "Retention is held at 10% of each progress claim.",
        "Retention is held at 5% of each progress claim.",
    )
    validate_slice_output(
        SECTION,
        revised,
        instructions=[_instruction("change the retention to 5%")],
    )


def test_validator_ignores_trailing_punctuation_on_numbers() -> None:
    revised = SECTION.replace(
        "Tender list lock is scheduled before the DA determination.",
        "Tender list lock is scheduled before the DA determination, at 10%.",
    )
    validate_slice_output(SECTION, revised, instructions=[_instruction("restate retention")])


def test_validator_rejects_truncated_section() -> None:
    revised = "## Procurement posture\n\nShort.\n"
    with pytest.raises(WorkflowValidationError) as exc:
        validate_slice_output(SECTION, revised, instructions=[_instruction("tighten this")])
    assert "dropped more than half the section" in str(exc.value)


def test_validator_rejects_ballooned_section() -> None:
    body = "Padding sentence that says nothing new. " * 60
    revised = SECTION + body
    with pytest.raises(WorkflowValidationError) as exc:
        validate_slice_output(SECTION, revised, instructions=[_instruction("expand this")])
    assert "more than doubled the section" in str(exc.value)


def test_build_slice_prompt_includes_section_instructions_and_constraints() -> None:
    prompt = build_slice_prompt(
        section_markdown=SECTION,
        instructions=[_instruction("tighten this paragraph")],
        project_title="Chen Residence",
        project_profile=_profile(),
    )
    assert "Project: Chen Residence" in prompt
    assert "--- SECTION START ---" in prompt
    assert "--- SECTION END ---" in prompt
    assert "--- PROJECT PROFILE ---" in prompt
    assert "site_address: 82 Queen Street, Petersham NSW 2049" in prompt
    assert "client: Win Pty Ltd" in prompt
    assert "1. Regarding this passage:" in prompt
    assert "tighten this paragraph" in prompt
    assert "You are not the calculator." in prompt
    assert "REVISION REQUIRED" not in prompt


def test_format_project_profile_skips_empty_fields() -> None:
    rendered = format_project_profile(
        _profile(site_address=None, client="", work_scope=[], scale={})
    )
    assert "state: NSW" in rendered
    assert "site_address" not in rendered
    assert "client" not in rendered
    assert "work_scope" not in rendered
    assert "scale" not in rendered


def test_build_slice_prompt_appends_validation_feedback() -> None:
    prompt = build_slice_prompt(
        section_markdown=SECTION,
        instructions=[_instruction("tighten this")],
        project_title="Chen Residence",
        validation_feedback="heading line was modified",
    )
    assert "REVISION REQUIRED" in prompt
    assert "heading line was modified" in prompt


def test_run_slice_revision_returns_validated_output() -> None:
    revised = SECTION.replace("single-stage invited tender", "single-stage tender")
    runner = AsyncMock(return_value=_result(revised))
    with patch("app.workflows.draft_instructions.run_agent_with_retry", new=runner):
        result = run_async(
            run_slice_revision(
                section_markdown=SECTION,
                instructions=[_instruction("tighten this")],
                project_title="Chen Residence",
            )
        )
    assert result == revised
    assert runner.await_count == 1


def test_run_slice_revision_retries_on_validation_failure() -> None:
    bad = SECTION.replace("## Procurement posture", "## Procurement approach")
    good = SECTION.replace("single-stage invited tender", "single-stage tender")
    runner = AsyncMock(side_effect=[_result(bad), _result(good)])
    with patch("app.workflows.draft_instructions.run_agent_with_retry", new=runner):
        result = run_async(
            run_slice_revision(
                section_markdown=SECTION,
                instructions=[_instruction("tighten this")],
                project_title="Chen Residence",
            )
        )
    assert result == good
    assert runner.await_count == 2
    second_prompt = runner.await_args_list[1].args[1]
    assert "REVISION REQUIRED" in second_prompt
    assert "heading line was modified" in second_prompt


def test_run_slice_revision_raises_after_max_attempts() -> None:
    bad = SECTION.replace("## Procurement posture", "## Procurement approach")
    runner = AsyncMock(return_value=_result(bad))
    with patch("app.workflows.draft_instructions.run_agent_with_retry", new=runner):
        with pytest.raises(WorkflowValidationError):
            run_async(
                run_slice_revision(
                    section_markdown=SECTION,
                    instructions=[_instruction("tighten this")],
                    project_title="Chen Residence",
                    max_attempts=2,
                )
            )
    assert runner.await_count == 2
