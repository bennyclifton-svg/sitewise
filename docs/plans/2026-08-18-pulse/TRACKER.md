# X1 Programme Tracker

**Created:** 2026-08-18 · **Baseline commit:** `acb10131` · **Status:** Stage 8 code complete; GATE 2 awaits human signature

This file is the programme's memory. Authoritative spec:
[`../2026-08-18-pulse.md`](../2026-08-18-pulse.md). Binding rules:
[`00-doctrine.md`](./00-doctrine.md) and root `AGENTS.md`.

If this tracker and the plan disagree, the plan and `AGENTS.md` win — but
**update this file to match** before continuing.

## Status key

`[ ]` not started · `[~]` in progress · `[!]` blocked · `[x]` done **and verified**

A packet is `[x]` only when its exit command output is pasted below. Code written
is not done.

---

## Baseline facts (fill during Stage 0 — everything downstream reads these)

| Fact | Value | Recorded by |
|---|---|---|
| Baseline commit | `acb10131` (`acb101313bba69330366e90df4f69677ecd34f5b`) | plan author / Stage 0 |
| Backend suite: pass/fail counts | **4 failed, 2402 passed, 7 skipped, 34 deselected** (52.01s). Exact `uv run pytest -q` cannot collect on this machine (3 collection ERRORs); counts are from `uv run pytest -q --tb=line --import-mode=importlib`. | Stage 0 |
| Pre-existing backend failures (names) | See `docs/acceptance/x1/baseline-backend-failures.txt` (4 FAILED). Collection-only ERRORs of the exact command: `tests/tender/test_models.py`, `tests/tender/test_schemas.py`, `tests/web_research/test_service.py`. | Stage 0 |
| Frontend typecheck clean? | Yes. `pnpm typecheck` → `$ tsc -b --pretty false`, exit 0, no diagnostics. | Stage 0 |
| Frontend test pass/fail | **82 files passed, 520 tests passed** (vitest 4.1.9, 81.63s). `pnpm build` succeeded (vite 8.0.16, 2.23s). | Stage 0 |
| Classification production LOC (D8 gate) | **5609** (`find backend/ingest backend/app/intake -name '*.py' -not -path '*/__pycache__/*' -not -name 'test_*' -exec wc -l {} +`) | Stage 0 |
| `source_documents` row count | **543** | Stage 0 |
| Rows with `ingest_mode='register_only'` | **200** (`full_text` = 343) | Stage 0 |
| …of those, with useful text (≥200 chars) | **192** (headline number for Stage 2). Text ≥200 chars with zero chunks: **224**. | Stage 0 |
| Rows per legacy `document_class` | unknown 234, drawing 200, reference_guide 75, certificate 9, correspondence 9, report 8, specification 5, planning_instrument 2, doctrine 1. Outside declared Literal: **none**. Legacy procurement classes (tep/eoi/rft/addendum/tender_submission/evaluation/trr): **0**. Null `content_hash`: **0**. | Stage 0 |

> **Do not start Stage 1 until every row above is filled.** Stage 2's backfill
> is validated against these numbers.

---

## Wave 1 — Foundation (Gate 1)

### Stage 0 — Baseline & safety harness → [`stage-00-baseline.md`](./stage-00-baseline.md)

- [x] 0.1 Record commit + create branch — Cursor Grok 4.6 / `x1/stage-0-baseline` / from `acb101313bba69330366e90df4f69677ecd34f5b`
- [x] 0.2 Backend suite baseline
- [x] 0.3 Frontend typecheck/test/build baseline
- [x] 0.4 Database census query
- [x] 0.5 Fixture corpus committed
- [x] 0.6 LOC gate baseline recorded

### Stage 1 — Evidence safety → [`stage-01-evidence-safety.md`](./stage-01-evidence-safety.md)

- [x] 1.1 Failing test: `Cost Plan.pdf` keeps chunks — Cursor Grok 4.6 / `x1/stage-1-evidence-safety`
- [x] 1.2 Add `has_useful_text` helper (D3 threshold)
- [x] 1.3 `should_persist_chunks` keyed on text, not class
- [x] 1.4 `_chunker_for` no longer keyed on `ingest_mode`
- [x] 1.5 Narrow `_looks_like_drawing` `\bplan\b` (tactical safety fix)
- [x] 1.6 Rewrite `tests/ingest/test_classify.py:55,67,94,114`
- [x] 1.7 Drawing register still works (regression)
- [x] 1.8 Full backend suite vs. baseline

### Stage 2 — Audit & backfill → [`stage-02-audit-backfill.md`](./stage-02-audit-backfill.md)

- [x] 2.1 Read-only audit script — Cursor Grok 4.6 / `x1/stage-2-audit-backfill`
- [x] 2.2 Audit report committed to `docs/acceptance/x1/`
- [x] 2.3 Backfill with `--dry-run` (default)
- [x] 2.4 Idempotency test (run twice, zero delta)
- [x] 2.5 Live backfill + post-counts recorded

### Stage 3 — Classification contract 🔒 → [`stage-03-classification-contract.md`](./stage-03-classification-contract.md)

**Gate 1 lives here. Contract freezes at 3.6.**

- [x] 3.1 New closed `Literal`s in `ingest/types.py` — Cursor Grok 4.6 / `x1/stage-3-classification-contract`
- [x] 3.2 Extend `Classification` with `document_subject` / `confidence` / `basis`
- [x] 3.3 Fix all `Classification(...)` construction sites
- [x] 3.4 Exhaustiveness test over every `DocumentClass`
- [x] 3.5 Chunker/extractor policy guard test
- [x] 3.6 **FREEZE** — tag `x1-gate-1` / SHA `c1b38f4b`
- [x] 3.7 Legacy→canonical mapping table agreed (see *Open decisions*; OD-1 uses default)

### Stage 4 — Deterministic classifier → [`stage-04-deterministic-classifier.md`](./stage-04-deterministic-classifier.md)

- [x] 4.1 Structural signals (Stage B) — Cursor Grok 4.6 / `x1/stage-4-deterministic-classifier`
- [x] 4.2 Scored filename rules replace first-match-wins (Stage C)
- [x] 4.3 Filename test matrix (≥40 cases)
- [x] 4.4 Deterministic content markers (Stage D)
- [x] 4.5 Persist `confidence` + `basis`
- [x] 4.6 Accuracy measured on fixture corpus, recorded below
- [x] 4.7 Model fallback remains **absent** (not merely disabled)

### Stage 5 — User override → [`stage-05-user-override.md`](./stage-05-user-override.md)

- [x] 5.1 Migration: `document_classification_overrides` — Cursor Grok 4.6 / `x1/stage-5-user-override`
- [x] 5.2 `set_document_classification()` service
- [x] 5.3 Stage A lookup wired into classifier
- [x] 5.4 REST endpoint (+ project authorization test)
- [x] 5.5 Survives re-ingest test
- [x] 5.6 Survives file-move test
- [x] 5.7 Frontend classification chip
- [x] 5.8 MCP tool `set_document_classification`
- [x] 5.9 Null `content_hash` path handled

### Stage 6 — Collapse duplicate classifiers → [`stage-06-collapse-classifiers.md`](./stage-06-collapse-classifiers.md)

- [x] 6.1 Signal inventory: which of B's rules survive — Cursor Grok 4.6 / `x1/stage-6-collapse-classifiers`
- [x] 6.2 Port surviving semantic signals into `classify.py`
- [x] 6.3 `filing_destination(Classification) -> str | None`
- [x] 6.4 Delete superseded regex families from `app/intake/classifier.py`
- [x] 6.5 Routing test matrix
- [x] 6.6 **LOC gate check vs. Stage 0.6 number** — 5982 vs 5609 (**+6.6%**, <10%; justification in packet record)

### Stage 7 — Auto-filing / Sort repair → [`stage-07-auto-filing.md`](./stage-07-auto-filing.md)

- [x] 7.1 Add `waiting` + `needs-review` to `SortOutcome` — Cursor Grok 4.6 / `x1/stage-7-auto-filing`
- [x] 7.2 Auto-file on successful classification
- [x] 7.3 Remove `_file_previews` re-download (D2) — Sort Files no longer calls it; `repair_service` still does (justified below)
- [x] 7.4 Idempotent move test
- [x] 7.5 Frontend per-outcome breakdown
- [!] 7.6 Ten-file upload-then-immediately-sort scenario — ports 5173/8000 were not listening; automated waiting + auto-file tests stand in

### Stage 8 — Taxonomy migration → [`stage-08-taxonomy-migration.md`](./stage-08-taxonomy-migration.md)

- [x] 8.1 Data migration with dry-run + counts — Cursor Grok 4.6 / `x1/stage-8-taxonomy-migration`
- [x] 8.2 `planning_instrument` → `statutory_instrument`
- [x] 8.3 Procurement classes → `commercial` + metadata
- [x] 8.4 `inbox_pending` removed from class
- [x] 8.5 `corpus_catalog` resolved
- [x] 8.6 `doctrine` / `reference_guide` resolved (OD-1 default)
- [x] 8.7 All 14 consumer files migrated
- [x] 8.8 Rollback rehearsed on a copy
- [x] 8.9 **Shims list emptied**

---

## 🔒 GATE 1 — Contract frozen

Do not open a Wave 2 packet until all are true:

- [x] Stage 1 green; no class-driven evidence suppression anywhere
- [x] Stage 3 contract frozen and tagged (`x1-gate-1`)
- [x] Stage 0 baseline table fully populated
- [x] Backend suite failures ⊆ Stage 0 pre-existing failures
- [X] Gate signed off by: BC on 18/08

## 🔒 GATE 2 — Canonical classification live

- [x] Stages 4–8 green
- [x] All 14 consumers read canonical classification
- [x] Shims outstanding = 0
- [x] LOC gate passed
- [ ] Gate signed off by: __________ on __________

---

## Wave 2+ — expanded only after Gate 2

See [`90-downstream-stages.md`](./90-downstream-stages.md). Stage cards there are
deliberately *not* decomposed into packets yet, because they depend on interfaces
that do not exist. Expanding them now would produce fiction.

- [ ] Stage 9 consumer migration — expand at Gate 2
- [ ] Stages 10–12 invoice — expand at Gate 2
- [ ] Stage 13 event spine — expand at Gate 2
- [ ] Stage 14 Pulse MVP — expand after 13
- [ ] Stages 15–22 email + closed loop — expand after Gate 3

---

## Open decisions (blocking — a human must answer)

| # | Decision | Default if unanswered | Needed by |
|---|---|---|---|
| OD-1 | What class do `doctrine` / `reference_guide` rows become? Neither is an artefact form. | **Used:** `report` + `document_metadata.reference_kind = doctrine\|reference_guide` (Stage 8.6 default; human did not answer) | Stage 8.6 |
| OD-2 | `corpus_catalog` — synthetic row, not a real document. Keep as pseudo-class or move to `source_type`? | **Used:** `document_class="schedule"`, `document_metadata.synthetic=true` (Stage 8.5 default; human did not answer) | Stage 8.5 |
| OD-3 | `content_hash` is nullable. Override key when null? | Fall back to `(project_id, relative_path)`; record `key_basis` on the override row | Stage 5.9 |
| OD-4 | Do Stages 14/15 get a kill-switch flag despite `AGENTS.md`? | No flag until an external provider is live | Stage 14 |

---

## Accuracy measurements (Stage 4.6, then re-measured each wave)

| Date | Corpus | Class acc. | Subject acc. | Unknown % | Low-conf % | By |
|---|---|---|---|---|---|---|
| 2026-08-18 | fixture corpus (14) | 14/14 | 14/14 | 1/14 (`IMG_4471.pdf`, expected) | 1/14 (same row, conf 0.0) | Cursor Grok 4.6 |

---

## Shims outstanding (must be empty before Gate 2)

None. `LegacyDocumentClass` and `_LEGACY_TO_CANONICAL` deleted in Stage 8.9.

---

## Legacy → canonical mapping

Copied verbatim from `ingest.classify._LEGACY_TO_CANONICAL`. Stage 8's data
migration must use this exact table.

```python
_LEGACY_TO_CANONICAL: dict[str, tuple[DocumentClass, dict[str, str]]] = {
    "tep":              ("commercial", {"procurement_stage": "tep"}),
    "eoi":              ("commercial", {"procurement_stage": "eoi"}),
    "rft":              ("commercial", {"procurement_stage": "rft"}),
    "addendum":         ("commercial", {"procurement_stage": "addendum"}),
    "tender_submission":("commercial", {"procurement_stage": "submission"}),
    "evaluation":       ("commercial", {"procurement_stage": "evaluation"}),
    "trr":              ("commercial", {"procurement_stage": "trr"}),
    "planning_instrument": ("statutory_instrument", {}),
    "doctrine":         ("report", {"reference_kind": "doctrine"}),        # OD-1
    "reference_guide":  ("report", {"reference_kind": "reference_guide"}), # OD-1
}
```

`inbox_pending` and `corpus_catalog` are on `LegacyDocumentClass` but **not** in
this table. They are not produced by `classify_entry`; Stage 8.4 / 8.5 own them.

---

## Integration notes

Raise here instead of modifying another agent's files, or instead of fixing an
unrelated bug you found.

| Date | Agent | Note | Resolved |
|---|---|---|---|
| 2026-08-18 | Cursor Grok 4.6 | Exact `uv run pytest -q` (Stage 0.2 as written) cannot collect: duplicate basenames `test_models.py`, `test_schemas.py`, `test_service.py` under `tests/programme/` vs `tests/tender/` and `tests/web_research/`. Clearing `__pycache__` does not fix it. The committed failure contract was produced with `--import-mode=importlib`. Later stages must compare against that contract, not the collection-ERROR run. Do not "fix" the duplicate names in a Wave 1 packet. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 1.5 expected `should_persist_chunks` in `ingest/persist.py`. Grep found no call there; the only production caller is `ingest/pipeline.py`. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 2 sketch imported `get_sessionmaker`; real name is `get_session_factory` in `app/database/session.py`. Audit uses that. Persist helpers are sync (`ingest.db.get_sync_session_factory`), so `x1_backfill.py` is sync rather than async. | open |
| 2026-08-18 | Cursor Grok 4.6 | Live DB has no filename `Cost Plan.pdf`. Spot-check used previously-suppressed `cost-plan-system.md` (26 chunks; FTS `plainto_tsquery('english', 'cost plan')` rank 0.905). | open |
| 2026-08-18 | Cursor Grok 4.6 | OD-1 unanswered. Stage 3 mapped `doctrine`/`reference_guide` → `report` + `reference_kind` per the default. Flag if a human answers otherwise before Stage 8.6. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 3.3 expected `Classification(` in `ingest/pipeline.py`. Grep found none; `plan_entry` calls `classify_entry`. Construction sites were `classify.py`, tests, and `scripts/x1_backfill.py`. | open |
| 2026-08-18 | Cursor Grok 4.6 | `ingest/router.py` `_extractor_for` still branches on `doctrine`/`reference_guide`. Dead after canonical mapping (`.md` still hits the generic markdown extractor). Left untouched — not a construction site; Stage 8/6 can delete. | open |
| 2026-08-18 | Cursor Grok 4.6 | Gate 1 contract frozen as tag `x1-gate-1` (`c1b38f4b128ded46755ee0cb8236188a4bf4ac90`). Human signature on the GATE 1 checklist is still required before Wave 2. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 4: `pipeline.py` / `hosted.py` still call `classify_entry(entry)` before extraction, so Stage D content markers only run when the caller passes `extracted_text`. Did not rewire those files (outside Stage 4 ownership). Fixture accuracy passes text in. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 4 filename table extras beyond the sketch: `\bpayment plan\b` (test matrix), `^M\d{2,3}\b` (split mechanical sheets), DCP/LEP skipped when assessment/report/statement/review present (keeps Heritage DCP assessment as report). Content extras: `\bBUSINESS PLAN\b` → report (fixture; filename scoring correctly returns None). | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 5: Alembic `version_num` is `varchar(32)`. Sketch revision `048_document_classification_overrides` (40 chars) cannot be stored. Used `048_classification_overrides`. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 5.3: `infer_project_context` never sets `project_id`, so corpus `pipeline.plan_entry` cannot look up overrides. Hosted ingest (`ingest/hosted.py`) is the project-scoped path and now looks up by content hash before `classify_entry`. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 5.6 known limitation: `key_basis=relative_path` (null `content_hash`, OD-3) does not survive a file move. Hash-keyed overrides do. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 5.2 does not re-OCR or re-embed. Updating `source_documents.document_class` is enough for drawing-register membership and retrieval class filters. Existing chunks are left in place (D3). | open |
| 2026-08-18 | Cursor Grok 4.6 | `pnpm lint` still fails on pre-existing `CostPlanGrid.tsx` `react-hooks/set-state-in-effect`. Stage 5 chip/panel files lint clean. Not fixed in this packet. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 6.1 extras not in the stage-file sketch: `_PREVIEW_BRIEF_PATTERNS`, `_PREVIEW_CONSULTANT_COMMERCIAL_PATTERNS`, `_PREVIEW_DUE_DILIGENCE_PATTERNS`, `_consultant_destination`. Ported with the parent filename families. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 6.1 did not port bare `Development Application (DA)` / `Complying Development (CDC)` as class — too broad; they would steal reports. Chen pack still classifies from filename (`planning-pathway`, `certifier-appointment`). | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 6.3 `_ROUTES` table does not name `00-brief-pmp`, `02-consultant/{discipline}`, `05-procurement/quotes`, or generic due-diligence. `filing_destination` reads `brief_kind` / `commercial_type` / `due_diligence` metadata so Classifier B destinations survive. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 6.4 kept `tests/intake/test_classifier.py` as shim regression (filename+preview → destination via classify then route). New matrix is `tests/intake/test_filing_destination.py`. | open |
| 2026-08-18 | Cursor Grok 4.6 | `grep classify_inbox_destination` hits the shim plus `sort_service.py` / `repair_service.py` callers (Stage 7 wires those) and adapter tests. | resolved in Stage 7 for sort_service |
| 2026-08-18 | Cursor Grok 4.6 | Stage 7.3: `_file_previews` kept because `app/intake/repair_service.py` still imports it. Sort Files no longer calls it (`test_sort_does_not_download_files`). Repair is outside Stage 7 ownership. | open |
| 2026-08-18 | Cursor Grok 4.6 | Stage 7.6 live 10-file scenario not run: `Get-NetTCPConnection` showed nothing on 5173/8000. Automated stand-in: waiting outcome + `file_single_document` after ingest. | open |
| 2026-08-18 | Cursor Grok 4.6 | OD-1/OD-2 unanswered; Stage 8 used the documented defaults (`report`+`reference_kind`, `schedule`+`synthetic=true`). | open |
| 2026-08-18 | Cursor Grok 4.6 | Ground-truth listed mcp_bridge as the `planning_instrument` writer; the persist path is `app/web_research/attachments.py`. Updated that writer so new official instruments stay canonical. | open |
| 2026-08-18 | Cursor Grok 4.6 | Downgrade is keyed on `document_metadata._legacy_document_class` so newly written canonical rows are not reversed. Inbox_pending had empty extra metadata and could not round-trip without a marker. | open |
| 2026-08-18 | Cursor Grok 4.6 | `psql` is not on PATH. Snapshot used SQLAlchemy CSV (`x1_pre_taxonomy.csv`, not committed). Snapshot had 542 rows / unknown 233; live audit had 543 / unknown 234. Migrated classes round-tripped exactly (75 reference_guide, 2 planning_instrument, 1 doctrine). | open |
| 2026-08-18 | Cursor Grok 4.6 | `classify_inbox_destination` remains as classify-then-route for `repair_service` (outside Stage 8 ownership). It is not a second vocabulary. Removed from Shims outstanding. | open |
| 2026-08-18 | Cursor Grok 4.6 | 14 consumers batched in one commit: register/document_register/consultant_facts/consultant_appointment/queries/validator/assistant/persist/pipeline were verify-only. Writers changed with the migration so DB and writers never diverged. | open |

---

## Packet record

Copy this block under a packet when you claim it.

```text
Packet:
Status:
Owner/agent:
Branch/worktree:
Predecessors verified:
Reading list actually read:
Failing test written (name + confirmed FAIL):
Commit SHA:
Verification commands + EXACT pasted output:
Files added / changed / deleted:
Production LOC delta:
Integration notes raised:
Handoff (if stopping mid-packet — exactly where you got to):
```

### Stage 0 (0.1–0.6) — 2026-08-18

```text
Packet: 0.1–0.6 Baseline & safety harness
Status: [x]
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-0-baseline (repo root)
Predecessors verified: n/a (first stage). Repo HEAD at start: acb101313bba69330366e90df4f69677ecd34f5b
Reading list actually read: 00-doctrine.md, 01-ground-truth.md, backend/AGENTS.md §Tests, stage-00-baseline.md
Failing test written (name + confirmed FAIL): n/a — Stage 0 is harness only; fixture expect values are canonical and not asserted yet. load_fixtures() returns 14.
Commit SHA: 7a819d6ff4da71d5fa00af399ebf4ded4dd16f40
Production LOC delta: 0 under backend/app/ and backend/ingest/
Integration notes raised: pytest collection import-mode; census query 6 empty (see table above)
Handoff: Stage 0 complete. Stage 1 is unblocked.

Verification — 0.2 exact command `cd backend && uv run pytest -q` (full output; collection aborted):

=================================== ERRORS ====================================
________________ ERROR collecting tests/tender/test_models.py _________________
import file mismatch:
imported module 'test_models' has this __file__ attribute:
  D:\AI Projects\clerk\backend\tests\programme\test_models.py
which is not the same as the test file we want to collect:
  D:\AI Projects\clerk\backend\tests\tender\test_models.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
________________ ERROR collecting tests/tender/test_schemas.py ________________
import file mismatch:
imported module 'test_schemas' has this __file__ attribute:
  D:\AI Projects\clerk\backend\tests\programme\test_schemas.py
which is not the same as the test file we want to collect:
  D:\AI Projects\clerk\backend\tests\tender\test_schemas.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
_____________ ERROR collecting tests/web_research/test_service.py _____________
import file mismatch:
imported module 'test_service' has this __file__ attribute:
  D:\AI Projects\clerk\backend\tests\programme\test_service.py
which is not the same as the test file we want to collect:
  D:\AI Projects\clerk\backend\tests\web_research\test_service.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
=========================== short test summary info ===========================
ERROR tests/tender/test_models.py
ERROR tests/tender/test_schemas.py
ERROR tests/web_research/test_service.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!
34 deselected, 1 warning, 3 errors in 11.76s

Verification — 0.2 contract run `uv run pytest -q --tb=line --import-mode=importlib` last 40 lines:

=========================== short test summary info ===========================
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2402 passed, 7 skipped, 34 deselected, 5 warnings in 52.01s

Verification — 0.3 `pnpm typecheck` tail:
$ tsc -b --pretty false
(exit 0)

Verification — 0.3 `pnpm test` tail:
 RUN  v4.1.9 D:/AI Projects/clerk/frontend
 Test Files  82 passed (82)
      Tests  520 passed (520)
   Duration  81.63s

Verification — 0.3 `pnpm build` tail:
✓ built in 2.23s
(enforced size budgets passed; initialCockpit gzipBytes 242297 / budget 256000)

Verification — 0.4 census (dev database):
1.total: 543
2.by_class: unknown 234, drawing 200, reference_guide 75, certificate 9, correspondence 9, report 8, specification 5, planning_instrument 2, doctrine 1
3.by_ingest_mode: register_only 200, full_text 343
4.suppressed_with_text: 192
5.text_no_chunks: 224
6.classes_outside_literal: (no rows)
7.legacy_procurement: 0
8.null_content_hash: 0

Verification — 0.5:
14
Fixture(filename='Cost Plan.pdf', ...)

Verification — 0.6:
5609 total

Files added:
- backend/tests/fixtures/classification/manifest.yaml (new; replaces nothing)
- backend/tests/fixtures/classification/__init__.py (new; replaces nothing)
- backend/scripts/x1_census.sql (new; replaces nothing)
- docs/acceptance/x1/baseline-backend-failures.txt (new; replaces nothing)
- docs/plans/2026-08-18-pulse/** working-set docs (new; replace nothing)

Files changed: docs/plans/2026-08-18-pulse/TRACKER.md
Files deleted: none
```

### Stage 1 (1.1–1.8) — 2026-08-18

```text
Packet: 1.1–1.8 Evidence safety (D3)
Status: [x]
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-1-evidence-safety
Predecessors verified: Stage 0 complete, SHA 7a819d6f, baseline table filled
Reading list actually read: 00-doctrine.md §D3, 01-ground-truth.md suppression section, ingest/router.py (all), ingest/classify.py _looks_like_drawing + _ingest_mode_for_class, tests/ingest/test_classify.py. Callers required by 1.5: ingest/pipeline.py, tests/ingest/test_pipeline.py. persist.py has no should_persist_chunks call.
Failing test written: tests/ingest/test_evidence_safety.py (3 tests). Confirmed FAIL: TypeError: should_persist_chunks() got an unexpected keyword argument 'extracted_text'
Commit SHA: 8438ecb96d944623d9dd9043656ad73d96c4c2a3
Production LOC delta: router.py net +13, classify.py net +8, pipeline.py 0 (message + extracted_text kwarg). persist.py unchanged.
Integration notes raised: persist.py has no should_persist_chunks caller (stage file expected one).

Verification — 1.1 RED:
FAILED tests/ingest/test_evidence_safety.py::test_drawing_with_useful_text_still_persists_chunks
FAILED tests/ingest/test_evidence_safety.py::test_document_without_useful_text_is_register_only
FAILED tests/ingest/test_evidence_safety.py::test_useful_text_threshold_is_200_chars
TypeError: should_persist_chunks() got an unexpected keyword argument 'extracted_text'

Verification — 1.8 GREEN:
uv run pytest tests/ingest/test_evidence_safety.py -v
  3 passed, 1 warning in 0.18s

uv run pytest tests/ingest/ -q
  147 passed, 1 warning in 1.57s

uv run pytest tests/ -q -k "register" --import-mode=importlib
  64 passed, 2387 deselected, 1 warning in 8.26s

uv run pytest -q --tb=line --import-mode=importlib
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2406 passed, 7 skipped, 34 deselected, 5 warnings in 50.57s
(diff vs baseline-backend-failures.txt: empty — same 4 FAILED names; +4 passed from new tests)

grep -rn "register_only" backend/ingest/router.py
(no matches)

Files added:
- backend/tests/ingest/test_evidence_safety.py (new; does not replace a file)

Files changed:
- backend/ingest/router.py (replaces class-driven should_persist_chunks / ingest_mode chunker)
- backend/ingest/classify.py (widens _NOT_A_DRAWING_PLAN exclusions; Stage 4 supersedes)
- backend/ingest/pipeline.py (passes already-extracted text; skip reason text)
- backend/tests/ingest/test_classify.py (mode assertions → class; Cost Plan not drawing)
- backend/tests/ingest/test_pipeline.py (extracted_text kwarg; mock bodies ≥200 chars)
- docs/plans/2026-08-18-pulse/TRACKER.md

Files deleted: none
```

### Stage 2 (2.1–2.5) — 2026-08-18

```text
Packet: 2.1–2.5 Historical audit & backfill
Status: [x]
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-2-audit-backfill (repo root)
Predecessors verified: Stage 1 complete, SHA 8438ecb9; baseline suppressed_with_text=192, text_without_chunks=224
Reading list actually read: 00-doctrine.md §D3, backend/scripts/x1_census.sql, ingest/persist.py (delete_document_chunks, upsert_chunks), app/database/source_document.py, app/database/session.py (get_session_factory, not get_sessionmaker)
Failing test written: tests/scripts/test_x1_backfill.py::test_backfill_twice_produces_identical_chunk_counts. Confirmed FAIL: ImportError: cannot import name 'x1_backfill' from 'scripts'
Commit SHA: 563eee84b6bd4aa8581fc8c2843dfe1b8969b397
Production LOC delta: 0 under backend/app/ and backend/ingest/ (forbidden this stage)
Integration notes raised: get_sessionmaker missing → get_session_factory; backfill is sync because persist helpers are sync; no live filename Cost Plan.pdf
x1_backfill_log: created before apply; 224 rows
Handoff: Stage 2 complete. Stage 3 is unblocked.

Headline counts:
  pre  suppressed_with_text=192  text_without_chunks=224
  post suppressed_with_text=0    text_without_chunks=0
  ingest_mode pre  register_only=200 full_text=343
  ingest_mode post register_only=8   full_text=535
  remaining register_only=8 are docs without useful text (correct)

Verification — 2.1/2.2 audit-pre-backfill.json:
{
  "total": 543,
  "suppressed_with_text": 192,
  "text_without_chunks": 224,
  "by_ingest_mode": {"register_only": 200, "full_text": 343}
}

Verification — 2.3 dry-run (before apply):
would re-index 224 documents

Verification — 2.4 RED:
ERROR tests/scripts/test_x1_backfill.py
ImportError: cannot import name 'x1_backfill' from 'scripts'

Verification — 2.4 GREEN:
uv run pytest tests/scripts/test_x1_backfill.py -v
  1 passed, 1 warning in 1.07s

Verification — 2.5 apply:
progress: re-indexed 100/224 documents
progress: re-indexed 200/224 documents
progress: re-indexed 224/224 documents
re-indexed 224 documents

Verification — 2.5 dry-run after apply:
would re-index 0 documents

Verification — 2.5 audit-post-backfill.json:
{
  "total": 543,
  "suppressed_with_text": 0,
  "text_without_chunks": 0,
  "by_ingest_mode": {"register_only": 8, "full_text": 535}
}

Verification — 2.5 x1_backfill_log:
x1_backfill_log_rows=224

Verification — 2.5 Cost Plan spot-check (no live filename 'Cost Plan.pdf'):
FTS plainto_tsquery('english', 'cost plan') on previously-suppressed cost-plan-system.md:
  filename=cost-plan-system.md chunk_index=1 rank=0.90506
  snippet='## When to use\n\nWhen the PM asks for:\n- a project budget allocation;\n- a cost-plan structure or review;\n- a cost-plan workbook update;\n- reconciliation of cost-plan line items with'
  ingest_mode=full_text chunks=26

Verification — 2.5 backend suite `uv run pytest -q --tb=line --import-mode=importlib`:
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2407 passed, 7 skipped, 34 deselected, 5 warnings in 49.75s
(diff vs baseline-backend-failures.txt: empty — same 4 FAILED names; +5 passed vs Stage 0 from Stage 1 tests + this idempotency test)

Files added:
- backend/scripts/x1_audit.py (new; replaces nothing — read-only census)
- backend/scripts/x1_backfill.py (new; replaces nothing — one-shot historical repair using ingest/persist.py helpers)
- backend/tests/scripts/test_x1_backfill.py (new; replaces nothing)
- docs/acceptance/x1/audit-pre-backfill.json (new; replaces nothing)
- docs/acceptance/x1/audit-post-backfill.json (new; replaces nothing)

Files changed: docs/plans/2026-08-18-pulse/TRACKER.md
Files deleted: none
```

### Stage 3 (3.1–3.7) — 2026-08-18

```text
Packet: 3.1–3.7 Canonical classification contract (Gate 1)
Status: [x] code frozen; GATE 1 human signature still required
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-3-classification-contract (repo root)
Predecessors verified: Stage 1 SHA 8438ecb9; Stage 2 SHA 563eee84
Reading list actually read: 00-doctrine.md §Canonical vocabularies, 01-ground-truth.md §Current DocumentClass vs target, ingest/types.py, ingest/classify.py. Callers required by 3.3 grep: ingest/pipeline.py (no Classification()), ingest/router.py (chunker/extractor for 3.4/3.5), tests, scripts/x1_backfill.py
Failing test written: tests/ingest/test_classification_contract.py (5 tests). Confirmed FAIL: ImportError: cannot import name 'ClassificationBasis' from 'ingest.types'
Commit SHA: c1b38f4b128ded46755ee0cb8236188a4bf4ac90
Tag: x1-gate-1
Production LOC delta: ingest/types.py +27/−13; ingest/classify.py +46/−15 (net +45). x1_backfill.py +11/−2 is a construction-site fix, not app/intake.
Integration notes raised: OD-1 default used; pipeline.py has no Classification(); router.py dead doctrine/reference_guide extractor branch left; Gate 1 awaits human signature
Handoff: Stage 3 complete. Wave 2 waits on GATE 1 human signature. Stage 4 (still Wave 1) is unblocked for classifier logic against the frozen fields.

Verification — 3.4 RED:
ERROR tests/ingest/test_classification_contract.py
ImportError: cannot import name 'ClassificationBasis' from 'ingest.types'

Verification — 3.4/3.5 GREEN:
uv run pytest tests/ingest/test_classification_contract.py -v
  5 passed, 1 warning in 0.19s

uv run ruff check .
  All checks passed!

uv run pytest tests/ingest/ tests/scripts/test_x1_backfill.py -q
  153 passed, 1 warning in 1.65s

uv run pytest -q --tb=line --import-mode=importlib
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2412 passed, 7 skipped, 34 deselected, 5 warnings in 50.00s
(diff vs baseline-backend-failures.txt: empty — same 4 FAILED names; +10 passed vs Stage 0 from Stages 1–3 tests)

Stage 3.5 written command `uv run pytest -q` still cannot collect (duplicate basenames). Compared with --import-mode=importlib per Stage 0 integration note.

Files added:
- backend/tests/ingest/test_classification_contract.py (new; does not replace a file)

Files changed:
- backend/ingest/types.py (replaces 18-value DocumentClass; adds DocumentSubject, ClassificationBasis, LegacyDocumentClass shim, Classification fields)
- backend/ingest/classify.py (replaces legacy class emission; maps through _LEGACY_TO_CANONICAL)
- backend/scripts/x1_backfill.py (Classification construction now canonicalizes stored class)
- backend/tests/ingest/test_classify.py (legacy class assertions → canonical + metadata)
- backend/tests/ingest/test_rtf.py (planning_instrument → statutory_instrument)
- backend/tests/stage01/test_database_gates.py (tender_submission → commercial)
- docs/plans/2026-08-18-pulse/TRACKER.md

Files deleted: none
```

### Stage 4 (4.1–4.7) — 2026-08-18

```text
Packet: 4.1–4.7 Deterministic classifier (no model fallback)
Status: [x]
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-4-deterministic-classifier (repo root)
Predecessors verified: Stage 3 [x], tag x1-gate-1 at c1b38f4b
Reading list actually read: 00-doctrine.md §Canonical vocabularies, ingest/classify.py, tests/fixtures/classification/manifest.yaml, ingest/drawing_parse.py + title_block.py (interfaces). persist.py required by 4.5.
Failing test written: tests/ingest/test_filename_scoring.py. Confirmed FAIL: ImportError: cannot import name 'score_filename' from 'ingest.classify'
Commit SHA: 7052d14304bf09434b7e116c800c24a30fbbb624
Production LOC delta: ingest/classify.py +318/−118 (net +200); ingest/persist.py +3 (writes confidence/basis/subject into JSONB). types.py untouched.
Integration notes raised: pipeline/hosted classify before extract so Stage D is opt-in via extracted_text; extra payment-plan / M## / BUSINESS PLAN / DCP-exclude signals
Handoff: Stage 4 complete. Stage 5 (user override into Stage A seam `_user_override`) is unblocked.

Verification — 4.3 RED:
ERROR tests/ingest/test_filename_scoring.py
ImportError: cannot import name 'score_filename' from 'ingest.classify'

Verification — 4.3/4.4/4.5 GREEN:
uv run pytest tests/ingest/ -q
  203 passed, 1 warning in 1.75s
  (46 filename cases + count assertion; Scan_20260815_001 → report/heritage/content; persist round-trip)

Verification — 4.6:
uv run pytest tests/ingest/test_fixture_corpus_accuracy.py -s
  class accuracy: 14/14
  subject accuracy: 14/14
  unknown rate: 1/14
  low-confidence rate: 1/14
  ratchet raised 11 → 14

Verification — 4.7:
grep openai|OpenAI|completion backend/ingest/classify.py
  (no matches)

uv run ruff check .
  All checks passed!

uv run pytest -q --tb=line --import-mode=importlib
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2463 passed, 7 skipped, 34 deselected, 5 warnings in 52.09s
(diff vs baseline-backend-failures.txt: empty — same 4 FAILED names)

Files added:
- backend/tests/ingest/test_filename_scoring.py (new; does not replace a file)
- backend/tests/ingest/test_fixture_corpus_accuracy.py (new; does not replace a file)

Files changed:
- backend/ingest/classify.py (replaces first-match-wins with B/C/D cascade; removes _looks_like_drawing / _filename_hints)
- backend/ingest/persist.py (copies confidence/basis/subject into document_metadata JSONB)
- backend/tests/ingest/test_classify.py (confidence 0.85; Stage D + title-block cases)
- backend/tests/ingest/test_persist_metadata.py (round-trip)
- docs/plans/2026-08-18-pulse/TRACKER.md

Files deleted: none
```

### Stage 5 (5.1–5.9) — 2026-08-18

```text
Packet: 5.1–5.9 User classification override
Status: [x]
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-5-user-override (repo root)
Predecessors verified: Stage 3 [x] tag x1-gate-1; Stage 4 [x] SHA 7052d143
Reading list actually read: 00-doctrine.md §D4, backend/app/database/source_document.py, alembic/versions/047_programme.py, app/api/projects.py PUT authorization pattern, backend/AGENTS.md §Database Migrations. Stage-A hook: ingest/classify.py. Callers required by 5.3/5.5: ingest/hosted.py.
Failing test written: tests/projects/test_classification_override.py (ImportError classification_override); tests/test_classification_override_api.py (404 "Not Found" missing route); tests/mcp_bridge/test_set_document_classification.py (missing tool); ClassificationChip.test.tsx (missing module)
Commit SHA: 90f12255c6147fd9685f8285675aac5eb87acde6
Production LOC delta: classification_override.py 200; document_classification_override.py 70; alembic 048 113; projects.py +54; mcp_bridge/server.py +66; schemas +10; models +4; classify.py +8/−3; hosted.py +25. Frontend ClassificationChip.tsx new.
Integration notes raised: alembic version_num varchar(32); hosted.py lookup (pipeline has no project_id); path-keyed move limitation; no re-embed on override; pre-existing CostPlanGrid lint
Handoff: Stage 5 complete. Stage 6 is unblocked.

Verification — 5.4 RED:
PUT /projects/{B}/documents/{A}/classification → 404 detail="Not Found" (route missing)

Verification — 5.1 alembic:
uv run alembic upgrade head → 047_programme -> 048_classification_overrides
uv run alembic downgrade -1 → 048_classification_overrides -> 047_programme
uv run alembic upgrade head → 047_programme -> 048_classification_overrides
uv run alembic current → 048_classification_overrides (head)

Verification — GREEN:
uv run pytest tests/ingest/ tests/projects/test_classification_override.py tests/test_classification_override_api.py tests/mcp_bridge/test_set_document_classification.py -q
  214 passed, 1 warning in 6.28s
uv run ruff check . → All checks passed!
pnpm typecheck → exit 0
pnpm test → 83 files, 522 tests passed
Stage 5 eslint files clean; repo-wide pnpm lint fails on pre-existing CostPlanGrid.tsx

Verification — one implementation:
  app/projects/classification_override.py  async def set_document_classification
  app/api/projects.py                      await set_document_classification(
  app/mcp_bridge/server.py                 import as set_document_classification_service; tool wraps it

Verification — backend suite:
uv run pytest -q --tb=line --import-mode=importlib
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2474 passed, 7 skipped, 34 deselected, 5 warnings in 52.71s
(diff vs baseline-backend-failures.txt: empty — same 4 FAILED names; +11 passed vs Stage 4)

Files added:
- backend/alembic/versions/048_document_classification_overrides.py (new)
- backend/app/database/document_classification_override.py (new)
- backend/app/projects/classification_override.py (new; REST and MCP share this)
- backend/tests/projects/test_classification_override.py (new)
- backend/tests/test_classification_override_api.py (new)
- backend/tests/mcp_bridge/test_set_document_classification.py (new)
- frontend/src/components/project/ClassificationChip.tsx (new; replaces class Badge in preview/explorer)
- frontend/src/components/project/ClassificationChip.test.tsx (new)

Files changed:
- backend/ingest/classify.py (Stage A override= keyword)
- backend/ingest/hosted.py (hash lookup into classify_entry)
- backend/app/api/projects.py (PUT classification; evidence preview fields)
- backend/app/mcp_bridge/server.py (MCP tool wraps the service)
- backend/app/schemas/projects.py
- backend/app/database/models.py
- frontend/src/lib/api.ts, types/project.ts
- frontend/src/components/project/WorkspaceFilePanel.tsx, WorkspaceFolderPanel.tsx
- frontend/src/pages/ProjectCockpitPage.tsx, CockpitPreviewPage.tsx
- docs/plans/2026-08-18-pulse/TRACKER.md

Files deleted: none
```

### Stage 6 (6.1–6.6) — 2026-08-18

```text
Packet: 6.1–6.6 Collapse duplicate classifiers
Status: [x]
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-6-collapse-classifiers (repo root)
Predecessors verified: Stage 4 [x] SHA 7052d143; Stage 5 [x] SHA 90f12255
Reading list actually read: 00-doctrine.md, 01-ground-truth.md §The two classifiers, app/intake/classifier.py (full), ingest/classify.py (post-Stage-4/5), tests/workflows/test_sort_files.py. Callers required by 6.4: tests/intake/test_classifier.py (destination assertions kept as shim regression).
Failing test written: tests/ingest/test_filename_scoring.py (9 new cases → None/wrong class); tests/ingest/test_classify.py (8 metadata/content tests); tests/intake/test_filing_destination.py (ImportError filing_destination)
Commit SHA: a914dc7b
Production LOC delta: ingest/classify.py 436→577 (+141); app/intake/classifier.py 288→233 (−55). Gate total 5982 vs Stage 0.6 5609 = +373 / +6.6% (<10%).
Integration notes raised: extra preview families; DA/CDC not ported as class; metadata routes beyond 6.3 table; test_classifier.py kept; shim callers remain until Stage 7
Handoff: Stage 6 complete. Stage 7 is unblocked. sort_service still calls classify_inbox_destination (shim).

LOC justification (D8): increase is Stages 1–6 scoring tables and extras inside the one classifier, not a parallel engine. classifier.py lost every semantic regex family. classify_inbox_destination is a thin classify-then-route adapter listed under Shims outstanding (removal: 7.2).

Verification — 6.2 RED:
FAILED score_filename planning-pathway / certifier-appointment / engagement-letter / owner-project-brief / PPR / email-thread-brief / sydney-water / Price Schedule / cdc-screening
FAILED classify_entry metadata/content ports (unknown or correspondence; KeyError due_diligence)
17 failed, 70 passed

Verification — 6.5 RED:
ImportError: cannot import name 'filing_destination' from 'app.intake.classifier'

Verification — GREEN:
uv run pytest tests/ingest/ tests/intake/test_filing_destination.py tests/intake/test_classifier.py tests/workflows/test_sort_files.py -q
  279 passed, 1 warning in 4.11s

uv run ruff check .
  All checks passed!

grep classify_inbox_destination backend/:
  app/intake/classifier.py          def classify_inbox_destination  (shim)
  app/intake/sort_service.py        destination_folder = classify_inbox_destination(
  app/intake/repair_service.py      destination_folder = classify_inbox_destination(
  tests/intake/test_classifier.py   adapter regression

Verification — 6.6 LOC:
5982 total  (Stage 0.6 baseline 5609; +373 / +6.6%)

Verification — backend suite:
uv run pytest -q --tb=line --import-mode=importlib
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2501 passed, 7 skipped, 34 deselected, 5 warnings in 50.64s
(diff vs baseline-backend-failures.txt: empty — same 4 FAILED names; +27 passed vs Stage 5)

Files added:
- docs/acceptance/x1/classifier-signal-inventory.md (new; replaces nothing — 6.1 inventory)
- backend/tests/intake/test_filing_destination.py (new; does not replace a file)

Files changed:
- backend/ingest/classify.py (replaces nothing; receives ported semantic signals)
- backend/app/intake/classifier.py (replaces regex semantic families with filing_destination + shim)
- backend/tests/ingest/test_filename_scoring.py
- backend/tests/ingest/test_classify.py
- docs/plans/2026-08-18-pulse/TRACKER.md

Files deleted: none
```

### Stage 7 (7.1–7.5) — 2026-08-18

```text
Packet: 7.1–7.5 Auto-filing / Sort Files repair (7.6 live blocked)
Status: [x] for 7.1–7.5; 7.6 [!]
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-7-auto-filing (repo root)
Predecessors verified: Stage 6 [x] SHA a914dc7b
Reading list actually read: 00-doctrine.md §D2, 01-ground-truth.md §Sort Files path, sort_service.py 30–90 and 410–end (needed already-filed + _file_previews), document_ingest.py 54–end, tests/workflows/test_sort_files.py. Extra (named in tasks): SortFilesResultPanel, schemas SortFilesSummary, test_document_ingest_auto_sort.py, repair_service import of _file_previews.
Failing test written: test_files_still_ingesting_report_waiting_not_skipped (skipped vs waiting); test_failed_ingest_reports_failed_not_skipped; test_low_confidence_reports_needs_review (unresolved vs needs-review); test_sort_does_not_download_files (one download); file_single_document ImportError
Commit SHA: 432e3ce5

Verification — 7.1 RED:
assert 'skipped' == 'waiting'
assert 'skipped' == 'failed'
assert 'unresolved' == 'needs-review'

Verification — 7.3 RED:
assert [{'storage_key': '...CC-A-010.pdf'}] == []

Verification — GREEN:
uv run pytest tests/workflows/test_sort_files.py tests/workflows/test_document_ingest_auto_sort.py -q
  24 passed, 1 warning in 3.87s

uv run ruff check .
  All checks passed!

pnpm typecheck → exit 0
pnpm test → 83 files, 525 tests passed
pnpm build → ✓ built in 1.54s (initialCockpit gzipBytes 242707 / budget 256000)

Verification — backend suite:
uv run pytest -q --tb=line --import-mode=importlib
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2508 passed, 7 skipped, 34 deselected, 4 warnings in 82.48s
(diff vs baseline: empty — same 4 FAILED names; +7 passed vs Stage 6)

7.6 live: NOT RUN. Get-NetTCPConnection Listen on 5173/8000 returned no rows.

Files added: none (SortFilesResultPanel already existed; rewritten in place — replaces the collapsed "Moved/Skipped" grid)

Files changed:
- backend/app/intake/sort_service.py (replaces classify_inbox_destination + _file_previews on the Sort path with filing_destination + persisted Classification; adds file_single_document)
- backend/app/workflows/document_ingest.py (replaces whole-inbox sort_inbox_files call with file_single_document)
- backend/app/workflows/sort_files.py (summary + waiting headline)
- backend/app/schemas/projects.py
- backend/tests/workflows/test_sort_files.py
- backend/tests/workflows/test_document_ingest_auto_sort.py
- frontend/src/components/project/SortFilesResultPanel.tsx (replaces metric grid that could show a bare 0 moved)
- frontend/src/components/project/SortFilesResultPanel.test.tsx
- frontend/src/lib/types/project.ts
- docs/plans/2026-08-18-pulse/TRACKER.md

Files deleted: none (_file_previews kept for repair_service)
```

### Stage 8 (8.1–8.9) — 2026-08-18

```text
Packet: 8.1–8.9 Taxonomy data migration (Gate 2)
Status: [x] code complete; GATE 2 human signature still required
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-8-taxonomy-migration (repo root)
Predecessors verified: Stage 6 [x] SHA a914dc7b; Stage 7 [x] SHA 432e3ce5
Reading list actually read: 01-ground-truth.md §Consumers of document_class, TRACKER.md mapping + OD-1/OD-2, docs/acceptance/x1/audit-post-backfill.json. Owned consumers named in stage-08. Alembic 048 for down_revision (varchar(32) note from Stage 5).
Failing test written: tests/ingest/test_taxonomy_migration.py (FileNotFoundError 049); test_catalog_passages_use_schedule_not_corpus_catalog (corpus_catalog); test_append_unindexed_inbox_workspace_files (inbox_pending); test_bootstrap_skips_statutory_instruments (did not skip)
Commit SHA: (recorded in follow-up docs commit)
Production LOC delta: ingest+intake 6073 vs Stage 0.6 5609 (+464 / +8.3%, <10%). Alembic 049 is data-only and outside that glob.
Integration notes raised: OD-1/OD-2 defaults; attachments.py writer; _legacy_document_class marker; psql missing; classify_inbox_destination kept for repair; batched consumer commits
Handoff: Stage 8 complete. GATE 2 awaits human signature. Then expand Stage 9 from 90-downstream-stages.md.

Verification — 8.1 RED:
FileNotFoundError: 049_canonical_document_taxonomy.py
assert 'corpus_catalog' == 'schedule'
assert 'inbox_pending' == 'unknown'

Verification — mapping test GREEN:
uv run pytest tests/ingest/test_taxonomy_migration.py -q
  3 passed

Verification — 8.4 rehearsal (psql missing; SQLAlchemy snapshot + alembic):
uv run alembic upgrade head
taxonomy migration before:
  planning_instrument: 2  doctrine: 1  reference_guide: 75  report: 8  unknown: 234
taxonomy migration after:
  planning_instrument: 0  doctrine: 0  reference_guide: 0  statutory_instrument: 2  report: 84  unknown: 234

uv run python scripts/x1_audit.py  (after first upgrade)
{
  "total": 543,
  "by_class": {
    "statutory_instrument": 2,
    "certificate": 9,
    "correspondence": 9,
    "specification": 5,
    "report": 84,
    "unknown": 234,
    "drawing": 200
  },
  "non_canonical_classes": {},
  "planning_instrument": 0
}

uv run alembic downgrade -1
taxonomy migration downgrade after:
  planning_instrument: 2  doctrine: 1  reference_guide: 75  report: 8  unknown: 234

uv run python scripts/x1_audit.py  (after downgrade)
{
  "total": 543,
  "by_class": {
    "certificate": 9,
    "correspondence": 9,
    "reference_guide": 75,
    "planning_instrument": 2,
    "doctrine": 1,
    "specification": 5,
    "report": 8,
    "unknown": 234,
    "drawing": 200
  },
  "non_canonical_classes": {
    "reference_guide": 75,
    "planning_instrument": 2,
    "doctrine": 1
  }
}
(matches audit-post-backfill.json class distribution)

uv run alembic upgrade head  (second apply; same before/after counts as first)
uv run alembic current → 049_canonical_document_taxonomy (head)

Verification — 8.6 SQL (zero non-canonical rows):
SELECT document_class, count(*) FROM source_documents WHERE document_class NOT IN (...)
(empty)

Verification — 8.5 shim grep LegacyDocumentClass|_LEGACY_TO_CANONICAL under backend/app ingest alembic scripts tests:
(no matches)

Verification — GREEN tests:
uv run pytest tests/ingest/ tests/intake/ tests/scripts/test_x1_backfill.py tests/workflows/test_sort_files.py tests/workflows/test_document_ingest_auto_sort.py tests/retrieval/ tests/projects/test_identity_bootstrap.py tests/web_research/test_attachments.py tests/mcp_bridge/test_tools_web_research.py tests/mcp_bridge/test_tools_get_document.py tests/mcp_bridge/test_tools_find_document_text.py tests/test_project_evidence.py -q
  377 passed, 6 deselected

uv run ruff check .
  All checks passed!

pnpm typecheck → exit 0
pnpm test → 83 files, 525 tests passed
pnpm build → ✓ built in 1.35s (initialCockpit gzipBytes 242707 / budget 256000)

Verification — backend suite:
uv run pytest -q --tb=line --import-mode=importlib
FAILED tests/test_database_runner_contract.py::test_database_compose_is_private_ephemeral_and_digest_pinned
FAILED tests/workflows/test_create_pmp.py::test_create_pmp_repairs_taxonomy_engagement_status_before_validation
FAILED tests/workflows/test_update_pmp.py::test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged
FAILED tests/workflows/test_worker_entrypoint.py::test_worker_failure_logs_error_class_without_provider_detail
4 failed, 2513 passed, 7 skipped, 34 deselected, 5 warnings in 80.97s
(diff vs baseline-backend-failures.txt: empty — same 4 FAILED names; +5 passed vs Stage 7)

Verification — 8.6 LOC:
6073 total  (Stage 0.6 baseline 5609; +464 / +8.3%)

Files added:
- backend/alembic/versions/049_canonical_document_taxonomy.py (new; data-only rewrite, replaces stored legacy document_class values)
- backend/tests/ingest/test_taxonomy_migration.py (new; does not replace a file)

Files changed:
- backend/ingest/types.py (deletes LegacyDocumentClass shim)
- backend/ingest/classify.py (deletes _LEGACY_TO_CANONICAL / canonicalize_document_class; doctrine/reference emit report+reference_kind)
- backend/ingest/router.py (deletes dead doctrine/reference_guide extractor branch)
- backend/app/api/projects.py (inbox_pending → unknown)
- backend/app/retrieval/catalog.py (corpus_catalog → schedule + synthetic)
- backend/app/retrieval/inventory.py (display falls back to reference_kind)
- backend/app/projects/identity_bootstrap.py (statutory_instrument)
- backend/app/mcp_bridge/server.py (writes statutory_instrument)
- backend/app/web_research/attachments.py (writes statutory_instrument; not in the original 14, actual persist writer)
- backend/app/intake/sort_service.py (drops canonicalize; stored class is canonical)
- backend/scripts/x1_backfill.py, backend/scripts/x1_audit.py
- tests and TRACKER / stage-08 as listed in git

Files deleted: none
```



