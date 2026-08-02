# SiteWise — Unattended Deployment Runbook

Operational runbook for shipping `main` to production at `https://sitewise.au`.
This is the *how*; `docs/deployment.md` is the *what* (architecture, services,
env var inventory, phase gates). Read this one to deploy.

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
| Orchestrator | Dokploy (compose app) |
| Dokploy stack prefix | `sitewise-3m1mco-` |
| Containers | `sitewise-3m1mco-sitewise-api-1`, `-sitewise-worker-1`, `-sitewise-web-1` |
| Compose file | `deploy/dokploy.compose.yml` |
| Docker network | external `sitewise-public` |
| Database / Auth / Storage | hosted Supabase, project ref `kdeqyxexexcywtsxiugz` |
| DB connection (from laptop) | session pooler `aws-1-ap-northeast-1.pooler.supabase.com:5432` |
| Git remote | `origin` → `https://github.com/bennyclifton-svg/sitewise.git` |
| Deploy branch | `main` |

### Access credentials — FILL THESE IN

These are the only things that block a fully unattended deploy. Secrets stay out
of git: record the *method and location*, not the value.

- **SSH host/port/user:** `root@45.151.153.218` on port `22` is the documented
  path (`scripts/sitewise-vps-*.ps1` default to
  `root@45-151-153-218.cloud-xip.com`). _If the port is non-standard or the
  firewall allowlists source IPs, record that here._
  - Non-standard SSH port: `TODO`
  - Firewall / IP allowlist in play: `TODO`
  - Key file: `TODO` (candidates on this machine: `~/.ssh/id_ed25519`,
    `~/.ssh/assemble-vps.pem`). Passphrase location: `TODO`
- **Dokploy dashboard URL:** `TODO` (commonly `http://45.151.153.218:3000` or a
  `dokploy.` subdomain). Login method: `TODO`
- **Dokploy API token:** `TODO` — with one, deploys can be triggered by HTTP and
  no dashboard click is needed. Generate in Dokploy under
  *Settings → API/CLI → Generate token*. Store in a local ignored file, e.g.
  `deploy/env/dokploy.local.env` as `DOKPLOY_URL=` / `DOKPLOY_TOKEN=`.
- **Provider console** (for power-cycle / VNC when SSH is dead): `TODO` — URL and
  account.

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
npx tsc --noEmit
npm run test -- --run
npm run build
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

### Step 1 — Push

```bash
git add -A
git commit -m "…"
git push origin main
```

A push **does not deploy**. Dokploy on this stack has been observed not to
auto-deploy on push; treat the push as staging the source only.

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

### Step 2b — Reconcile the Dokploy environment with the code defaults

**Dokploy env vars override code defaults, so shipping code is not enough.**
Any setting pinned in the stack's environment keeps its old value after deploy,
silently. Check this every time a default in `app/config.py` changes.

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
HERMES_MODEL_PROVIDER=openai
HERMES_MODEL=gpt-5.6-terra
```

Leave `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` alone — embeddings are a
different model family and changing it would invalidate every stored vector.

Keep the local `deploy/env/sitewise-api.env` in sync so the file stays a truthful
mirror of production.

### Step 3 — Roll out the containers

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

Fallback A — SSH and drive compose directly:

```bash
ssh root@45.151.153.218
cd /etc/dokploy/compose/sitewise-3m1mco   # verify path on the box
docker compose up -d --build
```

Fallback B — Dokploy dashboard: open the `sitewise` compose app, click
**Deploy** / **Redeploy**.

### Step 4 — Verify

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

Then the manual smoke path in `docs/deployment.md` §Smoke Test: sign in, project
list loads, open a cockpit, ask a project-scoped chat question with citations,
upload a small document, check billing entitlement.

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
| 2026-08-02 | `TODO` | GPT-5.6 model migration (chat/PMP/tender/Hermes) + Responses API provider switch | Pushed; **rollout blocked — VPS unreachable, see section 1 blanks** |
