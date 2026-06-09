import pytest

from app.intake.classifier import (
    classify_inbox_destination,
    inbox_package_folder,
    is_intake_manifest,
)

PROJECT = "04-projects/greenfield-demo"


def test_is_intake_manifest_matches_versioned_names() -> None:
    assert is_intake_manifest("intake_manifest_v01.md")
    assert is_intake_manifest("intake_manifest_v12.md")
    assert not is_intake_manifest("report.pdf")


def test_inbox_package_folder_returns_top_level_package() -> None:
    path = f"{PROJECT}/_inbox/ARCHITECTURE/CC 010/CC-A-010 SITE PLAN.pdf"
    assert inbox_package_folder(path, PROJECT) == "ARCHITECTURE"


def test_classify_architecture_package_to_design_architect() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/ARCHITECTURE/drawing.pdf",
        filename="drawing.pdf",
        project_workspace_path=PROJECT,
    )
    assert destination == "03-design/architect"


def test_classify_da_package_to_planning_authorities() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/DA, MODS & STAMPED PLANS/plan.pdf",
        filename="plan.pdf",
        project_workspace_path=PROJECT,
    )
    assert destination == "04-planning-and-authorities"


def test_classify_cc_a_filename_without_package() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/CC-A-010 SITE PLAN.pdf",
        filename="CC-A-010 SITE PLAN.pdf",
        project_workspace_path=PROJECT,
    )
    assert destination == "03-design/architect"


def test_classify_electrical_sheet_prefix() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/E03 - LIGHTING.pdf",
        filename="E03 - LIGHTING.pdf",
        project_workspace_path=PROJECT,
    )
    assert destination == "03-design/electrical"


def test_classify_returns_none_for_unknown_files() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/random-notes.txt",
        filename="random-notes.txt",
        project_workspace_path=PROJECT,
    )
    assert destination is None


def test_classify_engagement_letter_to_consultant_architect() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/01-engagement-letter-harrison-clarke-studio.md",
        filename="01-engagement-letter-harrison-clarke-studio.md",
        project_workspace_path=PROJECT,
        preview_snippet="# LETTER OF ENGAGEMENT\n\nArchitect and project management services",
    )
    assert destination == "02-consultant/architect"


def test_classify_fee_proposal_to_consultant_architect() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/02-fee-proposal-harrison-clarke-studio.md",
        filename="02-fee-proposal-harrison-clarke-studio.md",
        project_workspace_path=PROJECT,
        preview_snippet="# FEE PROPOSAL\n\nArchitectural design, consultant coordination",
    )
    assert destination == "02-consultant/architect"


def test_classify_project_brief_to_brief_pmp_folder() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/owner-project-brief.md",
        filename="owner-project-brief.md",
        project_workspace_path=PROJECT,
    )
    assert destination == "00-brief-pmp"


def test_classify_email_thread_brief_signoff_to_brief_pmp_folder() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/04-email-thread-brief-signoff.md",
        filename="04-email-thread-brief-signoff.md",
        project_workspace_path=PROJECT,
    )
    assert destination == "00-brief-pmp"


def test_classify_brief_signoff_preview_to_brief_pmp_folder() -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/thread.md",
        filename="thread.md",
        project_workspace_path=PROJECT,
        preview_snippet=(
            "Subject: RE: Owner brief — Chen Residence — ready for your sign-off\n\n"
            "**Brief formal sign-off received** — filed as owner project brief signed 14 May 2026."
        ),
    )
    assert destination == "00-brief-pmp"


@pytest.mark.parametrize(
    ("filename", "preview_snippet"),
    [
        ("05-survey-report-north-shore-surveying.md", "# FEATURE & LEVEL SURVEY REPORT"),
        ("06-geotechnical-report-terratech.md", "# GEOTECHNICAL INVESTIGATION REPORT"),
        ("07-dilapidation-report-buildcheck.md", "# DILAPIDATION CONDITION REPORT"),
        (
            "08-email-sydney-water-sewer-diagram.md",
            "Subject: Sewerage services diagram — 14 Wattle Grove Lindfield",
        ),
    ],
)
def test_classify_chen_due_diligence_pack_to_due_diligence_folder(
    filename: str,
    preview_snippet: str,
) -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/{filename}",
        filename=filename,
        project_workspace_path=PROJECT,
        preview_snippet=preview_snippet,
    )
    assert destination == "03-design/01-due-diligence"


@pytest.mark.parametrize(
    ("filename", "preview_snippet"),
    [
        (
            "09-planning-pathway-memo-harrison-clarke.md",
            "# PLANNING PATHWAY MEMO\n\nPursue DA + CC pathway via Ku-ring-gai Council.",
        ),
        (
            "12-certifier-appointment-chen-residence.md",
            "Subject: Principal certifier appointed\n\nCertifier engagement on file.",
        ),
    ],
)
def test_classify_chen_authority_pack_to_planning_authorities(
    filename: str,
    preview_snippet: str,
) -> None:
    destination = classify_inbox_destination(
        workspace_path=f"{PROJECT}/_inbox/{filename}",
        filename=filename,
        project_workspace_path=PROJECT,
        preview_snippet=preview_snippet,
    )
    assert destination == "04-planning-and-authorities"
