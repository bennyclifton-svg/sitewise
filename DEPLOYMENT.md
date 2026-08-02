# SiteWise — Unattended Deployment Runbook

The single deployment document for shipping `main` to production at
`https://sitewise.au` — production facts, environment inventory, deploy
sequence, smoke tests and triage.

> **Purpose:** this file exists so a deploy can be driven end-to-end without the
> operator at the keyboard. Anything an agent would otherwise have to ask for
> belongs here. If you hit a blank, fill it in rather than answering it once.

---

## 1. Production facts

| Thing | Value |
| --- | --- |
| Public URL | `https://sitewise.au` |
| VPS IP | `45.151.153.218` |
| VPS reverse DNS | `45-151-153-218.cloud-xip.com` |
| Hosting provider (per APNIC RDAP) | CloudWebManage Platform AU (`CLOUDWEBMANAGE-AU-SY`), country AU |
| Provider panel | **My Cloud → Server Management**, server `SiteWise` |
| Provider server ID | `a50faedb-d09d-411a-8d91-1cde9a1af697` |
| VPS shape / zone | 1 vCPU, 4096 MB RAM, 50 GB disk; AU-SY Sydney |
| Root filesystem | ext4 on `/dev/sda2` |
| Orchestrator | Dokploy (compose app) |
| Dokploy dashboard | `http://45.151.153.218:3000` |
| Dokploy stack prefix | `sitewise-3m1mco-` |
| Containers | `sitewise-3m1mco-sitewise-api-1`, `-sitewise-worker-1`, `-sitewise-core-workflow-worker-1`, `-sitewise-web-1` |
| Dokploy checkout | `/etc/dokploy/compose/sitewise-3m1mco/code` |
| Compose file | `deploy/dokploy.compose.yml` |
| Docker network | external `sitewise-public` |
| Database / Auth / Storage | hosted Supabase, project ref `kdeqyxexexcywtsxiugz` |
| DB connection (from laptop) | session pooler `aws-1-ap-northeast-1.pooler.supabase.com:5432` |
| Git remote | `origin` → `https://github.com/bennyclifton-svg/sitewise.git` |
| Deploy branch | `main` |

### Services

| Service | Role |
| --- | --- |
| `sitewise-api` | FastAPI API, TCM router, billing, Hermes/MCP runtime |
| `sitewise-worker` | Tender Comparison worker running `python -m tender.worker` |
| `sitewise-core-workflow-worker` | Durable core workflow worker running `python -m app.workflows.worker` |
| `sitewise-web` | Static React SPA and nginx proxy to FastAPI |
| Supabase | Auth, Postgres, and object storage |
| Stripe | Billing provider |

The backend image bundles Hermes CLI v0.17.x with JVM/ODL support, FastAPI, MCP,
and the Tender Comparison worker path. `AGENT_WORKSPACE_ROOT` is a persistent
volume for scratch and artefact files; Supabase Storage stays canonical for
uploaded source documents. nginx must keep `/api/*` and SSE streams unbuffered.

### Access credentials and recovery access

These are the only things that block a fully unattended deploy. Secrets stay out
of git: record the *method and location*, not the value.

- **SSH host/port/user:** `root@45.151.153.218` on port `22`. The working key on
  the deployment laptop is `C:\Users\orlan\.ssh\id_ed25519`. The equivalent
  hostname is `root@45-151-153-218.cloud-xip.com`.
  - Provider firewall: disabled in My Cloud on 2026-08-02.
  - Ubuntu UFW: inactive on 2026-08-02.
- **Dokploy dashboard URL:** `http://45.151.153.218:3000`. Login method/account:
  `TODO`.
- **Dokploy API token:** `TODO` — with one, deploys can be triggered by HTTP and
  no dashboard click is needed. Generate in Dokploy under
  *Settings → API/CLI → Generate token*. Store in a local ignored file, e.g.
  `deploy/env/dokploy.local.env` as `DOKPLOY_URL=` / `DOKPLOY_TOKEN=`.
- **Provider console** (for power-cycle / VNC when SSH is dead): sign in to the
  **My Cloud** panel, open **Server Management**, select `SiteWise`, then use
  **Actions → Console**. **Actions → Reboot** is the out-of-band restart. The
  exact panel URL/account is still `TODO`; record it here without storing a
  password in git. See the resolved recovery incident in section 6.

### Environment inventory

Backend runtime values must live in the Dokploy compose app's persistent
**Environment** settings. Never commit live secrets. `deploy/env/sitewise-api.env`
is the local gitignored mirror of what Dokploy holds — keep it truthful.

The checkout-local file
`/etc/dokploy/compose/sitewise-3m1mco/code/deploy/.env` is generated/replaced
when Dokploy checks out a push. Editing it over SSH is suitable for an emergency
restart only; it is **not** durable configuration. On 2026-08-02 an automatic
checkout erased values added only to this file. Save values in Dokploy before
the next push or redeploy.

Required backend values:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `PUBLIC_APP_URL=https://sitewise.au`
- `ALLOWED_ORIGINS=https://sitewise.au`

Agent and billing values:

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

Model values are listed separately in step 2b, because they are the ones that
silently override a code change.

`BILLING_PROVIDER` accepts only `none` or `stripe`. Polar was removed on
2026-08-02; a leftover `BILLING_PROVIDER=polar` now fails validation and will
stop the container booting. Any other stale `POLAR_*` values are inert — the
settings model is `extra="ignore"` — and can be deleted at leisure.

---

## 2. Pre-flight (do this before touching production)

Run from the repo root. All of these work offline and none touch prod.

```bash
# Backend: lint + offline tests (integration + tender_eval are deselected by
# pyproject addopts, which is what keeps pytest off the live database)
cd backend
uv run ruff check app ingest tender tests
uv run python -m pytest -q

# Frontend: typecheck, tests, production build
cd ../frontend
pnpm exec tsc --noEmit
pnpm test -- --run
pnpm build
```

> **Live-database hazard.** `backend/.env` `DATABASE_URL` points at the **live
> Supabase database**, not a local one. A bare `pytest` once ran
> `tests/tender/test_migrations.py::test_tender_migrations_roundtrip_against_database`,
> which downgrades to `006_cockpit_refresh_indexes` and drops every tender and
> taxonomy table. It is now double-guarded (`@pytest.mark.integration` plus a
> `TENDER_MIGRATION_ROUNDTRIP=1` opt-in) and `addopts` deselects `integration`.
> **Never** run pytest with `-m ""` or `--override-ini` against this `.env`, and
> never `alembic downgrade` against prod.

If a model id changed, verify it exists before shipping — a bad id takes the
whole app down at first request:

```bash
cd backend
KEY=$(grep -E "^OPENAI_API_KEY=" .env | cut -d= -f2- | tr -d '"'"'"'\r')
curl -sS https://api.openai.com/v1/models -H "Authorization: Bearer $KEY" \
  | python -c "import sys,json;print([m['id'] for m in json.load(sys.stdin)['data']])"
```

---

## 3. Deploy sequence

Order matters. Migrations are additive, so schema-first is safe for the
still-running old code; code-first is not.

### Step 1 — Reconcile the persistent Dokploy environment

**Dokploy env vars override code defaults, so shipping code is not enough.**
Any setting pinned in the stack's environment keeps its old value after deploy,
silently. Check this every time a default in `app/config.py` changes.

Use the compose app's **Environment** editor and save there. Do not rely on
editing `code/deploy/.env`: the next automatic checkout replaces it. Confirm all
five required billing/agent secrets are non-empty without printing their values:
`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`,
`AGENT_TURN_TOKEN_SECRET`, and `AGENT_PLATFORM_API_KEY`.

Known trap: `deploy/env/sitewise-api.env` (gitignored; mirrors what Dokploy
holds) pins `OPENAI_CHAT_MODEL=gpt-4o-mini`. With the GPT-5.6 code deployed but
that variable still set, `allowed_chat_models()` *prepends* the configured
default to the allowlist — so prod would keep answering on `gpt-4o-mini`, show it
as the picker default with a raw unlabelled id, and look healthy while running
the wrong model.

For the GPT-5.6 rollout, set in Dokploy (or delete the keys so code defaults win):

```
OPENAI_CHAT_MODEL=gpt-5.6-luna
OPENAI_CHAT_MODELS=gpt-5.6-sol,gpt-5.6-terra,gpt-5.6-luna
PMP_MODEL_PROVIDER=openai-api
PMP_MODEL=gpt-5.6-terra
PMP_MODEL_LABEL=GPT-5.6 Terra (balanced)
COST_PLAN_MODEL=gpt-5.6-luna
TENDER_MODEL_EXTRACT=gpt-5.6-luna
TENDER_MODEL_ADJUDICATE_SMALL=gpt-5.6-terra
TENDER_MODEL_ADJUDICATE_FRONTIER=gpt-5.6-sol
HERMES_MODEL_PROVIDER=openai-api
HERMES_MODEL=gpt-5.6-terra
HERMES_MODEL_OPTIONS=openai-api:gpt-5.6-sol:GPT-5.6 Sol (complex),openai-api:gpt-5.6-terra:GPT-5.6 Terra (balanced),openai-api:gpt-5.6-luna:GPT-5.6 Luna (fast),openai-codex:gpt-5.5:gpt-5.5 (Codex subscription)
```

Leave `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` alone — embeddings are a
different model family and changing it would invalidate every stored vector.

Keep the local `deploy/env/sitewise-api.env` in sync so the file stays a truthful
mirror of production.

### Step 2 — Migrate the production database

The backend container's CMD is just `uvicorn` — there is no migrate-on-start.
Run Alembic from the laptop; `backend/.env` already points at prod:

```bash
cd backend
uv run alembic current   # read-only; confirm where prod actually is
uv run alembic heads     # confirm the target
uv run alembic upgrade head
```

If `current` already equals `heads`, skip — DB and code drift independently and
prod is often already at head.

### Step 3 — Push and monitor the automatic deployment

```bash
git add -A
git commit -m "…"
git push origin main
```

A push to `main` **does trigger an automatic Dokploy deployment** on this stack;
this was confirmed twice on 2026-08-02. During deployment the `code` directory
may briefly contain only a partial `.git` checkout; do not run compose commands
against it until `deploy/dokploy.compose.yml` exists again.

### Step 4 — Roll out manually if the automatic deploy does not complete

The compose uses `pull_policy: never` with `image: sitewise-production-*:latest`,
so **Dokploy builds the images on the VPS from current `main`**. There is no
registry push step.

Preferred (unattended) — Dokploy API:

```bash
# needs DOKPLOY_URL + DOKPLOY_TOKEN from section 1
curl -sS -X POST "$DOKPLOY_URL/api/compose.deploy" \
  -H "x-api-key: $DOKPLOY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"composeId":"<COMPOSE_ID>"}'
```

`<COMPOSE_ID>`: `TODO` — read it from the Dokploy compose app's URL.

Fallback A — SSH and drive the effective Dokploy compose file directly:

```bash
ssh root@45.151.153.218
cd /etc/dokploy/compose/sitewise-3m1mco/code
test -f deploy/dokploy.compose.yml
docker compose \
  --env-file deploy/.env \
  -p sitewise-3m1mco \
  -f deploy/dokploy.compose.yml \
  config --quiet
docker compose \
  --env-file deploy/.env \
  -p sitewise-3m1mco \
  -f deploy/dokploy.compose.yml \
  up -d --build
```

Dokploy adds routing labels and the `dokploy-network` attachment to its effective
checkout copy of `deploy/dokploy.compose.yml`, so that file is normally dirty on
the VPS. Preserve those changes; do not replace it with the pristine git copy.

Check disk before an on-host build with `df -h /` and `docker system df`. The
backend image is large because it includes LibreOffice, Hermes, Playwright and
document-extraction dependencies. Linux builds must retain the explicit
CPU-only PyTorch source in `backend/pyproject.toml`/`uv.lock`; resolving the CUDA
wheels exhausted the 50 GB VPS during the first attempt. After a successful
deploy, `docker builder prune --all --force` and `docker image prune --force`
remove build cache and dangling layers without touching running containers or
volumes. The 2026-08-02 cleanup moved `/` from 89% to 77% used.

The API image must contain `/app/data/taxonomy`, `/app/data/seed`,
`/app/data/skills/reference`, `/app/data/tender`, and
`/app/docs/clerk-brief.md`. A build that omits these source-of-truth files fails
at startup with `FileNotFoundError: /app/data/taxonomy/emphasis-profiles.json`.

Fallback B — Dokploy dashboard: open the `sitewise` compose app, click
**Deploy** / **Redeploy**.

### Step 5 — Verify

```bash
curl -sS https://sitewise.au/api/health
```

**The health payload is the live-version tell.** A stale build returns only
`status`, `chat_model`, `chat_provider`, `embedding_model`. Current code also
returns `pmp_model`, `pmp_model_provider`, `pmp_model_label`, `cost_plan_model`,
`hermes_model`, `hermes_model_provider`, `pi_model`. If the extra keys are
missing, the new code is **not** live regardless of what Dokploy reported.

After a model change, confirm the values match what you shipped — e.g.
`"chat_model":"gpt-5.6-luna"`, `"chat_provider":"openai-responses:gpt-5.6-luna"`.

Then walk the manual smoke path:

1. Open `https://sitewise.au` and sign in with Supabase Auth.
2. Confirm the project list loads.
3. Open a project cockpit.
4. Ask a project-scoped chat question and inspect the citations.
5. Upload a small document to the project repository.
6. Open billing and confirm entitlement state loads.

Full agent-path smoke test, when the change touches Hermes or tender:

1. Sign up and subscribe through Stripe test mode.
2. Create or open a project.
3. Upload tender documents.
4. Ask chat to compare the selected tenders.
5. Confirm Hermes tool chips stream.
6. Confirm the TCM worker completes.
7. Confirm the comparison panel and report artefact populate.
8. Edit the artefact and confirm persistence.

### Deeper validation on the host

```powershell
./scripts/sitewise-vps-phase8-validate.ps1
```

Writes `tmp/sitewise-vps-phase8-validate-*.txt` and checks: backend container
starts and `/health` responds; a Hermes headless turn works in-container; MCP
initialize/tool-call round-trips over the internal network; SSE streams through
nginx unbuffered; ODL/JVM extraction works; the tender worker drains jobs; a
Stripe webhook updates entitlement state; and production container env is
present without printing secrets. It needs the section 1 SSH access.

---

## 4. Health / triage

Quick classification of what is broken, from the outside in:

| Symptom | Means |
| --- | --- |
| `curl` to `:443` returns **connection refused** (TCP RST) | Host is up, nothing listening — Traefik/Docker/the stack is down. Needs SSH or provider console. |
| `curl` to `:443` **times out** | Packets dropped — host down, or a firewall/routing problem between you and it. Compare from a second network before concluding the server is dead. |
| `:3000` (Dokploy) also refused | Dokploy itself is not running, not just the app. Dashboard won't help; you need shell. |
| `/api/health` responds but lacks `pmp_model` etc. | Old code still live — the deploy didn't take. |
| App loads, chat 500s | Usually a bad model id or a missing env var; check `docker logs` on `sitewise-api`. |
| Provider console stops at `(initramfs)` with `UNEXPECTED INCONSISTENCY` | Root filesystem check failed. Use the exact device printed by boot; this VPS used `/dev/sda2`. Follow the section 6 recovery. |
| `dokploy-traefik` loops with exit `139` / kernel segfaults | The local Traefik image may be corrupt after a filesystem incident. An ordinary pull can falsely report it up to date; force-remove and re-pull as in section 6. |
| Alembic reports `EMAXCONNSESSION max clients reached` | The Supabase session pooler is saturated. Stop API and both workers, wait for their sessions to close, run the migration/check as the sole client, then restart the stack. |

Probe from two vantage points before diagnosing — a local-ISP routing fault to
this IP looks identical to an outage if you only test from one network.

Useful VPS scripts (all SSH to the box, so they need section 1 access):

- `scripts/sitewise-vps-phase8-validate.ps1` — full stack validation, writes
  `tmp/sitewise-vps-phase8-validate-*.txt`
- `scripts/sitewise-vps-billing-diagnose.ps1`

### Reseeding after a tender-table wipe

```bash
cd backend
uv run python -m tender.seeds.load          # idempotent
uv run python -m tender.services.embedding  # ~1,826 synonym embeddings, needs OpenAI key
```

Health probe: `select count(*) from taxonomy_cells where active` → expect 180.

---

## 5. Rollback

Use Dokploy's rollback to the previous working images. Leave Supabase data alone
unless a migration rollback has been explicitly planned and tested — **do not**
`alembic downgrade` to "recover"; that is what dropped the tender tables before.

---

## 6. Deploy log

| Date | Commit | What shipped | Outcome |
| --- | --- | --- | --- |
| 2026-08-02 | `cc167bf8` | GPT-5.6 model migration (chat/PMP/cost plan/tender/Hermes) + Responses API provider switch | Live. `/api/health` reports chat `gpt-5.6-luna`, Hermes/PMP `gpt-5.6-terra`, cost plan `gpt-5.6-luna`, and embedding `text-embedding-3-small`. |
| 2026-08-02 | `5f597424` | Polar removed; Stripe is the only billing provider | Live. Required Stripe values are present in the running container; values were not printed or committed. |
| 2026-08-02 | `219763b1` | Procurement Requests (RFP/EOI/RFT/RFQ) register | Live. Production Alembic revision confirmed as `038_procurement_requests (head)`. Optional follow-up: run `uv run python scripts/backfill_procurement_requests.py` in report mode, then explicitly use `--apply` if the report is correct. |
| 2026-08-02 | `f8bc5ef6` | Deployment preflight fixes | Live. Backend: 1,561 passed, 6 skipped, 24 deselected. Frontend: 181 tests, typecheck, production build and bundle budget passed. |
| 2026-08-02 | `ec57eb81` | CPU-only PyTorch resolution on Linux | Live. Removed CUDA/NVIDIA wheels that exceeded the 50 GB VPS during image build. |
| 2026-08-02 | `5a0f9595` | Package runtime taxonomy, platform knowledge, tender seeds and doctrine in the API image | Live. Fixed the startup `FileNotFoundError`; API and core worker healthy, tender worker ready, all application/Traefik restart counts zero. |

### 2026-08-02 — production outage and recovery (resolved)

The outage predated and was unrelated to the release. The provider console
showed the actual cause: Ubuntu could not mount the root filesystem because
`/dev/sda2` contained errors. Rebooting alone repeated the failure.

#### Filesystem recovery

Open **My Cloud → Server Management → SiteWise → Actions → Console**. At the
`(initramfs)` prompt, use the device named in the boot error. For this VPS it was:

```sh
fsck.ext4 -f -y /dev/sda2
reboot -f
```

Do not copy `/dev/sda2` to a different server without checking its boot output;
running `fsck` against the wrong device is destructive. The repair reported and
fixed filesystem errors, after which Ubuntu 24.04 booted and SSH returned.

#### Traefik recovery after boot

Docker and the old application containers returned, but HTTPS remained down
because `dokploy-traefik` repeatedly exited `139`; the kernel logged Traefik
segfaults. Even a minimal container using the local `traefik:v3.6.1` image
segfaulted, isolating the fault to the image rather than dynamic routing config.
An ordinary `docker pull` said the image was current, so force-refresh it:

```bash
docker inspect dokploy-traefik \
  > /root/dokploy-traefik.inspect-$(date +%Y%m%d).json
docker rm -f dokploy-traefik
docker image rm traefik:v3.6.1
docker pull traefik:v3.6.1
docker run -d \
  --name dokploy-traefik \
  --restart always \
  -p 80:80/tcp \
  -p 443:443/tcp \
  -p 443:443/udp \
  -v /etc/dokploy/traefik/traefik.yml:/etc/traefik/traefik.yml \
  -v /etc/dokploy/traefik/dynamic:/etc/dokploy/traefik/dynamic \
  -v /var/run/docker.sock:/var/run/docker.sock \
  traefik:v3.6.1
docker network connect dokploy-network dokploy-traefik
docker network connect sitewise-public dokploy-traefik
```

Verify `docker inspect dokploy-traefik` shows ports 80/443, both networks and
restart policy `always`, then check `curl -fsS https://sitewise.au/api/health`.
The inspect backup from this incident is
`/root/dokploy-traefik.inspect-20260802.json`.

#### Release outcome

After recovery, the schema-first migration reached revision 038 and commit
`5a0f9595` was deployed. Final checks on 2026-08-02:

- TCP 22, 80 and 443 reachable from the deployment laptop.
- `sitewise-api` and `sitewise-core-workflow-worker` healthy.
- Tender worker ready with four lanes; web and Traefik running.
- Zero restarts for API, both workers, web and Traefik.
- Public `/api/health` returned the intended GPT-5.6 and embedding models.
- UFW inactive; provider firewall disabled.
- Docker cache/dangling-layer cleanup left 12 GB free on `/` (77% used).
