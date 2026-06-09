from app.sitewise.template import SITEWISE_PROJECT_TEMPLATE


def test_sitewise_project_template_top_level_folders() -> None:
    assert [node.name for node in SITEWISE_PROJECT_TEMPLATE] == [
        "00-brief-pmp",
        "01-cost",
        "02-consultant",
        "03-design",
        "04-planning-and-authorities",
        "05-procurement",
        "06-programme",
        "07-construction",
        "08-reporting",
        "09-handover-dlp",
    ]


def test_sitewise_project_template_exposes_workflow_hints() -> None:
    brief = SITEWISE_PROJECT_TEMPLATE[0]
    construction = SITEWISE_PROJECT_TEMPLATE[7]

    assert "create_pmp" in brief.related_workflows
    assert any(child.name == "02-rfis" for child in construction.children)

