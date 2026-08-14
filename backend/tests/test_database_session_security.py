from __future__ import annotations

from typing import Any

from sqlalchemy.exc import StatementError

from app.database import session as database_session
from ingest import db as ingest_database


def test_engine_hides_bound_parameters(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    engine = object()

    def fake_create_async_engine(url: str, **kwargs: Any) -> object:
        captured["url"] = url
        captured.update(kwargs)
        return engine

    database_session.get_engine.cache_clear()
    monkeypatch.setattr(
        database_session, "create_async_engine", fake_create_async_engine
    )

    try:
        assert database_session.get_engine() is engine
    finally:
        database_session.get_engine.cache_clear()

    assert captured["hide_parameters"] is True


def test_statement_error_with_hidden_parameters_omits_bound_secret() -> None:
    secret = "ch03-bound-parameter-xxxxxxxxxxxxxxxx"
    error = StatementError(
        "statement failed",
        "SELECT :payload",
        {"payload": secret},
        RuntimeError("driver failed"),
        hide_parameters=True,
    )

    assert secret not in str(error)
    assert "SQL parameters hidden" in str(error)


def test_sync_ingest_engine_hides_bound_parameters(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    engine = object()

    def fake_create_engine(url: str, **kwargs: Any) -> object:
        captured["url"] = url
        captured.update(kwargs)
        return engine

    ingest_database.get_sync_engine.cache_clear()
    monkeypatch.setattr(ingest_database, "create_engine", fake_create_engine)

    try:
        assert ingest_database.get_sync_engine() is engine
    finally:
        ingest_database.get_sync_engine.cache_clear()

    assert captured["hide_parameters"] is True
