import pytest

from ingest.metadata import infer_project_context


@pytest.mark.parametrize(
    ("relative_path", "project", "phase", "source_type"),
    [
        ("procurment-demo/rft.pdf", "procurment-demo", "procurement", "project_evidence"),
        ("delivery-house/contract.pdf", "delivery-house", "delivery", "project_evidence"),
        ("seed/defects-and-dlp-guide.md", "sitewise-platform", "reference", "reference"),
        ("docs/clerk-brief.md", "sitewise-platform", "reference", "doctrine"),
        ("skills/systems/cost-plan-system.md", "sitewise-platform", "reference", "reference"),
        ("project-template/README.md", "sitewise-platform", "reference", "reference"),
        ("procurement-blockb/03 RFT/spec.pdf", "procurement-blockb", "procurement", "project_evidence"),
    ],
)
def test_infer_project_context(relative_path, project, phase, source_type):
    context = infer_project_context(relative_path)
    assert context.project == project
    assert context.phase == phase
    assert context.source_type == source_type
