from app.retrieval.router import should_use_whole_document_path
from app.retrieval.schemas import RetrievalFilters


def test_whole_document_path_for_platform_questions() -> None:
    assert should_use_whole_document_path("what is a PMP", filters=None)
    assert should_use_whole_document_path(
        "what are the main stages of a residential construction program",
        filters=None,
    )


def test_whole_document_path_off_for_inventory() -> None:
    assert not should_use_whole_document_path(
        "list the seed knowledge files you have ingested",
        filters=None,
    )


def test_whole_document_path_off_for_cross_project() -> None:
    assert not should_use_whole_document_path(
        "what is a PMP",
        filters=RetrievalFilters(cross_project=True),
    )


def test_whole_document_path_off_for_project_only_scope() -> None:
    assert not should_use_whole_document_path(
        "what is the contract sum",
        filters=RetrievalFilters(
            active_project="delivery-house",
            include_platform_knowledge=False,
        ),
    )


def test_whole_document_path_off_for_project_evidence_question() -> None:
    assert not should_use_whole_document_path(
        "What are the evaluation criteria?",
        filters=None,
    )
