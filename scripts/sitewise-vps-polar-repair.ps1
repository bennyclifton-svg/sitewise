param(
    [string]$HostName = "root@45-151-153-218.cloud-xip.com"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $repoRoot "tmp"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outFile = Join-Path $outDir "sitewise-vps-polar-repair-$stamp.txt"

$remoteScript = @'
set -euo pipefail

APP_DIR=/etc/dokploy/compose/sitewise-3m1mco/code
APP_CONTAINER=sitewise-3m1mco-sitewise-api-1
WEB_CONTAINER=sitewise-3m1mco-sitewise-web-1
WEBHOOK_URL=https://sitewise.au/api/billing/webhook/polar

cd "$APP_DIR"

echo "== host =="
hostname
date -Is

echo
echo "== configure Polar webhook endpoint =="
cat >/tmp/sitewise-polar-webhook-repair.py <<'PY'
from __future__ import annotations

import json
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENV_PATH = Path("deploy/.env")
WEBHOOK_URL = "https://sitewise.au/api/billing/webhook/polar"
EVENTS = [
    "customer.created",
    "customer.updated",
    "subscription.created",
    "subscription.updated",
    "subscription.active",
    "subscription.canceled",
    "subscription.uncanceled",
    "subscription.revoked",
    "subscription.past_due",
]


def read_env(path: Path) -> tuple[list[str], dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return lines, values


def write_env(path: Path, lines: list[str], key: str, value: str) -> None:
    output: list[str] = []
    replaced = False
    for line in lines:
        if line.split("=", 1)[0].strip() == key and "=" in line:
            output.append(f"{key}={value}")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"{key}={value}")
    backup = path.with_suffix(path.suffix + f".bak-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(path, backup)
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"Updated {key} in deploy/.env and wrote backup {backup.name}")


def api(base_url: str, token: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Polar API {method} {path} failed with {exc.code}: {body[:500]}") from exc
    return json.loads(body) if body else {}


def main() -> None:
    if not ENV_PATH.exists():
        raise SystemExit("STOP: deploy/.env is missing on the VPS.")
    lines, env = read_env(ENV_PATH)
    token = env.get("POLAR_ACCESS_TOKEN")
    if not token:
        raise SystemExit("STOP: POLAR_ACCESS_TOKEN is missing in deploy/.env.")
    environment = env.get("POLAR_ENVIRONMENT", "sandbox")
    base_url = "https://api.polar.sh/v1" if environment == "production" else "https://sandbox-api.polar.sh/v1"

    endpoints = api(base_url, token, "GET", "/webhooks/endpoints/?limit=100")
    items = endpoints.get("items")
    if not isinstance(items, list):
        raise RuntimeError("Polar API returned an unexpected endpoint list.")

    payload = {
        "url": WEBHOOK_URL,
        "format": "raw",
        "events": EVENTS,
        "enabled": True,
        "name": "SiteWise production",
    }
    endpoint = next((item for item in items if item.get("url") == WEBHOOK_URL), None)
    action = "updated"
    if endpoint:
        endpoint = api(base_url, token, "PATCH", f"/webhooks/endpoints/{endpoint['id']}/", payload)
    else:
        endpoint = api(base_url, token, "POST", "/webhooks/endpoints/", payload)
        action = "created"

    secret = endpoint.get("secret")
    if not isinstance(secret, str) or not secret:
        raise RuntimeError("Polar webhook endpoint did not return a signing secret.")

    print(f"Webhook endpoint {action}: {endpoint.get('id')} enabled={endpoint.get('enabled')} events={len(endpoint.get('events') or [])}")
    if env.get("POLAR_WEBHOOK_SECRET") == secret:
        print("VPS POLAR_WEBHOOK_SECRET already matches Polar.")
    else:
        write_env(ENV_PATH, lines, "POLAR_WEBHOOK_SECRET", secret)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
PY

python3 /tmp/sitewise-polar-webhook-repair.py

echo
echo "== restart SiteWise with repaired environment =="
docker compose --env-file deploy/.env -p sitewise-3m1mco -f deploy/dokploy.compose.yml up -d --no-build --force-recreate sitewise-api sitewise-web
docker network connect --alias sitewise-api sitewise-public "$APP_CONTAINER" 2>/dev/null || true
docker network connect --alias sitewise-web sitewise-public "$WEB_CONTAINER" 2>/dev/null || true
docker restart dokploy-traefik >/dev/null

echo
echo "== wait for health =="
for i in $(seq 1 30); do
  if curl -fsS https://sitewise.au/api/health >/dev/null; then
    echo "SiteWise health is OK"
    break
  fi
  sleep 2
  if [ "$i" = 30 ]; then
    echo "SiteWise health did not recover in time"
    exit 1
  fi
done

echo
echo "== backfill active Polar subscriptions by SiteWise user ID =="
cat >/tmp/sitewise-polar-backfill.py <<'PY'
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import text

from app.billing.polar import polar_base_url
from app.config import settings
from app.database.billing import upsert_polar_customer, upsert_polar_subscription
from app.database.session import get_session_factory


def as_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def as_bool(value: Any) -> bool:
    return value is True


def first_price_id(subscription: dict[str, Any]) -> str | None:
    direct = subscription.get("price_id") or subscription.get("priceId")
    if isinstance(direct, str) and direct:
        return direct
    product = subscription.get("product")
    prices = product.get("prices") if isinstance(product, dict) else None
    if isinstance(prices, list) and prices and isinstance(prices[0], dict):
        value = prices[0].get("id")
        return value if isinstance(value, str) and value else None
    return None


async def get_subscriptions(client: httpx.AsyncClient, external_customer_id: str) -> list[dict[str, Any]]:
    response = await client.get(
        f"{polar_base_url()}/subscriptions/",
        params={"external_customer_id": external_customer_id, "limit": 100},
        headers={
            "Authorization": f"Bearer {settings.polar_access_token}",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items")
    return items if isinstance(items, list) else []


async def get_recent_active_subscriptions(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    response = await client.get(
        f"{polar_base_url()}/subscriptions/",
        params={"active": "true", "limit": 10, "sorting": "-started_at"},
        headers={
            "Authorization": f"Bearer {settings.polar_access_token}",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items")
    return items if isinstance(items, list) else []


async def main() -> None:
    factory = get_session_factory()
    synced = 0
    async with factory() as session:
        users = (
            await session.execute(text("select id, email from users order by created_at desc limit 100"))
        ).mappings().all()
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            for user in users:
                subscriptions = await get_subscriptions(client, str(user["id"]))
                for subscription in subscriptions:
                    status = subscription.get("status")
                    if status not in {"active", "trialing"}:
                        continue
                    customer = subscription.get("customer") if isinstance(subscription.get("customer"), dict) else {}
                    polar_customer_id = subscription.get("customer_id") or customer.get("id")
                    product_id = subscription.get("product_id") or (
                        subscription.get("product", {}).get("id") if isinstance(subscription.get("product"), dict) else None
                    )
                    subscription_id = subscription.get("id")
                    if not all(isinstance(value, str) and value for value in [polar_customer_id, product_id, subscription_id, status]):
                        continue
                    polar_customer = await upsert_polar_customer(
                        session,
                        user_id=user["id"],
                        polar_customer_id=polar_customer_id,
                        email=customer.get("email") if isinstance(customer.get("email"), str) else user["email"],
                    )
                    await upsert_polar_subscription(
                        session,
                        customer_id=polar_customer.id,
                        polar_subscription_id=subscription_id,
                        product_id=product_id,
                        price_id=first_price_id(subscription),
                        status=status,
                        current_period_start=as_dt(subscription.get("current_period_start") or subscription.get("currentPeriodStart")),
                        current_period_end=as_dt(subscription.get("current_period_end") or subscription.get("currentPeriodEnd")),
                        cancel_at_period_end=as_bool(subscription.get("cancel_at_period_end") or subscription.get("cancelAtPeriodEnd")),
                        canceled_at=as_dt(subscription.get("canceled_at") or subscription.get("canceledAt")),
                    )
                    synced += 1
            await session.commit()

        print(f"Backfilled active subscriptions linked by SiteWise user ID: {synced}")

        rows = (
            await session.execute(
                text(
                    """
                    select u.email as app_email,
                           pc.email as polar_email,
                           ps.product_id,
                           ps.status,
                           ps.current_period_end
                    from users u
                    left join polar_customers pc on pc.user_id = u.id
                    left join polar_subscriptions ps on ps.customer_id = pc.id
                    order by coalesce(ps.updated_at, pc.updated_at, u.created_at) desc
                    limit 10
                    """
                )
            )
        ).mappings().all()
        print("\nCurrent SiteWise billing rows:")
        if not rows:
            print("(none)")
        for row in rows:
            print(dict(row))

        if synced == 0:
            print("\nNo active Polar subscription was found by SiteWise user ID.")
            print("Recent active Polar subscriptions:")
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                recent = await get_recent_active_subscriptions(client)
            if not recent:
                print("(none)")
            for item in recent:
                customer = item.get("customer") if isinstance(item.get("customer"), dict) else {}
                print(
                    {
                        "customer_email": customer.get("email"),
                        "customer_external_id": customer.get("external_id"),
                        "status": item.get("status"),
                        "product_id": item.get("product_id"),
                    }
                )


asyncio.run(main())
PY

docker cp /tmp/sitewise-polar-backfill.py "$APP_CONTAINER":/tmp/sitewise-polar-backfill.py
docker exec "$APP_CONTAINER" python /tmp/sitewise-polar-backfill.py

echo
echo "== recent webhook logs after repair =="
docker logs "$APP_CONTAINER" --since 10m 2>&1 | grep -Ei 'POST /billing/webhook|polar|billing|webhook|subscription|checkout|error|exception|traceback' | tail -120 || true

echo
echo "== done =="
'@

Write-Host "Running SiteWise VPS Polar repair against $HostName ..."
$remoteScript = $remoteScript -replace "`r", ""
$remoteScript | ssh $HostName "bash -s" 2>&1 | Tee-Object -FilePath $outFile

Write-Host ""
Write-Host "Saved repair output to: $outFile"
