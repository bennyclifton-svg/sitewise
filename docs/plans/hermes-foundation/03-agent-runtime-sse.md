# Phase 3: Agent Runtime And SSE

## Objective

Add `backend/app/agent/` so a Clerk chat turn can invoke headless Hermes,
stream AI-SDK-compatible SSE through a new sibling endpoint, persist messages,
and cancel in-flight turns. The existing `/chat/stream` path remains live.

## Preconditions

- [Phase 2 gate](./01-phase-2-gate.md) is green.
- Hermes headless invocation details from
  `docs/plans/omnigent/hermes-headless-probe.md` are still valid on Linux/WSL2.
- The existing frontend SSE vocabulary remains unchanged:
  `start`, `text-start`, `text-delta`, `text-end`, `data-clerk-status`,
  `source-document`, `finish`, `[DONE]`.

## Implementation Changes

- Add settings in `backend/app/config.py`: agent runtime flag, Hermes binary,
  invocation mode, platform API key, MCP URL, max concurrency, turn timeout, and
  workspace root.
- Add `backend/app/agent/hermes_process.py` with an injectable async subprocess
  wrapper. Secrets go into child-process env only, never argv.
- Add `backend/app/agent/sse_relay.py` that reuses the existing SSE helpers from
  `app/chat/streaming.py`; do not re-frame SSE by hand.
- Add `backend/app/agent/concurrency.py` for a process-local semaphore and
  cancel registry keyed by thread or turn id.
- Add a `hermes_session_id` nullable column on `chat_threads`.
- Add `POST /chat/agent/stream` and `POST /chat/agent/{thread_id}/cancel`.
- Persist the user message before spawning Hermes. Persist the assistant
  message only after a successful finish. On cancel, do not create a partial
  assistant message; record cancellation in logs/status metadata only.

## Tool Progress Decision

Do not scrape Hermes console output for tool progress. Live tool status comes
from Clerk's tool layer:

- Mint each agent turn with a `turn_id`.
- Include `turn_id` in the turn token claims.
- Add an in-process `AgentTurnStatusBus` keyed by `turn_id`.
- The agent endpoint multiplexes Hermes text chunks with status-bus events.
- MCP tools publish `running`, `done`, and `error` status events to the bus when
  they start and finish user-visible work.

This is acceptable for the MVP because the Dokploy target is a single API
container. If the backend later runs multiple replicas, move the bus to Postgres
or another shared transport.

## Tests

- Hermes wrapper yields chunks in order with a fake subprocess.
- Wrapper env contains platform key and bearer token, and argv does not.
- ANSI/Rich chrome stripping is covered.
- Non-zero exit raises a typed turn error with stderr tail.
- Timeout kills the child and raises a typed timeout.
- SSE relay emits ordered AI-SDK events and always ends with `[DONE]`.
- Status-bus tool events interleave as `data-clerk-status`.
- Cancel endpoint cancels the registered task and releases the semaphore.
- Endpoint tests cover 401, 403, 402, happy stream persistence, and cancel.

## Gate

- Backend tests and ruff pass.
- A real Hermes turn streams through `POST /chat/agent/stream`.
- The turn calls one MCP tool successfully.
- The unchanged chat UI can render the streamed text.

## Gate Result

Status: **GREEN** on 2026-07-03.

- `uv run pytest tests -q`: 639 passed, 7 skipped, 4 warnings.
- `uv run ruff check .`: all checks passed.
- Manual smoke ran a temporary localhost FastAPI server with
  `AGENT_RUNTIME_ENABLED=true`, `AGENT_TURN_TOKEN_SECRET` set, and Hermes
  platform-key routing through `openai-api / gpt-5.1`.
- `POST /chat/agent/stream` returned `start`, `text-start`,
  `data-clerk-status`, `text-delta`, `text-end`, `finish`, and `[DONE]`.
- Hermes called Clerk MCP `list_tender_comparisons` for project
  `6ba20b0a-f469-427a-853c-00f549572b03`; the status bus emitted `running`
  and `done`, and the assistant streamed: "The call returned 0 tender
  comparisons."
