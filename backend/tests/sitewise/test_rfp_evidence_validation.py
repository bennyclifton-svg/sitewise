import pytest

from app.sitewise.rfp_evidence_validation import validate_rfp_output
from app.sitewise.rfp_renderer import build_rfp_citation_index
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.rfp_narrative import RfpNarrativeOutput


def test_rfp_validation_rejects_out_of_range_citation() -> None:
    citation_index = build_rfp_citation_index(
        [
            {"relative_path": "docs/brief.pdf"},
            {"relative_path": "docs/site-plan.pdf"},
            {"relative_path": "docs/survey.pdf"},
        ]
    )
    output = RfpNarrativeOutput(
        background="The brief confirms the proposed works. [99]",
        information_to_review=["Review the site plan. [2]"],
    )

    with pytest.raises(WorkflowValidationError, match=r"\[99\]"):
        validate_rfp_output(output, citation_index=citation_index)
