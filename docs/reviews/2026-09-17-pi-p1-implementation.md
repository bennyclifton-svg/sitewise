# Pi P1 implementation — 17 September 2026

Implements the two P1 recommendations from the Pi/MCP lifecycle review.

## Execution and recovery

`app/agent/turn_supervisor.py` owns a task for each accepted turn. The HTTP
response reads the Postgres journal rather than owning the Pi iterator. Browser
disconnect, navigation and reconnect therefore do not cancel Pi. Explicit Stop
commits capability revocation before cancelling the supervised task. A late Stop
does not overwrite an already completed turn.

`agent_turn_events` stores the existing AI SDK SSE frames with per-turn sequence
numbers. A bounded producer/writer queue batches journal commits; readers only see
committed frames. SSE comments keep idle readers alive. The journal recognizes
only the standalone `[DONE]` frame as terminal, never that string inside model
text. Reading a terminal row committed between queries cannot prematurely close
the stream. Iterator closure explicitly propagates through relay and Pi cleanup.

Authenticated endpoints:

- `GET /chat/agent/{thread_id}/stream`: attach to the current active turn, or 204.
- Same endpoint with `turn_id=<uuid>&after=<sequence>`: replay that owned turn
  after the cursor. Events carry SSE `id` values. It never invokes Pi.
- Reposting the same user-message ID and content reattaches to its turn instead
  of charging or executing it again. A different payload under that ID is rejected.
- A second message cannot bypass an active thread reservation while the first
  turn is still queued.

The React client uses the existing AI SDK `resumeStream` API and a GET transport.
It clears only the interrupted assistant fragment before replaying from sequence
zero, so replay does not duplicate text. Reconnect backs off and stops after an
explicit Stop. Saved completion is reloaded when the durable turn settles.

On API startup, reconciliation revokes unfinished capabilities, preserves saved
mutations, repairs incomplete terminal streams, and saves an interruption message
when necessary. If the answer committed before the final stream event, recovery
reconstructs its missing text and terminal events. It does **not** rerun a tool or
restart the original prompt. Exactly which mutations committed may be uncertain
after a crash; automatic replay would risk applying them twice.

The supervisor remains inside the existing single API process. Keep one API
process/replica and stop the old process before starting its replacement. This
change does not introduce distributed worker ownership or promise continued
generation through host/process failure. Durable replay and conservative restart
reconciliation are the recovery contract.

## Common MCP tracing

FastMCP middleware covers the registered tool surface. A verified project/turn
token supplies correlation, while each tool retains its existing ownership and
mutation-scope checks. Every correlated invocation gets a separate call ID, including
repeated calls to the same tool. `agent_tool_calls` stores tool, turn, outcome,
duration, exception class, provider spans and commit receipts. Initial trace
persistence happens before invoking the tool. A trace-finalization error after a
tool commits is logged without converting the tool's success into a retry.

SQLAlchemy transaction hooks record ORM identities/revisions after flush and
persist receipts in the **same transaction** as the write. Rollback removes the
receipt with the mutation. Bulk ORM DML is recorded as a committed table operation
without inventing a row revision. Receipts contain identifiers and revision
numbers, not project text. Raw SQL outside ORM instrumentation and external storage
publication are not represented as row-revision receipts.

Brave/Tavily searches, web fetches and embedding calls record bounded metadata
spans. Pi model messages log turn/provider/model, message-stream duration and
terminal reason. Model duration measures Pi's message-start/end events, not an
independently measured provider HTTP round trip. Background workflow tracing remains
with the existing workflow infrastructure.

The saved source trace now reads the durable call records, with status events
adding document/source metadata. It no longer relies on selected UI status events
or deduplicating tool names to count calls. The UI groups activity by call ID.

`GET /chat/agent/{thread_id}/turns/{turn_id}/tools` exposes the safe diagnostic
fields only after thread/project/turn ownership checks. It does not expose tool
arguments, results, tokens, prompts or raw documents. Reconciliation marks orphaned
running traces interrupted without deleting any committed receipts.

## Migration and rollout

Apply Alembic migration `065_agent_replay` before starting the new API build:

```powershell
cd backend
uv run --frozen alembic upgrade head
```

It creates the event and tool-call tables, cascading from the durable turn, with
RLS enabled and no browser access policies. Replay text has the same sensitivity
as saved chat messages. Records follow their parent turn's retention; this change
does not add an independent timed-purge policy. No runtime dependency was added.

The existing disposable database runner now includes
`tests/database/test_agent_replay.py`. It tests a real mutation commit with a lost
tool response, rollback of a later write, durable receipts, repeat reconciliation,
cursor replay and rejection of subsequent writes under the revoked capability.
It checks the existing loopback/test-database marker before writing or cleaning up,
and cleans up only its generated fixture IDs.

## Verification

- Backend agent/MCP/procurement/research/quota plus migration/runner contracts:
  **490 passed, 4 skipped, 2 deselected**, including the final replay-race and
  late-Stop regressions. Pytest reports its existing AnyIO import-rewrite warning.
- Frontend chat/activity suite: 115 passed, including a real AI SDK test proving
  one POST, reconnect through GET, and no duplicate assistant text.
- Frontend TypeScript and full ESLint passed. Backend changed-file Ruff passed.
- Alembic generated the migration's PostgreSQL SQL successfully without a live
  connection.
- Live disposable PostgreSQL validation was attempted. The target guard passed,
  but Docker is unavailable on this machine, so the transactional integration test
  and live migration application remain for CI. No production migration or deploy
  was performed, and no live provider/customer mutation was used for testing.

Offline regressions exercise disconnect during read/search/write, cancellation,
journal failure stopping the producer, safe replay/auth/cursors, repeated calls,
provider errors, recovery without re-execution, and commit-before-finish. The
database integration gate remains necessary before production rollout.
