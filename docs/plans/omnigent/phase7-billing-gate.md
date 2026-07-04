# Phase 7 Billing Gate

Date: 2026-07-04

Status: green.

## Implemented

- Stripe SDK dependency added: `stripe==15.3.0`.
- Added `BILLING_PROVIDER`, Stripe secret/webhook/price settings, return paths,
  and monthly agent quota settings.
- Added Stripe customer/subscription models and migration
  `016_stripe_billing`.
- Added Stripe Checkout and Customer Portal wrapper.
- Added `POST /billing/webhook/stripe` with SDK-backed signature verification.
- Added webhook sync for `checkout.session.completed`,
  `customer.subscription.updated`, and `customer.subscription.deleted`.
- Updated the entitlement seam so `require_active_entitlement(session, user)`
  still has the same signature and can read `none`, `polar`, or `stripe`.
- Added monthly agent-turn quota checks only to `/chat/agent/stream`.
- Added quota usage and warning UI to the Billing page.

## Verification

- `uv run alembic upgrade head`: passed.
- `uv run pytest tests/billing tests/agent tests/mcp_bridge tests/test_project_draft_versioning.py tests/tender/test_migrations.py -q`:
  92 passed, 1 skipped.
- `uv run ruff check app/billing app/api/billing.py app/api/chat.py app/config.py app/database/stripe_billing.py app/database/stripe_customer.py app/database/stripe_subscription.py app/database/models.py tests/billing tests/agent/test_agent_chat_api.py tests/tender/test_migrations.py`:
  passed.
- `npm test`: 10 files passed, 23 tests passed.
- `npm run build`: passed. Vite reported the existing large-chunk warning.
- `npm run lint`: passed with one existing warning in
  `frontend/src/components/project/tender/TenderMatrix.tsx` about TanStack
  Virtual and React Compiler memoization.

## External Stripe Gate

- Stripe test-mode Checkout created a subscription and redirected to the app.
- `checkout.session.completed` was forwarded by the Stripe CLI to
  `POST /billing/webhook/stripe` and returned 200.
- Entitlement flipped to `active`, `read_only=false`, `plan_id=starter`.
- Stripe Customer Portal opened for the test customer.
- Portal cancellation sent `customer.subscription.updated` webhooks and the
  backend returned 200.
- The canceled subscription then blocked `require_active_entitlement` with 402.
- Simulated quota exhaustion remains scoped to `/chat/agent/stream`; dashboards
  and document browsing remain available.

## Gate Fixes From The Live Run

- Stripe SDK webhook events are SDK objects, not dictionaries, so the verifier
  now converts through `_to_dict_recursive()` when needed.
- Stripe can keep canceled portal subscriptions at `status=active` while
  setting `canceled_at`, so active-entitlement lookup now excludes canceled
  rows.

Phase 8 may begin.
