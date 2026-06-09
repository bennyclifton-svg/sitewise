from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import get_entitlement_state
from app.billing.plans import get_plan_by_id, get_public_plans
from app.billing.polar import create_checkout_url, create_customer_portal_url
from app.billing.webhooks import parse_polar_payload, sync_polar_webhook, verify_polar_webhook
from app.config import settings
from app.database.billing import get_polar_customer_by_user_id
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
    polar_enabled: bool
    environment: str
    plans: list[BillingPlanResponse]


class BillingStatusResponse(BaseModel):
    polar_enabled: bool
    environment: str
    current_plan_id: str
    subscription_status: str
    read_only: bool
    has_polar_customer: bool


class CheckoutRequest(BaseModel):
    plan_id: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


@router.get("/plans")
async def get_billing_plans() -> BillingPlansResponse:
    return BillingPlansResponse(
        polar_enabled=settings.polar_enabled,
        environment=settings.polar_environment,
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
    return BillingStatusResponse(
        polar_enabled=entitlement.polar_enabled,
        environment=settings.polar_environment,
        current_plan_id=entitlement.plan_id,
        subscription_status=entitlement.subscription_status,
        read_only=entitlement.read_only,
        has_polar_customer=entitlement.has_polar_customer,
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
    checkout_url = await create_checkout_url(plan=plan, user=user, request=request)
    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal")
async def post_billing_portal(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalResponse:
    await ensure_user_exists(session, user)
    customer = await get_polar_customer_by_user_id(session, user.id)
    if settings.polar_enabled and customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Polar customer exists for this account yet.",
        )
    portal_url = await create_customer_portal_url(user=user)
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
