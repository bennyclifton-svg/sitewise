# SiteWise Production Deployment

This is the deployment runbook for Clerk as the production SiteWise app at `https://sitewise.au`.

## Target

- Host: `sitewise.au`
- VPS pattern: Kamatera VPS managed through Dokploy and Traefik
- Services: `sitewise-web` and `sitewise-api`
- Routing: `sitewise-web` serves the React SPA and proxies `/api/*` to FastAPI
- Public network: Docker external network `sitewise-public`
- Database: the single Clerk Supabase project
- Auth: Supabase Auth
- Billing authorization: Polar entitlements

The old Assemble/SiteWise app, old hosted database, and Better Auth runtime are retired for this deployment. Do not migrate the Assemble database into production Clerk, and do not deploy Practice Node, Hermes, or Assemble runtime services.

## VPS Login

Run this from local Windows PowerShell:

```powershell
ssh root@45-151-153-218.cloud-xip.com
```

## Where Commands Run

- Local Windows PowerShell prompt looks like `PS D:\AI Projects\...`.
- VPS SSH prompt looks like `root@assemblep2:~#`.
- Run `git push` and the SSH login command locally.
- Run Docker, Dokploy, Traefik, migrations, and health-check deployment commands on the VPS after SSH login.
- If Docker prints a `docker-desktop://...` build link, the command ran locally and did not deploy to the VPS.

## First-Time Setup

1. In Dokploy, create a compose app named `sitewise`.
2. Point the app at this repo and use `deploy/dokploy.compose.yml`.
3. Create the external public network on the VPS:

```bash
docker network create sitewise-public 2>/dev/null || true
docker network connect sitewise-public dokploy-traefik 2>/dev/null || true
```

4. Configure Traefik/custom domain for `sitewise.au` to the `sitewise-web` service on port `80`.
   If Dokploy's compose labels do not register with Traefik, use the manual route in `Manual Traefik Route`.
5. Put backend runtime secrets in `deploy/env/sitewise-api.env` or Dokploy's secret/environment UI.
6. Put frontend build values in `deploy/env/sitewise-build.env` or Dokploy's compose/build environment UI.
7. Create a Polar webhook endpoint for `https://sitewise.au/api/billing/webhook/polar`.
8. Subscribe the webhook to `customer.created`, `customer.updated`, `subscription.created`, `subscription.updated`, `subscription.active`, `subscription.canceled`, `subscription.uncanceled`, `subscription.revoked`, and `subscription.past_due`.
9. Run backend migrations before routing traffic:

```bash
cd backend
uv run alembic upgrade head
```

## Environment

Use placeholders in committed files only. Live values belong in Dokploy or ignored env files.

Required backend values:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `PUBLIC_APP_URL=https://sitewise.au`
- `ALLOWED_ORIGINS=https://sitewise.au`
- `POLAR_ENABLED=true`
- `POLAR_ENVIRONMENT=sandbox` for first workflow test, then `production` when ready for real payments
- `POLAR_ACCESS_TOKEN`
- `POLAR_WEBHOOK_SECRET`
- `POLAR_STARTER_PRODUCT_ID`
- `POLAR_PROFESSIONAL_PRODUCT_ID`

Required frontend build values:

- `VITE_API_BASE_URL=/api`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

To import the existing Polar values from the Assemble local env into Clerk's local backend env without printing secrets:

```powershell
.\scripts\sync-assemble-polar-env.ps1
```

## Deploy

The Kamatera VPS currently uses local prebuilt images because its Docker Compose Bake path crashed during source builds.
Build these images on the VPS from the Dokploy checkout before deploying:

```bash
cd /etc/dokploy/compose/sitewise-3m1mco/code

VITE_SUPABASE_URL="$(awk -F= '$1=="VITE_SUPABASE_URL"{print substr($0,index($0,"=")+1)}' deploy/.env)"
VITE_SUPABASE_ANON_KEY="$(awk -F= '$1=="VITE_SUPABASE_ANON_KEY"{print substr($0,index($0,"=")+1)}' deploy/.env)"

docker build -t sitewise-production-api:latest -f deploy/docker/backend.Dockerfile .
docker build -t sitewise-production-web:latest \
  --build-arg VITE_API_BASE_URL=/api \
  --build-arg VITE_SUPABASE_URL="$VITE_SUPABASE_URL" \
  --build-arg VITE_SUPABASE_ANON_KEY="$VITE_SUPABASE_ANON_KEY" \
  -f deploy/docker/frontend.Dockerfile .
```

In Dokploy, trigger a deploy after the target branch is pushed and the images are built. Keep server-only values as runtime environment variables, not Docker build arguments.

If the retired Assemble service still owns the domain, remove its Traefik labels:

```bash
docker service update \
  --label-rm traefik.enable \
  --label-rm traefik.http.routers.assembleai.entrypoints \
  --label-rm traefik.http.routers.assembleai.rule \
  --label-rm traefik.http.routers.assembleai.tls \
  --label-rm traefik.http.routers.assembleai.tls.certresolver \
  --label-rm traefik.http.services.assembleai.loadbalancer.server.port \
  assembleai-assembleai-bxojdu
```

## Manual Traefik Route

The current VPS uses this file route because the Dokploy compose labels did not consistently register for the non-Swarm compose containers:

```bash
docker network create sitewise-public 2>/dev/null || true
docker network connect sitewise-public dokploy-traefik 2>/dev/null || true
docker network connect --alias sitewise-api sitewise-public sitewise-3m1mco-sitewise-api-1 2>/dev/null || true
docker network connect --alias sitewise-web sitewise-public sitewise-3m1mco-sitewise-web-1 2>/dev/null || true

cat >/etc/dokploy/traefik/dynamic/sitewise-clerk.yml <<'EOF'
http:
  routers:
    sitewise-clerk-websecure:
      rule: "Host(`sitewise.au`)"
      entryPoints:
        - websecure
      service: sitewise-clerk-web
      tls:
        certResolver: letsencrypt

  services:
    sitewise-clerk-web:
      loadBalancer:
        servers:
          - url: "http://sitewise-web:80"
EOF

docker restart dokploy-traefik
```

Validate the route with:

```bash
curl -i http://127.0.0.1:8080/api/health
curl -i https://sitewise.au/api/health
```

## Smoke Test

1. Open `https://sitewise.au`.
2. Sign in with Supabase Auth.
3. Check `https://sitewise.au/api/health`.
4. Confirm project list loads.
5. Open billing and confirm the current entitlement status loads.
6. Start Starter checkout and return from Polar.
7. Confirm a webhook updates local subscription state.
8. Open the customer portal from billing.
9. Open a project cockpit.
10. Ask a project-scoped chat question and inspect citations.
11. Upload a small document to the project repository.
12. Run Create PMP and inspect the saved draft provenance.

## Rollback

If the new deployment fails, use Dokploy rollback to the previous working image. If DNS or Traefik routing was changed manually, restore the old route while keeping Supabase data untouched.
