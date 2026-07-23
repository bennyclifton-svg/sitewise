# Core workflow worker

The core workflow worker executes Project Plan create/refresh, Cost Plan create,
file sort, and consultant procurement runs from the durable `workflow_runs`
queue. It is separate from the Tender worker and uses the same backend image.

## Production start and health

Run `python -m app.workflows.worker`. Dokploy defines this as
`sitewise-core-workflow-worker`; the process logs `workflow_worker_started` only
after settings and the database session factory load successfully. Container
restart policy is `unless-stopped`. Operational health is a running container
plus a fresh workflow-run heartbeat while a job is active; queued work older
than two poll intervals should alert.

Only local development may set `WORKFLOW_WORKER_INPROC_ENABLED=true`. Production
keeps it false so API restarts cannot own or lose workflow execution.

## Local development

Chat-queued Project Plan, Cost Plan, file sort, and consultant RFP runs stay
`queued` until a core worker claims them. For local API-only development:

1. Set `WORKFLOW_WORKER_INPROC_ENABLED=true` in `backend/.env` (see
   `.env.example`), then restart the API; or
2. Run a separate worker: `cd backend && uv run python -m app.workflows.worker`.

Without one of those, agent replies that queue an RFP will never produce a
draft. The in-process worker covers every `consultant_procurement` discipline
(named profiles and generic fallbacks alike).

## Graceful shutdown and recovery

SIGTERM stops new claims and lets active lanes finish. Each active run renews a
lease every third of `WORKFLOW_WORKER_LEASE_SECONDS`. If a worker exits, another
worker reclaims the expired row with `FOR UPDATE SKIP LOCKED` and increments the
attempt. Retries use the frozen run brief rather than current project state.

Cancellation marks a running row cooperatively. Before publishing, the worker
locks and rechecks the run in the same transaction as the artefact. If cancelled,
that transaction rolls back, then the run becomes terminal `cancelled`.

## Rollback

1. Stop `sitewise-core-workflow-worker`; do not remove `workflow_runs`.
2. Deploy the prior API image. Additive synchronous routes remain available
   until the Stage 5 UI cutover gate is accepted.
3. Inspect queued/running rows. Running rows become reclaimable after lease
   expiry; either restore the new worker or cancel them through the API.
4. Downgrade `032_workflow_runs` only after all rows are terminal and their
   result references are archived. The migration drops only the Stage 5 table.
