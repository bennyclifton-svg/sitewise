import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.chat_message import ChatMessage
from app.database.chat_thread import ChatThread


async def list_threads(session: AsyncSession, user_id: uuid.UUID) -> list[ChatThread]:
    result = await session.execute(
        select(ChatThread)
        .where(ChatThread.user_id == user_id)
        .order_by(ChatThread.updated_at.desc())
    )
    return list(result.scalars().all())


async def list_threads_page(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: uuid.UUID | None = None,
) -> tuple[list[ChatThread], uuid.UUID | None]:
    stmt = select(ChatThread).where(ChatThread.user_id == user_id)
    if cursor is not None:
        anchor = await session.get(ChatThread, cursor)
        if anchor is not None and anchor.user_id == user_id:
            stmt = stmt.where(
                or_(
                    ChatThread.updated_at < anchor.updated_at,
                    and_(
                        ChatThread.updated_at == anchor.updated_at,
                        ChatThread.id < anchor.id,
                    ),
                )
            )
    rows = list(
        (
            await session.execute(
                stmt.order_by(ChatThread.updated_at.desc(), ChatThread.id.desc()).limit(
                    limit + 1
                )
            )
        ).scalars().all()
    )
    next_cursor = rows[limit - 1].id if len(rows) > limit else None
    return rows[:limit], next_cursor


async def create_thread(
    session: AsyncSession,
    user_id: uuid.UUID,
    title: str | None = None,
    project_id: uuid.UUID | None = None,
) -> ChatThread:
    thread = ChatThread(user_id=user_id, project_id=project_id, title=title)
    session.add(thread)
    await session.flush()
    await session.refresh(thread)
    return thread


async def get_thread_by_id(
    session: AsyncSession,
    thread_id: uuid.UUID,
) -> ChatThread | None:
    return await session.get(ChatThread, thread_id)


async def list_messages(
    session: AsyncSession,
    thread_id: uuid.UUID,
    *,
    limit: int,
) -> list[ChatMessage]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def get_latest_project_thread(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ChatThread | None:
    return await session.scalar(
        select(ChatThread)
        .where(
            ChatThread.project_id == project_id,
            ChatThread.user_id == user_id,
        )
        .order_by(ChatThread.updated_at.desc(), ChatThread.id.desc())
        .limit(1)
    )


def title_from_message(text: str, *, max_length: int = 60) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_length:
        return collapsed
    return f"{collapsed[: max_length - 1].rstrip()}…"


async def update_thread(
    session: AsyncSession,
    thread: ChatThread,
    *,
    title: str | None = None,
) -> ChatThread:
    if title is not None:
        thread.title = title
    await session.flush()
    await session.refresh(thread)
    return thread


async def delete_thread(session: AsyncSession, thread: ChatThread) -> None:
    await session.delete(thread)
    await session.flush()


async def create_message(
    session: AsyncSession,
    *,
    thread_id: uuid.UUID,
    role: str,
    content: str,
    message_data: dict | None = None,
) -> ChatMessage:
    message = ChatMessage(
        thread_id=thread_id,
        role=role,
        content=content,
        message_data=message_data,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    return message
