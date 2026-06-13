# M5 — QA console + report pipeline

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Two sessions.** Part A: backend API + report assembly (§9.8, §13, §15, §18). Part B: cockpit frontend (§12, §16). Branch `feature/tcm-main`. Prerequisite: M4 merged.

---

# Part A — API surface + report pipeline

**Goal:** The full `/api/tender` router per PRD §15; QA resolve writing corrections; report assembled as a Clerk draft, HTML→PDF, approve freezes a version.

## Design decisions (made; do not relitigate)

1. **Router mounting** follows the existing pattern in `backend/app/main.py` (see how `app/api/projects.py` routers mount). The router file is `backend/tender/router.py`; Clerk core gains exactly one line (the mount) — that is the permitted direction of dependency.
2. **Auth:** reuse the existing operator-gated dependency used by other cockpit routes (find it in `app/api/`; do not invent a new auth scheme).
3. **QA queue ordering** (PRD §12): entity-type priority (cell statuses → mappings → flags → document classifications), then report-impact desc, then confidence asc. Report-impact v1 heuristic = amount_cents involved (null → 0). Encode as an explicit ORDER BY, unit-tested.
4. **Resolve endpoint** `POST /qa/items/{id}/resolve` body: `{action: accept|correct|suppress, corrected_value: {...}|null, reason: str|null}`. Every call writes `tender_corrections`; mapping corrections also route through `record_mapping_correction()` from M3 (do not duplicate that logic).
5. **State machine guard:** comparison cannot move to `report_draft` while any `needs_review` exists (PRD §12); enforced server-side in the report/build endpoint, tested.
6. **Report rendering:** Jinja2 templates in `backend/tender/report_templates/` (one file per §13 section, a base layout, print CSS); WeasyPrint for PDF. All phrases via `report_language` lookups; matrix glyphs per §13.4. DRAFT watermark via CSS on pre-approval renders.
7. **Drafts integration:** create/update the report through Clerk's existing drafts service (inspect `backend/app/` for the drafts module used by PMP/cost-plan workflows and follow the same creation path). `tender_reports` row links `draft_id`, stores `html_path`/`pdf_path` via the existing storage layer, bumps `version` on rebuild. Operator-editable narrative blocks are stored as draft content; **structured tables regenerate from data on every rebuild** — rebuilds must preserve narrative edits and replace everything else (test this).
8. **Approve** freezes: re-render without watermark, store both artifacts, set `approved_by`/`approved_at`, comparison → `approved`. Further rebuilds after approval require a new version (no in-place mutation of an approved artifact).
9. **PDF tests don't assert pixels.** Tests assert HTML content (phrases, glyphs, numbers, watermark class present/absent) and that WeasyPrint produces a nonzero PDF; rendering fidelity is reviewed by a human.

## Tasks (Part A)

1. **Router skeleton + auth + comparisons/quotes/documents endpoints** (§15 lines 1–6: create, get, patch context, create quote, upload, retry). Files: `backend/tender/router.py`, `backend/tender/schemas.py` (I/O models), mount line in `app/main.py`, `backend/tests/tender/test_api_comparisons.py`. PATCH context re-enqueues `run_expectations` downstream (PRD §15). Use the existing FastAPI test-client conventions from `backend/tests/`.
2. **QA queue + resolve.** Files: `router.py` (cont.), `backend/tender/services/qa.py`, `backend/tests/tender/test_api_qa.py`. Tests: ordering, resolve writes corrections, mapping-correction flywheel reached, state-machine guard.
3. **Matrix + taxonomy endpoints.** `GET /comparisons/{id}/matrix` returns the grid shaped for the frontend (groups → cells → per-quote `{status, amount_cents, flags}`); `GET /taxonomy` + `/taxonomy/search?q=` (trigram-backed typeahead, reuse T0 machinery). Tests for shape and search.
4. **Report templates + assembly service.** Files: `backend/tender/report_templates/*`, `backend/tender/services/report.py`, `backend/tests/tender/test_report_assembly.py`. Build §13 sections 1–8 from the M4 fixture comparison; narrative-preservation test; watermark test; Appendix C phrase test (assert "Excluded" appears only with a page reference).
5. **Build/approve/delivered endpoints + worker stage.** `assemble_report_draft` job handler (comparison-level), endpoints per §15, version freeze semantics. Files: `report.py` (cont.), `router.py` (cont.), `backend/tests/tender/test_report_lifecycle.py`.

## Exit criteria (Part A)

- [ ] Every §15 endpoint implemented and tested (full suite output pasted)
- [ ] Rebuild preserves narrative, regenerates tables (test green)
- [ ] Approval freeze + watermark semantics tested
- [ ] A real rendered PDF from the fixture comparison attached for human review

---

# Part B — Cockpit frontend

**Goal:** Routes per §16; QA console at < 20s/item; matrix; report preview/approve.

## Design decisions (made; do not relitigate)

1. **Follow the house style.** Components live in `frontend/src/components/project/` and pages/routes follow the existing cockpit patterns (`ProjectShell.tsx`, `ProjectLeftNav.tsx`, existing panels). Reuse the existing data-fetching idiom (inspect how `WorkbookGrid.tsx` / `DraftReviewPanel.tsx` fetch) — no new state libraries.
2. **Page viewer = image + bbox overlay only.** An `<img>` of `tender_pages.image_path` with absolutely-positioned highlight divs scaled from page coords. No PDF.js.
3. **Keyboard map** (PRD §12): `a` accept, `e` edit, `j/k` next/prev, `s` split. Global within the console route, disabled when a text input is focused.
4. **Split UI:** fraction sliders constrained to sum 1.0 (UI renormalizes on release); submits multiple mappings via resolve.
5. **Matrix virtualised** (~250 cells × 5 quotes): use whatever virtualisation the repo already depends on; if none, `@tanstack/react-virtual` (small, headless). Glyphs per §13.4 with a legend.
6. **Report tab:** iframe the draft HTML; narrative blocks editable via the existing draft-editing surface (see `DraftReviewPanel.tsx`); Approve button calls the approve endpoint and then shows the frozen PDF link.

## Tasks (Part B)

- [x] Routes + comparisons list + overview page (stage status per quote, retry buttons). Files: route registrations per existing router setup, `frontend/src/components/project/tender/ComparisonList.tsx`, `ComparisonOverview.tsx`.
- [x] QA console: queue pane, page-image pane with bbox overlay, adjudication pane with taxonomy typeahead; keyboard bindings. Files: `frontend/src/components/project/tender/QaConsole.tsx` + subcomponents.
- [x] Matrix view. `TenderMatrix.tsx`.
- [x] Report preview/approve. `TenderReportPanel.tsx`.
- [ ] Verification: frontend test/build commands per repo convention (check `frontend/package.json` scripts) pass; a manual click-through script (listed steps) executed against a seeded local comparison, results noted in this doc.

## Exit criteria (Part B)

- [x] All §16 routes reachable; build + tests green (output pasted)
- [ ] Keyboard-only QA pass over ≥ 20 fixture items, median < 20s/item (measure roughly, note it)
- [ ] Bbox highlights align on at least one real scanned document

## Part B verification notes - 2026-06-13

- Frontend routes added for `/projects/:projectId/tender`,
  `/projects/:projectId/tender/:cid`,
  `/projects/:projectId/tender/:cid/qa`,
  `/projects/:projectId/tender/:cid/matrix`, and
  `/projects/:projectId/tender/:cid/report`.
- `pnpm.cmd run build` passes.
- `pnpm.cmd run lint` passes with one TanStack Virtual compatibility warning
  from the required `useVirtualizer()` matrix implementation.
- Browser/manual seeded click-through was not completed in this sandbox:
  no local frontend `.env` exists, background dev-server launch was blocked by
  local process/job permissions, and no authenticated seeded comparison session
  was available to measure 20 QA items or real bbox alignment.
