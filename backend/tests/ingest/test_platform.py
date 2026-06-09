from ingest.platform import sitewise_platform_metadata


def test_sitewise_platform_metadata_tags_doctrine() -> None:
    metadata = sitewise_platform_metadata("docs/clerk-brief.md")
    assert metadata == {
        "knowledge_scope": "platform",
        "platform": "sitewise",
        "sitewise_knowledge_kind": "doctrine",
    }


def test_sitewise_platform_metadata_tags_seed_skills_and_templates() -> None:
    assert sitewise_platform_metadata("seed/new-dwelling-guide.md")["sitewise_knowledge_kind"] == "seed"
    assert sitewise_platform_metadata("skills/systems/cost-plan-system.md")["sitewise_knowledge_kind"] == "skill"
    assert sitewise_platform_metadata("project-template/README.md")["sitewise_knowledge_kind"] == "template"


def test_sitewise_platform_metadata_ignores_project_evidence() -> None:
    assert sitewise_platform_metadata("procurement-blockb/brief.pdf") == {}
