from pathlib import Path

from app.sitewise.markdown_sections import (
    assemble_sections,
    doctrine_core_content,
    list_section_ids,
    section_by_id,
    split_sections,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCTRINE_PATH = REPO_ROOT / "docs" / "clerk-brief.md"

STAGE_SECTION_IDS = (
    "00-brief-pmp",
    "01-cost",
    "02-consultant",
    "03-design",
    "04-planning-and-authorities",
    "05-procurement",
    "06-programme",
    "07-construction",
    "08-meetings-reporting",
    "09-handover-dlp",
)

CROSS_CUTTING_ANCHORS = (
    "§voice-and-style",
    "§evidence-discipline",
    "§document-quality-discipline",
    "§seed-consultation-discipline",
    "§register-discipline",
    "§decision-discipline",
    "§escalation-triggers",
    "§owner-communication",
    "§state-handling",
)


def _doctrine_text() -> str:
    return DOCTRINE_PATH.read_text(encoding="utf-8")


def test_doctrine_heading_structure_is_the_expected_contract() -> None:
    """The doctrine's heading structure is a runtime contract: stage sections
    and §-anchors must stay addressable. If this test fails after editing
    docs/clerk-brief.md, update the section IDs everywhere they are consumed."""
    section_ids = list_section_ids(_doctrine_text())

    for stage_id in STAGE_SECTION_IDS:
        assert stage_id in section_ids
    for anchor in CROSS_CUTTING_ANCHORS:
        assert anchor in section_ids
    assert "cross-cutting-rules" in section_ids


def test_doctrine_core_contains_disciplines_not_stage_content() -> None:
    text = _doctrine_text()
    core = doctrine_core_content(text)

    assert core is not None
    assert "## Authority stack" in core
    assert "## §register-discipline" in core
    assert "## §state-handling" in core
    assert "## 03-design" not in core
    assert "## 07-construction" not in core
    # The core must beat the old truncation: previously only the first 12k
    # chars were served, which cut off every cross-cutting rule.
    assert "§state-handling" in core[-len(core) // 2 :]


def test_doctrine_stage_sections_are_loadable_individually() -> None:
    text = _doctrine_text()
    cost_section = assemble_sections(text, ["01-cost"])

    assert cost_section is not None
    assert cost_section.startswith("## 01-cost")
    assert "## 02-consultant" not in cost_section


def test_section_spans_reconstruct_source_text() -> None:
    text = _doctrine_text()
    for section in split_sections(text):
        assert section.content == text[section.start : section.end]


def test_split_sections_skips_frontmatter_and_fences() -> None:
    text = (
        "---\n"
        "tier: topic\n"
        "---\n"
        "# Guide\n"
        "Intro.\n"
        "```text\n"
        "# not a heading\n"
        "```\n"
        "## First\n"
        "Alpha.\n"
        "## Second\n"
        "Beta.\n"
    )
    sections = split_sections(text)

    assert [section.section_id for section in sections] == ["guide", "first", "second"]
    assert sections[0].level == 1
    assert sections[1].parent_id == "guide"
    assert "# not a heading" in sections[0].content
    assert sections[1].content == "## First\nAlpha.\n"


def test_duplicate_slugs_are_qualified_by_parent() -> None:
    text = "# One\n## Notes\nA.\n# Two\n## Notes\nB.\n"
    sections = split_sections(text)

    ids = [section.section_id for section in sections]
    assert ids == ["one", "notes", "two", "two/notes"]
    assert section_by_id(sections, "two/notes").content == "## Notes\nB.\n"
    # Bare ref is ambiguous across parents once qualified IDs exist
    assert section_by_id(sections, "one") is not None


def test_assemble_sections_returns_none_for_unknown_id() -> None:
    assert assemble_sections("# A\nbody\n", ["missing"]) is None


def test_assemble_sections_orders_and_dedupes_nested_spans() -> None:
    text = "# Top\nintro\n## Child\nbody\n# Next\nend\n"
    assembled = assemble_sections(text, ["child", "top"])

    assert assembled == "# Top\nintro\n## Child\nbody"


def test_doctrine_core_returns_none_for_unrecognised_structure() -> None:
    assert doctrine_core_content("no headings at all") is None
