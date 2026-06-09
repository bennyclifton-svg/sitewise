from app.retrieval.query_text import lexical_query_text


def test_lexical_query_text_keeps_domain_terms() -> None:
    assert (
        lexical_query_text("What are the Block B tender evaluation criteria?")
        == "block tender evaluation criteria"
    )


def test_lexical_query_text_keeps_numbers() -> None:
    assert (
        lexical_query_text("Compare tenderer 01 with tenderer 02")
        == "compare tenderer 01 02"
    )


def test_lexical_query_text_falls_back_for_empty_terms() -> None:
    assert lexical_query_text("what is the") == "what is the"
