# Phase 7 Billing Decision

Date: 2026-07-04

Status: decided.

## Decision

Billing is selected through `BILLING_PROVIDER`:

- `none`: internal mode, entitlement gate allows actions.
- `polar`: legacy Polar path retained and importable until Phase 8.5.
- `stripe`: Stripe Checkout, Customer Portal, webhooks, and Stripe-backed
  entitlement state.

Stripe uses new tables rather than a generalized subscription table:

- `stripe_customers`
- `stripe_subscriptions`

This mirrors the existing Polar shape and keeps the Phase 8.5 Polar removal
small and reversible.

The Stripe path uses the official `stripe` Python SDK, pinned by `uv` as
`stripe==15.3.0`. The SDK is justified because Checkout session creation,
Customer Portal session creation, and webhook signature verification are
security- and billing-critical integrations where hand-rolled HTTP/signature
logic would be higher risk than a maintained SDK.

## Configuration

New settings:

- `BILLING_PROVIDER=none|polar|stripe`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `STRIPE_CHECKOUT_SUCCESS_PATH`
- `STRIPE_PORTAL_RETURN_PATH`
- `AGENT_MONTHLY_TURN_QUOTA`

The Phase 7 plan names a single `STRIPE_PRICE_ID`, so Stripe is wired to the
existing Starter plan. The legacy Polar two-plan shape is left intact behind
`BILLING_PROVIDER=polar`.

## Usage Quota

The monthly agent quota is enforced only on `/chat/agent/stream`. Dashboard,
document repository, project browsing, and existing legacy routes remain usable
when the quota is exhausted.

The counter uses persisted Hermes assistant messages for the current calendar
month. At 80 percent usage the agent stream emits a soft quota status event; at
100 percent it returns HTTP 402 before spawning Hermes.

