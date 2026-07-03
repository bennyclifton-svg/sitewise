import uuid

from sqlalchemy import select
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
) -> list[ChatMessage]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(result.scalars().all())


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
