"""F10 release-gate guards: removed superseded mutation and helper paths stay gone."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import get_args

import pytest

from app.cost_plan.schemas import CostPlanOperation
from app.projects.artefact_blocks import ArtefactBlockOperation, BlockOperationType
from app.schemas import projects as project_schemas

BACKEND_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = BACKEND_ROOT / "app"

# External mutation vocabulary (domain review/protect ops are additive, not synonyms).
EXTERNAL_OPS = {"ADD", "UPDATE", "DELETE", "MOVE", "DUPLICATE"}
DOMAIN_BLOCK_OPS = {"PROTECT", "UNPROTECT", "KEEP", "CONFIRM_DELETE"}


def _python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if "migrations" not in path.parts
        and "__pycache__" not in path.parts
        and path.name != "conftest.py"
    )


def test_patch_draft_request_schema_removed() -> None:
    assert not hasattr(project_schemas, "PatchDraftRequest")


def test_retrieval_profiles_module_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.retrieval.profiles")


def test_no_production_import_of_removed_paths() -> None:
    offenders: list[str] = []
    for path in _python_files(APP_ROOT):
        source = path.read_text(encoding="utf-8")
        if "PatchDraftRequest" in source:
            offenders.append(f"{path.relative_to(BACKEND_ROOT)}: PatchDraftRequest")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "app.retrieval.profiles" or alias.name.startswith(
                        "app.retrieval.profiles."
                    ):
                        offenders.append(
                            f"{path.relative_to(BACKEND_ROOT)}: import {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "app.retrieval.profiles" or node.module.startswith(
                    "app.retrieval.profiles."
                ):
                    offenders.append(
                        f"{path.relative_to(BACKEND_ROOT)}: from {node.module}"
                    )
                if node.module == "app.schemas.projects":
                    for alias in node.names:
                        if alias.name == "PatchDraftRequest":
                            offenders.append(
                                f"{path.relative_to(BACKEND_ROOT)}: "
                                "from app.schemas.projects import PatchDraftRequest"
                            )
    assert offenders == []


def test_external_mutation_vocabulary_converged() -> None:
    block_ops = set(get_args(BlockOperationType))
    assert EXTERNAL_OPS.issubset(block_ops)
    assert block_ops - EXTERNAL_OPS == DOMAIN_BLOCK_OPS

    sample = ArtefactBlockOperation.model_validate(
        {
            "operation": "UPDATE",
            "target": {"type": "paragraph", "id": "blk_" + ("a" * 32)},
            "content": "Hello",
        }
    )
    assert sample.operation == "UPDATE"

    cost_ops = set(get_args(CostPlanOperation.model_fields["operation"].annotation))
    assert cost_ops == EXTERNAL_OPS
