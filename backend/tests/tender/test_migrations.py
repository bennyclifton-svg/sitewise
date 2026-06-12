"""Migration coverage for the tender chain (007–010).

The chain/structure tests run anywhere. The roundtrip test is marked
``integration``: it applies ``upgrade head``, walks back down to
006_cockpit_refresh_indexes (dropping the tender tables), and re-upgrades —
run it only against a database where the tender tables carry no data you
want to keep.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[2]
PRE_TENDER_REV = "006_cockpit_refresh_indexes"
TENDER_REVISIONS = [
    "007_tender_core",
    "008_tender_knowledge",
    "009_tender_mapping_status",
    "010_tender_jobs_eval",
]


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def _script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(_alembic_config())

def test_tender_migrations_chain_in_order() -> None:
    scripts = _script_directory()
    expected_parent = PRE_TENDER_REV
    for revision in TENDER_REVISIONS:
        script = scripts.get_revision(revision)
        assert script.down_revision == expected_parent
        expected_parent = revision


def test_head_is_last_tender_migration() -> None:
    assert _script_directory().get_current_head() == TENDER_REVISIONS[-1]


def test_every_tender_migration_has_real_downgrade() -> None:
    for revision in TENDER_REVISIONS:
        module_path = BACKEND_DIR / "alembic" / "versions" / f"{revision}.py"
        source = module_path.read_text(encoding="utf-8")
        assert "def downgrade() -> None:" in source
        downgrade_body = source.split("def downgrade() -> None:", 1)[1]
        assert "drop_table" in downgrade_body, f"{revision} downgrade drops nothing"


@pytest.mark.integration
def test_tender_migrations_roundtrip_against_database() -> None:
    """upgrade head → downgrade to pre-tender → upgrade head, then spot-check schema."""
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
        for table in ("tender_comparisons", "tender_pages", "tender_jobs", "eval_results"):
            assert table in tables

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
        assert embedding_type == "vector(1536)"
    finally:
        engine.dispose()
