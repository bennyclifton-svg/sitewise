import uuid
from unittest.mock import AsyncMock, MagicMock

from app.database.chats import (
    list_messages,
    replace_thread_title_if_matches,
    title_from_message,
)
from tests.conftest import run_async


def test_title_from_message_short_text() -> None:
    assert title_from_message("Hello world") == "Hello world"


def test_title_from_message_collapses_whitespace() -> None:
    assert title_from_message("  Hello   world  ") == "Hello world"


def test_title_from_message_truncates_long_text() -> None:
    text = "a" * 80
    title = title_from_message(text)
    assert len(title) == 60
    assert title.endswith("…")


def test_list_messages_bounds_in_sql_then_restores_chronological_order() -> None:
    newest = MagicMock(id=uuid.uuid4())
    older = MagicMock(id=uuid.uuid4())
    result = MagicMock()
    result.scalars.return_value.all.return_value = [newest, older]
    session = AsyncMock()
    session.execute.return_value = result

    messages = run_async(list_messages(session, uuid.uuid4(), limit=2))

    assert messages == [older, newest]
    statement = session.execute.await_args.args[0]
    assert statement._limit_clause.value == 2


def test_replace_thread_title_is_conditional_on_the_automatic_fallback() -> None:
    result = MagicMock(rowcount=0)
    session = AsyncMock()
    session.execute.return_value = result
    thread_id = uuid.uuid4()

    replaced = run_async(
        replace_thread_title_if_matches(
            session,
            thread_id,
            expected_title="Compare the tender quotes",
            title="Tender Quote Comparison",
        )
    )

    assert replaced is False
    statement = session.execute.await_args.args[0]
    params = statement.compile().params
    assert str(thread_id) in {str(value) for value in params.values()}
    assert "Compare the tender quotes" in params.values()
    assert "Tender Quote Comparison" in params.values()
