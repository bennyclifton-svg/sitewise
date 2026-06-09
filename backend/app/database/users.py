from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.database.user import User


async def ensure_user_exists(session: AsyncSession, user: CurrentUser) -> None:
    stmt = insert(User).values(id=user.id, email=user.email)
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.id],
        set_={"email": user.email},
    )
    await session.execute(stmt)
