# Phase 8 Deploy Validation

Date: 2026-07-04

Status: deploy scaffolding implemented; live production acceptance pending.

## Implemented

- Backend Docker image installs pinned Hermes `v0.17.0` / `2026.6.19`.
- Backend Docker image preserves JVM and LibreOffice for ODL extraction.
- Backend Docker image now bakes `/opt/hermes/config.yaml` with the production
  model provider and Clerk MCP server shape.
- Dokploy compose includes the `AGENT_WORKSPACE_ROOT` volume.
- Dokploy compose includes agent, MCP, Stripe, quota, and worker environment.
- Dokploy compose includes a separate `sitewise-worker` service running
  `python -m tender.worker`.
- nginx disables response and request buffering for `/api/*`.
- `scripts/sitewise-vps-phase8-validate.ps1` records read-only VPS validation
  output for public health, in-container Hermes, MCP initialize/auth, ODL/JVM,
  nginx buffering, worker state, tender job counts, and Stripe rows.

## Live Validation

Not run in this coding session. The validation script needs SSH access to the
Dokploy host and the production containers:

```powershell
./scripts/sitewise-vps-phase8-validate.ps1
```

Attach the generated `tmp/sitewise-vps-phase8-validate-*.txt` output to this
record or paste the relevant green lines below before marking the gate passed.

## Production Acceptance

Not run in this coding session. The required production gate is still:

- signup
- Stripe subscription
- create project
- upload tender documents
- chat request starts tender comparison
- Hermes streams through the UI
- MCP tools execute with scoped authorization
- TCM worker drains jobs
- comparison panel populates
- report artefact card appears
- artefact edit persists

## Legacy Cutover

Deferred. The Phase 8.5 deletion gate has not passed, so the legacy
PydanticAI chat/orchestrator, cockpit safety-valve pages, and Polar code remain
in place.
