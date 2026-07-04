# SiteWise Production Deployment

This is the active deployment summary for Clerk as the SiteWise app at
`https://sitewise.au`.

## Current State

The deployed shape is a Dokploy compose app with:

- `sitewise-api`: FastAPI backend container
- `sitewise-web`: static React SPA served by nginx
- external Docker network `sitewise-public`
- hosted Supabase for Auth, Postgres, and Storage

Stripe is the Phase 7+ billing provider. Polar remains importable and disabled
as a safety valve until the Phase 8.5 cutover gate passes.

The Phase 8 deploy scaffold bundles Hermes CLI, MCP runtime config, an agent
workspace volume, and a separate Tender Comparison worker. Final Linux
acceptance still has to run against the live `sitewise.au` deployment before
legacy code is deleted.

## Phase 8 Target

Phase 8 deploys the agent-first product to `sitewise.au`:

1. Backend image includes Hermes CLI v0.17.x, JVM/ODL support, FastAPI, MCP, and
   the Tender Comparison worker path.
2. Backend has a persistent `AGENT_WORKSPACE_ROOT` volume for scratch/artefact
   files. Supabase Storage remains canonical for uploaded source documents.
3. nginx keeps `/api/*` and SSE streams unbuffered.
4. Stripe env and webhook secrets replace Polar env after Phase 7 is complete.
5. Production acceptance proves signup, subscription, project creation, tender
   upload, chat-triggered comparison, tool chips, comparison panel, report
   artefact, and artefact editing.
6. Only after that gate passes, legacy chat runtime, old cockpit pages, and
   Polar code are removed.

## Services

| Service | Role |
| --- | --- |
| `sitewise-api` | FastAPI API, TCM router, billing, Hermes/MCP runtime |
| `sitewise-worker` | Tender Comparison worker running `python -m tender.worker` |
| `sitewise-web` | Static React SPA and nginx proxy to FastAPI |
| Supabase | Auth, Postgres, and object storage |
| Stripe | Phase 7 billing provider |

## Environment

Backend runtime values belong in Dokploy or ignored env files. Do not commit
live secrets.

Current required backend values:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `PUBLIC_APP_URL=https://sitewise.au`
- `ALLOWED_ORIGINS=https://sitewise.au`

Legacy billing values, retained disabled until Phase 8.5:

- `POLAR_ENABLED`
- `POLAR_ENVIRONMENT`
- `POLAR_ACCESS_TOKEN`
- `POLAR_WEBHOOK_SECRET`
- `POLAR_STARTER_PRODUCT_ID`
- `POLAR_PROFESSIONAL_PRODUCT_ID`

Phase 7/8 agent and Stripe values:

- `AGENT_RUNTIME_ENABLED`
- `HERMES_BINARY_PATH`
- `HERMES_INVOCATION_MODE`
- `AGENT_PLATFORM_API_KEY`
- `AGENT_MCP_URL`
- `AGENT_WORKSPACE_ROOT`
- `AGENT_MAX_CONCURRENT_TURNS`
- `AGENT_TURN_TIMEOUT_SECONDS`
- `AGENT_TURN_TOKEN_SECRET`
- `BILLING_PROVIDER=stripe`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `STRIPE_CHECKOUT_SUCCESS_PATH`
- `STRIPE_PORTAL_RETURN_PATH`

Frontend build values:

- `VITE_API_BASE_URL=/api`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

## Deployment Flow

1. Push the target branch.
2. Build the backend and frontend images on the VPS or through Dokploy's build
   path.
3. Apply Alembic migrations from `backend/` using the direct/session database
   connection:

   ```bash
   uv run alembic upgrade head
   ```

4. Deploy the Dokploy compose app.
5. Confirm the external public network connects Traefik/nginx to
   `sitewise-web`.
6. Smoke test the app before routing users to it.

## Phase 8 Linux Validation

On the real host or staging app, run:

```powershell
./scripts/sitewise-vps-phase8-validate.ps1
```

The script writes `tmp/sitewise-vps-phase8-validate-*.txt` and validates:

- backend container starts and `/health` responds
- Hermes headless turn works in-container
- MCP initialize/tool call round-trips over the internal network
- SSE streams through nginx without buffering
- ODL/JVM extraction works
- Tender worker drains jobs
- Stripe webhook updates entitlement state
- production container env is present without printing secrets

Then manually validate that the full flagship demo completes on `sitewise.au`.

Record Phase 8 findings in `docs/plans/omnigent/phase8-deploy.md` when that
phase is executed.

## Smoke Test

Current pre-Hermes smoke path:

1. Open `https://sitewise.au`.
2. Sign in with Supabase Auth.
3. Check `https://sitewise.au/api/health`.
4. Confirm project list loads.
5. Open a project cockpit.
6. Ask a project-scoped chat question and inspect citations.
7. Upload a small document to the project repository.
8. Open billing and confirm entitlement state loads.

Phase 8 smoke path:

1. Sign up and subscribe through Stripe test mode.
2. Create or open a project.
3. Upload tender documents.
4. Ask chat to compare the selected tenders.
5. Confirm Hermes tool chips stream.
6. Confirm the TCM worker completes.
7. Confirm the comparison panel and report artefact populate.
8. Edit the artefact and confirm persistence.

## Rollback

Use Dokploy rollback to return to the previous working images. Keep Supabase data
untouched unless a migration rollback has been explicitly planned and tested.
