# Phase 4: Chat UI

## Objective

Extend the existing AI-SDK chat UI with tool chips, stop/cancel, per-project
session management, and artefact cards. Do not replace the chat stack and do not
add Zustand.

## Implementation Changes

- Add Vitest, Testing Library, jest-dom, and jsdom to the frontend using pnpm.
- Add a trivial render test proving the harness.
- Add `ToolCallChip` and store tool status in component state keyed by message
  id. Do not fake tool chips as AI-SDK message text parts.
- Wire a Stop button to both the AI-SDK `stop()` function and
  `POST /chat/agent/{thread_id}/cancel`.
- Add a project/session list panel backed by existing thread list/create/update
  APIs.
- Add a backend `DELETE /chat/threads/{thread_id}` endpoint if still absent,
  with owner checks and cascade through existing message relationships.
- Add `ArtefactCard` for `data-clerk-status` artefact events. For tender
  comparison reports, link to the existing tender/report or draft route using
  the `draft_id` produced by `tender_reports`.

## Visual Style

Reference Omnigent only for structural/interaction patterns: chip layout,
spacing rhythm, streaming/typing motion, and information density. Do not
adopt Omnigent's color palette. Render every color through Sitewise's
existing design tokens in `frontend/src/index.css` (the pine/gray/ochre/
clay/azure semantic variables already wired through shadcn) so the new chat
surfaces read as native Sitewise, not a re-skin.

## Event Shapes

Tool status events:

```json
{
  "type": "data-clerk-status",
  "data": {
    "kind": "tool",
    "tool": "start_tender_comparison",
    "state": "running",
    "message": "Starting tender comparison"
  }
}
```

Long-running tool calls must never sit at a bare `running` state with no
further signal. When a tool has stage/progress data available (for example
`get_comparison_status`), the `done` event carries it as flat fields so the
chip can render advancing progress instead of a dead spinner:

```json
{
  "type": "data-clerk-status",
  "data": {
    "kind": "tool",
    "tool": "get_comparison_status",
    "state": "done",
    "message": "Checked comparison progress",
    "stage": "qa",
    "percent": 42.9,
    "doneUnits": 6,
    "totalUnits": 14
  }
}
```

Artefact events:

```json
{
  "type": "data-clerk-status",
  "data": {
    "kind": "artefact",
    "workflowType": "tender_report",
    "draftId": "...",
    "comparisonId": "...",
    "title": "Tender comparison report"
  }
}
```

## Tests

- Tool chip renders running, done, and error states.
- Stop button appears only while the chat is busy and calls both client stop and
  backend cancel.
- Session list can resume, rename, and delete a thread.
- Artefact card renders title and target link from the event payload.
- Existing citation/source rendering still works.

## Gate

- `pnpm test`, `pnpm lint`, and `pnpm build` pass.
- Manual UX checklist covers streaming, chips, stop, resume/rename/delete,
  artefact navigation, and error states.

## Gate Result - 2026-07-03

Status: green.

- `pnpm test`: passed, 7 files / 16 tests.
- `pnpm lint`: passed with the pre-existing `TenderMatrix.tsx`
  TanStack Virtual compiler warning and no errors.
- `pnpm build`: passed.
- Backend chat delete touchpoint is covered by `tests/test_chat_api.py`.
- Manual UX checklist recorded in
  `docs/plans/omnigent/phase4-ux-checklist.md`.

Implementation note: tool and artefact cards are derived from structured
AI-SDK message data parts keyed by message id at render time. This keeps them
out of text parts while avoiding React compiler warnings from mirroring message
parts into state synchronously.

## Addendum - 2026-07-03: stage-progress chips

Closed a gap found after the Phase 4 gate went green: `get_comparison_status`
already computed `stage`/`done_units`/`total_units`/`percent` on the backend
(`backend/app/mcp_bridge/server.py`'s `_progress_payload`), but the status-bus
publish call dropped those fields before they reached the SSE stream, so the
chip only ever showed a flat running/done/error state with no progress
detail. Fixed test-first:

- `_tool_status` (`server.py`) now yields a mutable `extra` dict that a tool
  can populate before its `done` event publishes; `get_comparison_status`
  fills it from the progress payload.
- `ToolStatusEvent` (`frontend/src/lib/chat-events.ts`) and `toolStatusFromPart`
  carry optional `stage`/`percent`/`doneUnits`/`totalUnits` fields.
- `ToolCallChip` renders a `NN%` badge in the chip when `percent` is present,
  and the stage name in the expanded detail panel.

Verified: `uv run pytest tests/mcp_bridge -q` (29 passed), full backend suite
(655 passed, 7 skipped), `pnpm test` (21 passed across 8 files), `pnpm lint`
and `ruff check` both clean (only the pre-existing `TenderMatrix.tsx`
TanStack Virtual warning).
