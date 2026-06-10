param(
    [string]$HostName = "root@45-151-153-218.cloud-xip.com"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $repoRoot "tmp"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outFile = Join-Path $outDir "sitewise-vps-billing-diagnose-$stamp.txt"

$remoteScript = @'
set -euo pipefail

echo "== host =="
hostname
date -Is

echo
echo "== sitewise and routing containers =="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'sitewise|dokploy-traefik' || true

echo
echo "== public health =="
curl -sS -i https://sitewise.au/api/health | sed -n '1,24p' || true

echo
echo "== recent billing and webhook logs =="
docker logs sitewise-3m1mco-sitewise-api-1 --since 4h 2>&1 \
  | grep -Ei 'POST /billing/webhook|polar|billing|webhook|subscription|checkout|error|exception|traceback' \
  | tail -180 || true

echo
echo "== database billing rows =="
docker exec -i sitewise-3m1mco-sitewise-api-1 python - <<'PY'
import asyncio
from sqlalchemy import text

from app.database.session import get_session_factory


async def print_rows(session, title, sql):
    print(f"\n--- {title} ---")
    rows = (await session.execute(text(sql))).mappings().all()
    if not rows:
        print("(none)")
        return
    for row in rows:
        print(dict(row))


async def main():
    factory = get_session_factory()
    async with factory() as session:
        await print_rows(
            session,
            "recent_users",
            """
            select id, email, created_at
            from users
            order by created_at desc
            limit 10
            """,
        )
        await print_rows(
            session,
            "polar_customers",
            """
            select id, user_id, polar_customer_id, email, created_at, updated_at
            from polar_customers
            order by updated_at desc
            limit 10
            """,
        )
        await print_rows(
            session,
            "polar_subscriptions",
            """
            select customer_id, polar_subscription_id, product_id, status,
                   current_period_start, current_period_end, created_at, updated_at
            from polar_subscriptions
            order by updated_at desc
            limit 10
            """,
        )
        await print_rows(
            session,
            "entitlement_view",
            """
            select u.email as app_email,
                   pc.email as polar_email,
                   pc.polar_customer_id,
                   ps.polar_subscription_id,
                   ps.product_id,
                   ps.status,
                   ps.current_period_end
            from users u
            left join polar_customers pc on pc.user_id = u.id
            left join polar_subscriptions ps on ps.customer_id = pc.id
            order by coalesce(ps.updated_at, pc.updated_at, u.created_at) desc
            limit 10
            """,
        )


asyncio.run(main())
PY
'@

Write-Host "Running SiteWise VPS billing diagnostics against $HostName ..."
$remoteScript = $remoteScript -replace "`r", ""
$remoteScript | ssh $HostName "bash -s" 2>&1 | Tee-Object -FilePath $outFile

Write-Host ""
Write-Host "Saved diagnostic output to: $outFile"
