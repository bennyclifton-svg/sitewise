import uuid

from app.retrieval.queries import apply_document_filters
from app.retrieval.schemas import RetrievalFilters
from app.database.source_document import SourceDocument
from sqlalchemy import select


def test_project_scope_filter_includes_platform_knowledge() -> None:
    stmt = apply_document_filters(
        select(SourceDocument.id),
        RetrievalFilters(
            active_project_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            include_platform_knowledge=True,
        ),
    )

    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "11111111111111111111111111111111" in sql
    assert "knowledge_scope" in sql
    assert "project_id IS NULL" in sql


def test_cross_project_scope_is_limited_to_authorized_project_ids() -> None:
    stmt = apply_document_filters(
        select(SourceDocument.id),
        RetrievalFilters(
            active_project_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            authorized_project_ids=(
                uuid.UUID("11111111-1111-1111-1111-111111111111"),
                uuid.UUID("22222222-2222-2222-2222-222222222222"),
            ),
            include_platform_knowledge=True,
            cross_project=True,
        ),
    )

    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "11111111111111111111111111111111" in sql
    assert "22222222222222222222222222222222" in sql
