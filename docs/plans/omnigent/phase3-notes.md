# Phase 3 Notes: Hermes Runtime And SSE

Date: 2026-07-03

Phase 2 is green. This note records the Phase 3 Task 3.0 decisions before the
runtime implementation starts.

## Invocation Mode

Default mode is `chat_stream`.

Command shape for streamed turns:

```text
hermes chat -q "<prompt>" --source tool
```

`hermes chat -q` was proven in Phase 0 to line-stream through a non-TTY pipe.
It emits human-facing Rich chrome as well as answer text, so
`app/agent/hermes_process.py` strips ANSI escape sequences, query echoes,
box/border lines, initialization lines, and session summaries before yielding
text chunks to the SSE relay.

Fallback mode is `oneshot`.

Command shape:

```text
hermes -z "<prompt>"
```

This is final-only and clean. If streamed chrome stripping proves fragile in the
Phase 3 E2E gate, the endpoint can switch to `oneshot` and use synthetic
word-level streaming through the existing AI-SDK relay.

## MCP Token Injection

Each Clerk agent turn mints a short-lived Phase 2 turn token for the current
`(user_id, project_id)`.

The token is injected only into the Hermes child process environment:

```text
AGENT_TURN_TOKEN=<token>
CLERK_MCP_TOKEN=<token>
```

The runtime writes a temporary Hermes config for the child process that points
to `settings.agent_mcp_url` and references the token through the environment.
The token never appears in argv, logs, or prompts.

## Platform Key Injection

If `settings.agent_platform_api_key` is set, it is copied into the child
environment as `OPENAI_API_KEY`. Platform-key mode writes a per-turn Hermes
config with `model.provider = openai-api` and `model.default = gpt-5.1`, both
overridable through backend settings. This pair was verified in the Phase 3
manual smoke. The key is never passed in argv.

If no platform key is set, local OAuth/dev mode copies the active Hermes
`config.yaml`, `auth.json`, and `.env` into the per-turn temp home, strips any
existing `mcp_servers` block, and overlays the Clerk MCP server with the
per-turn authorization header. This keeps local OAuth providers working without
leaking the turn token into the user's global Hermes config.

## Session Mapping

Phase 3 reuses `chat_threads` and `chat_messages`.

`chat_threads.hermes_session_id` is added as a nullable column. The first
shipping path can run a fresh `chat -q` turn; later turns can pass
`--resume <hermes_session_id>` once the wrapper captures the session id from
Hermes stderr/stdout reliably.

## Status Events

Do not scrape Hermes tool-progress chrome. Tool progress comes from Clerk's own
tool layer. MCP tools publish status events to an in-process turn bus keyed by a
Phase 3 `turn_id`; the SSE endpoint multiplexes those events as
`data-clerk-status`.

This MVP assumes a single API container, matching the Dokploy target. If Clerk
later runs multiple API replicas, move the turn bus to Postgres or another
shared transport.
