from app.retrieval.whole_document import _query_terms, score_platform_document


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
