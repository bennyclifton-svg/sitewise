from __future__ import annotations

import ast
from pathlib import Path


VERSIONS_DIR = Path(__file__).parents[1] / "alembic" / "versions"
ALEMBIC_VERSION_NUM_LIMIT = 32


def _revision_id(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        value_node: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "revision"
            for target in node.targets
        ):
            value_node = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "revision"
        ):
            value_node = node.value
        if value_node is None:
            continue
        value = ast.literal_eval(value_node)
        if isinstance(value, str):
            return value
    raise AssertionError(f"Migration {path.name} does not declare a string revision")


def test_migration_revision_ids_fit_alembic_version_column() -> None:
    oversized = {
        path.name: revision
        for path in sorted(VERSIONS_DIR.glob("*.py"))
        if path.name != "__init__.py"
        if len(revision := _revision_id(path)) > ALEMBIC_VERSION_NUM_LIMIT
    }

    assert oversized == {}
