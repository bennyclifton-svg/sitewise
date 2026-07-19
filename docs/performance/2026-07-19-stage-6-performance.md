# Stage 6 performance implementation record

Date: 2026-07-19
Environment: canonical Windows development host from `environment.md`
Base: Stage 5 commit `a0ceeb66`

## Implemented results

| Packet | Result | Comparison / pressure / rollback |
| --- | --- | --- |
| 5.1 | Production build enforces an authenticated-cockpit budget of 250 KiB gzip and a 150 KiB workflow-entry budget. Cockpit: **246,609 bytes gzip**. Tender entry: **23,494 bytes gzip**. | Stage 0 entry was 460,568 bytes gzip. Three.js is confined to `StyleGenomeDemoPage` (553,560 raw / 142,730 gzip) and is absent from cockpit/Tender static imports. Rollback: revert lazy imports, manifest output, and the budget script together. |
| 5.2A | Project shell and bounded active chat bootstrap are independent concurrent GETs. Both publish ETags; neither creates users/catalogues/threads. New projects create their initial thread during POST lifecycle creation. | Critical warm path is two calls. Pane failures remain independent. Canonical remote p95 remains a deployment gate. Rollback: restore the former sequential thread lookup; no schema change. |
| 5.2B | Thread and Tender comparison HTTP consumers use additive keyset pages of 50; legacy internal/MCP list services remain available. | Keyset order is `(updated_at, id)` so concurrent inserts do not shift later pages. Evidence/workspace pagination remains additive follow-up work before unbounded legacy shapes can be removed. |
| 5.3A | Chat display reads at most 100 rows and agent prompt history at most 12 rows. Both bounds execute in SQL before chronological reversal. MCP project-file query, prefix, and limit filters execute in SQL. | Avoids loading full histories/project trees. Rollback: revert repository query signatures and MCP adapter together. |
| 5.3B | Model/runtime selectors share one five-minute TanStack configuration key and one `/config/agent` request. The project-agent cross-project toggle was removed. | One browser request per cache window; project tokens make no cross-project promise. |
| 5.3C | Supabase auth uses one lifespan-owned async HTTP client (50 connections, 20 keepalive; explicit connect/read/write/pool timeouts). | Logs distinguish `cold` from `warm_cache`; shutdown closes the client. Auth payload/status behavior is unchanged. |
| 5.4A | Neighbours for all fused hits are fetched by one tenant-filtered query. | Database query count changes from `2 + result_limit` to **3**, so the default limit of 10 changes 12 queries to 3 (75% reduction). Golden equivalence and isolation tests pass; canonical remote p95 remains open. |
| 5.5A | Browser batch analysis/ingest uses two workers; failures settle independently; evidence/tree/activity refresh occurs once after the batch. | Pressure is capped at two heavy ingests. Rollback: set concurrency to one and retain the single batch refresh. |
| 5.5B | One project-scoped batch endpoint prevalidates every ID before deletion, preserves retention-locked inputs as per-item failures, and returns deleted/failed IDs. The UI removes optimistically and restores failures. | Cross-project/unknown IDs fail before any delete. Storage cleanup remains out of band. Rollback: return to the existing single-delete mutation. |
| 5.6A | Comparison/list/progress/matrix/QA/report keys are comparison-scoped. Active visible progress uses non-overlapping 1.5 s TanStack polling, pauses hidden, and backs off on errors. | Cached tabs use the shared cache; visible progress staleness is bounded below 2 s after a successful poll. |
| 5.6B | Single QA acceptance removes the item before the request, restores it on failure, prefetches the next evidence image, and does not reload the queue. | Optimistic response is synchronous in the browser. Canonical settled HTTP p95 remains a deployment gate. |

## 5.4B semantic/lexical concurrency decision

Decision: **retain sequential execution in production**.

The current path performs one semantic and one lexical index query on one checked-out
session, then deterministic reciprocal-rank fusion. A composed SQL path couples two
independently tuned result shapes and makes the Python golden-result contract harder to
inspect. Concurrent execution requires two checked-out connections per retrieval and
there is no canonical fixture result demonstrating that the added pool pressure improves
end-to-end p95 after embedding time. Therefore Stage 6 does not speculate. Query-count,
result-equivalence, isolation, and pressure evidence select the current sequential path;
there is no implementation follow-up packet.

## 5.7 Hermes session decision and 5.8 implementation

Decision: **do not reuse Hermes processes/sessions; remove the unused mapping**.

Hermes 0.17.0 has no Clerk-integrated session-id capture or verified resume contract.
The Stage 0 probes measured successful isolated turns at 6.91 s (workspace probe bypass)
and 9.61 s (one-shot), while ACP remains blocked by the Windows workspace probe and
prompt-prefix logging. Consequently there is no measured resumed TTFT improvement, let
alone the required 20%, and no concurrency/history/tenancy proof for reuse. Keeping an
unused nullable column would imply a capability the runtime does not provide.

The exact 5.8 branch is implemented by migration
`033_remove_unused_hermes_session`: remove `chat_threads.hermes_session_id` from the
model, API contract, and frontend type. Downgrade restores the nullable column. Per-turn
process isolation, cancellation, history bounding, and project authorization remain
unchanged.

## Open measured gates

- Warm remote cockpit bootstrap p95 <=500 ms.
- Retrieval p50/p95 before/after on the canonical populated database fixture.
- Settled QA response p95 <=800 ms.
- Browser cached-transition screenshots/timing and real deployment rollback.

These require the deployed/canonical data path and are not inferred from local unit-test
duration. They remain unchecked in the programme exit record.

## Local validation

- Backend: `uv run pytest -q` — **1,164 passed, 6 skipped, 22 deselected**.
- Backend lint: `uv run ruff check .` — **all checks passed**.
- Database: disposable PostgreSQL 16 `upgrade head -> downgrade 032_workflow_runs -> upgrade head` — **passed**, current revision `033_remove_unused_hermes_session`.
- Frontend: `pnpm test -- --run` — **31 files / 113 tests passed**.
- Frontend lint: `pnpm lint` — **0 errors** (one pre-existing TanStack Virtual compatibility warning).
- Frontend production build: `pnpm build` — **passed**, including the enforced bundle budgets recorded above.
