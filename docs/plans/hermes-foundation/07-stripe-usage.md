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

## Gate Result - 2026-07-04

Status: green.

Implemented and verified:

- `BILLING_PROVIDER` now selects `none`, `polar`, or `stripe`.
- Polar remains importable behind the legacy provider path.
- Stripe Checkout, Customer Portal, webhook signature verification, webhook
  sync, Stripe customer/subscription tables, and entitlement branching are
  implemented.
- Monthly agent-turn quota checks are wired only into `/chat/agent/stream`.
- Billing UI surfaces quota usage and the 80 percent warning.
- `uv run alembic upgrade head` passed.
- `uv run pytest tests/billing tests/agent tests/mcp_bridge tests/test_project_draft_versioning.py tests/tender/test_migrations.py -q`
  passed: 92 passed, 1 skipped.
- Backend ruff passed for the Phase 7 billing surface.
- `npm test` passed: 10 files, 23 tests.
- `npm run build` passed.
- `npm run lint` passed with one pre-existing TanStack Virtual warning in
  `TenderMatrix.tsx`.

External Stripe test-mode gate:

- Stripe test-mode Checkout created a subscription and redirected to the app.
- `checkout.session.completed` was forwarded through the Stripe CLI to the
  local backend and returned 200.
- The webhook upserted the Stripe customer/subscription and flipped entitlement
  to `active`, `read_only=false`, `plan_id=starter`.
- Stripe Customer Portal cancellation sent `customer.subscription.updated`
  webhooks and the local backend returned 200.
- The canceled subscription now blocks `require_active_entitlement` with 402.
- The live gate exposed and fixed two issues: Stripe SDK event objects require
  `_to_dict_recursive()` conversion, and canceled Stripe subscriptions can
  retain `status=active` while setting `canceled_at`.

Phase 8 may begin.
