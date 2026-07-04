from dataclasses import dataclass

from app.config import settings

STARTER_PLAN_ID = "starter"
PROFESSIONAL_PLAN_ID = "professional"


@dataclass(frozen=True, slots=True)
class BillingPlan:
    id: str
    name: str
    description: str
    price_monthly: int
    product_id: str | None


def get_public_plans() -> list[BillingPlan]:
    stripe_enabled = settings.billing_provider == "stripe"
    return [
        BillingPlan(
            id=STARTER_PLAN_ID,
            name="Starter",
            description="For PMs and small teams proving SiteWise on active work.",
            price_monthly=49,
            product_id=(
                settings.stripe_price_id if stripe_enabled else settings.polar_starter_product_id
            ),
        ),
        BillingPlan(
            id=PROFESSIONAL_PLAN_ID,
            name="Professional",
            description="For practices and owner-side teams running multiple live projects.",
            price_monthly=149,
            product_id=None if stripe_enabled else settings.polar_professional_product_id,
        ),
    ]


def get_plan_by_id(plan_id: str) -> BillingPlan | None:
    return next((plan for plan in get_public_plans() if plan.id == plan_id), None)


def get_plan_id_for_product(product_id: str | None) -> str | None:
    if product_id is None:
        return None
    return next(
        (plan.id for plan in get_public_plans() if plan.product_id == product_id),
        None,
    )
