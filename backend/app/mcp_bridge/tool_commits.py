"""Commit receipts recorded atomically with MCP mutations, even if replies fail."""

from __future__ import annotations

import uuid

from sqlalchemy import cast, event, inspect, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.agent.observability import current_tool_trace
from app.database.agent_event import AgentToolCall


@event.listens_for(Session, "before_flush")
def capture_mutations(session, _flush_context, _instances):
    if current_tool_trace.get() is None:
        return
    pending = session.info.setdefault("agent_mutated_objects", {})
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        if not isinstance(obj, AgentToolCall):
            pending[id(obj)] = obj


@event.listens_for(Session, "after_flush_postexec")
def capture_flushed_revisions(session, _flush_context):
    # IDs/default versions for new rows are only available after flush.
    pending = session.info.pop("agent_mutated_objects", {})
    if not pending:
        return
    receipts = session.info.setdefault("agent_commit_receipts", {})
    for obj in pending.values():
        mapper = inspect(type(obj))
        identity = getattr(obj, "id", None)
        if not isinstance(identity, uuid.UUID):
            continue
        revision = next(
            (
                getattr(obj, name)
                for name in ("revision", "version")
                if name in mapper.columns and isinstance(getattr(obj, name), int)
            ),
            None,
        )
        table = mapper.local_table.name
        receipts[(table, str(identity))] = {
            "table": table,
            "id": str(identity),
            "revision": revision,
        }


@event.listens_for(Session, "do_orm_execute")
def capture_bulk_mutations(state):
    if current_tool_trace.get() is None or not (
        state.is_update or state.is_delete or state.is_insert
    ):
        return
    table = getattr(getattr(state.statement, "table", None), "name", None)
    if table is None or table == "agent_tool_calls":
        return
    state.session.info.setdefault("agent_commit_receipts", {})[(table, "bulk")] = {
        "table": table,
        "id": None,
        "revision": None,
        "operation": "bulk_mutation",
    }


@event.listens_for(Session, "before_commit")
def persist_commit_receipts(session):
    trace = current_tool_trace.get()
    if trace is None:
        return
    session.flush()
    receipts = list(session.info.pop("agent_commit_receipts", {}).values())
    if receipts:
        session.execute(
            update(AgentToolCall)
            .where(AgentToolCall.id == trace.id)
            .values(
                committed_revisions=AgentToolCall.committed_revisions.op("||")(
                    cast(receipts, JSONB)
                ),
            )
        )


@event.listens_for(Session, "after_rollback")
def discard_rolled_back_receipts(session):
    session.info.pop("agent_commit_receipts", None)
    session.info.pop("agent_mutated_objects", None)
