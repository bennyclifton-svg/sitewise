from app.sitewise.workspace_tree import build_project_workspace_tree

ROOT = "04-projects/test-project-112"


def test_workspace_tree_includes_consultant_discipline_subfolder() -> None:
    tree = build_project_workspace_tree(
        root_path=ROOT,
        workspace_paths=[
            f"{ROOT}/02-consultant/architect/01-engagement-letter-harrison-clarke-studio.md",
            f"{ROOT}/02-consultant/architect/02-fee-proposal-harrison-clarke-studio.md",
        ],
    )

    consultant = next(node for node in tree if node.name == "02-consultant")
    assert len(consultant.children) == 1
    architect = consultant.children[0]
    assert architect.name == "architect"
    assert architect.document_count == 2
    assert len(architect.children) == 2
    assert {child.name for child in architect.children} == {
        "01-engagement-letter-harrison-clarke-studio.md",
        "02-fee-proposal-harrison-clarke-studio.md",
    }


def test_workspace_tree_preserves_template_children_and_adds_inbox() -> None:
    tree = build_project_workspace_tree(
        root_path=ROOT,
        workspace_paths=[f"{ROOT}/_inbox/report.pdf"],
    )

    cost = next(node for node in tree if node.name == "01-cost")
    assert {child.name for child in cost.children} == {"invoices", "variations"}

    inbox = next(node for node in tree if node.name == "_inbox")
    assert inbox.document_count == 1
