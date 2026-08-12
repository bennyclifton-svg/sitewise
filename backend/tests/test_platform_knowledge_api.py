"""Unit tests for the platform-knowledge REST read endpoint."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api import projects as projects_api
from app.schemas.projects import PlatformKnowledgeContent
from tests.conftest import run_async


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def test_get_platform_knowledge_document_returns_content(monkeypatch):
    document = SimpleNamespace(
        filename="new-dwelling-guide.md",
        relative_path="seed/new-dwelling-guide.md",
        normalized_content="# New dwelling\n\nGuidance body.",
        document_metadata={"sitewise_knowledge_kind": "seed", "knowledge_scope": "platform"},
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarResult(document))
    monkeypatch.setattr(projects_api, "ensure_user_exists", AsyncMock())

    result = run_async(
        projects_api.get_platform_knowledge_document(
            path="seed/new-dwelling-guide.md",
            user=MagicMock(),
            session=session,
        )
    )

    assert isinstance(result, PlatformKnowledgeContent)
    assert result.filename == "new-dwelling-guide.md"
    assert result.relative_path == "seed/new-dwelling-guide.md"
    assert result.kind == "seed"
    assert result.content.startswith("# New dwelling")


def test_get_platform_knowledge_document_rejects_traversal(monkeypatch):
    session = AsyncMock()
    monkeypatch.setattr(projects_api, "ensure_user_exists", AsyncMock())

    with pytest.raises(HTTPException) as exc:
        run_async(
            projects_api.get_platform_knowledge_document(
                path="../secrets.md",
                user=MagicMock(),
                session=session,
            )
        )

    assert exc.value.status_code == 400
    session.execute.assert_not_called()


def test_get_platform_knowledge_document_not_found(monkeypatch):
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarResult(None))
    monkeypatch.setattr(projects_api, "ensure_user_exists", AsyncMock())

    with pytest.raises(HTTPException) as exc:
        run_async(
            projects_api.get_platform_knowledge_document(
                path="seed/missing.md",
                user=MagicMock(),
                session=session,
            )
        )

    assert exc.value.status_code == 404
