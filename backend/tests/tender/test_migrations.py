"""Migration coverage for the tender chain (007–011).

The chain/structure tests run anywhere. The roundtrip test is marked
``integration``: it applies ``upgrade head``, walks back down to
006_cockpit_refresh_indexes (dropping the tender tables), and re-upgrades —
run it only against a database where the tender tables carry no data you
want to keep.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
    "021_source_document_uuid_expand",
    "021b_source_doc_path_contract",
    "022_source_doc_uuid_contract",
    "023_agent_turns",
    "024_tender_quote_total_source",
    "025_project_profile_revision",
    "026_project_events",
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
    "024_tender_quote_total_source",
]
DESTRUCTIVE_OPT_IN = "ALLOW_DESTRUCTIVE_TEST_DATABASE"


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


def _verify_migration_graph(scripts: ScriptDirectory) -> str:
    heads = scripts.get_heads()
    assert len(heads) == 1, f"migration graph must have one head; found {heads}"
    head = heads[0]
    ancestors = {script.revision for script in scripts.iterate_revisions(head, "base")}
    missing = [revision for revision in TENDER_REVISIONS if revision not in ancestors]
    assert not missing, f"Tender revisions are not ancestors of {head}: {missing}"
    return head


def test_single_head_contains_every_tender_migration() -> None:
    scripts = _script_directory()
    assert _verify_migration_graph(scripts) == scripts.get_current_head()


def test_uuid_expand_retains_global_path_uniqueness_until_cutover() -> None:
    expand_source = (
        BACKEND_DIR
        / "alembic"
        / "versions"
        / "021_source_document_project_uuid_expand.py"
    ).read_text(encoding="utf-8")
    expand_upgrade = expand_source.split("def upgrade() -> None:", 1)[1].split(
        "def downgrade() -> None:", 1
    )[0]
    cutover_source = (
        BACKEND_DIR
        / "alembic"
        / "versions"
        / "021b_source_document_path_contract.py"
    ).read_text(encoding="utf-8")

    assert "DROP CONSTRAINT" not in expand_upgrade
    assert "DROP CONSTRAINT IF EXISTS source_documents_relative_path_key" in cutover_source


def test_migration_graph_rejects_synthetic_branch() -> None:
    scripts = SimpleNamespace(get_heads=lambda: ["main_head", "branch_head"])
    with pytest.raises(AssertionError, match="one head"):
        _verify_migration_graph(scripts)  # type: ignore[arg-type]


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
    if os.environ.get(DESTRUCTIVE_OPT_IN) != "1":
        pytest.skip(
            "DESTRUCTIVE: drops and recreates every tender table (data and seeds "
            f"included). Set TEST_DATABASE_URL and {DESTRUCTIVE_OPT_IN}=1 "
            "against a disposable database to run it."
        )

    import sqlalchemy as sa
    from alembic import command

    from app.config import settings

    test_database_url = require_destructive_test_database_url(
        application_url=settings.database_url,
        test_url=os.environ.get("TEST_DATABASE_URL"),
        opted_in=True,
    )

    def sync_database_url() -> str:
        url = test_database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        if "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"
        return url

    config = _alembic_config()
    original_database_url = settings.database_url
    settings.database_url = test_database_url

    try:
        command.upgrade(config, "head")
        command.downgrade(config, PRE_TENDER_REV)

        engine = sa.create_engine(sync_database_url())
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

        project_columns = {
            column["name"]: column for column in inspector.get_columns("projects")
        }
        profile_revision = project_columns["profile_revision"]
        assert profile_revision["nullable"] is False
        assert str(profile_revision["default"]) in {"1", "'1'::integer"}
        event_sequence = project_columns["event_sequence"]
        assert event_sequence["nullable"] is False
        assert str(event_sequence["default"]) in {"0", "'0'::integer"}
        assert "project_events" in tables
        event_unique_names = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("project_events")
        }
        assert "uq_project_events_project_sequence" in event_unique_names
        assert "uq_project_events_project_deduplication_key" in event_unique_names

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
        if "engine" in locals():
            engine.dispose()
        settings.database_url = original_database_url


def _database_identity(url: str) -> str:
    parts = urlsplit(url.replace("postgresql+psycopg://", "postgresql://", 1))
    query = urlencode(
        sorted(
            (key.lower(), value)
            for key, value in parse_qsl(parts.query)
            if key.lower() not in {"sslmode", "pgbouncer"}
        )
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, ""))


def require_destructive_test_database_url(
    *, application_url: str, test_url: str | None, opted_in: bool
) -> str:
    if not opted_in:
        raise RuntimeError(f"{DESTRUCTIVE_OPT_IN}=1 is required")
    if not test_url:
        raise RuntimeError("TEST_DATABASE_URL is required")
    if _database_identity(test_url) == _database_identity(application_url):
        raise RuntimeError("TEST_DATABASE_URL must not equal DATABASE_URL")
    return test_url


def test_destructive_database_guard_requires_dedicated_url() -> None:
    application_url = "postgresql://user:pass@db.example/clerk?sslmode=require"
    with pytest.raises(RuntimeError, match="TEST_DATABASE_URL is required"):
        require_destructive_test_database_url(
            application_url=application_url, test_url=None, opted_in=True
        )
    with pytest.raises(RuntimeError, match="must not equal"):
        require_destructive_test_database_url(
            application_url=application_url,
            test_url="postgresql+psycopg://user:pass@db.example/clerk",
            opted_in=True,
        )
    assert require_destructive_test_database_url(
        application_url=application_url,
        test_url="postgresql://user:pass@db.example/clerk_test",
        opted_in=True,
    ).endswith("/clerk_test")
