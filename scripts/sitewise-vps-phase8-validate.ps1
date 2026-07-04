param(
    [string]$HostName = "root@45-151-153-218.cloud-xip.com",
    [string]$ApiContainer = "sitewise-3m1mco-sitewise-api-1",
    [string]$WorkerContainer = "sitewise-3m1mco-sitewise-worker-1",
    [string]$WebContainer = "sitewise-3m1mco-sitewise-web-1",
    [string]$PublicUrl = "https://sitewise.au"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $repoRoot "tmp"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outFile = Join-Path $outDir "sitewise-vps-phase8-validate-$stamp.txt"

$remoteScript = @'
set -uo pipefail

section() {
  echo
  echo "== $1 =="
}

run() {
  "$@" || {
    status=$?
    echo "WARN: command failed with status $status: $*"
    return 0
  }
}

section "host"
hostname
date -Is

section "containers"
run docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

section "public health"
run curl -sS -i "$PUBLIC_URL/api/health" | sed -n '1,24p'

section "backend runtime env summary"
run docker exec -i "$API_CONTAINER" python - <<'PY'
import os

SECRET_PARTS = ("KEY", "SECRET", "TOKEN", "PASSWORD")
KEYS = [
    "BILLING_PROVIDER",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_ID",
    "POLAR_ENABLED",
    "AGENT_RUNTIME_ENABLED",
    "HERMES_BINARY_PATH",
    "HERMES_INVOCATION_MODE",
    "HERMES_MODEL_PROVIDER",
    "HERMES_MODEL",
    "AGENT_PLATFORM_API_KEY",
    "AGENT_MCP_URL",
    "AGENT_WORKSPACE_ROOT",
    "AGENT_TURN_TOKEN_SECRET",
    "TENDER_WORKER_INPROC_ENABLED",
]

for key in KEYS:
    value = os.getenv(key)
    if value is None:
        print(f"{key}=missing")
        continue
    if any(part in key for part in SECRET_PARTS):
        print(f"{key}=set")
    else:
        print(f"{key}={value}")
PY

section "hermes install and base config"
run docker exec -i "$API_CONTAINER" sh -lc '
  hermes --version &&
  echo "-- HERMES_HOME=${HERMES_HOME:-unset}" &&
  test -f "${HERMES_HOME:-/opt/hermes}/config.yaml" &&
  sed -E "s/(Bearer )[^\"]+/\1[redacted]/" "${HERMES_HOME:-/opt/hermes}/config.yaml"
'

section "jvm libreoffice odl smoke"
run docker exec -i "$API_CONTAINER" sh -lc '
  java -version 2>&1 | sed -n "1,3p"
  libreoffice --version
  python - <<'"'"'PY'"'"'
import fitz
from tender.services.pdf import extract_pages

doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), "Phase 8 ODL smoke")
pdf = doc.tobytes()
pages = extract_pages(pdf)
if not pages or "Phase 8 ODL smoke" not in pages[0].text:
    raise SystemExit("ODL smoke returned no expected text")
print(f"ODL smoke ok: {len(pages)} page(s)")
PY
'

section "internal api and mcp"
run docker exec -i "$API_CONTAINER" python - <<'PY'
import json
import urllib.request
import uuid

ACCEPT = "application/json, text/event-stream"
BASE = "http://127.0.0.1:8000"

def post(payload, headers=None):
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{BASE}/mcp/",
        data=body,
        headers={
            "Accept": ACCEPT,
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode()
        session_id = response.headers.get("mcp-session-id")
    data_lines = [
        line.removeprefix("data: ")
        for line in text.splitlines()
        if line.startswith("data: ")
    ]
    message = json.loads(data_lines[-1] if data_lines else text)
    return message, session_id

with urllib.request.urlopen(f"{BASE}/health", timeout=10) as response:
    print(f"internal health: {response.status}")

init, session_id = post(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "phase8-vps-validate", "version": "0"},
        },
    }
)
server_name = init["result"]["serverInfo"]["name"]
if server_name != "clerk":
    raise SystemExit(f"unexpected MCP server name: {server_name}")
print(f"mcp initialize ok: {server_name}")

notify_request = urllib.request.Request(
    f"{BASE}/mcp/",
    data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode(),
    headers={
        "Accept": ACCEPT,
        "Content-Type": "application/json",
        "mcp-session-id": session_id,
    },
    method="POST",
)
try:
    urllib.request.urlopen(notify_request, timeout=20).read()
except Exception as exc:
    print(f"WARN: initialized notification failed: {exc}")

tool, _ = post(
    {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "list_tender_comparisons",
            "arguments": {"project_id": str(uuid.uuid4())},
        },
    },
    {"mcp-session-id": session_id},
)
result = tool["result"]
if result.get("isError") is not True:
    raise SystemExit("unauthenticated MCP tool call unexpectedly succeeded")
content = " ".join(block.get("text", "") for block in result.get("content", []))
if "turn token" not in content:
    raise SystemExit(f"unexpected unauthenticated tool response: {content}")
print("mcp auth seam ok: missing turn token rejected")
PY

section "optional hermes headless turn"
run docker exec -i "$API_CONTAINER" sh -lc '
  if [ -z "${AGENT_PLATFORM_API_KEY:-}" ]; then
    echo "SKIP: AGENT_PLATFORM_API_KEY is not set in the API container"
    exit 0
  fi
  timeout 120s hermes -z "Reply exactly: PHASE8_HERMES_OK" 2>&1 | tail -80
'

section "nginx sse buffering"
run docker exec -i "$WEB_CONTAINER" sh -lc '
  nginx -T 2>/dev/null | grep -nE "location /api/|proxy_buffering off|proxy_request_buffering off|proxy_read_timeout"
'

section "worker service"
run docker inspect "$WORKER_CONTAINER" --format 'worker status={{.State.Status}} command={{json .Config.Cmd}}'
run docker logs "$WORKER_CONTAINER" --since 30m 2>&1 | tail -120

section "tender job counts"
run docker exec -i "$API_CONTAINER" python - <<'PY'
import asyncio
from sqlalchemy import text

from app.database.session import get_session_factory

async def main():
    async with get_session_factory()() as session:
        rows = (
            await session.execute(
                text(
                    """
                    select status, count(*) as count
                    from tender_jobs
                    group by status
                    order by status
                    """
                )
            )
        ).mappings().all()
        if not rows:
            print("no tender jobs found")
            return
        for row in rows:
            print(dict(row))

asyncio.run(main())
PY

section "stripe rows"
run docker exec -i "$API_CONTAINER" python - <<'PY'
import asyncio
from sqlalchemy import text

from app.database.session import get_session_factory

async def print_rows(title, sql):
    async with get_session_factory()() as session:
        rows = (await session.execute(text(sql))).mappings().all()
    print(f"-- {title} --")
    if not rows:
        print("(none)")
        return
    for row in rows:
        clean = dict(row)
        print(clean)

async def main():
    await print_rows(
        "stripe_customers",
        """
        select user_id, stripe_customer_id, email, updated_at
        from stripe_customers
        order by updated_at desc
        limit 10
        """,
    )
    await print_rows(
        "stripe_subscriptions",
        """
        select stripe_subscription_id, product_id, status, canceled_at,
               current_period_end, updated_at
        from stripe_subscriptions
        order by updated_at desc
        limit 10
        """,
    )

asyncio.run(main())
PY
'@

Write-Host "Running Phase 8 VPS validation against $HostName ..."
$remoteScript = $remoteScript -replace "`r", ""
$remoteScript |
    ssh $HostName `
        "API_CONTAINER='$ApiContainer' WORKER_CONTAINER='$WorkerContainer' WEB_CONTAINER='$WebContainer' PUBLIC_URL='$PublicUrl' bash -s" `
        2>&1 |
    Tee-Object -FilePath $outFile

Write-Host ""
Write-Host "Saved validation output to: $outFile"
