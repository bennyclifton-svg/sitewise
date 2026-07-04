from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.stripe_customer import StripeCustomer
from app.database.stripe_subscription import StripeSubscription


async def get_stripe_customer_by_user_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> StripeCustomer | None:
    stmt = select(StripeCustomer).where(StripeCustomer.user_id == user_id).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_stripe_customer_by_stripe_id(
    session: AsyncSession,
    stripe_customer_id: str,
) -> StripeCustomer | None:
    stmt = (
        select(StripeCustomer)
        .where(StripeCustomer.stripe_customer_id == stripe_customer_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_stripe_customer(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    stripe_customer_id: str,
    email: str | None,
) -> StripeCustomer:
    stmt = insert(StripeCustomer).values(
        id=uuid.uuid4(),
        user_id=user_id,
        stripe_customer_id=stripe_customer_id,
        email=email,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[StripeCustomer.user_id],
        set_={
            "stripe_customer_id": stripe_customer_id,
            "user_id": user_id,
            "email": email,
            "updated_at": datetime.utcnow(),
        },
    ).returning(StripeCustomer)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_latest_stripe_subscription_for_customer(
    session: AsyncSession,
    customer_id: uuid.UUID,
) -> StripeSubscription | None:
    stmt = (
        select(StripeSubscription)
        .where(StripeSubscription.customer_id == customer_id)
        .order_by(desc(StripeSubscription.created_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_stripe_subscription_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> StripeSubscription | None:
    customer = await get_stripe_customer_by_user_id(session, user_id)
    if customer is None:
        return None
    stmt = (
        select(StripeSubscription)
        .where(
            StripeSubscription.customer_id == customer.id,
            StripeSubscription.status.in_(["active", "trialing"]),
            StripeSubscription.cancel_at_period_end.is_(False),
            StripeSubscription.canceled_at.is_(None),
        )
        .order_by(desc(StripeSubscription.created_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_stripe_subscription_by_stripe_id(
    session: AsyncSession,
    stripe_subscription_id: str,
) -> StripeSubscription | None:
    stmt = (
        select(StripeSubscription)
        .where(StripeSubscription.stripe_subscription_id == stripe_subscription_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_stripe_subscription(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    stripe_subscription_id: str,
    price_id: str,
    status: str,
    current_period_start: datetime | None,
    current_period_end: datetime | None,
    cancel_at_period_end: bool,
    canceled_at: datetime | None,
) -> StripeSubscription:
    existing = await get_stripe_subscription_by_stripe_id(
        session,
        stripe_subscription_id,
    )
    stmt = insert(StripeSubscription).values(
        id=existing.id if existing is not None else uuid.uuid4(),
        customer_id=customer_id,
        stripe_subscription_id=stripe_subscription_id,
        price_id=price_id,
        status=status,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
        canceled_at=canceled_at,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[StripeSubscription.stripe_subscription_id],
        set_={
            "customer_id": customer_id,
            "price_id": price_id,
            "status": status,
            "current_period_start": current_period_start,
            "current_period_end": current_period_end,
            "cancel_at_period_end": cancel_at_period_end,
            "canceled_at": canceled_at,
            "updated_at": datetime.utcnow(),
        },
    ).returning(StripeSubscription)
    result = await session.execute(stmt)
    return result.scalar_one()
