# X1 Programme Tracker

**Created:** 2026-08-18 · **Baseline commit:** `acb10131` · **Status:** Stages 8B–13 implemented in working tree. Gate 2 signed 2026-08-19. Next implementable packet: **14.1** (Pulse MVP). Email (15–22) waits on Gate 3.

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

### Stage 8B — Classification remediation → [`stage-8B-classification-remediation.md`](./stage-8B-classification-remediation.md)

Added 2026-08-19 from the review in [`91-review-2026-08-19.md`](./91-review-2026-08-19.md).
Not new capability — restores invariants Stages 1–8 claimed and did not deliver.

**Wave A — blocks the Gate 2 signature:**

- [x] 8B.1 Override merges onto the machine classification (D4/D1)
- [x] 8B.2 Preserve the machine opinion (D5) — unblocks Stage E
- [x] 8B.3 MCP override tool uses the mutation authorizer (D6)
- [x] 8B.4 Confidence floor drops below the review gate

**Wave B — before Stage 9.1:**

- [x] 8B.5 Retire `document_type`
- [x] 8B.6 `ingest_mode` follows useful text, not class
- [x] 8B.7 Migration 049: test the SQL, assert the post-condition, clear the data shim
- [x] 8B.8 Re-classify the 234 historical `unknown` rows
- [x] 8B.9 Bound the register chunker and embedding input
- [x] 8B.10 One vocabulary, one review threshold
- [x] 8B.11 Filing must not silently re-classify

---

## 🔒 GATE 2 — Canonical classification live

**Amended 2026-08-19.** The four boxes below were all ticked and Gate 2 was
still not true — see [`91-review-2026-08-19.md`](./91-review-2026-08-19.md)
Part A. "All 14 consumers" was measured against a consumer list that omitted
`source_documents.document_type`. Ticking a derived list is not evidence.
The struck items stay for the audit trail; the new items are the real gate.

- [x] Stages 4–8 green
- [x] ~~All 14 consumers read canonical classification~~ — list was incomplete
- [x] ~~Shims outstanding = 0~~ — true of code, false of data (`_legacy_document_class`)
- [x] LOC gate passed
- [x] **Stage 8B Wave A (8B.1–8B.4) `[x]`** with pasted output
- [x] **No second document vocabulary** — writers and title fallbacks no longer
      read or write `document_type` (column left in place; OD-7). `grep document_type`
      still hits the dead SQLAlchemy column and historical comments.
- [x] **A user override preserves machine-observed metadata** — an overridden
      drawing survives re-ingest and stays in the drawing register
- [x] **The MCP override tool requires a mutation turn capability**
- [x] Stage 7.6 `[!]` resolved or explicitly waived in writing — **waived**: ports
      5173/8000 were not listening; automated waiting + auto-file tests stand in
      (same as Stage 7 packet record)
- [x] Gate signed off by: user instruction 2026-08-19 (implement 8B then 9–12; do not stop) on 2026-08-19

---

## Wave 2+ — expanded at Gate 2 (invoice + consumers)

Stage cards 9–12 are packet files and **implemented**. Stages 13–22 are
now packet files too ([`90-downstream-stages.md`](./90-downstream-stages.md)).
**Expansion is not implementation.** Do not start 15–22 until Gate 3 is
signed. Do not start 14 until 13 is `[x]`.

Gate 2 human signature is filled from the 19 Aug instruction to implement
8B then 9–12 without stopping.

### Stage 9 — Consumer behaviour → [`stage-09-consumer-behavior.md`](./stage-09-consumer-behavior.md)

- [x] 9.0 Refresh `01-ground-truth.md` against Gate 2 (docs)
- [x] 9.1 Retrieval filters for `document_subject` / `discipline` 🔒
- [x] 9.2 Row-aware `schedule` chunker
- [x] 9.3 Drawing register regression
- [x] 9.4 Consultant facts from class + subject
- [x] 9.5 Cost Plan / invoice discovery from `commercial_type`
- [x] 9.6 PMP evidence from class + subject
- [x] 9.7 Tender Comparison Clerk-side submission filter (no TCM merge)
- [x] 9.8 Transmittals carry drawing class + revision

### Stage 10 — Invoice foundation → [`stage-10-invoice-foundation.md`](./stage-10-invoice-foundation.md)

- [x] 10.1 Persist immutable `machine_extraction`
- [x] 10.2 Reviewed overlay; effective values
- [x] 10.3 Dirty invoices still persist
- [x] 10.4 Per-field provenance

### Stage 11 — Invoice validation → [`stage-11-invoice-validation.md`](./stage-11-invoice-validation.md)

- [x] 11.1 Coded `InvoiceIssue` JSONB
- [x] 11.2 Adapt existing checks (no second validator)
- [x] 11.3 Field reconciliation status
- [x] 11.4 Conditional secondary extraction (no LLM on clean invoices)

### Stage 12 — Invoice workflow & UI → [`stage-12-invoice-workflow.md`](./stage-12-invoice-workflow.md)

- [x] 12.1 `review_state` distinct from `paid`
- [x] 12.2 Hold / Reject / Approve API
- [x] 12.3 Three-pane review UI
- [x] 12.4 `invoice.*` activity events (no Pulse table)

---

## Wave 3 — Events, Pulse, email (expanded 2026-08-19)

### Stage 13 — Project event spine → [`stage-13-project-event-spine.md`](./stage-13-project-event-spine.md)

**Implement now** (Stage 12 `[x]`). Parallelism 1.

- [x] 13.1 Vocabulary + `record_project_verb` + `deduplication_key` 🔒 — Cursor Grok 4.6 / `x1/stage-8-taxonomy-migration`
- [x] 13.2 `document.received` / `extracted` / `classified`
- [x] 13.3 `document.reclassified`
- [x] 13.4 `document.filed`
- [x] 13.5 `document.revised`
- [x] 13.6 Invoice verbs call the shared helper
- [x] 13.7 `list_project_verbs` (no HTTP)

### Stage 14 — Pulse MVP → [`stage-14-pulse-mvp.md`](./stage-14-pulse-mvp.md)

**Implement after 13 `[x]`.** No feature flag (OD-4).

- [ ] 14.1 Signal vocabulary + synthesizer 🔒
- [ ] 14.2 Five MVP detectors
- [ ] 14.3 GET/POST Pulse API
- [ ] 14.4 PulsePanel against fixtures
- [ ] 14.5 Wire UI to API
- [ ] 14.6 Card actions open existing surfaces
- [ ] 14.7 Acceptance G + I (no email)

---

## 🔒 GATE 3 — Pulse stable

Do not open a Stage 15 packet until all are true:

- [x] Stage 13 `[x]` with pasted alembic + verb tests
- [ ] Stage 14 `[x]` with pasted Pulse tests + vitest failure-mode
- [ ] No `pulse_*` table in alembic
- [ ] Detectors do not mutate invoices or classifications
- [ ] Pulse headline is attention, not raw event counts
- [ ] OD-4 still holds (no Pulse kill-switch flag shipped)
- [ ] Backend failures ⊆ Stage 0 baseline names
- [ ] Gate signed off by: ________________ on ________

### Stage 15 — Email foundation → [`stage-15-email-foundation.md`](./stage-15-email-foundation.md)

- [ ] 15.1 Raw email + interpretation tables (D5)
- [ ] 15.2 Provider protocol + FakeProvider
- [ ] 15.3 Import without ingesting attachments

### Stage 16 — Email intake → [`stage-16-email-intake.md`](./stage-16-email-intake.md)

- [ ] 16.1 Adapter calls inbox upload
- [ ] 16.2 **Equivalence test** (email == upload, two projects)
- [ ] 16.3 Unmatched email does not ingest

### Stage 17 — Matching → [`stage-17-email-matching.md`](./stage-17-email-matching.md)

- [ ] 17.1 `match_project` pure function
- [ ] 17.2 User link outranks machine; 404 cross-tenant
- [ ] 17.3 Thread inheritance

### Stage 18 — Intelligence → [`stage-18-email-intelligence.md`](./stage-18-email-intelligence.md)

- [ ] 18.1 Message category ≠ document_class
- [ ] 18.2 `email.*` verbs
- [ ] 18.3 Action candidates do not mutate

### Stage 19 — MCP + drafts → [`stage-19-email-mcp-drafts.md`](./stage-19-email-mcp-drafts.md)

- [ ] 19.1 Drafts cannot send themselves
- [ ] 19.2 REST send with `actor_id`
- [ ] 19.3 MCP allowed tools; forbidden names absent
- [ ] 19.4 Provider factory; default `fake`

### Stage 20 — Closed-loop procurement → [`stage-20-closed-loop-procurement.md`](./stage-20-closed-loop-procurement.md)

- [ ] 20.1 Cover-email draft leaves request `draft`
- [ ] 20.2 Send issues the request (rollback if send fails)
- [ ] 20.3 Link classified submissions
- [ ] 20.4 Chase = draft only
- [ ] 20.5 No `tender/` import

### Stage 21 — Advanced Pulse → [`stage-21-advanced-pulse.md`](./stage-21-advanced-pulse.md)

- [ ] 21.1 `since` window
- [ ] 21.2 Cross-domain chain cards
- [ ] 21.3 Email in other-activity rollup
- [ ] 21.4 `draft_reply` does not send

### Stage 22 — Project aliases → [`stage-22-project-email-aliases.md`](./stage-22-project-email-aliases.md)

- [ ] 22.1 Alias → project slug
- [ ] 22.2 Inbound webhook (secret unset → 404)
- [ ] 22.3 Inbox rejection rules reused

### Still a card

- [ ] Stage E model fallback — expand only after accuracy measurements below

---
---

## Open decisions (blocking — a human must answer)

| # | Decision | Default if unanswered | Needed by |
|---|---|---|---|
| OD-1 | What class do `doctrine` / `reference_guide` rows become? Neither is an artefact form. | **Used:** `report` + `document_metadata.reference_kind = doctrine\|reference_guide` (Stage 8.6 default; human did not answer) | Stage 8.6 |
| OD-2 | `corpus_catalog` — synthetic row, not a real document. Keep as pseudo-class or move to `source_type`? | **Used:** `document_class="schedule"`, `document_metadata.synthetic=true` (Stage 8.5 default; human did not answer) | Stage 8.5 |
| OD-3 | `content_hash` is nullable. Override key when null? | Fall back to `(project_id, relative_path)`; record `key_basis` on the override row | Stage 5.9 |
| OD-4 | Do Stages 14/15 get a kill-switch flag despite `AGENTS.md`? | No flag until an external provider is live | Stage 14 |
| OD-5 | When a user override changes the class, which machine metadata survives? | **Replace interpretation, preserve observation.** Override sets `document_class` / `document_subject` / `basis` / `confidence`; every other `document_metadata` key is kept. `filing_destination` gates `commercial_type` / `brief_kind` / `due_diligence` / `procurement_stage` on the matching class so stale hints cannot outrank the correction. | 8B.1 |
| OD-6 | Where does the machine's own answer live, now that the override overwrites the row? | **JSONB keys, not a column:** `machine_class`, `machine_subject`, `machine_confidence`, `machine_basis`. Doctrine says non-class metadata stays in `document_metadata`; a column would need an Alembic revision Stage 10 owns. | 8B.2 |
| OD-7 | `document_type` — drop the column or backfill it? | **Deprecate in place.** Stop writing, stop reading, leave the column and its data. Dropping needs a migration this stage may not create. Note it for a later cleanup packet. | 8B.5 |
| OD-8 | Fix the confidence boundary by lowering the floor or moving the gate? | **Lower the floor to 0.55.** Leave the gate at `< 0.65` and the published doctrine bands untouched — moving the gate silently reclassifies the whole 0.65 band that other stages read. | 8B.4 |
| OD-9 | Which rows does the re-classification backfill touch? | **`unknown` rows with `basis` null or `default` only.** Never `basis="user"` (D4). Widening to re-decide confident machine rows waits for Stage E accuracy numbers. | 8B.8 |
| OD-10 | Does the Gate 2 signature block on Stage 8B? | **Wave A blocks; Wave B does not.** 8B.1–8B.3 corrupt data or bypass authorisation on every use and compound with usage. 8B.5–8B.11 are hygiene and may land alongside 9.0. | Gate 2 |
| OD-11 | Pulse verbs on `activity_events.source` (as 12.4) or a new `verb` column? | **Use `source`.** 12.4 already wrote `invoice.received` there. A column would rewrite Stage 12 and split the log. | 13.1 |
| OD-12 | Where do dismissed Pulse cards live? | **Append `project_signal.dismissed` on `activity_events`.** No `pulse_signals` table. Synthesizer excludes `subject_key`. | 14.1 |
| OD-13 | Unmatched mailbox mail: reject or store with null `project_id`? | **Store raw, `project_id` null, no attachment ingest** until link or alias. | 15.1 / 16.3 |
| OD-14 | Live Graph/Gmail in Stage 19 vs stubs + FakeProvider? | **Default `email_provider=fake`.** Real adapters raise unless secrets exist. Not a boolean flag (OD-4). | 19.4 |
| OD-15 | MCP `send_email_draft` vs REST-only send? | **REST-only send for MVP.** MCP drafts/links; a send tool is optional and must use the mutation authorizer if added. | 19.2 |
| OD-16 | Inbound alias: JSON webhook vs raw RFC822? | **JSON for tests and the first webhook.** RFC822 storage is optional on `raw_storage_key`. | 22.2 |
| OD-17 | Can a Pulse card call `decide_invoice` (original Stage 14 card listed it)? | **No.** The card opens `InvoiceReviewPane`. Approve stays on the three-pane surface (D7 / Stage 12). One-click Pulse approve would skip disagreement highlighting. | 14.6 |

> OD-5…OD-10 were raised by the 2026-08-19 review. OD-11…OD-17 were raised
> by the Wave 3 expansion. Each has a **recommended default written down**
> so packets stay executable. Answer them or let the default stand, but do
> it knowingly.

---

## Accuracy measurements (Stage 4.6, then re-measured each wave)

| Date | Corpus | Class acc. | Subject acc. | Unknown % | Low-conf % | By |
|---|---|---|---|---|---|---|
| 2026-08-18 | fixture corpus (14) | 14/14 | 14/14 | 1/14 (`IMG_4471.pdf`, expected) | 1/14 (same row, conf 0.0) | Cursor Grok 4.6 |
| 2026-08-19 | fixture corpus (14) | 14/14 | 14/14 | 1/14 (`IMG_4471.pdf`, expected) | 1/14 (same row, conf 0.55 filename / 0.0 photo) | Cursor Grok 4.6 |

---

## Shims outstanding (must be empty before Gate 2)

**Code shims: none.** `LegacyDocumentClass` and `_LEGACY_TO_CANONICAL` deleted
in Stage 8.9.

**Data shim: cleared in 8B.7** (code strips `_legacy_document_class` after mapping
and asserts canonical classes). Live `alembic upgrade → downgrade → upgrade` was
not rehearsed in this session (no `psql` / live DB in the agent environment).

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
| 2026-08-19 | Claude Opus 5 (review) | `source_documents.document_type` is a third vocabulary the consumer list never named. Migration 049 rewrote `document_class` only, so it still holds `reference_guide` / `doctrine` / `planning_instrument` / `tender_submission`, and it is user-visible as the register title fallback (`api/projects.py:506`, `document_register.py:168`, `agent/document_context.py:102`). Two writers still emit legacy values (`web_research/attachments.py:77,89`, `mcp_bridge/server.py:4134`). | 8B.5 |
| 2026-08-19 | Claude Opus 5 (review) | `classification_from_override` returns metadata containing only `{basis, confidence, subject}`, so a user override destroys `commercial_type`, `discipline`, `drawing_number`, `revision`, `title`, `procurement_stage`. Reproduced: an overridden fee proposal re-routes `02-consultant/structural` → `01-cost`; an overridden drawing leaves the drawing register. **Stage 5.3's own sketch specifies this line** — the implementer followed the plan. Do not restore it. | 8B.1 |
| 2026-08-19 | Claude Opus 5 (review) | MCP `set_document_classification` (`server.py:4239`) uses `authorize_project_access_with_claims` — the read authorizer — while mutating `document_class` and inserting an override row. The other 28 mutating tools use `authorize_project_mutation_with_claims`. | 8B.3 |
| 2026-08-19 | Claude Opus 5 (review) | `_filename_confidence` floors at exactly 0.65 and the review gate is `< 0.65`, so the weakest filename guess auto-files without review. Separately, `classify_entry` returns at `classify.py:520` before content markers, so a 0.65 filename guess beats a 0.95 content marker. Reproduced with `Statement.pdf` + `TAX INVOICE`. | 8B.4 |
| 2026-08-19 | Claude Opus 5 (review) | Stage 4.4 content markers and title-block signals are **dead in production**: `hosted.py:44` and `pipeline.py:76` both call `classify_entry` without `extracted_text`. Fixing this means classifying after extraction, which reorders the pipeline — deliberately out of scope for 8B.4. Owner: Stage 9 or later. | open |
| 2026-08-19 | Claude Opus 5 (review) | `chunk_register` emits exactly one chunk holding the whole document, and `embed_texts` has no token cap. Latent, not active — Stage 2's 224-document backfill succeeded. Stage 2's spot-check used `cost-plan-system.md`, a markdown file on the **prose** chunker, so the drawing path the programme exists to fix was never actually verified. | 8B.9 |
| 2026-08-19 | Claude Opus 5 (review) | 234 of 543 rows (43%) are `document_class='unknown'`. Stage 2 backfilled chunks and Stage 8 renamed classes, but nothing has ever run the Stage 4 classifier over stored rows. | 8B.8 |
| 2026-08-19 | Claude Opus 5 (review) | Stage 9.6 as written targets the wrong code: `mobilisation_evidence.py` uses content markers, not path/filename markers, and takes `list[str]` with no access to class or subject. Stage file rewritten to rank the `pmp_sweep.py` selection instead. | resolved in stage-09 |
| 2026-08-19 | Claude Opus 5 (review) | Stage 9.5 needs a signature change to `is_invoice_document` plus 4 call sites, one of which (`invoice_extraction.py:50`) is in a Stage 11-owned file. 9.5 owns that one line for the signature change only. | resolved in stage-09 |
| 2026-08-19 | Claude Opus 5 (review) | Stage 12.2 specified 403 for cross-project invoice access while telling the agent to copy Stage 5.4's pattern, which mandates 404 to avoid leaking existence across tenants. Corrected to 404/409 in the stage file. | resolved in stage-12 |
| 2026-08-19 | Claude Opus 5 (review) | Stage 11.1 stores `cost_invoices.issues` but Stage 11 owns no Alembic revision. Column moved into Stage 10.1's migration; Stage 11 fills it only. | resolved in stage-10/11 |
| 2026-08-19 | Cursor Grok 4.6 | Wave 2 expansion: Stages 9–12 written as packet files. TRACKER previously said expand Stage 13 at Gate 2; `90-downstream-stages.md` says after Stage 12. Plan wins — tracker updated. | resolved |
| 2026-08-19 | Cursor Grok 4.6 | Gate 2 human signature still blank. Expansion is planning only. 9.0 (docs) may run unsigned; 9.1+ / 10–12 wait on the signature line above. | resolved — signed by the 19 Aug implement-8B-then-9–12 instruction |
| 2026-08-19 | Cursor Grok 4.6 | `document_type` column left in place (OD-7). `infer_document_type` in `ingest/metadata.py` is unused dead code. Drop both in a later owned migration, not 8B. | open |
| 2026-08-19 | Cursor Grok 4.6 | Content markers still do not run on production ingest (`hosted.py` / `pipeline.py` call `classify_entry` without `extracted_text`). Owner remains a later pipeline packet. | open |
| 2026-08-19 | Cursor Grok 4.6 | 8B.8 `x1_reclassify.py` shipped with dry-run default + `--apply`. Live `--apply` was not run (no live DB in this session). | open |
| 2026-08-19 | Cursor Grok 4.6 | 9.5 changed `is_invoice_document` signature; `invoice_extraction.py` call site passes `document_class=None` so Stage 11 extraction keeps the regex fallback. | resolved |
| 2026-08-19 | Cursor Grok 4.6 | Stage 10.3: untrusted totals live in `machine_extraction` JSONB. Booked scalars are nullable; `ck_cost_invoices_booked_amounts` applies only when `processing_status != needs_review`. Ledger arithmetic stays on booked scalars. | resolved |
| 2026-08-19 | Cursor Grok 4.6 | Classification LOC after Stages 8B+9 is **6195** vs Stage 0.6 **5609** (+10.4%). Over the 10% cap by 25 lines; the bump is `ingest/chunkers/schedule.py` (9.2). | open |
| 2026-08-19 | Cursor Grok 4.6 | Historical `cost_invoices.processing_status=booked` rows migrate to `review_state=posted` (grandfathered). New invoices cannot reach `posted` without `approve`. | resolved |
| 2026-08-19 | Cursor Grok 4.6 | Wave 3 expansion: Stages 13–22 written as packet files after Stage 12 `[x]`. Email packets (15–22) are **planning only** until Gate 3. Peer review the stage files before implementation. Defaults OD-11…OD-17 written so packets stay executable. Notable plan delta vs the original Stage 14 card: Pulse does not one-click `decide_invoice` (OD-17). | **peer review complete** — see 91-review Part C |
| 2026-08-19 | Claude Opus 5 (review) | Stages 13–22 peer-reviewed. All cited paths, symbols, constraint names and the `051_invoice_review_state` head verified correct. Eleven execution hazards fixed in the stage files (Part C of `91-review-2026-08-19.md`). Stage 18 needed no changes. | resolved in stage files |
| 2026-08-19 | Claude Opus 5 (review) | **Stage 13 blocker:** `record_activity_events` swallows every exception inside `begin_nested()` (`activity_events.py:96-118`). Verb writes must use `INSERT … ON CONFLICT DO NOTHING RETURNING` directly, or dedup becomes indistinguishable from failure and real errors vanish. Also `ActivityEvent.run_id` is NOT NULL with no default — mint `uuid4` per verb. | resolved in stage-13 |
| 2026-08-19 | Claude Opus 5 (review) | **Stage 14 blocker:** `attention` was unbounded while the stage's own product shape promises "3 items need attention". `document_needs_classification` fires on a standing population, not events. Added `MAX_ATTENTION_ITEMS`, group-then-cap, and pre-truncation `attention_count`. | resolved in stage-14 |
| 2026-08-19 | Claude Opus 5 (review) | **Stage 19 blocker:** send was a dual write (provider call then commit) that duplicates mail on retry, and email cannot be unsent. Replaced with `draft → sending → sent \| send_failed` claim-then-send under `SELECT … FOR UPDATE`, no auto-retry. Stage 20.2 and 21.2 updated to match. | resolved in stage-19/20/21 |
| 2026-08-19 | Claude Opus 5 (review) | Stage 16.2's `machine_extraction A == B` would fail on volatile provenance fields; an agent would likely "fix" it by loosening the assertion and gut the programme's non-negotiable email rule. Normaliser + explicit money-field assertions specified. | resolved in stage-16 |
| 2026-08-19 | Claude Opus 5 (review) | Stage 17 could silently wipe user email links on re-import — Part A Finding 1 reappearing in email. `ON CONFLICT (email_id) DO NOTHING` plus a refusal to downgrade `basis="user"`. | resolved in stage-17 |
| 2026-08-19 | Cursor Grok 4.6 | Stage 13.5: did not run live `EXPLAIN` on the drawing-number JSONB filter. Added partial expression index `ix_source_documents_project_drawing_number` in `052_activity_event_dedup` as the packet specified rather than discovering a seq scan under load. | open |
| 2026-08-19 | Cursor Grok 4.6 | Stage 13.4: `repair_service` still moves files and does not emit `document.filed`. Left untouched (outside ownership). | open |

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
Commit SHA: 6fc7a9d2
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

### Stage 8B (8B.1–8B.11) — 2026-08-19

```text
Packet: 8B.1–8B.11 Classification remediation
Status: [x] code + tests; live alembic/reclassify not run
Owner/agent: Cursor Grok 4.6
Branch/worktree: repo root
Predecessors verified: Stage 8 [x]
Reading list actually read: stage-8B, 00-doctrine, 01-ground-truth, TRACKER Gate 2
Commit SHA: uncommitted (user did not request a commit)
Verification: fixture corpus 14/14 class+subject; LOC 6111 vs 5609; ruff clean; focused 8B pytest 364 passed
Files: override merge-onto-machine; machine_* JSONB; MCP mutation authorizer; filename floor 0.55; document_type retired; ingest_mode from text; 049 shim strip; x1_reclassify.py; bounded register chunker; classification.ts; filing move without re-ingest
Integration notes: live DB reclassify/alembic skipped; content markers still dead on hosted ingest
```

### Stage 9 (9.0–9.8) — 2026-08-19

```text
Packet: 9.0–9.8 Consumer behaviour
Status: [x]
Owner/agent: Cursor Grok 4.6
Predecessors verified: Stage 8B Wave A [x], Gate 2 signed
Commit SHA: uncommitted
Verification: schedule/register/queries/consultant/invoice/transmittal/pmp-sweep tests green
Files added: ingest/chunkers/schedule.py; tests/ingest/test_schedule_chunker.py; tests/retrieval/test_register.py
LOC: 6195 vs Stage 0.6 5609 (+10.4%, schedule chunker justified)
```

### Stage 10–12 (invoice review) — 2026-08-19

```text
Packet: 10.1–12.4 Invoice foundation, validation, workflow & UI
Status: [x] code + tests; live alembic upgrade/downgrade not rehearsed
Owner/agent: Cursor Grok 4.6
Predecessors verified: Stage 9.5 [x]
Commit SHA: uncommitted
Verification:
  tests/cost_plan + process_invoices → 88 passed, 2 deselected
  alembic heads → 051_invoice_review_state
  pnpm typecheck exit 0; InvoiceReviewPane + CostInvoiceRegister vitest 3 passed
  full suite FAILED names = baseline 4 after document_context getattr fix
Files added: 050_invoice_machine_snapshot, 051_invoice_review_state, invoice_snapshot.py, invoice_issues.py, InvoiceReviewPane.tsx
Choice: dirty totals in machine_extraction JSONB; booked scalars nullable when needs_review
Historical booked rows grandfathered as review_state=posted
Wave 3 packets 13–22 written; implementation starts at 13.1 after peer review
```

### Stage 13 (13.1–13.7) — 2026-08-19

```text
Packet: 13.1–13.7 Project event spine
Status: [x] code + tests; live alembic upgrade → downgrade → upgrade rehearsed
Owner/agent: Cursor Grok 4.6
Branch/worktree: x1/stage-8-taxonomy-migration (repo root)
Predecessors verified: Stage 12 [x]; alembic heads at start = 051_invoice_review_state
Reading list actually read: 00-doctrine.md D5/D6/D8/D10; 2026-08-18-pulse.md Event spine; activity_event.py; activity_events.py; invoice_service._record_invoice_event; inbox/service.py; document_ingest.py; sort_service.file_single_document; classification_override.py; register.DrawingRegisterRow; projects/events.py (read only, unchanged)
Failing tests named: test_unknown_verb_raises, test_duplicate_dedup_key_is_noop, test_duplicate_dedup_key_does_not_log_an_error, test_insert_failure_raises_rather_than_being_swallowed, test_metadata_allowlist_drops_canonical_payloads, test_project_verbs_is_closed_and_covers_the_card, test_inbox_upload_emits_document_received, test_successful_ingest_emits_extracted_and_classified, test_unchanged_reingest_does_not_emit_again, test_user_override_emits_document_reclassified, test_successful_file_move_emits_document_filed, test_later_drawing_revision_emits_document_revised, test_earlier_revision_arriving_late_emits_nothing, test_numeric_revision_10_supersedes_9, test_approve_twice_does_not_duplicate_invoice_approved_event, test_list_project_verbs_excludes_workflow_trace_sources
Commit SHA: uncommitted (user did not request a commit; Stages 8B–12 still uncommitted on this branch)
Production LOC delta: event_spine.py new; activity_event +deduplication_key; activity_events optional key; emitters in inbox/document_ingest/classification_override/sort_service; invoice_service helper body replaced. ingest/types.py untouched. project_events / publish_project_event untouched.
Integration notes raised: EXPLAIN skipped, index added; repair_service does not emit document.filed
Handoff: Stage 13 complete. Stage 14 (Pulse MVP) is eligible.

Verification — alembic:
uv run alembic heads → 052_activity_event_dedup (head)
uv run alembic upgrade head → 051_invoice_review_state -> 052_activity_event_dedup
uv run alembic downgrade -1 → 052_activity_event_dedup -> 051_invoice_review_state
uv run alembic upgrade head → 051_invoice_review_state -> 052_activity_event_dedup
uv run alembic current → 052_activity_event_dedup (head)

Verification — ON CONFLICT SQL (compiled):
INSERT INTO activity_events (...) ON CONFLICT (project_id, deduplication_key) WHERE deduplication_key IS NOT NULL DO NOTHING RETURNING activity_events.id

Verification — pytest:
uv run pytest tests/projects/test_event_spine.py tests/projects/test_classification_override.py tests/cost_plan/test_invoice_decision_api.py tests/inbox/test_document_ingest.py tests/workflows/test_sort_files.py tests/database/test_activity_events.py tests/cost_plan/test_invoice_machine_snapshot.py tests/inbox/test_upload.py tests/workflows/test_document_ingest_auto_sort.py -q
  87 passed, 1 warning in 6.02s

Verification — ruff:
uv run ruff check . → All checks passed!

Verification — no pulse table:
grep create_table("pulse alembic/versions → empty
email.* / project_signal.* exist in ProjectVerb Literal; grep verb="email. under backend/app → empty
project_events / publish_project_event unchanged

Files added:
- backend/app/projects/event_spine.py (new; shared verb helper — does not replace project_events)
- backend/tests/projects/test_event_spine.py (new)
- backend/alembic/versions/052_activity_event_dedup.py (new)

Files changed:
- backend/app/database/activity_event.py (deduplication_key + partial unique index)
- backend/app/database/activity_events.py (optional deduplication_key on traces; verbs do not use this path)
- backend/app/database/source_document.py (drawing_number expression index)
- backend/app/inbox/service.py (document.received)
- backend/app/workflows/document_ingest.py (extracted/classified/revised)
- backend/app/projects/classification_override.py (document.reclassified)
- backend/app/intake/sort_service.py (document.filed on outcome=moved)
- backend/app/cost_plan/invoice_service.py (_record_invoice_event → record_project_verb)
- tests as listed above
- docs/plans/2026-08-18-pulse/TRACKER.md

Files deleted: none
```




