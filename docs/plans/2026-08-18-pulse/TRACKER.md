# X1 Programme Tracker

**Created:** 2026-08-18 · **Baseline commit:** `acb10131` · **Status:** Stage 3 complete (`c1b38f4b`, tag `x1-gate-1`)

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

- [ ] 4.1 Structural signals (Stage B)
- [ ] 4.2 Scored filename rules replace first-match-wins (Stage C)
- [ ] 4.3 Filename test matrix (≥40 cases)
- [ ] 4.4 Deterministic content markers (Stage D)
- [ ] 4.5 Persist `confidence` + `basis`
- [ ] 4.6 Accuracy measured on fixture corpus, recorded below
- [ ] 4.7 Model fallback remains **absent** (not merely disabled)

### Stage 5 — User override → [`stage-05-user-override.md`](./stage-05-user-override.md)

- [ ] 5.1 Migration: `document_classification_overrides`
- [ ] 5.2 `set_document_classification()` service
- [ ] 5.3 Stage A lookup wired into classifier
- [ ] 5.4 REST endpoint (+ project authorization test)
- [ ] 5.5 Survives re-ingest test
- [ ] 5.6 Survives file-move test
- [ ] 5.7 Frontend classification chip
- [ ] 5.8 MCP tool `set_document_classification`
- [ ] 5.9 Null `content_hash` path handled

### Stage 6 — Collapse duplicate classifiers → [`stage-06-collapse-classifiers.md`](./stage-06-collapse-classifiers.md)

- [ ] 6.1 Signal inventory: which of B's rules survive
- [ ] 6.2 Port surviving semantic signals into `classify.py`
- [ ] 6.3 `filing_destination(Classification) -> str | None`
- [ ] 6.4 Delete superseded regex families from `app/intake/classifier.py`
- [ ] 6.5 Routing test matrix
- [ ] 6.6 **LOC gate check vs. Stage 0.6 number**

### Stage 7 — Auto-filing / Sort repair → [`stage-07-auto-filing.md`](./stage-07-auto-filing.md)

- [ ] 7.1 Add `waiting` + `needs-review` to `SortOutcome`
- [ ] 7.2 Auto-file on successful classification
- [ ] 7.3 Remove `_file_previews` re-download (D2)
- [ ] 7.4 Idempotent move test
- [ ] 7.5 Frontend per-outcome breakdown
- [ ] 7.6 Ten-file upload-then-immediately-sort scenario

### Stage 8 — Taxonomy migration → [`stage-08-taxonomy-migration.md`](./stage-08-taxonomy-migration.md)

- [ ] 8.1 Data migration with dry-run + counts
- [ ] 8.2 `planning_instrument` → `statutory_instrument`
- [ ] 8.3 Procurement classes → `commercial` + metadata
- [ ] 8.4 `inbox_pending` removed from class
- [ ] 8.5 `corpus_catalog` resolved
- [ ] 8.6 `doctrine` / `reference_guide` resolved (see *Open decisions*)
- [ ] 8.7 All 14 consumer files migrated
- [ ] 8.8 Rollback rehearsed on a copy
- [ ] 8.9 **Shims list emptied**

---

## 🔒 GATE 1 — Contract frozen

Do not open a Wave 2 packet until all are true:

- [x] Stage 1 green; no class-driven evidence suppression anywhere
- [x] Stage 3 contract frozen and tagged (`x1-gate-1`)
- [x] Stage 0 baseline table fully populated
- [x] Backend suite failures ⊆ Stage 0 pre-existing failures
- [ ] Gate signed off by: __________ on __________

## 🔒 GATE 2 — Canonical classification live

- [ ] Stages 4–8 green
- [ ] All 14 consumers read canonical classification
- [ ] Shims outstanding = 0
- [ ] LOC gate passed
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
| OD-1 | What class do `doctrine` / `reference_guide` rows become? Neither is an artefact form. | `report` + `document_metadata.reference_kind = doctrine\|reference_guide` (lossless; `source_type` already carries the distinction) | Stage 8.6 |
| OD-2 | `corpus_catalog` — synthetic row, not a real document. Keep as pseudo-class or move to `source_type`? | `document_class="schedule"`, `document_metadata.synthetic=true` | Stage 8.5 |
| OD-3 | `content_hash` is nullable. Override key when null? | Fall back to `(project_id, relative_path)`; record `key_basis` on the override row | Stage 5.9 |
| OD-4 | Do Stages 14/15 get a kill-switch flag despite `AGENTS.md`? | No flag until an external provider is live | Stage 14 |

---

## Accuracy measurements (Stage 4.6, then re-measured each wave)

| Date | Corpus | Class acc. | Subject acc. | Unknown % | Low-conf % | By |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## Shims outstanding (must be empty before Gate 2)

| Shim | File | Added by | Removal packet |
|---|---|---|---|
| `LegacyDocumentClass` alias (procurement / doctrine / undeclared DB values kept reachable until data migration) | `backend/ingest/types.py` | Stage 3.1 | 8.9 |

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
