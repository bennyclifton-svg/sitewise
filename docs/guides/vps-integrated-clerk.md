# VPS Deployment Path For Integrated Clerk

The integrated product deploys one Clerk frontend SPA and one Clerk FastAPI backend service. Practice Node, Hermes, Assemble runtime services, and Better Auth are not production services.

The canonical deployment runbook is [Production Deployment](../deployment.md).

## Assemble Reference

Use Assemble as the deployment reference, not as a runtime dependency. The relevant portable notes are:

- VPS shape: Kamatera Ubuntu VPS, Dokploy-managed Docker services, Traefik TLS, and a public app domain.
- Service posture: build one app image, inject server secrets only at runtime, and keep worker/web commands explicit.
- Secret hygiene: committed docs and examples must use placeholders only; live VPS hosts, passwords, database URLs, dashboard logins, and root SSH commands stay outside the repo.
- Smoke posture: health endpoint first, then signup/login, file storage, AI action, checkout, webhook sync, customer portal, and entitlement gates.

Clerk differs from Assemble: Clerk is FastAPI plus a Vite static frontend, not a single Next.js app with bundled workers. Clerk does not currently have Docker packaging files.

## Target Services

- Frontend: build the Vite React SPA and serve the static `dist/` output.
- Backend: run the Clerk FastAPI app with ASGI serving.
- Database: use Supabase Postgres with Alembic-managed schema.
- Host: use the existing `sitewise.au` domain.
- Routing: serve the SPA and proxy `/api/*` to FastAPI on the same host.
- Auth identity: keep Supabase Auth.
- Billing authorization: add Polar subscription/customer state and gate paid actions from the backend.

## Packaging Plan

1. Add container packaging for the FastAPI backend and static frontend.
2. Add a production compose/Dokploy service definition for backend and frontend.
3. Run Alembic migrations against the production Supabase database using the direct or session connection, not the transaction pooler.
4. Configure Traefik routes in Dokploy: `/` to frontend and `/api/*` or a separate API subdomain to FastAPI.
5. Add Polar backend configuration and webhook route.
6. Add local subscription/entitlement tables by Alembic migration.
7. Add billing UI actions: start checkout, open customer portal, show current plan/status.
8. Gate expensive or write actions in FastAPI using local entitlement state.
9. Run the smoke path before calling the workflow live.

## Secrets

Backend-only:

- `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `POLAR_ACCESS_TOKEN`
- `POLAR_WEBHOOK_SECRET`
- `POLAR_STARTER_PRODUCT_ID`
- `POLAR_PROFESSIONAL_PRODUCT_ID`

Browser-safe:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_BASE_URL`

Shared backend configuration:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `OPENAI_CHAT_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `OPENAI_EMBEDDING_DIMENSIONS`
- `ALLOWED_ORIGINS`
- `DATA_DIR`
- `INGEST_EMBEDDING_BATCH_SIZE`
- `INGEST_SUPPORTED_EXTENSIONS`
- `RETRIEVAL_SEMANTIC_LIMIT`
- `RETRIEVAL_FTS_LIMIT`
- `RETRIEVAL_FINAL_LIMIT`
- `ASSISTANT_CONTEXT_PASSAGE_LIMIT`
- `ASSISTANT_PASSAGE_CONTENT_CHARS`

Do not pass server-only values as Docker build arguments. Build arguments may be used only for public client-bundled values.

## Polar Model

Assemble's working model uses Starter and Professional product IDs, checkout, customer portal, signature-validated webhooks, local subscription rows, and a derived entitlement state.

For Clerk, port the model rather than the Better Auth implementation:

- Use the Clerk/Supabase user id as Polar `external_customer_id`.
- Create checkout sessions from the backend for known plan IDs only.
- Receive Polar webhooks on the backend, verify signatures, and idempotently sync local customer/subscription state.
- Authorize backend actions from local entitlement state so request handling does not depend on live Polar reads.
- Provide a customer portal link from the app's billing page.

If full Better Auth migration is desired, treat it as a separate project because it replaces Clerk's current Supabase Auth identity flow.

## Routing

Serve the SPA and API behind the same public host where possible:

- `/` serves the frontend.
- `/api/*` proxies to the FastAPI backend, or the frontend uses a same-origin API base URL.
- Supabase, OpenAI, and Polar service credentials stay on the backend service only.

If using separate subdomains, configure `ALLOWED_ORIGINS` on the backend for the frontend origin and keep `VITE_API_BASE_URL` pointed at the public backend URL.

## Smoke Path

After deploy:

1. Open the frontend and sign in.
2. Confirm `/health` returns the backend health payload.
3. Confirm the project list loads for the signed-in user.
4. Open a project cockpit.
5. Ask a project-scoped chat question and inspect citations.
6. Confirm cross-project mode is explicit before broad retrieval.
7. Start checkout from billing and return from Polar.
8. Deliver a validated Polar webhook and confirm local subscription state updates.
9. Open the Polar customer portal from billing settings.
10. Run Create PMP on a valid project.
11. Open the saved PMP draft and inspect provenance.

## Remaining Operator Inputs

- Confirm Dokploy can reach this repo and target branch.
- Confirm DNS for `sitewise.au` points at the Dokploy/Traefik VPS.
- Confirm production Supabase values are present in Dokploy.
- Confirm whether the first Polar smoke test uses sandbox or production. Default to sandbox until real payments are intentional.

The deployment path does not require the Practice dashboard backend, Practice Node runtime, or Hermes runtime.
