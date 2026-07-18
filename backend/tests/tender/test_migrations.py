"""Migration coverage for the tender chain (007–011).

The chain/structure tests run anywhere. The roundtrip test is marked
``integration``: it applies ``upgrade head``, walks back down to
006_cockpit_refresh_indexes (dropping the tender tables), and re-upgrades —
run it only against a database where the tender tables carry no data you
want to keep.
"""

import os
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[2]
PRE_TENDER_REV = "006_cockpit_refresh_indexes"
MIGRATION_CHAIN = [
    "007_tender_core",
    "008_tender_knowledge",
    "009_tender_mapping_status",
    "010_tender_jobs_eval",
    "011_tender_report_language",
    "012_tender_mapping_support",
    "013_tender_analysis_results",
    "014_chat_threads_hermes_session",
    "015_tender_telemetry_events",
    "016_stripe_billing",
    "017_project_activity_events",
    "018_project_taxonomy",
    "019_project_decisions",
    "020_tender_extract_cache",
]
TENDER_REVISIONS = [
    "007_tender_core",
    "008_tender_knowledge",
    "009_tender_mapping_status",
    "010_tender_jobs_eval",
    "011_tender_report_language",
    "012_tender_mapping_support",
    "013_tender_analysis_results",
    "015_tender_telemetry_events",
    "020_tender_extract_cache",
]
HEAD_REVISION = "020_tender_extract_cache"


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def _script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(_alembic_config())


def test_tender_migrations_chain_in_order() -> None:
    scripts = _script_directory()
    expected_parent = PRE_TENDER_REV
    for revision in MIGRATION_CHAIN:
        script = scripts.get_revision(revision)
        assert script.down_revision == expected_parent
        expected_parent = revision


def test_head_is_last_tender_migration() -> None:
    assert _script_directory().get_current_head() == HEAD_REVISION


def test_every_tender_migration_has_real_downgrade() -> None:
    for revision in TENDER_REVISIONS:
        module_path = BACKEND_DIR / "alembic" / "versions" / f"{revision}.py"
        source = module_path.read_text(encoding="utf-8")
        assert "def downgrade() -> None:" in source
        downgrade_body = source.split("def downgrade() -> None:", 1)[1]
        assert any(
            operation in downgrade_body
            for operation in ("drop_table", "drop_column", "drop_index", "drop_constraint")
        ), f"{revision} downgrade drops nothing"


@pytest.mark.integration
def test_tender_migrations_roundtrip_against_database() -> None:
    """upgrade head → downgrade to pre-tender → upgrade head, then spot-check schema."""
    if os.environ.get("TENDER_MIGRATION_ROUNDTRIP") != "1":
        pytest.skip(
            "DESTRUCTIVE: drops and recreates every tender table (data and seeds "
            "included) on settings.database_url. Set TENDER_MIGRATION_ROUNDTRIP=1 "
            "against a disposable database to run it."
        )

    import sqlalchemy as sa
    from alembic import command

    from app.config import settings

    def sync_database_url() -> str:
        url = settings.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        if "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"
        return url

    config = _alembic_config()

    command.upgrade(config, "head")
    command.downgrade(config, PRE_TENDER_REV)

    engine = sa.create_engine(sync_database_url())
    try:
        inspector = sa.inspect(engine)
        assert "tender_jobs" not in inspector.get_table_names()
        assert "tender_pages" not in inspector.get_table_names()

        command.upgrade(config, "head")

        inspector = sa.inspect(engine)
        tables = inspector.get_table_names()
        for table in (
            "tender_comparisons",
            "tender_pages",
            "tender_jobs",
            "eval_results",
            "report_language",
            "taxonomy_synonyms",
        ):
            assert table in tables

        benchmark_unique_names = {
            constraint["name"] for constraint in inspector.get_unique_constraints("benchmarks")
        }
        assert "uq_benchmarks_stable_key" in benchmark_unique_names

        unique_names = {
            constraint["name"] for constraint in inspector.get_unique_constraints("tender_pages")
        }
        assert "uq_tender_pages_document_id_page_no" in unique_names

        with engine.connect() as connection:
            embedding_type = connection.execute(
                sa.text(
                    """
                    SELECT format_type(a.atttypid, a.atttypmod)
                    FROM pg_attribute a
                    WHERE a.attrelid = 'tender_line_items'::regclass
                      AND a.attname = 'embedding'
                    """
                )
            ).scalar_one()
            synonym_embedding_type = connection.execute(
                sa.text(
                    """
                    SELECT format_type(a.atttypid, a.atttypmod)
                    FROM pg_attribute a
                    WHERE a.attrelid = 'taxonomy_synonyms'::regclass
                      AND a.attname = 'embedding'
                    """
                )
            ).scalar_one()
            synonym_indexes = {
                row[0]
                for row in connection.execute(
                    sa.text(
                        """
                        SELECT indexname
                        FROM pg_indexes
                        WHERE tablename = 'taxonomy_synonyms'
                        """
                    )
                )
            }
        assert embedding_type == "vector(1536)"
        assert synonym_embedding_type == "vector(1536)"
        assert "ix_taxonomy_synonyms_phrase_norm_trgm" in synonym_indexes
        assert "ix_taxonomy_synonyms_embedding" in synonym_indexes
    finally:
        engine.dispose()
