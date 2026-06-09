from app.retrieval.queries import apply_document_filters
from app.retrieval.schemas import RetrievalFilters
from app.database.source_document import SourceDocument
from sqlalchemy import select


def test_project_scope_filter_includes_platform_knowledge() -> None:
    stmt = apply_document_filters(
        select(SourceDocument.id),
        RetrievalFilters(
            active_project="procurement-blockb",
            include_platform_knowledge=True,
        ),
    )

    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "procurement-blockb" in sql
    assert "knowledge_scope" in sql
    assert "doctrine" in sql
    assert "reference" in sql


def test_cross_project_scope_does_not_add_active_project_clause() -> None:
    stmt = apply_document_filters(
        select(SourceDocument.id),
        RetrievalFilters(
            active_project="procurement-blockb",
            include_platform_knowledge=True,
            cross_project=True,
        ),
    )

    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "procurement-blockb" not in sql
