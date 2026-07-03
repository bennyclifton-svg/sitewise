# Phase 8: Deploy And Legacy Cutover

## Objective

Deploy the Hermes-backed product to `sitewise.au`, validate the full production
flow, then remove legacy runtime and billing code only after the production gate
passes.

## Implementation Changes

- Add pinned Hermes CLI installation to the backend Docker image.
- Preserve JVM and LibreOffice dependencies already needed by ODL.
- Add `AGENT_WORKSPACE_ROOT` volume to Dokploy compose.
- Add agent, MCP, Stripe, and worker environment examples.
- Add a separate `sitewise-worker` service for `python -m tender.worker`, unless
  a deliberate production decision keeps in-process worker mode.
- Ensure nginx disables buffering for SSE routes.
- Validate Hermes-to-MCP networking from inside the deployed container.
- Run the full production acceptance before deleting any legacy code.

## Production Acceptance

The production gate must prove:

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

Only after production acceptance passes:

- remove retired PydanticAI chat/orchestrator code
- remove retired cockpit routes/pages superseded by the new shell
- remove Polar code/settings/env examples
- flip agent runtime default on
- keep commits small and revertable
- run full backend and frontend checks after each deletion group

## Gate

- Production acceptance passes on `sitewise.au`.
- Backend tests, ruff, frontend lint, frontend build, and frontend tests pass.
- Legacy deletion is complete only after the safety valve is no longer needed.

