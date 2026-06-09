from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.polar_customer import PolarCustomer
from app.database.polar_subscription import PolarSubscription


async def get_polar_customer_by_user_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> PolarCustomer | None:
    stmt = select(PolarCustomer).where(PolarCustomer.user_id == user_id).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_polar_customer_by_polar_id(
    session: AsyncSession,
    polar_customer_id: str,
) -> PolarCustomer | None:
    stmt = (
        select(PolarCustomer)
        .where(PolarCustomer.polar_customer_id == polar_customer_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_polar_customer(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    polar_customer_id: str,
    email: str | None,
) -> PolarCustomer:
    stmt = insert(PolarCustomer).values(
        id=uuid.uuid4(),
        user_id=user_id,
        polar_customer_id=polar_customer_id,
        email=email,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[PolarCustomer.user_id],
        set_={
            "polar_customer_id": polar_customer_id,
            "user_id": user_id,
            "email": email,
            "updated_at": datetime.utcnow(),
        },
    ).returning(PolarCustomer)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_latest_polar_subscription_for_customer(
    session: AsyncSession,
    customer_id: uuid.UUID,
) -> PolarSubscription | None:
    stmt = (
        select(PolarSubscription)
        .where(PolarSubscription.customer_id == customer_id)
        .order_by(desc(PolarSubscription.created_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_polar_subscription_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> PolarSubscription | None:
    customer = await get_polar_customer_by_user_id(session, user_id)
    if customer is None:
        return None
    stmt = (
        select(PolarSubscription)
        .where(
            PolarSubscription.customer_id == customer.id,
            PolarSubscription.status.in_(["active", "trialing"]),
        )
        .order_by(desc(PolarSubscription.created_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_polar_subscription_by_polar_id(
    session: AsyncSession,
    polar_subscription_id: str,
) -> PolarSubscription | None:
    stmt = (
        select(PolarSubscription)
        .where(PolarSubscription.polar_subscription_id == polar_subscription_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_polar_subscription(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    polar_subscription_id: str,
    product_id: str,
    price_id: str | None,
    status: str,
    current_period_start: datetime | None,
    current_period_end: datetime | None,
    cancel_at_period_end: bool,
    canceled_at: datetime | None,
) -> PolarSubscription:
    existing = await get_polar_subscription_by_polar_id(session, polar_subscription_id)
    stmt = insert(PolarSubscription).values(
        id=existing.id if existing is not None else uuid.uuid4(),
        customer_id=customer_id,
        polar_subscription_id=polar_subscription_id,
        product_id=product_id,
        price_id=price_id,
        status=status,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
        canceled_at=canceled_at,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[PolarSubscription.polar_subscription_id],
        set_={
            "customer_id": customer_id,
            "product_id": product_id,
            "price_id": price_id,
            "status": status,
            "current_period_start": current_period_start,
            "current_period_end": current_period_end,
            "cancel_at_period_end": cancel_at_period_end,
            "canceled_at": canceled_at,
            "updated_at": datetime.utcnow(),
        },
    ).returning(PolarSubscription)
    result = await session.execute(stmt)
    return result.scalar_one()
