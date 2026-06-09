from app.workflows.create_cost_plan import select_cost_evidence_paths


def test_select_cost_evidence_paths_reserves_mobilisation_pack_documents() -> None:
    paths = [
        "04-projects/test/02-consultant/architect/01-engagement-letter-harrison-clarke-studio.md",
        "04-projects/test/02-consultant/architect/02-fee-proposal-harrison-clarke-studio.md",
        "04-projects/test/00-brief-pmp/03-owner-project-brief-chen-residence.md",
        "04-projects/test/00-brief-pmp/09-planning-pathway-memo-harrison-clarke.md",
        "04-projects/test/03-design/01-due-diligence/06-geotechnical-report-terratech.md",
        "04-projects/test/00-brief-pmp/11-master-programme-chen-residence.md",
        "04-projects/test/04-authority/12-certifier-appointment-chen-residence.md",
        "04-projects/test/03-design/01-due-diligence/05-survey-report-north-shore-surveying.md",
    ]

    selected = select_cost_evidence_paths(paths, limit=12)

    assert any("engagement-letter" in path for path in selected)
    assert any("fee-proposal" in path for path in selected)
    assert any("owner-project-brief" in path for path in selected)
    assert any("planning-pathway" in path for path in selected)
    assert any("geotechnical" in path for path in selected)
    assert any("master-programme" in path for path in selected)
    assert any("certifier" in path for path in selected)


def test_select_cost_evidence_paths_includes_due_diligence_and_authority_markers() -> None:
    paths = [
        "04-projects/test/03-design/01-due-diligence/06-geotechnical-report-terratech.md",
        "04-projects/test/04-authority/12-certifier-appointment-chen-residence.md",
    ]

    selected = select_cost_evidence_paths(paths, limit=12)

    assert len(selected) == 2
