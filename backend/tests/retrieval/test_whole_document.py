from pathlib import Path

from app.retrieval.whole_document import (
    _query_terms,
    doctrine_passage_content,
    score_platform_document,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_query_terms_strips_stopwords() -> None:
    assert _query_terms("what is a PMP") == ["pmp"]


def test_score_platform_document_prefers_doctrine() -> None:
    seed_score = score_platform_document(
        relative_path="seed/guide.md",
        filename="guide.md",
        content="PMP guidance for residential projects.",
        source_type="reference",
        terms=["pmp"],
    )
    doctrine_score = score_platform_document(
        relative_path="docs/clerk-brief.md",
        filename="clerk-brief.md",
        content="PMP programme section.",
        source_type="doctrine",
        terms=["pmp"],
    )
    assert doctrine_score > seed_score


def test_doctrine_passage_serves_core_disciplines_not_first_n_chars() -> None:
    """Regression: func.left truncation used to cut the doctrine at 12k chars,
    so no platform turn ever saw the cross-cutting rules."""
    full_text = (REPO_ROOT / "docs" / "clerk-brief.md").read_text(encoding="utf-8")

    content, is_core = doctrine_passage_content(full_text, max_chars=12000)

    assert is_core
    assert "## §register-discipline" in content
    assert "## §state-handling" in content
    assert "## 03-design" not in content


def test_doctrine_passage_falls_back_to_truncation_without_headings() -> None:
    content, is_core = doctrine_passage_content("plain text " * 100, max_chars=50)

    assert not is_core
    assert len(content) == 50
