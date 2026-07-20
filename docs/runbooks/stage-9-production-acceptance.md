# Stage 9 production acceptance and cutover

This runbook is an execution record, not permission to cut over. Do not delete
legacy paths until every prerequisite and live check below has dated evidence,
an approver, and a successful rollback rehearsal.

## Prerequisites

- Stage 0-8 tracker gates are green or have an approved not-applicable record.
- Stage 7 Tender golden corpus, evaluation thresholds, mandatory QA, and QS
  approval are green.
- The Stage 8 typed Cost Plan migration/import reconciliation and application
  rollback have been exercised.
- A production backup has a verified restore point and named operator.
- `docs/performance/environment.md` matches the deployed build and regions.

## Live acceptance record

Record timestamp, operator, deployed commit/build hash, raw command or request
evidence, duration, and result for each item:

1. Database migration/head, RLS, grants, backup, and restore visibility.
2. Supabase Storage upload/read/delete with two isolated owners using the same
   project slug and relative path.
3. Hermes and Pi turns through MCP/SSE, including cancellation and durable turn
   revocation; confirm zero surviving child processes.
4. API worker and Tender worker health, graceful shutdown, lease expiry,
   restart recovery, and idempotent result publication.
5. ODL and Stripe live-mode health without logging secrets or customer content.
6. All three role manifests under `docs/acceptance/role-scenarios/`, including
   exact resource revisions, provenance, routes, forbidden transitions, and
   required typed needs-input/unsupported outcomes.
7. The full profile to Project Plan to Cost Plan to Tender to proposed Cost
   revision journey. Confirm the Tender report is frozen and approved, the QS
   gate passed, the selected quote/package was explicit, and the new Cost Plan
   revision remains proposed.
8. Every Section 9 hard SLO using the canonical sample counts and raw timing
   reports; confirm the production frontend build hash and bundle manifest.

## Rollback rehearsal

1. Stop new workflow claims without cancelling already committed records.
2. Deploy the previous compatible application build. Do not downgrade an
   additive schema while either build may still write it.
3. Verify accepted artefact revisions, frozen Tender inputs, Cost Plan versions,
   workflow runs, events, exports, and idempotency keys reconcile exactly.
4. Resume the previous workers and prove queued/leased work is reclaimed once,
   with no duplicate versions or stale exports.
5. Restore the Stage 9 build and repeat reconciliation.
6. Record recovery time, discrepancies, operator, approver, and the exact backup
   restore procedure used or verified.

## Cutover decision

The approver must record an explicit go/no-go decision in the execution tracker.
Only a go decision after all checks pass permits small, individually revertible
Phase 8.5 deletion packets. Polar, legacy chat/orchestrator, repair paths, and
legacy runtime fields remain live until their own deletion packet is verified.
