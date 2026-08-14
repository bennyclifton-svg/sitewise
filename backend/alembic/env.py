import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database.models import Base
from app.database.disposable_target import (
    migration_database_url,
    require_test_environment_marker,
)

import tender.models  # noqa: E402,F401 — register tender_* tables on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
_DATABASE_INTEGRATION = os.environ.get("DATABASE_INTEGRATION_TESTS") == "1"


def get_database_url() -> str:
    return migration_database_url(
        application_url=settings.database_url,
        test_url=os.environ.get("TEST_DATABASE_URL"),
        database_integration=_DATABASE_INTEGRATION,
    )


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    del object_, reflected, compare_to
    return not (type_ == "table" and name == "clerk_test_environment")


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if _DATABASE_INTEGRATION:
            require_test_environment_marker(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
