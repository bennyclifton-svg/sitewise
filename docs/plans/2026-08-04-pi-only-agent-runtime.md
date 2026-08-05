# Pi-only Agent Runtime

## Decision

As of 2026-08-04, Pi is Clerk's sole deployed agent runtime. This decision
supersedes the July Hermes plans only where they prescribe Hermes process,
configuration, model-selection, or deployment behaviour. The MCP bridge,
turn-token authorisation, SSE contract, workspace boundary, Tender Comparison
workflow, and legacy PydanticAI safety valve remain in place.

## Rationale

Clerk's agent should act only through an explicit, project-scoped domain tool
surface. Pi starts with `--no-builtin-tools`, receives a per-turn MCP configuration,
and exposes a deliberately allowlisted set of Clerk tools. It receives the
same bounded project context as the former runtime without Hermes' default
toolsets or dual-runtime routing logic.

## Runtime contract

- Pin `@earendil-works/pi-coding-agent` to `0.83.0` and `pi-mcp-adapter` to
  `2.19.0` in the backend image.
- Invoke Pi once per turn with `--no-builtin-tools`, `--no-session`, JSON streaming,
  an explicit `.pi/mcp.json`, the bundled MCP adapter as its only discovered
  extension, and a prompt file rather than prompt argv text.
- Configure the MCP endpoint with the short-lived `CLERK_MCP_TOKEN` only.
- Preserve the `agent_turns` capability row and enforce mutation scopes at the
  MCP tool boundary.
- Retain the Tender Comparison tools in Pi's direct allowlist:
  list/get/status/result, start/prepare, candidate discovery, and quote
  selection management.

## Acceptance gate

Before production deployment, prove all of the following with Pi:

1. A streamed project-evidence answer calls the authorised MCP read tools.
2. "Compare the selected tenders" starts and completes Tender Comparison, then
   returns the comparison report artefact.
3. A profile update and a workflow mutation both respect scoped turn authority.
4. Cancellation stops the Pi subprocess and revokes the turn.
5. The backend image builds and `pi --version` runs as the unprivileged
   `sitewise` user.
6. Backend tests, Ruff, frontend tests, TypeScript build, and deployment
   validation are green.

The live `sitewise.au` production acceptance remains a separate gate; it does
not authorise removal of the legacy PydanticAI chat path.
