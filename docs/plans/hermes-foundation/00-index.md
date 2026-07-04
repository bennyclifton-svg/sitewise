# Hermes Foundation Execution Shards

This directory shards the canonical Phase 3-8 overview into implementation
files that can be executed one gate at a time.

Canonical overview:
`docs/plans/2026-07-03-hermes-foundation-phases-3-8.md`

Predecessor plan:
`docs/plans/2026-07-02-hermes-foundation-phases-0-2.md`

The July Hermes plans remain the source of truth when they conflict with older
cockpit, local-first, or Practice Intelligence docs.

## Execution Order

Do not start a phase until the previous gate is green.

1. [Phase 2 gate](./01-phase-2-gate.md)
2. [Phase 3: agent runtime and SSE](./03-agent-runtime-sse.md)
3. [Phase 4: chat UI](./04-chat-ui.md)
4. [Phase 5: TCM flagship](./05-tcm-flagship.md)
5. [Phase 6: workspaces and artefacts](./06-workspaces-artefacts.md)
6. [Phase 7: Stripe and usage](./07-stripe-usage.md)
7. [Phase 8: deploy and cutover](./08-deploy-cutover.md)

## Global Rules

- Keep the existing `/chat/stream` legacy path until Phase 8.5.
- Add the Hermes runtime as an additive sibling path first.
- Preserve the AI-SDK SSE vocabulary already consumed by the frontend.
- Keep TCM in `backend/tender/`; Clerk core may only touch it through the
  existing router mount and MCP adapters.
- Use Supabase Storage as canonical source-document storage. Hermes gets only a
  scoped scratch/artefact filesystem.
- Reuse `require_active_entitlement(session, user)` as the single billing gate.
- Security and contract seams are test-first: MCP authz, SSE contract,
  traversal-safe paths, webhook signatures, cancellation, and quota blocking.

## Current Preflight Status

Phase 2 is green as of 2026-07-03. The MCP bridge is mounted at `/mcp`, all
four Phase 2 tools are covered, per-project turn-token authorization is proven,
and the WSL Hermes smoke successfully called a read tool through the mounted
endpoint.

Phase 3 is green as of 2026-07-03. The additive `/chat/agent/stream` endpoint
streams AI-SDK-compatible events from a real Hermes process, multiplexes Clerk
MCP tool status, persists successful turns, and supports cancellation. Phase 4
is complete.

Phase 4 is green as of 2026-07-03. The AI-SDK chat UI now has structured tool
chips, backend-backed stop/cancel, a per-project session list with
resume/rename/delete/create, artefact cards, frontend tests, and readable
agent-workflow error states. Phase 5 may begin.

Phase 5 is green as of 2026-07-04. The worker, MCP tools, report artefact
emission, timing ledger, WSL JVM speed gate, and scripted WSL chat acceptance
run are implemented and verified. A real Hermes turn started the TCM comparison,
the worker completed the pipeline through report assembly, and a second Hermes
turn retrieved the tender report artefact. Phase 6 may begin.

Phase 6 is green as of 2026-07-04. Hermes now uses the project-scoped scratch
root, traversal-safe MCP workspace tools are implemented, uploaded source
documents remain read-only, in-app draft edits create new `draft_artifacts`
versions, and the agent can read or version the latest editable artefact through
workspace paths. Phase 7 may begin.

Phase 7 is green as of 2026-07-04. Stripe-backed checkout, portal, webhook
sync, entitlement branching, quota checks, and billing UI are covered by local
tests and migration verification. A real Stripe test-mode Checkout created a
subscription, the webhook flipped entitlement active, Customer Portal
cancellation sent subscription update webhooks, and the canceled subscription
blocked subscribed-only actions with 402. Phase 8 may begin.
