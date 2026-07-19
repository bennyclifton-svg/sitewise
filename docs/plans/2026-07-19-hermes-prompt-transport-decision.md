# Hermes prompt transport decision — 2026-07-19

## Decision

Do not move the Clerk prompt to an interface that fails the no-prompt-content
logging gate. Keep the current Hermes invocation behavior for read-only turns
and block Hermes mutation tools by default with
`HERMES_MUTATIONS_ENABLED=false`.

## Evidence

The installed Hermes Agent reports version 0.17.0 (2026.6.19). Its supported
single-turn interfaces are:

- `hermes chat -q/--query QUERY`
- `hermes -z PROMPT` (the configured one-shot alternative)

Both take prompt text as a command-line argument. `hermes send --file -` and
stdin are message-delivery features that explicitly run no LLM or agent loop;
they are not valid transports for a Clerk agent turn.

The same installation also exposes `hermes acp`, a supported ACP JSON-RPC agent
server over stdin/stdout. On 2026-07-19, `hermes acp --check` passed and a direct
client completed `initialize` and `session/new`; `session/prompt` emitted ACP
session updates but did not return a terminal response within 180 seconds.

A minimized ACP probe established that the protocol client is not the cause:
the local `/help` command returned `stopReason=end_turn` in about four seconds.
A model-backed prompt then stalled before making a provider request. A timed
thread dump located the block in Hermes' coding workspace snapshot while
`agent.coding_context._git()` waited for
`git status --porcelain=2 --branch`. The same Git command completed in under
100 ms outside ACP. Bypassing only that upstream workspace probe made the ACP
model turn return `OK` with `stopReason=end_turn` in 6.91 seconds. The existing
Hermes one-shot path also returned `OK` in 9.61 seconds. This isolates the
terminal-smoke failure to Hermes ACP's workspace-probe subprocess path on this
Windows environment, not JSON-RPC framing, authentication, or model latency.

ACP is not currently acceptable for Clerk because Hermes logs
`Prompt on session ...` plus the first 100 prompt characters at INFO level to
stderr. `agent.turn_context` independently logs the message prefix as well. A
unique smoke marker was observed in both streams. The prompt was absent from the
spawned argv, but the stated packet gate requires absence from both argv and
logs.

## Consequences

- Packet 0.7B is blocked pending an ACP mode that does not log prompt content,
  a fix for the Windows ACP workspace-probe hang, and a successful terminal
  smoke turn with Clerk's MCP configuration.
- Packet 0.7C must not substitute `hermes send`, shell quoting, or another
  interface with different semantics. ACP integration is also blocked until the
  logging and terminal-smoke requirements pass.
- Pi continues to use a per-turn prompt file and deletes it on success, spawn
  failure, timeout, and cancellation.
- Enabling Hermes mutations is an explicit operational exception and must not
  occur until a non-argv smoke test proves prompt absence from process listings
  and logs on Windows and Linux.

An upstream issue was not created from this task because that is an external
write requiring maintainer coordination. When authorized, report the ACP prompt
logging behavior and record the issue URL here.

## Rollback

The safety change is rolled back by reverting the configuration/code change,
but doing so reopens the known prompt-exposure risk. The preferred operational
rollback is to leave Hermes mutations disabled and select Pi for supported
mutation turns.
