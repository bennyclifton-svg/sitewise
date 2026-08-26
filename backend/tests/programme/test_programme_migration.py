from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_dependency_migration() -> ModuleType:
    path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "061_programme_dependencies.py"
    )
    spec = spec_from_file_location("programme_dependencies_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_dependency_backfill_executes_literal_colons_as_driver_sql() -> None:
    migration = _load_dependency_migration()
    statements: list[str] = []

    class Bind:
        def exec_driver_sql(self, statement: str) -> None:
            statements.append(statement)

    class Operations:
        def add_column(self, *_args: object, **_kwargs: object) -> None:
            pass

        def drop_column(self, *_args: object, **_kwargs: object) -> None:
            pass

        def get_bind(self) -> Bind:
            return Bind()

    migration.op = Operations()
    migration.upgrade()

    assert len(statements) == 1
    assert "':finish->'" in statements[0]
    assert "':start'" in statements[0]
