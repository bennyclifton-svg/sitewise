from sqlalchemy import select

from app.database.source_document import SourceDocument
from app.retrieval.queries import apply_document_filters
from app.retrieval.schemas import RetrievalFilters


def test_apply_document_filters_matches_subject_and_discipline() -> None:
    filters = RetrievalFilters(
        document_subject="structural", discipline="structural"
    )
    stmt = apply_document_filters(select(SourceDocument.id), filters)
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "subject" in sql
    assert "discipline" in sql


def test_unfiltered_query_does_not_drop_unknown_documents() -> None:
    stmt = apply_document_filters(select(SourceDocument.id), RetrievalFilters())
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "unknown" not in sql
    assert "document_class" not in sql


def test_apply_document_filters_matches_commercial_submission() -> None:
    filters = RetrievalFilters(
        document_class="commercial", procurement_stage="submission"
    )
    stmt = apply_document_filters(select(SourceDocument.id), filters)
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "commercial" in sql
    assert "submission" in sql
    assert "tenderer-01" not in sql.lower()


def test_unknown_tenderer_filename_is_not_a_submission_filter() -> None:
    filters = RetrievalFilters(
        document_class="commercial", procurement_stage="submission"
    )
    stmt = apply_document_filters(select(SourceDocument.id), filters)
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "filename" not in sql.lower()
    assert "unknown" not in sql
