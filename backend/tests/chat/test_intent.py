from app.chat.intent import (
    is_corpus_catalog_question,
    is_pure_catalog_question,
    platform_inventory_scope,
)


def test_pure_catalog_question() -> None:
    assert is_pure_catalog_question("hello, what projects are you aware of?")
    assert is_pure_catalog_question("What projects are in the corpus?")


def test_not_pure_when_asking_for_content() -> None:
    assert not is_pure_catalog_question("What projects have TRR documents?")
    assert not is_pure_catalog_question("Tell me about Block B tender evaluation")


def test_catalog_question_with_greeting() -> None:
    assert is_corpus_catalog_question("hello, what projects are you aware of?")


def test_platform_inventory_scope_detects_seed_listing() -> None:
    assert (
        platform_inventory_scope("list the seed knowledge files you have ingested")
        == "seed"
    )
