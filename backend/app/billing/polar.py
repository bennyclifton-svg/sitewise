from __future__ import annotations

from json import JSONDecodeError
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException, Request, status

from app.auth.dependencies import CurrentUser
from app.billing.plans import BillingPlan
from app.config import settings
from app.logging import get_logger


log = get_logger(__name__)


class PolarApiError(RuntimeError):
    pass


def polar_base_url() -> str:
    if settings.polar_environment == "production":
        return "https://api.polar.sh/v1"
    return "https://sandbox-api.polar.sh/v1"


def absolute_app_url(path: str) -> str:
    return urljoin(f"{settings.public_app_url.rstrip('/')}/", path.lstrip("/"))


def customer_ip_address(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else None


async def polar_post(path: str, payload: dict) -> dict:
    if not settings.polar_access_token:
        raise PolarApiError("Polar access token is not configured.")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        try:
            response = await client.post(
                f"{polar_base_url()}/{path.strip('/')}/",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.polar_access_token}",
                    "Accept": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            raise PolarApiError(
                f"Polar API request failed: {type(exc).__name__}"
            ) from exc

    if response.status_code >= 300:
        raise PolarApiError(
            f"Polar API returned {response.status_code}: {response.text[:500]}"
        )

    try:
        data = response.json()
    except JSONDecodeError as exc:
        raise PolarApiError("Polar API returned a non-JSON response.") from exc
    if not isinstance(data, dict):
        raise PolarApiError("Polar API returned an unexpected response.")
    return data


async def create_checkout_url(
    *,
    plan: BillingPlan,
    user: CurrentUser,
    request: Request,
) -> str:
    if not settings.polar_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polar billing is not enabled.",
        )
    if not plan.product_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polar product is not configured for this plan.",
        )

    payload = {
        "products": [plan.product_id],
        "external_customer_id": str(user.id),
        "customer_email": user.email,
        "success_url": absolute_app_url(settings.polar_checkout_success_path),
        "customer_metadata": {
            "clerk_user_id": str(user.id),
            "plan_id": plan.id,
        },
    }
    if ip_address := customer_ip_address(request):
        payload["customer_ip_address"] = ip_address

    try:
        data = await polar_post("checkouts", payload)
    except PolarApiError as exc:
        log.warning(
            "polar_checkout_failed",
            environment=settings.polar_environment,
            plan_id=plan.id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Polar checkout could not be created.",
        ) from exc

    checkout_url = data.get("url")
    if not isinstance(checkout_url, str) or not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Polar checkout did not return a URL.",
        )
    return checkout_url


async def create_customer_portal_url(*, user: CurrentUser) -> str:
    if not settings.polar_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polar billing is not enabled.",
        )

    payload = {
        "external_customer_id": str(user.id),
        "return_url": absolute_app_url(settings.polar_customer_portal_return_path),
    }
    try:
        data = await polar_post("customer-sessions", payload)
    except PolarApiError as exc:
        log.warning(
            "polar_customer_portal_failed",
            environment=settings.polar_environment,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Polar customer portal could not be opened.",
        ) from exc

    portal_url = data.get("customer_portal_url")
    if not isinstance(portal_url, str) or not portal_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Polar customer portal did not return a URL.",
        )
    return portal_url
