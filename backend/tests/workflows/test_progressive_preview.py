from __future__ import annotations

from types import SimpleNamespace

from app.sitewise.rfp_renderer import (
    BACKGROUND_PLACEHOLDER,
    PROGRAMME_PLACEHOLDER,
    REQUESTED_SERVICES_PLACEHOLDER,
)
from app.workflows.progressive_preview import (
    assemble_procurement_progressive_preview,
)
from app.sitewise.pmp_assembler import assemble_pmp_markdown
from app.workflows.pmp_narrative import PmpNarrativeOutput
from app.workflows.progressive_preview import assemble_pmp_progressive_preview


def test_procurement_progressive_preview_fills_one_placeholder_at_a_time() -> None:
    scaffold = (
        f"## Background\n\n{BACKGROUND_PLACEHOLDER}\n\n"
        f"## Scope\n\n{REQUESTED_SERVICES_PLACEHOLDER}\n\n"
        f"## Programme\n\n{PROGRAMME_PLACEHOLDER}\n"
    )
    completed = {
        "background": SimpleNamespace(
            output=SimpleNamespace(background="Completed background text.")
        )
    }

    preview = assemble_procurement_progressive_preview(scaffold, completed)

    assert "Completed background text." in preview
    assert REQUESTED_SERVICES_PLACEHOLDER in preview
    assert PROGRAMME_PLACEHOLDER in preview


def test_pmp_progressive_preview_uses_completed_sections_only() -> None:
    scaffold = (
        "# Project Management Plan\n\n"
        "## Internal audit layer\n\n"
        "- **Evidence**\n"
        "  - On file\n"
        "- **Judgements**\n"
        "  - [Pending narrative generation — Phase 3]\n\n"
        "## Risks, decisions and next actions\n\n"
        "Risk wording and owner decision due dates: "
        "[Pending narrative generation — Phase 3]\n"
    )
    completed = {
        "assessment": SimpleNamespace(
            output=SimpleNamespace(
                judgements=["Fee proposal is on file.", "Programme target is known."],
                workflow_warnings=[],
            )
        )
    }

    preview = assemble_pmp_progressive_preview(scaffold, completed)
    full = assemble_pmp_markdown(
        scaffold,
        PmpNarrativeOutput.model_construct(
            judgements=["Fee proposal is on file.", "Programme target is known."],
            workflow_warnings=[],
            recommendations=[],
            register_rows=[],
            risk_rows=[],
        ),
    )

    assert "Fee proposal is on file." in preview
    assert preview == full


def test_blocked_section_still_leaves_completed_content_reviewable() -> None:
    scaffold = (
        f"## Background\n\n{BACKGROUND_PLACEHOLDER}\n\n"
        f"## Scope\n\n{REQUESTED_SERVICES_PLACEHOLDER}\n\n"
        f"## Programme\n\n{PROGRAMME_PLACEHOLDER}\n"
    )
    completed = {
        "requested_services": SimpleNamespace(
            output=SimpleNamespace(
                requested_services=["Prepare structural design drawings."]
            )
        )
    }

    preview = assemble_procurement_progressive_preview(scaffold, completed)

    assert "Prepare structural design drawings." in preview
    assert BACKGROUND_PLACEHOLDER in preview
