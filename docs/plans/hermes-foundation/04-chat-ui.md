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

