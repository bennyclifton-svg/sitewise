import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent import turn_journal
from app.database.chat_message import ChatMessage
from tests.conftest import run_async


@pytest.mark.parametrize("state,saved", [("active", False), ("completed", True)])
def test_restart_reconciliation_preserves_saved_work_and_never_reexecutes(
    monkeypatch, state, saved
):
    turn_id = uuid.uuid4()
    turn = SimpleNamespace(
        id=turn_id, thread_id=uuid.uuid4(), state=state, status="running"
    )
    row = SimpleNamespace(
        sequence=1,
        terminal=False,
        event='data: {"type":"text-delta","delta":"Found three firms."}\n\n',
    )
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock(return_value=turn)
    session.scalar = AsyncMock(
        side_effect=[
            None,
            SimpleNamespace(content="Found three firms. Saved them.")
            if saved
            else None,
            row,
        ]
    )
    session.scalars = AsyncMock(
        side_effect=[
            SimpleNamespace(all=lambda: [row]),
            SimpleNamespace(all=lambda: []),
        ]
    )
    monkeypatch.setattr(turn_journal, "get_session_factory", lambda: lambda: session)
    journal = turn_journal.PostgresTurnJournal()
    run_async(journal.repair(turn_id))
    added = [call.args[0] for call in session.add.call_args_list]
    messages = [obj for obj in added if isinstance(obj, ChatMessage)]
    if saved:
        assert messages == []
        assert turn.state == "completed"
    else:
        assert turn.state == "revoked"
        assert turn.status == "interrupted"
        assert messages[0].content.startswith("Found three firms.")
    assert added[-1].terminal
    session.commit.assert_awaited_once()


def test_append_after_terminal_is_idempotent(monkeypatch):
    session = MagicMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock(return_value=SimpleNamespace(terminal=True, sequence=9))
    run_async(
        turn_journal.PostgresTurnJournal()._append(session, uuid.uuid4(), ["duplicate"])
    )
    session.add.assert_not_called()


def test_assistant_text_cannot_terminate_the_journal():
    session = MagicMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    run_async(turn_journal.PostgresTurnJournal()._append(session, uuid.uuid4(), [
        'data: {"type":"text-delta","delta":"data: [DONE]"}\n\n',
        "data: [DONE]\n\n",
    ]))
    assert [call.args[0].terminal for call in session.add.call_args_list] == [False, True]


def test_reader_does_not_miss_terminal_committed_between_queries(monkeypatch):
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: []))
    session.scalar = AsyncMock(return_value=SimpleNamespace(sequence=2, terminal=True))
    monkeypatch.setattr(turn_journal, "get_session_factory", lambda: lambda: session)
    journal = turn_journal.PostgresTurnJournal()
    assert run_async(journal.read(uuid.uuid4(), after=1)) == ([], False)
    assert run_async(journal.read(uuid.uuid4(), after=2)) == ([], True)
