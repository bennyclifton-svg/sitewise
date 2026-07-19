import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Mapping
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi import Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic_ai.exceptions import ModelHTTPError

from app.auth.dependencies import CurrentUser, get_current_user
from app.agent.concurrency import AgentTurnAlreadyRunning, agent_turn_registry
from app.agent.agent_runtimes import (
    PI_RUNTIME_ID,
    default_agent_runtime,
    resolve_agent_runtime,
)
from app.agent.hermes_process import HermesTurnError, HermesTurnTimeout, stream_hermes_turn
from app.agent.hermes_models import resolve_hermes_model_override
from app.agent.pi_process import PiTurnError, PiTurnTimeout, stream_pi_turn
from app.agent.sse_relay import relay_agent_turn
from app.agent.status_bus import agent_turn_status_bus
from app.agent.turn_context import HistoryMessage, build_agent_prompt
from app.projects.snapshot import get_project_snapshot
from app.agent.mutation_intent import classify_mutation_intent
from app.agent.workspace_instructions import ensure_workspace_instructions
from app.agent.workspace_paths import project_workspace_root
from app.billing.entitlements import require_active_entitlement
from app.billing.usage import (
    complete_agent_turn,
    reserve_agent_turn,
    revoke_agent_turn,
)
from app.database.agent_turn import AgentTurn
from app.database.project import Project
from app.chat.messages import extract_last_user_message
from app.chat.orchestrator import run_chat_turn
from app.chat.streaming import (
    clerk_status_event,
    iter_chat_turn_with_status,
    stream_error,
    stream_grounded_answer,
)
from app.database.chat_thread import ChatThread
from app.database.chats import (
    create_message,
    create_thread,
    delete_thread,
    get_thread_by_id,
    list_messages,
    list_threads,
    title_from_message,
    update_thread,
)
from app.database.citations import citations_for_message_data, persist_message_citations
from app.database.projects import get_project, user_owns_project
from app.database.session import get_db, get_session_factory
from app.assistant.chat_models import resolve_chat_model
from app.config import settings
from app.database.users import ensure_user_exists
from app.grounding.validator import GroundingError
from app.logging import get_logger
from app.mcp_bridge.tokens import TurnTokenConfigurationError, mint_turn_token
from app.schemas.chat import (
    CreateThreadRequest,
    MessageListResponse,
    StreamChatRequest,
    ThreadListResponse,
    ThreadResponse,
    UpdateThreadRequest,
)
from app.retrieval.schemas import RetrievalFilters

log = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_PROJECT_DOCUMENT_TRACE_TOOLS = {
    "draft_consultant_procurement_artifact",
    "find_document_text",
    "search_documents",
    "get_document",
}
_PLATFORM_KNOWLEDGE_TRACE_TOOLS = {
    "draft_consultant_procurement_artifact",
    "list_platform_knowledge",
    "search_platform_knowledge",
    "read_platform_knowledge",
}


def require_thread_owner(
    thread: ChatThread | None,
    user_id: uuid.UUID,
) -> ChatThread:
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    if thread.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return thread


async def require_project_owner(
    session: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    if not user_owns_project(project, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return project


@router.get("/threads")
async def get_threads(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ThreadListResponse:
    threads = await list_threads(session, user.id)
    return ThreadListResponse(threads=threads)


@router.post("/threads", status_code=status.HTTP_201_CREATED)
async def post_thread(
    body: CreateThreadRequest = Body(default_factory=CreateThreadRequest),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)
    if body.project_id is not None:
        await require_project_owner(session, body.project_id, user.id)
    thread = await create_thread(
        session,
        user.id,
        title=body.title,
        project_id=body.project_id,
    )
    return ThreadResponse.model_validate(thread)


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    thread = await get_thread_by_id(session, thread_id)
    require_thread_owner(thread, user.id)
    return ThreadResponse.model_validate(thread)


@router.patch("/threads/{thread_id}")
async def patch_thread(
    thread_id: uuid.UUID,
    body: UpdateThreadRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    thread = await get_thread_by_id(session, thread_id)
    require_thread_owner(thread, user.id)
    await require_active_entitlement(session, user)
    updated = await update_thread(session, thread, title=body.title)
    await session.commit()
    return ThreadResponse.model_validate(updated)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_thread(
    thread_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    thread = await get_thread_by_id(session, thread_id)
    owned_thread = require_thread_owner(thread, user.id)
    await require_active_entitlement(session, user)
    await delete_thread(session, owned_thread)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    thread = await get_thread_by_id(session, thread_id)
    require_thread_owner(thread, user.id)
    messages = await list_messages(session, thread_id)
    return MessageListResponse(messages=messages)


async def _persist_chat_messages(
    session: AsyncSession,
    *,
    thread_id: uuid.UUID,
    user_text: str,
    grounded_answer,
    filters: RetrievalFilters | None,
) -> None:
    thread = await get_thread_by_id(session, thread_id)
    if thread is not None and not thread.title:
        await update_thread(
            session,
            thread,
            title=title_from_message(user_text),
        )
    await create_message(
        session,
        thread_id=thread_id,
        role="user",
        content=user_text,
    )
    assistant_message = await create_message(
        session,
        thread_id=thread_id,
        role="assistant",
        content=grounded_answer.answer,
        message_data={
            "citations": citations_for_message_data(grounded_answer),
            "evidenceSufficient": grounded_answer.evidence_sufficient,
            "assumptions": grounded_answer.assumptions,
            "escalationTriggers": grounded_answer.escalation_triggers,
            "workflowDeferred": grounded_answer.workflow_deferred,
            "workflowNote": grounded_answer.workflow_note,
            "retrievalScope": filters.model_dump()
            if filters is not None
            else {"cross_project": True},
        },
    )
    await persist_message_citations(
        session,
        message_id=assistant_message.id,
        answer=grounded_answer,
    )


async def _persist_agent_user_message(
    session: AsyncSession,
    *,
    thread: ChatThread,
    user_text: str,
    runtime: str,
) -> None:
    if not thread.title:
        await update_thread(
            session,
            thread,
            title=title_from_message(user_text),
        )
    await create_message(
        session,
        thread_id=thread.id,
        role="user",
        content=user_text,
        message_data={"agent": {"runtime": runtime}},
    )


async def _persist_agent_assistant_message(
    session: AsyncSession,
    *,
    thread_id: uuid.UUID,
    turn_id: uuid.UUID,
    content: str,
    runtime: str,
    source_trace: dict[str, Any] | None = None,
    terminal_events: list[dict[str, Any]] | None = None,
) -> None:
    agent_data: dict[str, Any] = {
        "runtime": runtime,
        "turnId": str(turn_id),
    }
    if source_trace is not None:
        agent_data["sourceTrace"] = source_trace
    if terminal_events:
        agent_data["terminalEvents"] = terminal_events

    await create_message(
        session,
        thread_id=thread_id,
        role="assistant",
        content=content,
        message_data={"agent": agent_data},
    )


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _agent_source_trace(status_events: list[Mapping[str, Any]]) -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    seen_tool_keys: set[str] = set()
    document_tools: list[str] = []
    document_references: list[str] = []
    knowledge_tools: list[str] = []
    knowledge_references: list[str] = []

    for event in status_events:
        if event.get("kind") != "tool" or event.get("state") != "done":
            continue
        tool = event.get("tool")
        if not isinstance(tool, str) or not tool:
            continue

        knowledge_path = event.get("knowledge_path")
        if isinstance(knowledge_path, str) and knowledge_path:
            _append_unique(knowledge_references, knowledge_path)

        has_document_references = False
        source_documents = event.get("source_documents")
        if isinstance(source_documents, list):
            for source_document in source_documents:
                if not isinstance(source_document, Mapping):
                    continue
                path = source_document.get("relative_path")
                filename = source_document.get("filename")
                if isinstance(path, str) and path:
                    _append_unique(document_references, path)
                    has_document_references = True
                elif isinstance(filename, str) and filename:
                    _append_unique(document_references, filename)
                    has_document_references = True

        has_platform_references = False
        platform_knowledge = event.get("platform_knowledge")
        if isinstance(platform_knowledge, list):
            for knowledge in platform_knowledge:
                if not isinstance(knowledge, Mapping):
                    continue
                path = knowledge.get("path")
                if isinstance(path, str) and path:
                    _append_unique(knowledge_references, path)
                    has_platform_references = True

        key = f"{tool}\0{knowledge_path if isinstance(knowledge_path, str) else ''}"
        if key not in seen_tool_keys:
            item: dict[str, Any] = {"name": tool}
            message = event.get("message")
            if isinstance(message, str) and message:
                item["message"] = message
            if isinstance(knowledge_path, str) and knowledge_path:
                item["knowledgePath"] = knowledge_path
            section_ids = event.get("section_ids")
            if isinstance(section_ids, list) and section_ids:
                item["sectionIds"] = [
                    section_id
                    for section_id in section_ids
                    if isinstance(section_id, str)
                ]
            document_count = event.get("document_count")
            if isinstance(document_count, int):
                item["documentCount"] = document_count
            knowledge_count = event.get("knowledge_count")
            if isinstance(knowledge_count, int):
                item["knowledgeCount"] = knowledge_count
            forecast_used = event.get("forecast_used")
            if isinstance(forecast_used, bool):
                item["forecastUsed"] = forecast_used
            tools.append(item)
            seen_tool_keys.add(key)

        if tool in _PROJECT_DOCUMENT_TRACE_TOOLS or has_document_references:
            _append_unique(document_tools, tool)
        if tool in _PLATFORM_KNOWLEDGE_TRACE_TOOLS or has_platform_references:
            _append_unique(knowledge_tools, tool)

    documents: dict[str, Any] = {"used": bool(document_tools), "tools": document_tools}
    if document_references:
        documents["references"] = document_references

    return {
        "context": {"used": True, "label": "Project context"},
        "documents": documents,
        "knowledge": {
            "used": bool(knowledge_tools),
            "tools": knowledge_tools,
            "references": knowledge_references,
        },
        "tools": tools,
        "model": {"used": True, "label": "LLM reasoning"},
    }


_TERMINAL_EVENT_FIELDS = frozenset(
    {
        "kind",
        "title",
        "workflowType",
        "draftId",
        "comparisonId",
        "projectId",
        "version",
        "revision",
        "resourceType",
        "resourceId",
        "action",
        "runId",
        "status",
    }
)


def _sanitized_terminal_events(
    status_events: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for event in status_events:
        if event.get("kind") not in {"artefact", "resource", "run"}:
            continue
        item = {
            key: value
            for key, value in event.items()
            if key in _TERMINAL_EVENT_FIELDS
            and isinstance(value, (str, int, float, bool))
        }
        if "kind" in item:
            sanitized.append(item)
    return sanitized


async def _capture_status_events(
    status: AsyncIterator[Mapping[str, Any] | str],
    captured: list[Mapping[str, Any]],
) -> AsyncIterator[Mapping[str, Any] | str]:
    async for event in status:
        if isinstance(event, Mapping):
            captured.append(dict(event))
        yield event


def _agent_workspace(project_id: uuid.UUID) -> str:
    path = project_workspace_root(project_id)
    path.mkdir(parents=True, exist_ok=True)
    ensure_workspace_instructions(path)
    return str(path)


@router.post("/agent/stream")
async def post_agent_stream(
    body: StreamChatRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    request_started = time.perf_counter()
    request_id = uuid.uuid4()
    if not settings.agent_runtime_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hermes agent runtime is not enabled.",
        )

    user_text = extract_last_user_message(body.messages)
    if not user_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No user message to send",
        )

    thread = await get_thread_by_id(session, body.thread_id)
    require_thread_owner(thread, user.id)
    await require_active_entitlement(session, user)
    if thread.project_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hermes agent chat requires a project thread.",
        )
    project = await require_project_owner(session, thread.project_id, user.id)
    auth_ms = int((time.perf_counter() - request_started) * 1000)

    # History is read before the new user message is persisted so the window
    # holds prior turns only; the current message travels as the prompt body.
    prior_messages = await list_messages(session, thread.id)
    mutation_intent = classify_mutation_intent(user_text)
    snapshot = await get_project_snapshot(
        session,
        project_id=project.id,
        owner_user_id=user.id,
    )
    agent_prompt = build_agent_prompt(
        user_text,
        project_id=str(thread.project_id),
        title=project.title,
        archetype=project.archetype,
        user_role=project.user_role,
        state=project.state,
        phase=project.phase,
        building_class=project.building_class,
        work_type=project.work_type,
        project_metadata=getattr(project, "project_metadata", None),
        history=[
            HistoryMessage(role=message.role, content=message.content)
            for message in prior_messages
        ],
        mutation_intent=mutation_intent,
        snapshot=snapshot,
    )
    prompt_build_ms = int((time.perf_counter() - request_started) * 1000) - auth_ms
    model_override = resolve_hermes_model_override(body.agent_model)
    agent_runtime = resolve_agent_runtime(body.agent_runtime or default_agent_runtime())

    proposed_turn_id = uuid.uuid4()
    last_message = body.messages[-1] if body.messages else {}
    supplied_message_id = last_message.get("id") if isinstance(last_message, dict) else None
    user_message_id = str(supplied_message_id or proposed_turn_id)
    turn, quota_state, reserved = await reserve_agent_turn(
        session,
        turn_id=proposed_turn_id,
        project_id=thread.project_id,
        user_id=user.id,
        thread_id=thread.id,
        user_message_id=user_message_id,
        user_message_hash=mutation_intent.user_message_hash,
        mutation_scopes=list(mutation_intent.scopes),
        mutation_intent=mutation_intent.as_turn_payload(),
        runtime=agent_runtime,
        model=(
            model_override.model
            if model_override
            else settings.pi_model if agent_runtime == PI_RUNTIME_ID else settings.hermes_model
        ),
    )
    turn_id = turn.id
    quota_ms = int((time.perf_counter() - request_started) * 1000) - auth_ms - prompt_build_ms
    try:
        turn_token = mint_turn_token(
            user_id=user.id,
            project_id=thread.project_id,
            turn_id=turn_id,
        )
    except TurnTokenConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hermes agent turn tokens are not configured.",
        ) from exc

    if reserved:
        await _persist_agent_user_message(
            session,
            thread=thread,
            user_text=user_text,
            runtime=agent_runtime,
        )
    await session.commit()

    workspace = _agent_workspace(thread.project_id)
    factory = get_session_factory()

    log.info(
        "agent_stream_start",
        request_id=str(request_id),
        user_id=str(user.id),
        thread_id=str(body.thread_id),
        project_id=str(thread.project_id),
        turn_id=str(turn_id),
        agent_runtime=agent_runtime,
        timings_ms={"auth": auth_ms, "quota": quota_ms, "prompt_build": prompt_build_ms},
    )

    async def event_stream() -> AsyncIterator[str]:
        stream_start = time.perf_counter()
        answer_parts: list[str] = []
        tool_status_events: list[Mapping[str, Any]] = []
        completed = False
        first_text_ms: int | None = None

        async def agent_chunks() -> AsyncIterator[str]:
            nonlocal completed, first_text_ms
            if agent_runtime == PI_RUNTIME_ID:
                stream = stream_pi_turn(
                    prompt=agent_prompt,
                    mcp_url=settings.agent_mcp_url,
                    turn_token=turn_token,
                    cwd=workspace,
                )
            else:
                stream = stream_hermes_turn(
                    prompt=agent_prompt,
                    mcp_url=settings.agent_mcp_url,
                    turn_token=turn_token,
                    cwd=workspace,
                    provider=model_override.provider if model_override else None,
                    model=model_override.model if model_override else None,
                )
            async for chunk in stream:
                if first_text_ms is None:
                    first_text_ms = int((time.perf_counter() - stream_start) * 1000)
                answer_parts.append(chunk)
                yield chunk
            completed = True

        try:
            async with agent_turn_registry.turn_scope(
                str(turn_id),
                thread_id=str(body.thread_id),
            ):
                if quota_state.warning:
                    yield clerk_status_event(
                        "You are near this month's agent quota.",
                        kind="quota",
                        usedTurns=quota_state.used_turns,
                        quota=quota_state.quota,
                        percent=quota_state.percent,
                    )
                async with agent_turn_status_bus.subscribe(str(turn_id)) as statuses:
                    traced_statuses = _capture_status_events(statuses, tool_status_events)
                    async for event in relay_agent_turn(agent_chunks(), status=traced_statuses):
                        yield event
        except AgentTurnAlreadyRunning:
            log.warning(
                "agent_stream_already_running",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
            )
            async for event in stream_error("An agent turn is already running for this chat."):
                yield event
            return
        except asyncio.CancelledError:
            log.info(
                "agent_stream_cancelled",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                turn_id=str(turn_id),
            )
            async for event in stream_error("Agent turn cancelled."):
                yield event
            return
        except HermesTurnTimeout:
            log.warning(
                "agent_stream_timeout",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                turn_id=str(turn_id),
                agent_runtime=agent_runtime,
            )
            async for event in stream_error("Hermes took too long to respond. Please try again."):
                yield event
            return
        except PiTurnTimeout:
            log.warning(
                "agent_stream_timeout",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                turn_id=str(turn_id),
                agent_runtime=agent_runtime,
            )
            async for event in stream_error("Pi took too long to respond. Please try again."):
                yield event
            return
        except HermesTurnError as exc:
            log.warning(
                "agent_stream_failed",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                turn_id=str(turn_id),
                agent_runtime=agent_runtime,
                error_type=type(exc).__name__,
            )
            async for event in stream_error("Hermes could not complete this turn. Please try again."):
                yield event
            return
        except PiTurnError as exc:
            log.warning(
                "agent_stream_failed",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                turn_id=str(turn_id),
                agent_runtime=agent_runtime,
                error_type=type(exc).__name__,
            )
            async for event in stream_error("Pi could not complete this turn. Please try again."):
                yield event
            return
        finally:
            if not completed:
                async with factory() as revoke_session:
                    await revoke_agent_turn(revoke_session, turn_id)
                    await revoke_session.commit()

        if completed:
            content = "".join(answer_parts)
            async with factory() as persist_session:
                await _persist_agent_assistant_message(
                    persist_session,
                    thread_id=body.thread_id,
                    turn_id=turn_id,
                    content=content,
                    runtime=agent_runtime,
                    source_trace=_agent_source_trace(tool_status_events),
                    terminal_events=_sanitized_terminal_events(tool_status_events),
                )
                await complete_agent_turn(persist_session, turn_id, status_value="completed")
                await persist_session.commit()
            elapsed_ms = int((time.perf_counter() - stream_start) * 1000)
            log.info(
                "agent_stream_persisted",
                request_id=str(request_id),
                project_id=str(thread.project_id),
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                turn_id=str(turn_id),
                timings_ms={
                    "auth": auth_ms,
                    "quota": quota_ms,
                    "prompt_build": prompt_build_ms,
                    "first_text": first_text_ms,
                    "total": elapsed_ms,
                },
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )


@router.post("/agent/{thread_id}/cancel")
async def post_agent_cancel(
    thread_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    thread = await get_thread_by_id(session, thread_id)
    require_thread_owner(thread, user.id)
    active_turn_id = await session.scalar(
        select(AgentTurn.id)
        .where(
            AgentTurn.thread_id == thread_id,
            AgentTurn.user_id == user.id,
            AgentTurn.state == "active",
        )
        .order_by(AgentTurn.created_at.desc())
        .limit(1)
    )
    if active_turn_id is not None:
        await revoke_agent_turn(session, active_turn_id)
        await session.commit()
    cancelled = await agent_turn_registry.cancel(str(thread_id))
    return {"cancelled": cancelled}


@router.post("/stream")
async def post_chat_stream(
    body: StreamChatRequest,
    cross_project: bool = Query(default=False),
    chat_model: str | None = Query(default=None, alias="chat_model"),
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    user_text = extract_last_user_message(body.messages)
    if not user_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No user message to send",
        )

    resolved_model = resolve_chat_model(chat_model or body.chat_model)

    factory = get_session_factory()
    filters: RetrievalFilters | None = None
    async with factory() as session:
        thread = await get_thread_by_id(session, body.thread_id)
        require_thread_owner(thread, user.id)
        await require_active_entitlement(session, user)
        if thread.project_id is not None:
            project = await require_project_owner(session, thread.project_id, user.id)
            authorized_project_ids: tuple[uuid.UUID, ...] = ()
            if cross_project:
                owned_project_ids = await session.scalars(
                    select(Project.id).where(Project.owner_user_id == user.id)
                )
                authorized_project_ids = tuple(owned_project_ids.all())
            filters = RetrievalFilters(
                active_project_id=project.id,
                authorized_project_ids=authorized_project_ids,
                include_platform_knowledge=True,
                cross_project=cross_project,
            )
        else:
            filters = RetrievalFilters(platform_knowledge_only=True)

    log.info(
        "chat_stream_start",
        user_id=str(user.id),
        thread_id=str(body.thread_id),
        query_length=len(user_text),
        chat_model=resolved_model,
    )

    async def event_stream() -> AsyncIterator[str]:
        stream_start = time.perf_counter()
        grounded_answer = None
        try:
            async with factory() as session:
                async for item in iter_chat_turn_with_status(
                    run_turn=lambda on_status: run_chat_turn(
                        session,
                        user_id=user.id,
                        thread_id=body.thread_id,
                        user_text=user_text,
                        filters=filters,
                        on_status=on_status,
                        chat_model=resolved_model,
                    ),
                ):
                    if isinstance(item, str):
                        yield item
                        continue
                    grounded_answer = item
            if grounded_answer is None:
                raise RuntimeError("Chat turn completed without an answer")

            persistence_start = time.perf_counter()
            async with factory() as session:
                async with session.begin():
                    await _persist_chat_messages(
                        session,
                        thread_id=body.thread_id,
                        user_text=user_text,
                        grounded_answer=grounded_answer,
                        filters=filters,
                    )
            persistence_ms = int((time.perf_counter() - persistence_start) * 1000)
            log.info(
                "chat_stream_persisted",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                persistence_ms=persistence_ms,
                citation_count=len(grounded_answer.citations),
            )

            turn_elapsed_ms = int((time.perf_counter() - stream_start) * 1000)
            log.info(
                "chat_stream_first_answer_event",
                elapsed_ms=turn_elapsed_ms,
                citation_count=len(grounded_answer.citations),
            )
            async for event in stream_grounded_answer(grounded_answer, chunk_delay_s=0):
                yield event
        except ModelHTTPError as exc:
            if exc.status_code == 429:
                log.warning(
                    "chat_openai_rate_limit",
                    user_id=str(user.id),
                    thread_id=str(body.thread_id),
                    model=settings.openai_chat_model,
                )
                async for event in stream_error(
                    "OpenAI rate limit reached for the chat model. "
                    "Wait about 10 seconds and try again."
                ):
                    yield event
            else:
                log.exception(
                    "chat_model_http_error",
                    user_id=str(user.id),
                    thread_id=str(body.thread_id),
                    status_code=exc.status_code,
                )
                async for event in stream_error(
                    "The language model returned an error. Please try again shortly."
                ):
                    yield event
        except GroundingError as exc:
            log.warning(
                "chat_grounding_failed",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                error_type=type(exc).__name__,
            )
            async for event in stream_error(
                "The assistant response could not be verified against retrieved sources. "
                "Please try rephrasing your question."
            ):
                yield event
        except Exception:
            log.exception(
                "chat_stream_error",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
            )
            async for event in stream_error(
                "Something went wrong while generating a response. Please try again."
            ):
                yield event
            return
        else:
            total_elapsed_ms = int((time.perf_counter() - stream_start) * 1000)
            log.info(
                "chat_stream_end",
                user_id=str(user.id),
                thread_id=str(body.thread_id),
                total_elapsed_ms=total_elapsed_ms,
                citation_count=len(grounded_answer.citations),
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )
