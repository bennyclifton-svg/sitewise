# Tender Completeness + Project Taxonomy — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> On approval, first copy this file to `docs/plans/2026-07-19-tender-completeness-project-taxonomy.md` and commit it (Phase 0, Task 0.1).

**Goal:** Every price printed in every uploaded quote appears in the tender matrix and report, reconciles to that quote's stated total, and the matrix rows become a per-project trade taxonomy generated from the quotes themselves (replacing the fixed 180-cell residential seed).

**Architecture:** The tender pipeline is a job-queue worker chain: `ingest_document → classify_document → extract_line_items → embed_items → map_items → run_expectations → infer_silence → run_analysis → generate_flags → assemble_report_draft`. This plan (a) rebuilds extraction around a deterministic per-page currency census + windowed LLM calls + a pure reconciliation module that proves `Σ counted items + residual = stated total`; (b) makes mapping unable to drop items (Unallocated bucket + sweep); (c) inserts a new fan-in stage `generate_project_taxonomy` that creates per-comparison trade rows anchored to the canonical taxonomy; (d) normalises comparison to ex-GST; (e) adds ledger/drill-down endpoints + UI so every cell and every column total is clickable down to line items.

**Tech stack:** FastAPI + SQLAlchemy (async, psycopg) + Alembic + pgvector on Supabase Postgres; OpenAI structured outputs; React + TypeScript frontend (hand-rolled `api` fetch object, no react-query); pytest.

---

## ⚠️ SAFETY RULES FOR EVERY EXECUTOR — READ FIRST

1. `backend/.env` `DATABASE_URL` points at the **LIVE Supabase database**. NEVER run plain `pytest` from `backend/`. Run only the specific test file you are working on:
   `cd backend; .venv\Scripts\python.exe -m pytest tests/tender/test_<name>.py -v`
   The migration roundtrip test (`tests/tender/test_migrations.py`) DROPS ALL TENDER TABLES if its env guard is bypassed. Do not set `ALLOW_DESTRUCTIVE_TEST_DATABASE` or `TENDER_MIGRATION_ROUNDTRIP`.
2. If taxonomy seeds are ever lost (`ValueError: tender taxonomy seed data has no active cells`), reseed:
   `python -m tender.seeds.load` then `python -m tender.services.embedding`. Health probe: `select count(*) from taxonomy_cells where active` → 180 (before Phase 3 adds one).
3. Migrations here are additive-only (new tables, nullable columns). Apply with `cd backend; .venv\Scripts\alembic.exe upgrade head` only after the migration file is reviewed. Never write a downgrade that drops populated tables beyond your own new ones.
4. Old comparison runs are NOT migrated. After the pipeline changes, the MERRICK comparison is re-run fresh through the UI (all derived tables regenerate).
5. Windows environment. Python is `backend\.venv\Scripts\python.exe`. Frontend: `cd frontend; pnpm test` / `pnpm build`.
6. Before modifying any function, READ it first — line numbers below are from 2026-07-19 exploration and may drift.

## Verified problem statement (why each phase exists)

Live MERRICK run (`tender_comparisons` id `7abca355-966d-4450-acb6-60492dc2382e`, project `08133c6e`):

| Quote | Builder | Stated total | Extracted | Problem |
|---|---|---|---|---|
| Quote 2 | Coastal Builders | $3,547,495 inc GST | 17 items / $574,822 (16%) | 36-category pricing table on pp.10-11 mostly missed by the single whole-doc LLM extraction call |
| Quote 1 | Montique | $3,605,841 inc GST | 42 items / $1,201,930 (33%) | Lump sum + ~45 nested PS allowances; "included" sum = $0 because every item is PS-status |
| Quote 3 | Toussaint | $3,482,868 inc GST | 129 items / $3,036,255 | Items are ex-GST vs inc-GST stated total (basis mismatch); 10 items incl. $20k fix carpentry silently dropped at mapping (empty allocations → no `tender_mappings` row → invisible everywhere incl. QA queue) |

Structural defects (all code-verified):
- `backend/tender/llm/openai_client.py:33-59` — extraction is ONE LLM call over all page text; page images unused.
- `backend/tender/services/mapping.py:1041-1055` (`_add_mapping_rows`) — empty `decision.allocations` writes zero rows; `services/expectations.py:536-558` inner-joins mappings → item vanishes from grid/totals/report/QA.
- `services/expectations.py:482-510` — one status per cell by priority (excluded beats included); `services/totals.py:25` `COUNTED_STATUSES` zeroes non-included cells → included money destroyed.
- `services/totals.py:66-76` — reconciliation vs `tender_quotes.stated_total_cents` is diagnostic-only.
- `frontend/src/components/project/tender/TenderMatrix.tsx:591-621` — cells clickable only when QA questions exist; NO line-item drill-down endpoint exists in `backend/tender/router.py`.
- Matrix rows = fixed seed taxonomy `data/tender/taxonomy.yaml` (180 cells, 22 groups, Class-1 residential).

Product decisions (Benny, 2026-07-19): capture EVERY printed figure classified by role; matrix compares **ex-GST**; native figures in drill-down summing to native stated totals; taxonomy = quote-derived per comparison with optional canonical anchors; non-comparable bases (Toussaint's excluded builder's margin) flagged, never guessed.

## Design invariants (cite these in code comments and tests as I1–I5)

- **I1** Every printed dollar figure exists as a `tender_line_items` row (rollups + reprinted duplicates included, marked). Verified by deterministic census, never LLM self-report.
- **I2** Per quote: `Σ counted items + residual_cents = stated_total_cents` (native basis); residual stored + rendered.
- **I3** Every non-duplicate item has ≥1 mapping row, fractions summing to 1.0; fallback target = Unallocated (a real matrix row).
- **I4** Σ matrix column (incl. Unallocated + Not-itemised rows) = quote computed ex-GST total. Money is never discarded by status.
- **I5** Ex-GST comparison; native in drill-down; cost-plus columns flagged non-comparable.

---

## MASTER TODO LIST

- [x] **Phase 0** — Branch, plan commit, pytest guard rails
- [ ] **Phase 1** — Migration **034** (ledger columns + reconciliation table) + model/schema updates
- [ ] **Phase 2** — Extraction overhaul (census → windowed extraction → reconciliation) + quote-ledger endpoint + `QuoteLedgerPanel`
- [ ] **Phase 3** — No-drop mapping + money-conserving grid + always-clickable cells + cell drill-down
- [ ] **Phase 4** — Migrations **035/036** + `generate_project_taxonomy` stage + mapping retarget + matrix rows from trades
- [ ] **Phase 5** — Ex-GST totals + reconciliation strip + non-comparable flags in UI
- [ ] **Phase 6** — Expectations/silence/benchmarks via anchor cells
- [ ] **Phase 7** — Report overhaul + golden fixtures/eval gates + E2E MERRICK acceptance

> **Migration renumber (2026-07-19):** Stages 3–6 already claimed `029`–`033` on
> `main`. This plan’s former `029`/`030`/`031` are implemented as
> `034_tender_ledger_completeness`, then `035`/`036` for project trades.
> `down_revision` for Phase 1 is `033_remove_unused_hermes_session`.

Each phase = one PR. Do not start a phase until the previous phase's "Definition of done" checks pass.

---

# Phase 0 — Setup and guard rails

**Todo:**
- [ ] 0.1 Branch + commit plan copy
- [ ] 0.2 pytest addopts guard

### Task 0.1: Branch and plan document

1. `cd "d:\AI Projects\clerk"; git checkout -b feature/tender-completeness`
2. Copy this plan to `docs/plans/2026-07-19-tender-completeness-project-taxonomy.md`.
3. `git add docs/plans/2026-07-19-tender-completeness-project-taxonomy.md; git commit -m "docs(tender): completeness + project taxonomy implementation plan"`

### Task 0.2: Deselect integration tests by default

**Files:** Modify: `backend/pyproject.toml`

1. Read `backend/pyproject.toml`, find `[tool.pytest.ini_options]` (it declares the `integration` marker but no `addopts`).
2. Add inside that section: `addopts = "-m 'not integration'"` . If an `addopts` already exists, append `-m 'not integration'` to it.
3. Verify: `cd backend; .venv\Scripts\python.exe -m pytest tests/tender/test_totals.py -v` runs and `tests/tender/test_migrations.py` is deselected when named with the marker filter active. Expected: totals tests pass (green baseline).
4. Commit: `git commit -am "test(tender): deselect integration marker by default"`

---

# Phase 1 — Schema: ledger tree, roles, reconciliation (Migration 029)

**Todo:**
- [ ] 1.1 Migration file 029
- [ ] 1.2 ORM models
- [ ] 1.3 Pydantic schema fields
- [ ] 1.4 Model tests

### Task 1.1: Migration `029_tender_ledger_completeness`

**Files:** Create: `backend/alembic/versions/029_tender_ledger_completeness.py`

1. Confirm head: `cd backend; .venv\Scripts\alembic.exe heads` → expect `028_project_decision_revisions` (or similar 028). Use that exact id as `down_revision`.
2. Write the migration. Upgrade ops:
   - `tender_line_items` add columns (ALL nullable unless stated):
     - `parent_id UUID` FK → `tender_line_items.id` ON DELETE CASCADE
     - `role VARCHAR(32)` + CHECK in `('contract_component','pc_allowance','ps_allowance','optional_upgrade','informational','excluded')`
     - `is_rollup BOOLEAN NOT NULL server_default 'false'`
     - `duplicate_of_id UUID` FK → `tender_line_items.id` ON DELETE SET NULL
     - `gst_basis VARCHAR(8)` + CHECK in `('inc','ex','unknown')`
     - `amount_ex_gst_cents BIGINT`
     - `counted_in_total BOOLEAN NOT NULL server_default 'false'`
     - `figure_key VARCHAR(64)`
     - Index `ix_tender_line_items_quote_parent` on `(quote_id, parent_id)`
   - Create table `tender_quote_reconciliations`:
     `id UUID PK default gen_random_uuid(); quote_id UUID FK→tender_quotes UNIQUE NOT NULL ON DELETE CASCADE; comparison_id UUID FK→tender_comparisons NOT NULL ON DELETE CASCADE; stated_total_cents BIGINT NULL; stated_basis VARCHAR(8) CHECK in ('inc','ex','unknown') NULL; gst_line_cents BIGINT NULL; counted_total_cents BIGINT NOT NULL DEFAULT 0; computed_ex_gst_cents BIGINT NULL; residual_cents BIGINT NOT NULL DEFAULT 0; status VARCHAR(16) NOT NULL CHECK in ('reconciled','residual','not_stated','non_comparable'); checks JSONB NOT NULL DEFAULT '[]'; uncaptured JSONB NOT NULL DEFAULT '[]'; created_at/updated_at timestamptz`
   - `tender_flags`: extend the `flag_type` CHECK constraint to add `'unreconciled_residual','non_comparable_basis','suspect_number_format'` (drop + recreate constraint; copy the existing allowed list from `backend/tender/models.py` FLAG_TYPES and append).
   - Downgrade: drop the new table, new columns, restore old CHECK. (Never touches existing data.)
3. Apply: `.venv\Scripts\alembic.exe upgrade head`. Expected output ends `Running upgrade 028_... -> 029_tender_ledger_completeness`.
4. Commit: `git commit -am "feat(tender): migration 029 ledger tree, roles, reconciliation table"`

### Task 1.2: ORM models

**Files:** Modify: `backend/tender/models.py`

1. At the enum block (top of file, ~lines 35-120): add tuples
   `LINE_ITEM_ROLES = ("contract_component","pc_allowance","ps_allowance","optional_upgrade","informational","excluded")`,
   `GST_BASES = ("inc","ex","unknown")`, `RECONCILIATION_STATUSES = ("reconciled","residual","not_stated","non_comparable")`; append the three new flag types to `FLAG_TYPES`.
2. On `TenderLineItem` (~line 285): add the eight new mapped columns exactly matching 029.
3. Add class `TenderQuoteReconciliation` matching the table, with `quote` / `comparison` relationships (follow the style of `TenderCellStatus`).
4. Add the fixed map used everywhere legacy `item_status` is still needed:
   ```python
   ROLE_TO_ITEM_STATUS = {
       "contract_component": "included",
       "pc_allowance": "pc_allowance",
       "ps_allowance": "ps_allowance",
       "optional_upgrade": "note",
       "informational": "note",
       "excluded": "excluded",
   }
   ```
5. Run: `.venv\Scripts\python.exe -m pytest tests/tender/test_models.py -v` → PASS.
6. Commit: `git commit -am "feat(tender): ORM for ledger tree + reconciliation"`

### Task 1.3: Extraction schema fields

**Files:** Modify: `backend/tender/schemas.py` (ExtractedLineItem ~line 363); Test: `backend/tests/tender/test_extraction_schemas.py`

1. Write failing test: `ExtractedLineItem` accepts `figure_key="p10-t1-r3"`, `parent_figure_key=None`, `role="contract_component"`, `gst_basis="inc"`, `is_rollup=True`, `duplicate_of_figure_key=None`, `printed_text="$159,123.20"`; and rejects `role="bogus"`.
2. Run it → FAIL (unknown fields / no validation).
3. Add the fields to `ExtractedLineItem` (Literal types for role/gst_basis; all new fields optional with defaults `None`/`False` except `figure_key: str` required, `printed_text: str` required). Keep every existing field untouched (`item_status` stays — the LLM no longer needs to emit it; make it optional if currently required, computed later via `ROLE_TO_ITEM_STATUS`).
4. Run → PASS. Also run `test_schemas.py` → PASS.
5. Commit: `git commit -am "feat(tender): extraction schema carries figure tree + roles + gst basis"`

### Phase 1 Definition of done
- [ ] `alembic heads` shows 029; app boots (`.venv\Scripts\python.exe -c "import app.main"` from `backend/` or start uvicorn briefly)
- [ ] `pytest tests/tender/test_models.py tests/tender/test_schemas.py tests/tender/test_extraction_schemas.py` all green

---

# Phase 2 — Extraction overhaul + quote ledger (HIGHEST RISK)

**Todo:**
- [ ] 2.1 Census module (pure, TDD)
- [ ] 2.2 Reconciliation module (pure, TDD)
- [ ] 2.3 Prompt v0.2.0 + windowed extraction
- [ ] 2.4 Handler: write tree + recon row + flags
- [ ] 2.5 Ledger service + endpoint
- [ ] 2.6 Frontend `QuoteLedgerPanel`
- [ ] 2.7 Live smoke test on MERRICK

### Task 2.1: Currency census (new pure module)

**Files:** Create: `backend/tender/services/census.py`; Test: `backend/tests/tender/test_census.py`

1. Write failing tests first (no DB, no LLM):
   ```python
   from tender.services.census import census_page, CensusToken

   def test_finds_currency_tokens():
       text = "Total price for demolition services listed above is $46,100 (incl GST)."
       toks = census_page(text, page_no=2)
       assert [t.cents for t in toks] == [4610000]

   def test_ignores_abn_phone_and_bare_numbers():
       text = "ABN: 96150010021 Ph: 0409 142 319 built in 2026 for 331.000 m2"
       assert census_page(text, page_no=1) == []

   def test_flags_malformed_grouping():
       toks = census_page("Internal balustrade and handrail - $9,5556.80", page_no=3)
       assert toks[0].suspect_format is True and toks[0].cents == 955680  # parsed, flagged
   ```
2. Run: `pytest tests/tender/test_census.py -v` → FAIL (module missing).
3. Implement:
   ```python
   """Deterministic per-page currency census. Invariant I1's measuring stick."""
   import re
   from dataclasses import dataclass

   CURRENCY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{2})?)")
   GROUPING_RE = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})?$")
   CONTEXT_BLOCKLIST = re.compile(r"(ABN|ACN|Ph|Phone|Mobile|Fax|Lic|Reg)\s*:?\s*$", re.IGNORECASE)

   @dataclass(frozen=True)
   class CensusToken:
       page_no: int
       raw: str            # e.g. "$46,100"
       cents: int
       context: str        # ±40 chars around the match
       suspect_format: bool

   def census_page(text: str, page_no: int) -> list[CensusToken]:
       out = []
       for m in CURRENCY_RE.finditer(text or ""):
           before = text[max(0, m.start() - 40):m.start()]
           if CONTEXT_BLOCKLIST.search(before):
               continue
           digits = m.group(1)
           cents = int(round(float(digits.replace(",", "")) * 100))
           if cents == 0:
               continue
           out.append(CensusToken(
               page_no=page_no,
               raw=m.group(0).strip(),
               cents=cents,
               context=text[max(0, m.start() - 40):m.end() + 40],
               suspect_format=not GROUPING_RE.fullmatch(digits),
           ))
       return out
   ```
   Reuse `currency_to_cents` from `backend/tender/schemas.py:405-430` instead of the inline float conversion if its signature fits strings like `"46,100.00"` — read it first; prefer one parser in the codebase (DRY).
4. Run → PASS. Commit: `git commit -am "feat(tender): deterministic currency census (I1)"`

### Task 2.2: Reconciliation module (new pure module — the core of I2)

**Files:** Create: `backend/tender/services/reconciliation.py`; Test: `backend/tests/tender/test_reconciliation.py`

Concepts: input is the merged list of extracted figures (schema objects from Task 1.3) + `stated_total_cents` + `gst_treatment`. Output is a `LedgerResult` with tree links, `duplicate_of` marks, per-node identity checks, chosen counting frontier (`counted_in_total` flags), ex-GST amounts, residual, status.

1. Write failing tests for the three real shapes (synthetic minimal versions):
   - **Coastal shape:** 3 top-level category rollups (inc GST) summing exactly to stated; one PS child nested under a category. Assert: categories `counted_in_total=True`, PS child False, `residual_cents == 0`, `status == "reconciled"`, `amount_ex_gst_cents == round(inc / 1.1)`.
   - **Toussaint shape:** 2 sections each with 2 ex-GST items; section rollups printed; a SUMMARY table reprinting both section totals; stated total inc GST with an explicit GST line. Assert: SUMMARY rows get `duplicate_of` set (and never counted); frontier = items (deepest reconciling); `Σ ex + gst_line == stated` accepted; status reconciled.
   - **Montique shape:** single lump-sum figure == stated; 3 PS children. Assert: lump sum counted, children not, residual 0.
   - **Residual case:** drop one category from the Coastal shape → `status == "residual"`, `residual_cents == missing amount`.
2. Run → FAIL. 3. Implement. Required pieces (complete the bodies; keep every function pure):
   ```python
   GST_RATE = 0.10
   COUNTABLE_ROLES = {"contract_component", "pc_allowance", "ps_allowance"}

   def build_tree(figures): ...        # parent_figure_key -> parent link; roots = no parent
   def mark_duplicates(figures): ...   # same cents + (same leading section number OR normalised-label
                                       # SequenceMatcher ratio >= 0.85) and one sits under a section whose
                                       # heading matches r"summary|quoted categories" (case-insens.)
                                       # -> summary-side figure.duplicate_of_figure_key = body figure
   def to_ex_gst(cents, basis): ...    # inc -> round(cents / (1 + GST_RATE)); ex -> cents; unknown -> None
   def rollup_checks(tree, tol): ...   # per rollup: {"figure_key", "printed_cents", "child_sum_cents", "delta_cents"}
   def select_counting_frontier(tree, stated_total_cents, stated_basis, gst_line_cents, tol_ratio):
       # Candidate frontiers, in order; each excludes duplicates and roles not in COUNTABLE_ROLES:
       #   F0 = roots; F1 = roots with each is_rollup-with-children replaced by its children;
       #   F2 = all leaves.
       # reconciles(F): S_inc = sum of inc-basis figures; S_ex = sum of ex-basis figures.
       #   stated inc: ok if |S_inc + round(S_ex*1.1) - stated| <= tol  OR  |S_inc + S_ex + gst_line - stated| <= tol
       #   stated ex : ok if |S_ex + round(S_inc/1.1) - stated| <= tol
       # Return the DEEPEST reconciling frontier (F2 > F1 > F0). If none reconciles,
       # return the frontier with the smallest |residual| plus that residual.
   def reconcile_quote(figures, stated_total_cents, gst_treatment, tol_ratio) -> LedgerResult: ...
   ```
   `tol_ratio` comes from `settings.tender_reconciliation_tolerance` (see `backend/app/config.py:90-96`) — pass it in, don't import settings in the pure module.
4. Run → PASS. Commit: `git commit -am "feat(tender): deterministic ledger reconciliation (I2)"`

### Task 2.3: Prompt v0.2.0 + windowed extraction calls

**Files:** Create: `backend/tender/llm/prompts/extract_line_items_v0.2.0.md`; Modify: `backend/tender/llm/openai_client.py` (PROMPT_VERSION, `extract()`), `backend/tender/services/extraction.py`; Test: `backend/tests/tender/test_extraction_service.py` (extend)

1. New prompt file. Key rules (write them out fully in the file):
   - Capture EVERY printed dollar figure: line items, section totals, subtotals, grand totals, PC/PS allowance tables, optional upgrades, priced exclusions, informational figures.
   - Emit `figure_key` = `p{page}-{ordinal-on-page}`; `parent_figure_key` when the figure sits inside a priced section/category; `is_rollup` true for totals of other figures; `role` classification; `gst_basis` ONLY when printed next to the figure ("inc GST", "ex GST", "+GST"), else `unknown`; `printed_text` verbatim including `$` and commas; never repair, round, or invent numbers; `duplicate_of_figure_key` when the same figure is a reprint in a summary table.
   - You see a WINDOW of pages; earlier windows' section headings are given as context; only emit figures printed in your window.
2. `openai_client.py`: bump `PROMPT_VERSION = "0.2.0"` (this rolls `extract_cache.EXTRACTOR_VERSION` automatically — verify by reading `backend/tender/services/extract_cache.py`; old cache rows simply miss). Change `extract()` to accept a page subset + optional `page_images: list[bytes]` and include images as vision content parts when provided.
3. `extraction.py` — replace the single-call flow inside `extract_line_items` with:
   1. `tokens = [census_page(p.text_content, p.page_no) for p in pages]`
   2. Window pages (size 4, overlap 1). `asyncio.gather` with `asyncio.Semaphore(settings.tender_extraction_concurrency or 4)` — copy the semaphore pattern from `mapping.map_prepared_line_items`.
   3. Merge windows: figures deduped by `figure_key`; overlap page figures deduped preferring the later window.
   4. Per page, diff census cents-multiset vs extracted cents-multiset. Pages with missing tokens → ONE targeted re-extract of that single page (“every $ figure on this page; here are the ones already found; find the rest”), attaching the page PNG from `tender_pages.image_path` when `len(census tokens) > 3 × len(extracted figures on page)` (thin text layer → vision). This is a bounded deterministic check, NOT a regenerate loop (house rule).
   5. Still-missing tokens → `uncaptured` list `[{page_no, raw, context}]` passed to the handler.
   6. Run `reconciliation.reconcile_quote(...)` over the merged figures.
   Keep `_gate_item`/confidence logic for per-item confidence; reconciliation replaces `_reconcile`'s role (read `_reconcile` at `extraction.py:128-189` and delete/absorb it, keeping its arithmetic-inconsistency flag emission via the new `checks`).
4. Tests (fake LLM client, existing pattern in `test_extraction_service.py`): window splitting, merge dedup, census-diff triggers exactly one re-extract call for a page with a missing token, uncaptured propagation.
5. Run the file's tests → PASS. Commit: `git commit -am "feat(tender): windowed census-verified extraction v0.2.0"`

### Task 2.4: Handler writes tree + reconciliation row

**Files:** Modify: `backend/tender/services/extraction_handler.py`; Test: `backend/tests/tender/test_extraction_handler.py` (extend)

1. In `extract_line_items_job` (read it fully first — it deletes+reinserts `tender_line_items` for the document, then caches + backfills `stated_total_cents` at lines ~85-95):
   - Insert figures in two passes: parents (no `parent_figure_key`) first, build `figure_key → id` map, then children with `parent_id`; same for `duplicate_of_id`. Set `role`, `is_rollup`, `gst_basis`, `amount_ex_gst_cents`, `counted_in_total`, `figure_key`, and legacy `item_status = ROLE_TO_ITEM_STATUS[role]`.
   - Upsert `tender_quote_reconciliations` for the quote (one row per quote — if multiple documents per quote, re-run reconciliation over ALL the quote's figures after each document).
   - Flags: census `suspect_format` → `suspect_number_format` (severity `caution`); `status == "residual"` beyond tolerance → `unreconciled_residual` (severity `warning`, `include_in_report=True`); populate `uncaptured`.
   - Keep the existing stated-total backfill (`quote_total_cents` → `stated_total_cents` when unset) BEFORE reconciliation runs.
2. Tests: given fake extraction output shaped like mini-Coastal, assert DB rows have correct parent links, counted flags, one recon row, flag rows. Use the existing async DB fixtures from `backend/tests/conftest.py`.
3. Run → PASS. Commit: `git commit -am "feat(tender): persist ledger tree + reconciliation per quote"`

### Task 2.5: Quote ledger service + endpoint

**Files:** Create: `backend/tender/services/ledger.py`; Modify: `backend/tender/router.py`, `backend/tender/schemas.py`; Test: `backend/tests/tender/test_api_ledger.py`

1. Response schema (`schemas.py`): `QuoteLedgerResponse { quote_id, builder_name, stated_total_cents, stated_basis, status, residual_cents, computed_ex_gst_cents, uncaptured: [...], items: [LedgerItem] }`; `LedgerItem { id, figure_key, page_no, description_raw, printed_text, amount_cents, amount_ex_gst_cents, gst_basis, role, is_rollup, counted_in_total, duplicate_of_id, parent_id, children: [LedgerItem] }`. The residual, when non-zero, is appended by the service as a synthetic item `{figure_key: "residual", description_raw: "Unexplained difference vs stated total", amount_cents: residual}` so the rendered list ALWAYS sums to stated (I2).
2. `ledger.py`: `async def build_quote_ledger(session, comparison_id, quote_id) -> QuoteLedgerResponse` — select items ordered `(page_no, figure_key)`, assemble tree in memory.
3. Router: `GET /api/tender/comparisons/{comparison_id}/quotes/{quote_id}/ledger`, owner-guarded exactly like `GET .../matrix` (`router.py:620`) — copy its dependency wiring.
4. API test (pattern from `test_api_matrix_taxonomy.py`): seeded mini-quote → response items sum (counted + residual) == stated.
5. Run → PASS. Commit: `git commit -am "feat(tender): quote ledger endpoint (every price, summing to stated total)"`

### Task 2.6: Frontend `QuoteLedgerPanel`

**Files:** Create: `frontend/src/components/project/tender/QuoteLedgerPanel.tsx`; Modify: `frontend/src/lib/api.ts` (add `getTenderQuoteLedger` near `getTenderMatrix` ~line 393), `frontend/src/lib/types/tender.ts` (mirror `QuoteLedgerResponse`), `frontend/src/components/project/tender/TenderMatrix.tsx` (header)

1. `api.ts`: `getTenderQuoteLedger: (comparisonId: string, quoteId: string) => apiRequest(...)` — follow the exact style of neighbouring functions (bearer auth wrapper).
2. `QuoteLedgerPanel.tsx`: props `{comparisonId, quoteId, onClose}`; `useEffect` + `useState` fetch (copy the loading/error pattern from `TenderMatrix.tsx:69-104`); render an indented tree table: description, page, role chip, native amount, ex-GST amount; duplicates greyed with "reprint" tag; uncounted rows visually muted; footer rows: counted sum, residual (highlighted when ≠ 0), stated total. Currency formatting via existing helpers in `format.ts`.
3. `TenderMatrix.tsx` header: on each quote column header add a "Ledger" button toggling the panel for that quote.
4. Verify: `cd frontend; pnpm build` → no type errors. Manual check deferred to 2.7.
5. Commit: `git commit -am "feat(tender): quote ledger drill-down UI"`

### Task 2.7: Live smoke test on MERRICK

1. Start the stack per repo skill `.claude/skills/verify` (backend uvicorn + `python -m tender.worker` + frontend dev server).
2. In the UI create a NEW comparison for the MERRICK project from the three quote files, process it, wait for extraction to finish (worker logs).
3. Read-only SQL acceptance (psql or a scratch script):
   - `select builder_name, r.status, r.residual_cents, r.counted_total_cents, q.stated_total_cents from tender_quote_reconciliations r join tender_quotes q on q.id=r.quote_id where r.comparison_id='<new id>';`
   - Expected: Coastal & Montique `status in ('reconciled','residual')` with `counted_total_cents` within tolerance of stated (NOT 16%/33% anymore); Toussaint reconciled via GST-line identity; Montique has a `suspect_number_format` flag.
4. Open each quote's Ledger panel → list sums to stated total, residual visible if any.
5. Fix anything that fails BEFORE proceeding. Commit fixes individually.

### Phase 2 Definition of done
- [ ] `pytest tests/tender/test_census.py tests/tender/test_reconciliation.py tests/tender/test_extraction_service.py tests/tender/test_extraction_handler.py tests/tender/test_api_ledger.py tests/tender/test_extract_cache.py` green
- [ ] MERRICK smoke: all three recon rows exist, coverage ≥ 95% of stated per quote, ledger UI sums correct

---

# Phase 3 — No-drop mapping + money-conserving grid + drill-down

**Todo:**
- [ ] 3.1 Unallocated seed cell
- [ ] 3.2 Mapping fallback + sweep (I3)
- [ ] 3.3 Grid per-role aggregation (I4)
- [ ] 3.4 Totals rewrite
- [ ] 3.5 Cell drill-down endpoint
- [ ] 3.6 Always-clickable cells UI

### Task 3.1: Seed `99.01 Unallocated`

**Files:** Modify: `data/tender/taxonomy.yaml`; Test: `backend/tests/tender/test_seed_loader.py` (extend)

1. Append group `99` ("Unallocated") with one cell `{code: "99.01", name: "Unallocated / uncategorised", stage: base}` following the file's compact format (read the header `meta.defaults` first). No synonyms (it must never win T0/T1).
2. Reload seeds: `cd backend; .venv\Scripts\python.exe -m tender.seeds.load` (idempotent upsert). Verify: `select count(*) from taxonomy_cells where active;` → 181.
3. In `backend/tender/services/mapping.py` define `UNALLOCATED_CELL_CODE = "99.01"` and exclude it from every LLM candidate list (T1 candidate query, `scope_cells_for_t3` at ~line 444).
4. Commit: `git commit -am "feat(tender): unallocated bucket cell 99.01"`

### Task 3.2: Mapping can never drop an item (I3)

**Files:** Modify: `backend/tender/services/mapping.py` (`_add_mapping_rows` ~1041-1055, end of `map_items` ~176-226); Test: `backend/tests/tender/test_mapping_t2_t3.py`, `backend/tests/tender/test_map_items_handler.py` (extend)

1. Failing tests: (a) a `MappingDecision` with empty `allocations` produces exactly one `tender_mappings` row with `cell_code == "99.01"`, `allocation_fraction == 1.0`, `qa_state == "needs_review"`, adjudication JSON containing the original failure reason; (b) after `map_items`, the zero-drop query returns 0:
   ```sql
   select count(*) from tender_line_items li
   left join tender_mappings m on m.line_item_id = li.id
   where li.quote_id = :q and li.duplicate_of_id is null and m.id is null
   ```
2. Implement: in `_add_mapping_rows`, when `allocations` is empty build the fallback row; add `_sweep_unmapped(session, quote_id)` executed at the end of `map_items` inserting fallback rows for any remaining unmapped non-duplicate items. Skip duplicates (`duplicate_of_id is not null`) from mapping input entirely (they're reprints).
3. Run tests → PASS. Commit: `git commit -am "fix(tender): no-drop mapping with unallocated fallback (I3)"`

### Task 3.3: Grid keeps money per role (I4)

**Files:** Modify: `backend/tender/services/expectations.py` (`_mapped_status_draft` ~423, `_status_priority` ~482-510, `_allocated_amount` ~501-510, `_mapped_items_for_comparison` ~536-558); Modify: `backend/tender/models.py` + new migration only if `amount_breakdown` was not added earlier — **add it here**: small migration `029b` adding `tender_cell_status.amount_breakdown JSONB NULL` and `'mixed'` to its status CHECK (or fold into 029 if Phase 1 not yet merged); Test: `backend/tests/tender/test_cell_status_grid.py` (extend)

1. Failing test: two items in one cell — included $100 + excluded $50 — produce `status == "mixed"`, `amount_cents == 100_00` (ex-GST counted sum), `amount_breakdown == {"contract_component": 10000, "excluded": 5000, "item_count": 2}`.
2. Implement: aggregation keyed `(quote_id, cell_code)`; sum `amount_ex_gst_cents × allocation_fraction` per role over **counted, non-duplicate** items only; `amount_cents` := Σ over `COUNTABLE_ROLES`; `status` := single role's legacy status when uniform, else `mixed` (display-only — never used for money again). Extend `MappedCellItem` with `role`, `counted_in_total`, `amount_ex_gst_cents`.
3. Run grid + expectations + silence test files → PASS (fix fallout: `test_expectations.py`, `test_infer_silence.py` consume statuses).
4. Commit: `git commit -am "feat(tender): per-role money-conserving cell aggregation (I4)"`

### Task 3.4: Totals from reconciliation + conservation assert

**Files:** Modify: `backend/tender/services/totals.py` (whole module), `backend/tender/schemas.py` (`MatrixQuoteTotal`); Test: `backend/tests/tender/test_totals.py` (rewrite)

1. Failing tests: column total == recon `computed_ex_gst_cents`; response carries `basis="ex"`, `residual_cents`, `unallocated_cents` (sum of 99.01 cell), `not_itemised_cents` (computed − Σ itemised cells), `stated_native_cents`, `non_comparable` true when `tender_quotes.contract_type == "cost_plus"`.
2. Implement `compute_quote_totals(session, comparison_id)` reading `tender_quote_reconciliations` + cell sums. Keep the function signature used by `matrix.py:112` and `report.py:286` or update both call sites.
3. Run: `pytest tests/tender/test_totals.py tests/tender/test_api_matrix_taxonomy.py -v` → PASS.
4. Commit: `git commit -am "feat(tender): ex-GST conserved totals with residual + unallocated"`

### Task 3.5: Cell drill-down endpoint

**Files:** Modify: `backend/tender/router.py`, `backend/tender/services/ledger.py`; Test: `backend/tests/tender/test_api_ledger.py` (extend)

1. `GET /api/tender/comparisons/{comparison_id}/cells/{cell_code}/items?quote_id=` → `{cell_code, name, quote_id, items: [{line_item_id, description_raw, page_no, role, allocation_fraction, amount_cents, amount_ex_gst_cents, mapping_tier, qa_state}], sum_ex_gst_cents}`. Query: `tender_mappings` join `tender_line_items` filtered by comparison/quote/cell. Add `getTenderCellItems` to `frontend/src/lib/api.ts`.
2. Test: seeded cell with 2 allocations returns both with correct fractions and sum. Commit: `git commit -am "feat(tender): cell line-item drill-down endpoint"`

### Task 3.6: Always-clickable matrix cells

**Files:** Modify: `frontend/src/components/project/tender/TenderMatrix.tsx` (MatrixCellRow ~501-625, totals row ~436-473); Create: `frontend/src/components/project/tender/TenderCellDrilldown.tsx`

1. Remove the `questions.length || mappingChoices.length` gate — every cell with any mapped items (or any cell at all) renders as `<button>`; clicking sets `activeCell` as today.
2. `TenderCellDrilldown.tsx`: fetches `getTenderCellItems`; renders the item list + sum; when the cell also has QA questions/mapping choices, render the existing `MatrixQaPanel` content beneath (import and compose — do not duplicate its logic).
3. Mount drilldown where `MatrixQaPanel` mounts today (~line 348-373), replacing it as the container.
4. Append pseudo-rows to the flattened rows: `Unallocated` (cell 99.01) and `Not itemised in quote` (from totals `not_itemised_cents`, no drill-down). Totals row shows `computed ex-GST` + reconciliation badge.
5. `pnpm build` → clean. Manual: run stack, click cells, verify sums. Commit: `git commit -am "feat(tender): every matrix cell drills down to line items"`

### Phase 3 Definition of done
- [ ] Zero-drop SQL returns 0 on a fresh MERRICK re-run; Toussaint's "51.01 Internal Fix Carpentry $20,000" visible (mapped or Unallocated)
- [ ] Σ every matrix column (cells + unallocated + not-itemised) == recon computed ex-GST (spot-check SQL)
- [ ] Grid/mapping/totals/api test files green

---

# Phase 4 — Project-generated taxonomy (Migrations 030/031)

**Todo:**
- [ ] 4.1 Migrations 030 (tender_project_trades) + 031 (mapping/cell_status trade targets)
- [ ] 4.2 ORM + trades endpoints
- [ ] 4.3 Fan-in barrier + worker stage
- [ ] 4.4 Generation service + prompt
- [ ] 4.5 Mapping retarget T0–T3
- [ ] 4.6 Matrix rows from trades (+ legacy fallback)
- [ ] 4.7 QA/corrections retarget

### Task 4.1: Migrations

**Files:** Create: `backend/alembic/versions/030_tender_project_trades.py`, `backend/alembic/versions/031_tender_mapping_trade_target.py`

- 030: table `tender_project_trades`: `id UUID PK; comparison_id FK NOT NULL ON DELETE CASCADE; code VARCHAR(32) NOT NULL; name TEXT NOT NULL; description TEXT; group_label VARCHAR(64); sort_order INT NOT NULL DEFAULT 0; source VARCHAR(16) NOT NULL CHECK in ('generated','manual') DEFAULT 'generated'; anchor_cell_codes TEXT[]; anchor_confidence NUMERIC; seed_assignments JSONB NOT NULL DEFAULT '[]'; embedding VECTOR(1536); created_at`. Unique `(comparison_id, code)`.
- 031: `tender_mappings` add `project_trade_id UUID` FK→tender_project_trades ON DELETE CASCADE; ALTER `cell_code` DROP NOT NULL; CHECK `(cell_code IS NOT NULL OR project_trade_id IS NOT NULL)`; add `'taxonomy_seed'` to the tier CHECK. `tender_cell_status` add `project_trade_id UUID` FK; `cell_code` DROP NOT NULL; drop the `(comparison_id, quote_id, cell_code)` unique constraint, create two partial unique indexes (`...cell_code) WHERE cell_code IS NOT NULL`, `...project_trade_id) WHERE project_trade_id IS NOT NULL`).
- Apply, verify `alembic heads` = 031. Commit.

### Task 4.2: ORM + read endpoints

**Files:** Modify: `backend/tender/models.py`, `backend/tender/router.py`, `backend/tender/schemas.py`; Test: `backend/tests/tender/test_api_matrix_taxonomy.py` (extend)

`TenderProjectTrade` model; `GET /api/tender/comparisons/{id}/trades` returning ordered trades (+ reserved `PT.UNALLOC`). Commit.

### Task 4.3: Barrier + worker stage

**Files:** Modify: `backend/tender/services/continuations.py`, `backend/tender/services/embedding.py` (`embed_items` chain), `backend/tender/worker.py` (HANDLERS), `backend/tender/router.py` (retry stages); Test: `backend/tests/tender/test_worker_continuation.py` (extend)

1. `embed_items` stops enqueuing `map_items`; sets quote stage to `map_items` (waiting) as it already advances stages — read `QUOTE_STAGES` in `models.py:47-60`; no new stage value needed.
2. In `continuations.after_job_complete` add `_enqueue_taxonomy_if_ready(comparison_id)`: clone `_enqueue_expectations_if_ready` (advisory lock `pg_advisory_xact_lock`, checks all quotes reached `map_items` and no `embed_items`/`extract_line_items` jobs active) → enqueue single `generate_project_taxonomy` job for the comparison.
3. Handler completion enqueues `map_items` per quote. Register kind in `worker.py` HANDLERS and in `MANUAL_COMPARISON_STAGES` (router retry).
4. Barrier tests: 3 quotes, taxonomy enqueued exactly once (concurrency-safe), map_items fan-out after. Commit.

### Task 4.4: Generation service

**Files:** Create: `backend/tender/services/project_taxonomy.py`, `backend/tender/llm/prompts/generate_project_taxonomy_v0.1.0.md`; Test: `backend/tests/tender/test_project_taxonomy.py`

1. Deterministic prep (pure functions, TDD):
   - `counted_sections(session, quote_id)` → the counting-frontier rollups/sections `{section_label, amount_ex_gst_cents, figure_key}` (fall back to top-level items when a quote has no rollups, e.g. Montique → its PS groups).
   - `alignment_hints(sections_by_quote)` → pairs with (a) embedding cosine of labels ≥ 0.75 (reuse `embedding.py` embed util) OR (b) amount-band match: `|a−b|/max(a,b) ≤ 0.15`, including 2-element subset sums per side (this encodes "Cabinetry $360,300 ≈ Joinery $345,059 + benchtops $45,671 ≈ JOINERY $138,000 + STONE $38,000" as candidate alignments).
2. One frontier structured-output call. Inputs: `ProjectContext` (from `tender_comparisons.context`), per-quote section lists, hints, canonical cell catalog (code+name only). Output schema `{trades: [{code: "PT.01", name, description, group_label, sort_order, per_quote_sections: {quote_id: [figure_key]}, anchor_cell_codes: [..] | null, confidence}]}`. Prompt instructions: trade granularity fits the project scale (broad for a $3.5M new build; narrow for a small industrial upgrade); every input section must appear in exactly one trade's `per_quote_sections`; anchors only when confident; use the project's own trade language.
3. Deterministic post-validation: unknown anchor codes → drop the anchor, keep the trade; any input section not assigned → auto-trade named after that section (nothing dropped); always insert `PT.UNALLOC`; write `seed_assignments` from `per_quote_sections`; embed trade name+description into `embedding`.
4. Idempotent: trades already exist and job payload lacks `regenerate: true` → skip straight to fan-out.
5. Tests with fake LLM: assignment completeness, unknown-anchor handling, idempotency. Commit.

### Task 4.5: Mapping retarget

**Files:** Modify: `backend/tender/services/mapping.py` (T0 ~466, T1 ~496-525, T2 ~570-744, T3 ~759-867, `_add_mapping_rows`); prompts `map_items_t2_*`, `map_items_t3_*` bumped v0.2.0; Test: `test_mapping_t0_t1.py`, `test_mapping_t2_t3.py` (extend)

1. When the comparison has project trades, the cascade targets trades:
   - **T0 (new first rung):** item's counted-frontier ancestor `figure_key` ∈ some trade's `seed_assignments` for that quote → map to that trade, `tier="taxonomy_seed"`, `auto_pass`, fraction 1.0. (Covers most items — the generator already assigned the sections.)
   - **T1:** cosine against trade embeddings for the comparison — load all (≤ ~60) into memory, `numpy` dot; same accept threshold/margin settings.
   - **T2/T3:** identical machinery, candidate codes = trade codes (+`none_of_these`); T3 receives the full trade list.
   - Fallback/sweep targets `PT.UNALLOC` (via `project_trade_id`) instead of cell 99.01.
2. No trades on the comparison (legacy) → cascade unchanged against `taxonomy_cells`.
3. Tests for T0 seed match, T1 trade cosine, fallback-to-PT.UNALLOC. Commit.

### Task 4.6: Grid/matrix keyed by trade + legacy fallback

**Files:** Modify: `backend/tender/services/expectations.py` (grid keys), `backend/tender/services/matrix.py` (`build_matrix` ~23-112), `backend/tender/services/totals.py` (unallocated source); Test: `test_cell_status_grid.py`, `test_api_matrix_taxonomy.py` (extend)

Grid drafts keyed `(quote_id, project_trade_id)` writing `tender_cell_status.project_trade_id`; matrix rows from `tender_project_trades` ordered by `sort_order`, grouped by `group_label`; when the comparison has no trades keep the existing cell_code path verbatim (legacy comparisons still render). Drill-down endpoint gains trade addressing: `GET .../trades/{trade_id}/items?quote_id=` (keep the cells route for legacy). Commit.

### Task 4.7: QA + corrections retarget

**Files:** Modify: `backend/tender/services/qa.py` (review queue mapping arm, resolve), `backend/tender/services/corrections.py` (`record_mapping_correction`), `frontend/src/components/project/tender/MatrixQaPanel.tsx` (`MappingChoiceControl` choices from `getTenderTrades`); Test: `backend/tests/tender/test_api_qa.py`, `test_corrections.py` (extend)

Resolve/correct accepts a `project_trade_id` target; corrections to a single-anchor trade also upsert a canonical `taxonomy_synonyms` row (flywheel preserved; skip when unanchored). Commit.

### Phase 4 Definition of done
- [ ] Fresh MERRICK re-run produces 20–60 trades in the matrix using project language (e.g. a "Joinery / cabinetry" row with Coastal ≈ $327k ex, Montique ≈ $314k ex, Toussaint $138k ex all aligned on it)
- [ ] Zero-drop invariant still 0; column conservation still holds; QA mapping corrections work against trades
- [ ] Mapping/grid/matrix/QA test files green

---

# Phase 5 — Ex-GST comparison surfaced (UI)

**Todo:**
- [ ] 5.1 Reconciliation strip + basis badges + non-comparable flag

**Files:** Modify: `frontend/src/components/project/tender/TenderMatrix.tsx` (header ~380-400, `MatrixTotalsRow` ~436-473, `TotalReconciliation` ~475-499), `frontend/src/components/project/tender/format.ts`, `frontend/src/lib/types/tender.ts`

1. All cell amounts + totals display ex-GST (they already are, from Phase 3 data); label the totals row "Total (ex GST)".
2. Under each column total render the strip: `Stated (native): $X inc GST · Counted: $Y · Residual: $Z` with residual highlighted when ≠ 0; "Not stated" case per existing `TotalReconciliation`.
3. Cost-plus / `non_comparable` columns get a persistent amber badge: "Cost-plus — excludes builder's margin; not directly comparable" (copy text may live in `data/tender/report_language.yaml` — follow existing report-language key pattern).
4. Fix today's header-vs-footer inconsistency: header quote figure = stated native (labelled), footer = computed ex-GST (labelled).
5. `pnpm build`; manual visual check; commit.

---

# Phase 6 — Expectations / silence / benchmarks via anchors

**Todo:**
- [ ] 6.1 Expectation → trade adapter
- [ ] 6.2 Silence over trades
- [ ] 6.3 Benchmarks/analysis retarget

**Files:** Modify: `backend/tender/services/expectations.py` (`evaluate_rules` consumers, `_silent_status_draft` ~452), `backend/tender/services/silence.py` (`SilenceCell` construction), `backend/tender/services/analysis.py` (`_analysis_inputs`, gap matrix keys), `backend/tender/services/benchmarks.py`; Tests: `test_expectations.py`, `test_infer_silence.py`, `test_analysis_flags.py`, `test_benchmarks.py` (extend)

1. `evaluate_rules` stays canonical (fires cell codes). Adapter: fired cell → trades whose `anchor_cell_codes` contain it; expected-but-unmapped trade per quote → `silent_ambiguous` + queue silence. Additionally (anchor-independent): trade priced in ≥1 quote and absent in another → `silent_ambiguous` for the absent quote (cross-quote presence is itself the expectation).
2. `infer_silence` evidence packet: union of anchor cells' synonyms/bundling parents; unanchored trades skip LLM silence (status stays `silent_ambiguous` with cross-quote evidence note).
3. Benchmarks: single-anchor trades inherit `benchmark_key`; multi/unanchored skip (v1). Gap matrix + ledgers keyed by trade code.
4. Tests per piece; commit per task.

---

# Phase 7 — Report, golden fixtures, eval gates, E2E acceptance

**Todo:**
- [ ] 7.1 Report: trade matrix + reconciliation strip + full ledger appendix
- [ ] 7.2 MERRICK golden fixtures + annotations
- [ ] 7.3 Eval metrics + completeness runner + gates
- [ ] 7.4 Final E2E acceptance run

### Task 7.1: Report

**Files:** Modify: `backend/tender/services/report.py` (`load_report_data` ~257, `_report_matrix` ~757, `render_draft_markdown` ~376), `backend/tender/report_templates/section_03_price_comparison.html`, `section_04_comparison_matrix.html`; Create: `backend/tender/report_templates/section_09_quote_ledgers.html`; Test: `backend/tests/tender/test_report_assembly.py` (extend)

Matrix section renders trades; price-comparison section gains the reconciliation strip + non-comparable note; new appendix section renders each quote's full ledger (every figure: counted, nested, duplicates marked, residual line) — reuse `ledger.build_quote_ledger`. Add `mixed` glyph to `GLYPHS`. Commit.

### Task 7.2: Golden fixtures

**Files:** Copy `data/real-project-data/*.pdf` → `backend/tests/tender/fixtures/` (Coastal-Builders.pdf, Montique.pdf, Toussaint.pdf); Modify: `data/tender/golden/manifest.yaml`, Create: `data/tender/golden/annotations/{coastal,montique,toussaint}.json`; Modify: `backend/tender/eval/golden.py` (annotation schema)

1. Read `manifest.yaml` + `annotations/enmore.json` first; mirror their structure exactly. Extend the annotation item schema with `role, parent, gst_basis, counted, duplicate_of` and a quote-level block `{stated_total_cents, stated_basis, expected_residual_cents}`.
2. Bootstrap annotations programmatically: run census + the new extractor over each PDF, dump to JSON, then MANUALLY verify the top-level identities against the documents (Coastal: 36 categories listed on pp.10-11 summing to $3,547,495 inc; Montique: lump $3,605,841 + 45 PS figures; Toussaint: 77 sections, sub $3,166,243.55 ex + GST $316,624.36). The manual check is the point — do not skip it.
3. `data/tender/tools/validate.py` (seed cross-checker) must still pass. Commit.

### Task 7.3: Eval metrics + gate

**Files:** Modify: `backend/tender/eval/metrics.py`, `backend/tender/eval/runners.py`; Test: `backend/tests/tender/test_eval_metrics.py` (extend)

New metrics: `printed_figure_recall` (extracted ∩ annotation figures / annotation figures, matched on cents+page), `counted_sum_reconciles` (bool per doc), `dedup_precision`, `role_accuracy`. New `CompletenessRunner` following `eval/runners.py` mapping-runner pattern. Gate values asserted in tests for the three MERRICK docs: recall ≥ 0.99, reconciles == True. Commit.

### Task 7.4: Final E2E acceptance (the user's success criteria)

1. Fresh MERRICK comparison via UI end-to-end (extract → taxonomy → map → QA accept-all → analysis → report build).
2. Acceptance checklist (record results in the PR description):
   - [ ] Every quote's Ledger lists every price and sums (counted + residual) to its stated total — Benny's foundational criterion
   - [ ] Zero-drop SQL == 0 for all quotes
   - [ ] Σ each matrix column == recon computed ex-GST
   - [ ] Matrix rows are project trades in project language; joinery-type row aligns all three builders' cabinetry money
   - [ ] Toussaint column shows the cost-plus non-comparable badge; Montique `$9,5556.80` flagged `suspect_number_format`
   - [ ] Report contains full per-quote ledger appendix + reconciliation strip
3. Save a short run report (counts, residuals, screenshots) and update the memory file `pmp-coverage-advisory-backfill`-style entry for the tender module.

---

## Rollback / risk notes for executors

- Extraction (Phase 2) is the highest-risk change. If windowed extraction underperforms, the census diff quantifies exactly what's missing per page — debug from the census, not from vibes.
- Phase 4 touches QA plumbing; keep the legacy cell_code paths working at every step (all changes conditional on "comparison has project trades").
- Every phase leaves `main`-mergeable state; do not interleave phases in one PR.
- LLM cost/latency: extraction goes from 1 call to ~⌈pages/3⌉ parallel calls + occasional single-page retries; taxonomy adds 1 frontier call per comparison; T0 seed-matching removes most per-item mapping LLM calls. Net latency should improve on the current serial cascade.
