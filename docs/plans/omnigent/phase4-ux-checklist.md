# Phase 4 UX Checklist

Date: 2026-07-03

Status: green.

## Automated Gate

- [x] `pnpm test` passed: 7 files, 16 tests.
- [x] `pnpm lint` passed with no errors. The remaining warning is the existing
  `TenderMatrix.tsx` TanStack Virtual React Compiler warning.
- [x] `pnpm build` passed.
- [x] Backend delete endpoint covered by focused chat API tests.

## UX Coverage

- [x] Token streaming remains on the existing AI-SDK chat path, with the
  additive Hermes agent path selected for project-scoped threads.
- [x] Tool status events render as structured collapsible chips with
  running, done, and error states.
- [x] Stop calls the AI-SDK client `stop()` and
  `POST /chat/agent/{thread_id}/cancel`.
- [x] Project sessions can be resumed, created, renamed inline, and deleted
  after an explicit confirmation step.
- [x] Artefact events render in-chat cards and tender report artefacts link to
  the tender report route when a comparison id is present.
- [x] Error copy is readable for rate limits, tool failures, partial pipeline
  failures, auth, access, grounding, retrieval, network, and generic errors.

## Notes

- Tool and artefact UI uses structured AI-SDK data parts, not assistant text.
- Session list state is backed by TanStack Query cache updates and invalidation
  patterns already present in the app.
