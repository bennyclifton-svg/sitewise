"""Run only against the migration runner's marked disposable Postgres database."""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent import turn_journal
from app.agent.observability import ToolTrace, current_tool_trace
from app.billing.usage import require_active_mutation_turn
from app.database.agent_event import AgentToolCall
from app.database.agent_turn import AgentTurn
from app.database.chat_message import ChatMessage
from app.database.chat_thread import ChatThread
from app.database.disposable_target import (
    migration_database_url,
    require_test_environment_marker,
)
from app.database.procurement_strategy import ProcurementStrategy
from app.database.project import Project
from app.database.user import User
from app.mcp_bridge import tracing
from tests.conftest import run_async


@pytest.mark.database_integration
def test_restart_after_commit_preserves_receipt_and_fences_mutations(monkeypatch):
    url = migration_database_url(
        application_url="postgresql://application-sentinel.invalid/unreachable",
        test_url=os.environ.get("TEST_DATABASE_URL"),
        database_integration=True,
    )

    async def run():
        engine = create_async_engine(url, hide_parameters=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        monkeypatch.setattr(turn_journal, "get_session_factory", lambda: factory)
        monkeypatch.setattr(tracing, "get_session_factory", lambda: factory)
        user_id, project_id, thread_id, turn_id = [uuid.uuid4() for _ in range(4)]
        verified = False
        try:
            async with engine.connect() as connection:
                await connection.run_sync(require_test_environment_marker)
                verified = True
            async with factory() as session:
                session.add(User(id=user_id, email=f"replay-{user_id}@example.com"))
                await session.flush()
                session.add(
                    Project(
                        id=project_id,
                        owner_user_id=user_id,
                        slug=f"replay-{project_id}",
                        title="Replay fixture",
                        workspace_path=f"projects/{project_id}",
                        phase="procurement",
                        project_metadata={},
                    )
                )
                await session.flush()
                session.add(
                    ChatThread(id=thread_id, user_id=user_id, project_id=project_id)
                )
                await session.flush()
                session.add(
                    AgentTurn(
                        id=turn_id,
                        project_id=project_id,
                        user_id=user_id,
                        thread_id=thread_id,
                        user_message_id=str(uuid.uuid4()),
                        runtime="pi",
                        state="active",
                        status="running",
                        mutation_scopes=["procurement_strategy_mutation"],
                        expires_at=datetime.now(UTC) + timedelta(minutes=5),
                    )
                )
                session.add(
                    ProcurementStrategy(
                        id=uuid.uuid4(), project_id=project_id, revision=11
                    )
                )
                await session.commit()

            trace = ToolTrace(
                uuid.uuid4(), turn_id, "apply_procurement_strategy_operations"
            )
            await tracing.ToolTraceStore().start(trace)
            token = current_tool_trace.set(trace)
            try:
                async with factory() as session:
                    await require_active_mutation_turn(
                        session,
                        turn_id=turn_id,
                        project_id=project_id,
                        user_id=user_id,
                        required_scope="procurement_strategy_mutation",
                    )
                    strategy = await session.scalar(
                        select(ProcurementStrategy).where(
                            ProcurementStrategy.project_id == project_id
                        )
                    )
                    strategy.revision = 12
                    await session.commit()
                    strategy.revision = 13
                    await session.flush()
                    await session.rollback()
            finally:
                current_tool_trace.reset(token)

            # Simulate losing the process before the MCP response and final text.
            journal = turn_journal.PostgresTurnJournal()
            await journal.append(
                turn_id, ['data: {"type":"text-delta","delta":"Researching firms"}\n\n']
            )
            await journal.reconcile()
            await journal.reconcile()
            async with factory() as session:
                strategy = await session.scalar(
                    select(ProcurementStrategy).where(
                        ProcurementStrategy.project_id == project_id
                    )
                )
                call = await session.get(AgentToolCall, trace.id)
                assert strategy.revision == 12
                assert call.outcome == "interrupted"
                assert [
                    receipt["revision"] for receipt in call.committed_revisions
                ] == [12]
                saved = (
                    await session.scalars(
                        select(ChatMessage).where(ChatMessage.thread_id == thread_id)
                    )
                ).all()
                assert len(saved) == 1
                assert "Saved changes were kept" in saved[0].content
                with pytest.raises(PermissionError):
                    await require_active_mutation_turn(
                        session, turn_id=turn_id, project_id=project_id, user_id=user_id
                    )
            events, terminal = await journal.read(turn_id, after=1)
            assert terminal
            assert [sequence for sequence, _ in events] == [2, 3]
        finally:
            if verified:
                async with factory() as session:
                    await session.execute(
                        delete(Project).where(Project.id == project_id)
                    )
                    await session.execute(
                        delete(ChatThread).where(ChatThread.id == thread_id)
                    )
                    await session.execute(delete(User).where(User.id == user_id))
                    await session.commit()
            await engine.dispose()

    run_async(run())
