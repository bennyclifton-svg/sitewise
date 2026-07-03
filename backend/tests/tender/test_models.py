import tender.models  # noqa: F401 — register tender mappers
from app.database.base import Base

EXPECTED_TABLES = {
    # core pipeline
    "tender_comparisons",
    "tender_quotes",
    "tender_documents",
    "tender_pages",
    "tender_line_items",
    # taxonomy & knowledge
    "taxonomy_cells",
    "taxonomy_synonyms",
    "expectation_rules",
    "benchmarks",
    # mapping, status, flags
    "tender_mappings",
    "tender_cell_status",
    "tender_flags",
    "tender_analysis_results",
    "tender_corrections",
    "tender_reports",
    "tender_telemetry_events",
    # jobs & evaluation
    "tender_jobs",
    "golden_documents",
    "golden_annotations",
    "eval_runs",
    "eval_results",
}


def _unique_constraint_columns(table_name: str) -> set[tuple[str, ...]]:
    from sqlalchemy import UniqueConstraint

    table = Base.metadata.tables[table_name]
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _foreign_key_targets(table_name: str, column_name: str) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {fk.target_fullname for fk in table.columns[column_name].foreign_keys}


def test_all_tender_tables_registered() -> None:
    missing = EXPECTED_TABLES - set(Base.metadata.tables)
    assert not missing, f"tables missing from metadata: {sorted(missing)}"


def test_tender_pages_checkpoint_unique_constraint() -> None:
    assert ("document_id", "page_no") in _unique_constraint_columns("tender_pages")


def test_tender_documents_dedupe_unique_constraint() -> None:
    assert ("quote_id", "content_hash") in _unique_constraint_columns("tender_documents")


def test_tender_cell_status_unique_constraint() -> None:
    assert ("comparison_id", "quote_id", "cell_code") in _unique_constraint_columns(
        "tender_cell_status"
    )


def test_tender_analysis_result_unique_constraint() -> None:
    assert ("comparison_id",) in _unique_constraint_columns("tender_analysis_results")


def test_taxonomy_synonyms_unique_constraint() -> None:
    assert ("cell_code", "phrase_norm") in _unique_constraint_columns("taxonomy_synonyms")


def test_comparison_foreign_keys_target_clerk_core() -> None:
    assert _foreign_key_targets("tender_comparisons", "project_id") == {"projects.id"}
    assert _foreign_key_targets("tender_comparisons", "created_by") == {"users.id"}


def test_report_draft_fk_targets_draft_artifacts() -> None:
    assert _foreign_key_targets("tender_reports", "draft_id") == {"draft_artifacts.id"}


def test_tender_jobs_claim_index_exists() -> None:
    table = Base.metadata.tables["tender_jobs"]
    indexed = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("status", "run_after") in indexed


def test_tender_telemetry_indexes_exist() -> None:
    table = Base.metadata.tables["tender_telemetry_events"]
    indexed = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("comparison_id",) in indexed
    assert ("comparison_id", "stage") in indexed


def test_line_item_embedding_is_1536_vector() -> None:
    from pgvector.sqlalchemy import Vector

    column = Base.metadata.tables["tender_line_items"].columns["embedding"]
    assert isinstance(column.type, Vector)
    assert column.type.dim == 1536
    assert column.nullable


def test_taxonomy_synonym_embedding_is_1536_vector() -> None:
    from pgvector.sqlalchemy import Vector

    column = Base.metadata.tables["taxonomy_synonyms"].columns["embedding"]
    assert isinstance(column.type, Vector)
    assert column.type.dim == 1536
    assert column.nullable
