from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.database.disposable_target import (
    migration_database_url,
    require_test_environment_marker,
)


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _expected_head() -> str:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    heads = scripts.get_heads()
    assert len(heads) == 1, f"migration graph must have one head; found {heads}"
    return heads[0]


@pytest.mark.database_integration
def test_fresh_database_has_head_extensions_and_test_marker() -> None:
    url = migration_database_url(
        application_url="postgresql://application-sentinel.invalid/unreachable",
        test_url=os.environ.get("TEST_DATABASE_URL"),
        database_integration=True,
    )
    engine = create_engine(url, hide_parameters=True)
    try:
        with engine.connect() as connection:
            require_test_environment_marker(connection)
            revision = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            extensions = set(
                connection.exec_driver_sql(
                    "SELECT extname FROM pg_extension "
                    "WHERE extname IN ('vector', 'pg_trgm')"
                ).scalars()
            )
            tables = set(
                connection.exec_driver_sql(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                ).scalars()
            )
    finally:
        engine.dispose()

    assert revision == _expected_head()
    assert extensions == {"vector", "pg_trgm"}
    assert {"users", "document_chunks", "tender_jobs", "workflow_runs"} <= tables
