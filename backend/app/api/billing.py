from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import get_entitlement_state
from app.billing.plans import get_plan_by_id, get_public_plans
from app.billing.polar import create_checkout_url, create_customer_portal_url
from app.billing.stripe_client import create_checkout_session, create_portal_session
from app.billing.stripe_webhooks import sync_stripe_webhook, verify_stripe_webhook
from app.billing.usage import agent_usage_state
from app.billing.webhooks import parse_polar_payload, sync_polar_webhook, verify_polar_webhook
from app.config import settings
from app.database.billing import get_polar_customer_by_user_id
from app.database.stripe_billing import get_stripe_customer_by_user_id
from app.database.session import get_db
from app.database.users import ensure_user_exists

router = APIRouter(prefix="/billing", tags=["billing"])


class BillingPlanResponse(BaseModel):
    id: str
    name: str
    description: str
    price_monthly: int
    configured: bool


class BillingPlansResponse(BaseModel):
    billing_provider: str
    billing_enabled: bool
    polar_enabled: bool
    environment: str
    plans: list[BillingPlanResponse]


class QuotaResponse(BaseModel):
    used_turns: int
    quota: int
    percent: int
    warning: bool


class BillingStatusResponse(BaseModel):
    billing_provider: str
    billing_enabled: bool
    polar_enabled: bool
    environment: str
    current_plan_id: str
    subscription_status: str
    read_only: bool
    has_customer: bool
    has_polar_customer: bool
    quota: QuotaResponse


class CheckoutRequest(BaseModel):
    plan_id: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


@router.get("/plans")
async def get_billing_plans() -> BillingPlansResponse:
    provider = settings.billing_provider
    return BillingPlansResponse(
        billing_provider=provider,
        billing_enabled=provider != "none",
        polar_enabled=provider == "polar" or settings.polar_enabled,
        environment=settings.polar_environment if provider == "polar" else provider,
        plans=[
            BillingPlanResponse(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                price_monthly=plan.price_monthly,
                configured=bool(plan.product_id),
            )
            for plan in get_public_plans()
        ],
    )


@router.get("/subscription")
async def get_billing_subscription(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BillingStatusResponse:
    await ensure_user_exists(session, user)
    entitlement = await get_entitlement_state(session, user.id)
    quota = await agent_usage_state(session, user_id=user.id)
    return BillingStatusResponse(
        billing_provider=entitlement.billing_provider,
        billing_enabled=entitlement.billing_enabled,
        polar_enabled=entitlement.polar_enabled,
        environment=(
            settings.polar_environment
            if entitlement.billing_provider == "polar"
            else entitlement.billing_provider
        ),
        current_plan_id=entitlement.plan_id,
        subscription_status=entitlement.subscription_status,
        read_only=entitlement.read_only,
        has_customer=entitlement.has_customer,
        has_polar_customer=entitlement.has_polar_customer,
        quota=QuotaResponse(
            used_turns=quota.used_turns,
            quota=quota.quota,
            percent=quota.percent,
            warning=quota.warning,
        ),
    )


@router.post("/checkout")
async def post_billing_checkout(
    body: CheckoutRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    await ensure_user_exists(session, user)
    plan = get_plan_by_id(body.plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown billing plan.",
        )
    if settings.billing_provider == "stripe":
        checkout_url = await create_checkout_session(plan=plan, user=user)
    elif settings.billing_provider == "polar" or settings.polar_enabled:
        checkout_url = await create_checkout_url(plan=plan, user=user, request=request)
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing checkout is not enabled.",
        )
    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal")
async def post_billing_portal(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalResponse:
    await ensure_user_exists(session, user)
    if settings.billing_provider == "stripe":
        customer = await get_stripe_customer_by_user_id(session, user.id)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Stripe customer exists for this account yet.",
            )
        portal_url = await create_portal_session(
            stripe_customer_id=customer.stripe_customer_id,
        )
        return PortalResponse(portal_url=portal_url)

    customer = await get_polar_customer_by_user_id(session, user.id)
    if (settings.billing_provider == "polar" or settings.polar_enabled) and customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Polar customer exists for this account yet.",
        )
    if settings.billing_provider == "polar" or settings.polar_enabled:
        portal_url = await create_customer_portal_url(user=user)
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing portal is not enabled.",
        )
    return PortalResponse(portal_url=portal_url)


@router.post("/webhook/polar")
async def post_polar_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    payload = await request.body()
    verify_polar_webhook(request.headers, payload)
    parsed_payload = parse_polar_payload(payload)
    result = await sync_polar_webhook(session, parsed_payload)
    return {"status": "ok", "action": result.action, "event_type": result.event_type}


@router.post("/webhook/stripe")
async def post_stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    payload = await request.body()
    event = verify_stripe_webhook(payload, request.headers.get("stripe-signature"))
    result = await sync_stripe_webhook(session, event)
    return {"status": "ok", "action": result.action, "event_type": result.event_type}
