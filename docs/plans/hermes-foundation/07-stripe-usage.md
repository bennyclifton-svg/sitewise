# Phase 7: Stripe And Usage

## Objective

Replace Polar with Stripe behind the existing entitlement seam and add monthly
agent-turn quota checks without blocking dashboard/document access.

## Implementation Changes

- Add settings for `billing_provider`, Stripe secret/webhook/price ids, return
  paths, and `agent_monthly_turn_quota`.
- Keep Polar importable and inert until Phase 8.5.
- Add Stripe customer/subscription tables mirroring the current Polar shape.
- Add a thin Stripe client wrapper for Checkout and Customer Portal.
- Add `POST /billing/webhook/stripe` with signature verification.
- Update `get_entitlement_state` so `billing_provider="stripe"` reads Stripe
  tables while preserving the `require_active_entitlement(session, user)`
  signature.
- Add usage aggregation over the telemetry records introduced before Phase 5
  speed gates.
- Apply quota checks only to agent turns. Dashboards, existing documents, and
  project browsing remain usable over quota.
- Surface quota usage and 80 percent warning in the frontend billing page.

## Tests

- Stripe client wrapper calls SDK with settings-derived URLs.
- Webhook bad signature returns 400 and writes nothing.
- Checkout completion upserts customer and subscription.
- Subscription deleted marks entitlement inactive.
- Entitlement gate covers `none`, `polar`, and `stripe`.
- Under quota allows agent turn.
- At 80 percent returns a soft warning.
- Over quota blocks agent turn with 402.
- Dashboard/document endpoints remain available over quota.
- Frontend renders quota warning.

## Gate

- Stripe test-mode Checkout creates an active subscription.
- Portal cancellation updates state through webhook.
- Entitlement gate allows and blocks correctly.
- Quota exhaustion blocks only the agent turn path.

