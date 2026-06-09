import uuid
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic_ai.exceptions import ModelHTTPError

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import require_active_entitlement
from app.chat.messages import extract_last_user_message
from app.chat.orchestrator import run_chat_turn
from app.chat.streaming import iter_chat_turn_with_status, stream_error, stream_grounded_answer
from app.database.chat_thread import ChatThread
from app.database.chats import (
    create_message,
    create_thread,
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
            filters = RetrievalFilters(
                active_project=project.slug,
                include_platform_knowledge=True,
                cross_project=cross_project,
            )

    log.info(
        "chat_stream_start",
        user_id=str(user.id),
        thread_id=str(body.thread_id),
        query=user_text,
        chat_model=resolved_model,
    )
    print(
        f"chat_stream_start query={user_text!r} model={resolved_model}",
        flush=True,
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
            print(
                f"chat_turn_complete citations={len(grounded_answer.citations)} "
                f"turn_ms={turn_elapsed_ms}",
                flush=True,
            )
            async for event in stream_grounded_answer(grounded_answer, chunk_delay_s=0):
                yield event
        except ModelHTTPError as exc:
            if exc.status_code == 429:
                log.warning(
                    "chat_openai_rate_limit",
                    user_id=str(user.id),
                    thread_id=str(body.thread_id),
                    query=user_text,
                    model=settings.openai_chat_model,
                )
                print(
                    f"chat_openai_rate_limit query={user_text!r} model={settings.openai_chat_model}",
                    flush=True,
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
                query=user_text,
                error=str(exc),
            )
            print(
                f"chat_grounding_failed query={user_text!r} error={exc}",
                flush=True,
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
            print(
                f"chat_stream_end citations={len(grounded_answer.citations)} "
                f"total_ms={total_elapsed_ms}",
                flush=True,
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
