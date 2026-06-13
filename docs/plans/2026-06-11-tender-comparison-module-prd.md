# Tender Comparison Module — PRD

- **Date:** 2026-06-11
- **Status:** Draft for acceptance
- **Repo target:** `docs/plans/2026-06-11-tender-comparison-module-prd.md`
- **Owner:** Ben (operator + reviewer)
- **Depends on:** Clerk core (projects, drafts, auth, storage, cockpit shell)
- **Related:** `2026-06-07-clerk-practice-intelligence-integration-prd.md`

---

## 1. Summary

The Tender Comparison Module ("TCM") adds a second cockpit workflow to Clerk:
**Run Tender Comparison**. It ingests 2–5 builder quotes for a residential
(Class 1) project in NSW/VIC/QLD, normalises every quote into a canonical
taxonomy, infers the meaning of silence (excluded vs bundled vs not required),
benchmarks allowances against market data, and assembles a customer-facing
comparison report as an auditable Clerk draft. The operator reviews and
approves every report in the cockpit before delivery.

v1 is a **concierge product with an industrial backend**: customers never log
in. They receive a PDF. All software effort goes into the pipeline and the QA
console, because that is where speed, accuracy, and eventual automation live.

## 2. Context & Product Direction

- The core pain point in residential building is **trust at the moment of
  commitment**: quotes are structurally incomparable, exclusions are hidden,
  allowances are gamed, and customers cannot tell a fair deal from a trap.
- The wedge product is **quote/tender normalisation**: a paid, per-project
  comparison report (~$299–499 retail) that makes 2–5 quotes truly
  apples-to-apples and arms the customer with specific questions.
- Clerk already provides the right substrate: project scoping, document
  storage, drafts-as-auditable-artifacts, grounded citation ethos, FastAPI +
  Supabase + pgvector, VPS/Dokploy hosting.
- TCM extends — never entangles — that substrate. The module must remain
  cleanly severable: if TCM becomes its own product, it lifts out with its
  tables, services, prompts, and seed data intact.

## 3. Goals / Non-Goals

### Goals (v1)

1. Process a full quote set (2–5 quotes, mixed PDF quality) end-to-end to an
   approved report with ≤ 2 hours of operator QA time per comparison.
2. Normalise quotes into the Class 1 taxonomy with cell-level provenance
   (document, page, bounding box) on every mapped figure.
3. Classify every expected-but-unstated scope item as
   `excluded | bundled | ps_covered | not_required | ambiguous`, with evidence.
4. Flag unrealistic PC/PS allowances against a confidence-tagged benchmark DB.
5. Produce a report draft (HTML + PDF) through Clerk's draft lifecycle, with
   operator approval gating delivery.
6. Ship an evaluation harness with a golden set, so every prompt/model/rule
   change is measured before merge.
7. Capture every QA correction as structured data that improves the synonym
   dictionary and (later) model fine-tuning.

### Non-Goals (v1)

- No customer login, portal, or self-serve upload (Phase 2: thin public
  intake page + Stripe payment link).
- No Class 2 / multi-residential (schema fields reserved, logic deferred).
- No contract review, design tools, builder marketplace, or construction
  tracking.
- No builder recommendations. TCM normalises documents; it never ranks
  builders.
- No automated report delivery without operator approval.

## 4. Users & Operating Model

| Role | Who | Surface | Job |
| --- | --- | --- | --- |
| Operator | Ben (construction pro) | Clerk cockpit | Intake, QA, approve, deliver |
| Customer | Homeowner / reno client | Email + PDF | Understand quotes, negotiate |
| Reviewer (later) | Contract QS | Cockpit (QA role) | Scale QA beyond founder |

Operating model v1: customer emails quote documents (or operator collects
them), operator creates the comparison in the cockpit, pipeline runs, operator
clears the QA queue, approves the draft, sends the PDF. Target turnaround:
**24 hours** from documents-received to report-delivered.

## 5. v1 Scope

| Dimension | In scope | Notes |
| --- | --- | --- |
| Building class | Class 1a (houses), incl. renovations & additions | Class 2 deferred |
| Build types | New build (volume + custom), renovation, addition | Reno quotes carry higher QA load by design |
| Geography | NSW, VIC, QLD; metro + regional tags | State-specific statutory cells |
| Documents | Quote letters, inclusions schedules, tender forms, priced BOQs, trade breakdowns, addenda; native + scanned PDF, XLSX, DOCX | Drawings stored but not parsed in v1 |
| Quotes per comparison | 2–5 | Hard cap 6 |
| Languages | English (AU) | — |

## 6. Cockpit Workflow (UX)

State machine for a comparison:

```
intake → processing → qa → report_draft → approved → delivered
                 ↘ failed (retryable per stage)
```

1. **Intake.** Operator creates/selects a Clerk project, then a Tender
   Comparison. Intake form captures project context (Section 8,
   `tender_comparisons.context`). Context is mandatory before processing —
   it drives the expectation engine and extraction prompts.
2. **Upload.** Operator attaches documents per quote (per builder). Each file
   is stored via Clerk's storage layer; TCM registers it in
   `tender_documents` and enqueues ingestion.
3. **Processing.** Background worker advances each quote through the pipeline
   (Section 9). Cockpit shows per-quote stage status with retry controls.
4. **QA.** Operator works the review queue (Section 12) until all items are
   `auto_pass | confirmed | corrected`. Pipeline computes; operator decides.
5. **Report draft.** Worker assembles the report as a Clerk draft artifact.
   Operator edits headline narrative text inline (structured data is
   regenerated, never hand-edited).
6. **Approve & deliver.** Approval freezes the report version, renders final
   PDF, records `approved_by`. Delivery (email) is manual in v1; the PDF and
   delivery timestamp are recorded.

## 7. Architecture

### 7.1 Module boundary

```
backend/
└── tender/
    ├── __init__.py
    ├── router.py            # FastAPI APIRouter, mounted at /api/tender
    ├── models.py            # SQLAlchemy models (tender_* tables only)
    ├── schemas.py           # Pydantic I/O + LLM JSON schemas
    ├── services/
    │   ├── ingestion.py     # storage registration, OCR, page rendering
    │   ├── classification.py
    │   ├── extraction.py    # structured line-item extraction
    │   ├── mapping.py       # tier 0–3 cascade
    │   ├── expectations.py  # deterministic expectation engine
    │   ├── silence.py       # evidence assembly + adjudication
    │   ├── analysis.py      # gaps, comparables, allowance realism
    │   ├── benchmarks.py
    │   └── report.py        # draft assembly, HTML→PDF render
    ├── llm/
    │   ├── client.py        # provider-agnostic interface
    │   ├── openai_client.py # default per repo stack
    │   └── prompts/         # versioned prompt files (see 7.5)
    ├── worker.py            # job loop (shared image, separate process)
    └── seeds/               # loaders for data/tender/*
```

Rules of the boundary:

- TCM owns all `tender_*` tables. It references Clerk's `projects`,
  `documents`/storage, `drafts`, and `users` by FK only.
- **TCM does not use Clerk's RAG chunking pipeline.** Clerk ingestion is
  retrieval-oriented (chunks for citation in chat). TCM extraction is
  schema-oriented (typed line items with coordinates). They share only the
  upload/storage layer. Quote documents MAY additionally be chunked into the
  project corpus so project chat can cite them, but TCM logic never reads
  chunks.
- No Clerk core module imports from `backend/tender/`. One-way dependency.

### 7.2 Pipeline overview

Per quote, jobs run in sequence; per comparison, quotes run in parallel:

```
ingest_document → classify_document → extract_line_items → embed_items
   → map_items → run_expectations → infer_silence → run_analysis
   → generate_flags → assemble_report_draft   (comparison-level, last 4)
```

Stages are idempotent: each writes its outputs keyed by stable IDs and may be
re-run after correction (e.g., re-run `infer_silence` after a mapping fix
without re-extracting).

### 7.3 Background jobs (VPS-friendly, no Redis)

- A `tender_jobs` table is the queue. Worker polls with
  `SELECT ... FOR UPDATE SKIP LOCKED` (poll interval 2s, batch 1).
- Worker is the same container image as the API, run as a second Dokploy
  service with command `python -m backend.tender.worker`. Scale by adding
  worker replicas; SKIP LOCKED makes this safe.
- Retries: exponential backoff, max 3 attempts, then `failed` with
  `last_error`; cockpit exposes per-stage retry.
- Long-running stages (OCR, extraction) checkpoint per document/page so a
  retry resumes rather than restarts.

### 7.4 OCR & page rendering

- Detect text layer per page (PyMuPDF). Pages below a text-density threshold
  are OCR'd with `ocrmypdf` (Tesseract) — runs locally on the VPS, keeps the
  system self-contained. Record `ocr_applied` and per-page confidence.
- Every page is rendered to PNG at 150 DPI at ingest (`tender_pages.image_path`)
  so the QA console can show source-region highlights without re-rendering.
- XLSX/DOCX inputs: convert to normalised intermediate (openpyxl /
  python-docx → structured rows) and a rendered PDF (LibreOffice headless)
  so provenance highlighting works uniformly.
- Escape hatch: if a document's OCR confidence is catastrophically low, the
  stage flags it `manual_transcription_required` rather than emitting junk.

### 7.5 LLM strategy

- **Provider abstraction.** `llm/client.py` defines two operations:
  `extract(document_pages, schema, context) -> typed JSON` and
  `adjudicate(question, choices, evidence, context) -> {choice, confidence,
  rationale}`. Default implementation targets OpenAI (per repo stack) with
  JSON-schema-enforced structured outputs. Model names are config keys, never
  hardcoded: `TENDER_MODEL_EXTRACT`, `TENDER_MODEL_ADJUDICATE_SMALL`,
  `TENDER_MODEL_ADJUDICATE_FRONTIER`, `TENDER_EMBED_MODEL`.
- **Embeddings:** OpenAI `text-embedding-3-small`, 1536 dims →
  `vector(1536)` columns. (If the embed model ever changes, a migration must
  re-embed; dims are pinned in config and asserted at startup.)
- **Cost architecture.** Open questions are never sent to a model when a
  constrained question will do. Tier structure (Section 9.3) routes ~all
  volume to dictionary/embedding matching and small-model multiple-choice
  adjudication; frontier calls are reserved for low-confidence and
  one-to-many splits. Taxonomy context blocks are stable strings to maximise
  provider-side prompt caching.
- **Prompt versioning.** Prompts live in `backend/tender/llm/prompts/` as
  files with semver headers. Every LLM output row records
  `{model, prompt_version, request_id}`. No prompt edits without an eval run
  (Section 14).
- **Determinism boundary.** LLMs classify and map. They never do arithmetic.
  All totals, deltas, comparables, and percentages are computed in Python
  from typed data.

## 8. Data Model

All tables prefixed `tender_` except shared seed tables (`taxonomy_*`,
`benchmarks`, `expectation_rules`), created by Alembic migrations in the main
chain. FKs to Clerk core: `projects.id`, `users.id`, `drafts.id`.

### 8.1 `tender_comparisons`

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| project_id | uuid fk → projects | |
| status | enum | `intake, processing, qa, report_draft, approved, delivered, failed` |
| context | jsonb | validated by Pydantic `ProjectContext` (below) |
| created_by | uuid fk → users | |
| created_at / updated_at | timestamptz | |

`ProjectContext` (Pydantic, versioned `context_version`):

```python
state: Literal["NSW", "VIC", "QLD"]
region: Literal["metro", "regional"]
build_type: Literal["new_build", "renovation", "addition"]
dwelling_class: Literal["class_1a"]          # reserved for class_2 later
storeys: int
floor_area_m2: float | None
site_area_m2: float | None
soil_class: Literal["A","S","M","H1","H2","E","P","unknown"]
slope_class: Literal["flat","moderate","steep","unknown"]
bal_rating: Literal["none","12.5","19","29","40","FZ","unknown"]
wind_rating: str | None                       # e.g. N2, N3, C1
flood_overlay: bool | None
heritage_overlay: bool | None
existing_dwelling_era: str | None             # reno: asbestos likelihood signal
demolition_required: bool | None
spec_level: Literal["builder_base","mid","high","architectural"]
target_budget_cents: int | None
notes: str | None
```

### 8.2 `tender_quotes`

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| comparison_id | uuid fk | |
| builder_name | text | |
| builder_abn | text null | |
| quote_ref / quote_date | text / date null | |
| stated_total_cents | bigint null | as printed on the quote |
| gst_treatment | enum | `inclusive, exclusive, unclear` |
| contract_type | enum | `hia, mba, custom, cost_plus, unknown` |
| validity_days | int null | |
| stage | enum | pipeline stage cursor |
| created_at / updated_at | timestamptz | |

### 8.3 `tender_documents` / `tender_pages`

```
tender_documents: id, quote_id fk, storage_path, original_filename,
  mime_type, doc_type enum(quote_letter, inclusions_schedule, tender_form,
  boq, trade_breakdown, addendum, drawing, other), classification_confidence
  numeric, ocr_applied bool, page_count int, ingest_status enum

tender_pages: id, document_id fk, page_no int, image_path text,
  text_content text, ocr_confidence numeric null
```

### 8.4 `tender_line_items`

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid pk | |
| quote_id / document_id | uuid fk | |
| page_no | int | |
| bbox | jsonb | `{x0,y0,x1,y1}` in page coords (provenance highlight) |
| description_raw | text | verbatim |
| section_path | text[] | document headings above the item |
| qty / unit | numeric null / text null | |
| rate_cents / amount_cents | bigint null | |
| item_status | enum | `included, excluded, pc_allowance, ps_allowance, note` |
| allowance_cents | bigint null | for PC/PS items |
| extraction_confidence | numeric | 0–1 |
| embedding | vector(1536) | of normalised description |

> Definitions used throughout: **PC (prime cost)** = a supply allowance for a
> selectable item (tapware, tiles, appliances). **PS (provisional sum)** = an
> allowance for work whose scope is not yet defined (labour + materials, e.g.
> "site costs", "rock excavation").

### 8.5 Taxonomy & knowledge tables

```
taxonomy_cells: id, code text unique (e.g. "03.05"), parent_code null,
  name, grp enum (Section 10 groups), stage enum(prelim, base, lockup,
  fixing, completion, external, statutory), description,
  applicability jsonb,            -- expectation predicate refs
  bundling_parents text[],        -- codes that commonly absorb this cell
  region_tags text[],             -- e.g. {"NSW"}, {"QLD:regional"}
  build_type_tags text[],         -- {"new_build","renovation","addition"}
  benchmark_key text null, sort_order int, active bool, version int

taxonomy_synonyms: id, cell_code fk, phrase text, phrase_norm text
  (lowercased/stemmed, unique with cell_code), source enum(seed, correction,
  auto), confidence numeric, correction_id fk null, created_at

expectation_rules: id, rule_code unique, cell_code fk, predicate jsonb
  (Appendix A DSL), severity enum(must, should, conditional),
  rationale text, region_tags text[], build_type_tags text[], version int

benchmarks: id, benchmark_key, state, region, build_type, spec_level,
  metric enum(absolute, per_m2, pct_of_build, ratio),
  p25 / p50 / p75 numeric, unit text,
  source enum(model_seed, published, observed),
  provenance text, confidence enum(low, medium, high),
  effective_date date, superseded_by fk null
```

### 8.6 Mapping, status, flags

```
tender_mappings: id, line_item_id fk, cell_code fk, allocation_fraction
  numeric default 1.0,            -- one-to-many splits sum to 1.0 per item
  tier enum(t0_exact, t1_embedding, t2_small_llm, t3_frontier, human),
  confidence numeric, adjudication jsonb (candidates, model, prompt_version,
  request_id, rationale), qa_state enum(auto_pass, needs_review, confirmed,
  corrected), reviewed_by fk null, reviewed_at

tender_cell_status: id, comparison_id, quote_id, cell_code,
  status enum(included, excluded_explicit, pc, ps, bundled, not_required,
  silent_ambiguous), amount_cents bigint null, bundled_into_cell text null,
  evidence jsonb (Appendix B packet), confidence numeric,
  qa_state enum(auto_pass, needs_review, confirmed, corrected),
  reviewed_by null, reviewed_at
  UNIQUE (comparison_id, quote_id, cell_code)

tender_flags: id, comparison_id, quote_id null, cell_code null,
  flag_type enum(gap, low_pc_allowance, unrealistic_ps, missing_expected,
  scope_ambiguity, price_outlier, exclusion_risk, statutory_missing,
  arithmetic_inconsistency),
  severity enum(info, caution, warning), headline text, detail text,
  evidence jsonb, include_in_report bool default true,
  qa_state enum(needs_review, confirmed, suppressed)

tender_corrections: id, entity_type, entity_id, field, before jsonb,
  after jsonb, reviewer fk, reason text null, created_at
  -- every QA edit lands here; corrections feed taxonomy_synonyms and
  -- the fine-tuning corpus

tender_reports: id, comparison_id fk, draft_id fk → drafts, version int,
  html_path, pdf_path, approved_by fk null, approved_at, delivered_at,
  delivery_note text

tender_jobs: id, kind, comparison_id fk null, quote_id fk null,
  payload jsonb, status enum(queued, running, done, failed),
  attempts int, locked_at, locked_by, last_error, run_after timestamptz,
  created_at / updated_at
```

### 8.7 Evaluation tables

```
golden_documents: id, storage_path, doc_meta jsonb, anonymised bool,
  source enum(real, synthetic), difficulty enum(easy, medium, hard)
golden_annotations: id, golden_document_id fk, annotation jsonb
  (ground-truth line items + mappings + cell statuses), annotator, version
eval_runs: id, git_sha, prompt_versions jsonb, models jsonb, started_at,
  finished_at, summary jsonb
eval_results: id, eval_run_id fk, golden_document_id fk, metrics jsonb
```

## 9. Pipeline Stage Specifications

### 9.1 `ingest_document` / `classify_document`

- Register file, compute hash (dedupe), render pages, OCR where needed
  (7.4), persist `tender_pages`.
- Classification: small-model adjudication over `doc_type` enum using first
  2 pages + filename. Confidence < 0.8 → QA queue (cheap to fix early,
  expensive to fix late).

### 9.2 `extract_line_items`

- Vision+text extraction per document section against the
  `tender_line_items` JSON schema (structured outputs enforced). Layout
  carries meaning in quotes; tables are first-class.
- Project context is injected into the prompt so the model reads, e.g.,
  `"site costs TBA"` on a steep H2 block with appropriate suspicion and tags
  it `ps_allowance` with `allowance_cents = null`.
- Hard rules enforced post-hoc in Python (never trusted to the model):
  - Page-level amount reconciliation: sum of extracted amounts vs any printed
    subtotal on the page; mismatch > 1% → `arithmetic_inconsistency` flag
    and items marked `needs_review`.
  - Quote-level reconciliation vs `stated_total_cents`.
  - Currency normalisation to integer cents; GST treatment recorded, never
    silently converted.
- Per-item `extraction_confidence` from model logprob-proxy + reconciliation
  outcome. Threshold (config, default 0.85) gates the QA queue.

### 9.3 `map_items` — tier cascade

For each line item, resolve to one or more taxonomy cells:

| Tier | Mechanism | Cost | Expected share at maturity |
| --- | --- | --- | --- |
| T0 | `phrase_norm` exact/fuzzy (trigram) match on `taxonomy_synonyms` | free | 50–70% |
| T1 | pgvector cosine vs cell exemplar embeddings → top-5 candidates; auto-accept if margin between #1 and #2 exceeds threshold | ~free | 15–25% |
| T2 | small model, multiple-choice among T1 candidates + `none_of_these`, with project context | cheap | 10–20% |
| T3 | frontier model: open mapping, one-to-many splits with `allocation_fraction`, weird items | $$ | < 5% |

- `none_of_these` at T2 escalates to T3. T3 below confidence 0.7 →
  `needs_review`.
- Every human correction inserts a `taxonomy_synonyms` row
  (`source=correction`), structurally shrinking future T2/T3 volume. This is
  the cost flywheel; it must work from day one.

### 9.4 `run_expectations` — deterministic, zero LLM

- Evaluate every `expectation_rules` predicate (Appendix A) against
  `ProjectContext` → the **expected scope set** for this project, each with
  severity and rationale.
- Examples encoded in seed data: soil class P → piering expected (`must`);
  slope moderate/steep → retaining (`should`); BAL ≥ 12.5 → bushfire
  compliance items (`must`); reno + pre-1990 building → asbestos
  allowance (`should`); NSW new build → BASIX/NatHERS compliance cell +
  HBCF insurance cell (`must`); VIC → DBI insurance cell; QLD → QBCC home
  warranty cell. *(Statutory thresholds and scheme names verified during
  seed QS review — see 11.3.)*
- Output: expected set ∪ mapped set drives the cell-status grid. Cells
  expected but with no mapped items are candidates for silence inference.

### 9.5 `infer_silence`

For each expected-but-unmapped cell, **deterministic evidence assembly
precedes any model call** (Appendix B packet):

1. Explicit exclusions list mention? → `excluded_explicit` (no LLM needed).
2. PS line plausibly covering it (synonym/embedding proximity to PS
   descriptions)? → candidate `ps`.
3. Bundling parent present (`bundling_parents`) with $ headroom vs benchmark
   p50 for parent + this cell? → candidate `bundled`.
4. Applicability genuinely conditional and context says condition absent? →
   candidate `not_required`.

One small-model adjudication call per cell chooses among
`{excluded, bundled, ps_covered, not_required, ambiguous}` given the packet.
Confidence < 0.75 or outcome `ambiguous` → QA queue, always.

**Language consequence (binding):** statuses map to fixed report phrases
(Appendix C). The system never prints "excluded" unless the quote says so
explicitly; inferred gaps print as "not explicitly itemised". This is the
difference between a report that survives builder pushback and one that
doesn't.

### 9.6 `run_analysis` / `generate_flags` — deterministic

- **Gap matrix:** per cell × quote status grid.
- **True comparable price:** per quote, stated total + Σ(fill-at-benchmark
  for cells `excluded_explicit` or confirmed-gap) + Σ(top-up where PC/PS
  allowance < benchmark p25, top-up to p50). Every adjustment line carries
  its benchmark provenance and confidence; low-confidence benchmarks
  produce ranges, not points.
- **Allowance realism:** PC/PS vs benchmark percentile bands →
  `low_pc_allowance` / `unrealistic_ps` flags with severity scaled by gap
  size and benchmark confidence.
- **Cross-quote outliers:** per-cell z-score across quotes (n ≥ 3) →
  `price_outlier` (info-level; small n, so never stronger than "worth
  querying").
- **Question list:** every warning/caution flag emits a builder-specific,
  plain-English question for the negotiation section.

### 9.7 Benchmarks

- Keyed `benchmark_key × state × region × build_type × spec_level`.
- Seeding strategy (Section 11): model-seeded **ratio framework**
  (relationships age slower than absolutes) + published anchors (ABS $/m²
  approvals data, HIA economics, volume-builder public price lists,
  Rawlinsons) + QS red-pen pass. Every row carries `source`, `provenance`,
  `confidence`, `effective_date`.
- Every processed quote writes anonymised observations
  (`source=observed`) — aggregation job recomputes percentiles monthly once
  n ≥ 5 per key. Observed data gradually supersedes seeds. This DB is the
  compounding moat.
- **Claim-strength rule (binding):** report language strength is capped by
  benchmark confidence — `high` → "below market range", `medium` → "appears
  low, worth querying", `low` → benchmark not cited in customer-facing text.

### 9.8 `assemble_report_draft`

- Renders structured data → HTML (Jinja2 templates in
  `backend/tender/report_templates/`) → PDF (WeasyPrint, runs on VPS).
- Created as a Clerk **draft** so the existing review/approve lifecycle and
  audit trail apply. Narrative blocks (exec summary intro, context note) are
  operator-editable; all tables/figures regenerate from data on every
  rebuild and cannot be hand-edited.
- Approval freezes `tender_reports.version`, stores both artifacts,
  watermark-free. Pre-approval renders are watermarked DRAFT.

## 10. Taxonomy v1 (Class 1)

Top-level groups (cells nest beneath; full cell list ships as seed data in
`data/tender/taxonomy.yaml`). Codes are stable identifiers; names are
display labels.

| Code | Group | Notes |
| --- | --- | --- |
| 01 | Preliminaries & approvals | supervision, insurances during works, plans, permits, surveys, engineering |
| 02 | Demolition & site preparation | reno/addition; asbestos removal cell with era-driven expectation |
| 03 | Site costs & groundworks | cut/fill, piering, rock allowance, retaining, site drainage, dewatering — the classic PS battleground |
| 04 | Substructure | slab class, stumps/subfloor, termite management |
| 05 | Frame & structure | incl. structural steel, engineered beams |
| 06 | Roofing | covering, fascia/gutter, sarking |
| 07 | External walls & cladding | brick/render/cladding systems |
| 08 | Windows & external doors | glazing spec, screens; BAL-driven upgrades |
| 09 | Garage & lockup misc | garage door is a notorious convention split between builders |
| 10 | Services rough-in & fit-off | plumbing, electrical (point counts), gas, HVAC, solar/battery provision |
| 11 | Energy & compliance | NatHERS/7-star measures, NSW BASIX, condensation/ventilation |
| 12 | Internal linings | plaster, cornice, wet-area substrates |
| 13 | Fixing & joinery | internal doors, skirting/architrave, robes, stairs |
| 14 | Kitchen | cabinetry, benchtops, splashback (PC-heavy) |
| 15 | Bathrooms & wet areas | vanities, screens, baths, tiling extents (floor-to-ceiling vs skirting height is a classic gap) |
| 16 | Painting | internal/external scope split |
| 17 | Floor coverings | the single most commonly excluded category |
| 18 | Appliances & fixtures | PC schedule: appliances, tapware, lighting |
| 19 | External works | driveway, paths, fencing, landscaping, decks/pergolas, letterbox/clothesline — exclusion central |
| 20 | Connections & authority | power, water, sewer, stormwater, NBN, traffic/hoarding where relevant |
| 21 | Statutory, insurance & certification | state home-warranty insurance (NSW HBCF / VIC DBI / QLD QBCC scheme), certifier/PCA, OC |
| 22 | Contract commercials | deposit %, progress stages, contingency, margin visibility, GST treatment |

Cell metadata that makes the taxonomy *data, not a list* — example:

```yaml
- code: "03.05"
  name: Retaining walls
  grp: site_costs
  stage: base
  build_type_tags: [new_build, addition]
  applicability:
    any:
      - { field: slope_class, in: [moderate, steep] }
      - { field: context.notes, contains_concept: cut_and_fill }
  bundling_parents: ["03.01"]        # "site costs" lump-sum lines
  benchmark_key: site.retaining
  synonyms_seed: [retaining wall, retainage, sleeper wall, block retaining,
                  boulder wall, RW allowance]
```

## 11. Seed Data Plan — `data/tender/`

Follows the repo's existing `data/` seed convention; loaded by
`backend/tender/seeds/` loaders, idempotent upserts keyed on stable codes.

```
data/tender/
├── taxonomy.yaml          # full Class 1 cell tree + metadata (≈180–250 cells)
├── synonyms.seed.csv      # cell_code, phrase  (target ≥ 1,500 rows at seed)
├── expectations.yaml      # rule DSL (Appendix A), ≈60–100 rules
├── benchmarks.seed.csv    # ratio framework + anchored absolutes, confidence-tagged
├── report_language.yaml   # status → phrase map (Appendix C), claim-strength caps
└── golden/                # eval set (gitignored payloads per repo convention)
    ├── manifest.yaml
    └── annotations/
```

### 11.1 Authoring sequence

1. Frontier-model drafting of `taxonomy.yaml`, `expectations.yaml`,
   `synonyms.seed.csv`, and the benchmark **ratio framework** (kitchen as %
   of build, prelims %, site-cost uplift per soil class, regional
   multipliers off a Sydney base). Ratios age slower than absolutes; this is
   the correct use of pre-trained knowledge.
2. Absolute anchors calibrated from current published data: ABS building
   approvals $/m² by state, HIA economics releases, public volume-builder
   price lists + inclusions (free ground truth), Rawlinsons handbook.
3. **QS red-pen day (11.3).**

### 11.2 Confidence discipline

Every benchmark row and expectation rule carries `confidence` and
`provenance` at seed time. Model-seeded rows enter as `confidence=low` and
cannot appear in customer-facing claims until upgraded by published anchors
or observed data (9.7 claim-strength rule).

### 11.3 QS review gate (blocking)

One paid day of an independent QS reviewing: taxonomy completeness,
expectation rules (esp. statutory cells — NSW HBCF, VIC DBI, QLD QBCC
thresholds and current names), benchmark sanity by state. No customer report
ships before this gate. Output recorded as corrections to seed files with
the QS named in `provenance`.

## 12. QA Console (cockpit)

The QA console is the v1 product as far as the operator is concerned. It is
**not** a temporary crutch — silence inference keeps a human in the loop far
longer than extraction does.

- **Queue.** All `needs_review` entities across the comparison, sorted by
  (report-impact desc, confidence asc): cell statuses first, then mappings,
  then flags, then document classifications.
- **Three-pane review.** Left: normalised entity (cell, status, amount,
  proposed mapping). Centre: source page image with bbox highlight,
  pinch-zoom. Right: adjudication panel — accept / choose alternative cell
  (typeahead over taxonomy) / edit status / set amount / annotate reason.
- **Keyboard-first.** `a` accept, `e` edit, `j/k` next/prev, `s` split
  (one-to-many with fraction sliders). Target throughput: < 20s per item.
- **Every action writes `tender_corrections`** and, where a mapping was
  corrected, a `taxonomy_synonyms` candidate (`source=correction`) pending
  weekly batch promotion.
- **Graduation dashboard.** Per category (e.g. extraction.amounts,
  mapping.kitchen, silence.bundled): rolling accuracy from QA outcomes.
  When a category sustains ≥ 98% accept-rate over ≥ 200 items, its
  auto-pass threshold may be lowered — a deliberate config change, never
  automatic.
- Comparison cannot advance to `report_draft` while any `needs_review`
  remains.

## 13. Customer Report Specification

Audience: anxious non-expert making a $300k–$1.5m decision. Tone: calm,
specific, non-alarmist. Every claim traceable; every number sourced.

Sections (HTML + PDF, ≈10–16 pages):

1. **Cover & project context** — what was compared, document inventory per
   builder, date, validity caveats.
2. **Executive summary** — one page: headline findings, the 3–5 things that
   matter, true-comparable-price table (with ranges where benchmark
   confidence requires).
3. **Price comparison** — stated totals; adjustments ledger per quote
   (each gap filled / allowance topped-up, with source + benchmark
   provenance); resulting comparable range. Adjustments are itemised so a
   builder can be shown exactly why their number moved.
4. **Comparison matrix** — by taxonomy group; per-cell status glyphs
   (✓ included, ◷ allowance, ✗ excluded-explicit, ◌ not itemised,
   – not required); amounts where stated.
5. **Allowances under the microscope** — PC/PS schedule per quote vs
   benchmark bands; flags rendered per claim-strength rule.
6. **Risk notes** — warning/caution flags in plain English with evidence
   snippets (quoted < 15 words, page-referenced).
7. **Questions to ask each builder** — the negotiation artillery; builder-
   specific, copy-paste ready.
8. **Methodology & limits** — what the analysis does and does not do;
   benchmark sources; "not itemised ≠ excluded" explanation; disclaimers
   (Section 18).

Operator-editable: §2 narrative intro, §6 phrasing. Everything else
regenerates from data.

## 14. Evaluation Harness (blocking infrastructure, built before mapping)

- **Golden set.** Target ≥ 30 real quote documents (anonymised: builder
  names/ABNs/addresses stripped at ingest into `golden_documents`) + ≥ 20
  synthetic adversarial documents (generated ground-truth-first: JSON →
  rendered PDF → optional scan-degrade). Real documents validate; synthetic
  documents stress edge cases. Synthetic never exceeds 50% of the set used
  for go/no-go decisions.
- **Metrics** (per eval run, per difficulty tier):
  - extraction: line-item recall / precision; amount exact-match rate;
    status (PC/PS/excluded) accuracy
  - mapping: cell accuracy@1; split (one-to-many) F1
  - silence: per-class precision/recall for
    `{excluded, bundled, ps_covered, not_required, ambiguous}` — class
    confusion here is the product's reputational risk, so it gets its own
    gate
  - end-to-end: report-impacting error rate (errors that would change a
    flag, a comparable price by > 2%, or a matrix glyph)
- **Gates.** `uv run pytest -m tender_eval` (manual/CI-on-label — runs cost
  money). No merge of prompt, model-config, taxonomy, or rule changes
  without an eval run attached; regression > 1pt on any gate metric blocks.
- **Drift watch.** Weekly scheduled eval on pinned golden subset to catch
  provider-side model drift.

## 15. API Surface (`/api/tender`)

```
POST   /comparisons                          create (project_id, context)
GET    /comparisons/{id}                     full state incl. stage statuses
PATCH  /comparisons/{id}/context             re-runs expectations downstream
POST   /comparisons/{id}/quotes              create quote (builder meta)
POST   /quotes/{id}/documents                multipart upload → enqueue ingest
POST   /quotes/{id}/retry/{stage}            per-stage retry
GET    /comparisons/{id}/qa/queue            ordered review items
POST   /qa/items/{id}/resolve                accept/correct (writes corrections)
GET    /comparisons/{id}/matrix              normalised grid (frontend)
POST   /comparisons/{id}/report/build        assemble/rebuild draft
POST   /comparisons/{id}/report/approve      freeze + final PDF
POST   /comparisons/{id}/report/delivered    record delivery
GET    /taxonomy / /taxonomy/search?q=       typeahead support
```

Auth: Clerk's existing Supabase Auth; all routes operator-role gated. v1 has
no customer-facing endpoints.

## 16. Frontend Surface (cockpit routes)

```
/projects/:projectId/tender                     comparisons list
/projects/:projectId/tender/:cid                overview + stage status
/projects/:projectId/tender/:cid/qa             QA console (12)
/projects/:projectId/tender/:cid/matrix         comparison grid
/projects/:projectId/tender/:cid/report         draft preview / approve
```

React SPA per repo stack; page-image viewer with bbox overlay (no PDF.js
text-layer dependency — images + coordinates only); matrix virtualised
(≈250 cells × 5 quotes).

## 17. Non-Functional Requirements

- **Provenance, end to end.** Every customer-facing figure resolves to
  (document, page, bbox) or (benchmark row id). This is Clerk's grounded-
  citation ethos applied to structured data, and it is non-negotiable.
- **Tenancy & sensitivity.** Quotes are commercially sensitive third-party
  documents. Private storage bucket, project-scoped access, no
  cross-project reads. Benchmark observations are aggregated and
  anonymised; raw quote data never leaves its project.
- **Data rights.** Engagement terms must grant the right to retain
  anonymised, aggregated pricing observations. (Open question 21.3 for
  wording; blocking before first paid report.)
- **PII.** Customer name/address only in `ProjectContext`; reports exclude
  builder ABNs unless operator opts in. Golden-set ingestion strips
  identifiers.
- **Retention.** Source documents retained per engagement terms (default
  24 months), then purged; observations persist.
- **Performance targets.** 5-quote comparison fully processed ≤ 30 min
  wall-clock on VPS (excl. QA); QA console interactions < 200ms;
  report rebuild < 60s.
- **Cost target.** ≤ A$15 LLM spend per comparison at v1, trending down via
  T0/T1 share growth; per-comparison spend logged on the comparison row.
- **Backups.** Supabase PITR for DB; storage bucket lifecycle per retention
  policy.

## 18. Legal & Positioning Guardrails (binding on copy)

- The report is **information and document analysis**, not financial,
  legal, or building advice; not a valuation; not a builder recommendation
  or ranking. Disclaimer block in §8 of every report; engagement terms
  mirror it.
- Inferred statuses use Appendix C language only. "Excluded" appears only
  for explicit exclusions with a page reference.
- Benchmark-based claims obey the claim-strength rule (9.7).
- No statement about a builder's licence status, solvency, or conduct.
  (A licence-check feature is out of scope v1; see 21.5.)

## 19. Delivery Plan (solo, AI-assisted; ~12 weeks)

| Milestone | Weeks | Exit criteria |
| --- | --- | --- |
| M0 Seed knowledge | 1–2 | taxonomy.yaml, expectations.yaml, synonyms seed, benchmark ratio framework drafted; real-quote acquisition started (target 30–50 sets via network); 10+ golden docs annotated |
| M1 Skeleton | 2–3 | migrations, module scaffold, jobs worker on Dokploy, ingest/OCR/page-render running on real docs |
| M2 Extraction + harness | 3–5 | extraction with reconciliation rules; **eval harness live with gates**; baseline metrics recorded |
| M3 Mapping | 6–7 | T0–T3 cascade; correction→synonym loop working; **checkpoint: 5 real quote sets end-to-end, however rough** |
| M4 Expectations + silence | 8–9 | expectation engine, silence inference, analysis/flags; QS red-pen day done; benchmarks calibrated |
| M5 QA console + report | 10–11 | console at < 20s/item; report draft→approve→PDF through Clerk drafts |
| M6 Pilot | 12 | 3 friendly-customer reports delivered; ≤ 2h QA each; go/no-go on payment link |

Standing rule: real documents flow through the pipeline from M1 onward.
Building against synthetic-only input is the failure mode this plan exists
to prevent.

## 20. Risks & Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Extraction long-tail (handwriting, terrible scans, cursed tables) | QA time blows out | reconciliation rules route junk to review early; `manual_transcription_required` escape hatch; difficulty-tiered golden set tracks the tail explicitly |
| Silence misclassification → false "gap" accusation | credibility loss in front of builders | Appendix C language rules; silence classes never auto-pass in v1; per-class eval gate |
| Benchmark staleness / wrong anchors | wrong "unrealistic allowance" flags | confidence-capped claims; QS gate; observed-data supersession; effective_date on every row |
| Provider model drift (hosted models change underneath) | silent quality regression | pinned model config; weekly drift eval; prompt/model versions on every output row |
| Reno quote chaos (both wedges day one) | reno reports uneconomic | acceptable by design — operator judgment absorbs breadth in concierge mode; track QA minutes by build_type; narrow later if data says so |
| Solo capacity | schedule slip | M-gates are scope cuts, not date slips: M6 can ship with silence inference fully manual if needed |
| VPS resource ceiling (OCR + WeasyPrint + LLM concurrency) | slow turnaround | jobs are queued, not real-time; 24h promise gives huge headroom; worker replicas if needed |

## 21. Open Questions

1. Report retail price point and whether reno comparisons price differently
   (likely higher QA cost).
2. Email delivery: manual from operator inbox (v1 default) vs transactional
   sender — decide before M6.
3. Engagement-terms wording for data rights (17) — needs legal review;
   blocking before first *paid* report.
4. Whether quote documents are also chunked into project corpus for Clerk
   chat (7.1 allows it) — default off until tested for confusion.
5. Builder licence-check add-on (NSW Fair Trading / VBA / QBCC public
   registers) — Phase 2 candidate, high perceived value, low effort.
6. Phase 2 thin customer surface: public upload page + Stripe payment link +
   status email — separate PRD once M6 pilots convert.

---

## Appendix A — Expectation Rule DSL

Predicates evaluate against `ProjectContext` (and only it — deterministic,
no document input, no LLM):

```yaml
- rule: SITE.PIERING.MUST
  cell: "03.02"
  severity: must
  predicate: { field: soil_class, in: [H2, E, P] }
  rationale: Reactive/problem soils typically require engineered piering.

- rule: SITE.RETAINING.SHOULD
  cell: "03.05"
  severity: should
  predicate:
    any:
      - { field: slope_class, in: [moderate, steep] }
  rationale: Sloping sites typically require retaining structures.

- rule: STATUTORY.HOME_WARRANTY.NSW
  cell: "21.01"
  severity: must
  region_tags: [NSW]
  predicate: { field: state, eq: NSW }
  rationale: NSW home-warranty (HBCF) cover must be evidenced before deposit.

- rule: DEMO.ASBESTOS.RENO
  cell: "02.03"
  severity: should
  build_type_tags: [renovation, addition]
  predicate:
    all:
      - { field: build_type, in: [renovation, addition] }
      - { field: existing_dwelling_era, before: "1990" }
  rationale: Pre-1990 dwellings carry material asbestos likelihood.
```

Combinators: `all`, `any`, `not`; comparators: `eq, in, gte, lte, before,
exists`. Versioned; loaded idempotently; every fired rule records
`rule_code` into downstream evidence packets.

## Appendix B — Silence-Inference Evidence Packet

Input to the single adjudication call per silent cell:

```json
{
  "cell": {"code": "03.05", "name": "Retaining walls",
            "expected_because": ["SITE.RETAINING.SHOULD"]},
  "explicit_exclusions": [],
  "candidate_ps_lines": [
    {"line_item_id": "…", "description": "Provisional sum – site works",
     "allowance_cents": 2500000, "similarity": 0.81,
     "page_ref": {"doc": "…", "page": 4}}
  ],
  "bundling_parents_present": [
    {"cell": "03.01", "quote_amount_cents": 4800000,
     "benchmark_p50_parent_cents": 3500000,
     "benchmark_p50_this_cell_cents": 1400000,
     "headroom_assessment": "parent ≈ p50(parent)+p50(cell)"}
  ],
  "context_signals": {"slope_class": "steep", "soil_class": "H2"},
  "allowed_outcomes": ["excluded", "bundled", "ps_covered",
                        "not_required", "ambiguous"]
}
```

Output schema: `{outcome, confidence, rationale, cites: [line_item_ids]}`.
Outcome `excluded` from this path is **always** downgraded to
`silent_ambiguous` + QA review — only an explicit exclusions-list match may
set `excluded_explicit`.

## Appendix C — Report Language Rules (binding)

| Internal status | Customer-facing phrase |
| --- | --- |
| excluded_explicit | "Excluded (stated, p. N)" |
| silent_ambiguous | "Not explicitly itemised — confirm with builder" |
| bundled | "Appears to be covered within ‹parent› — confirm" |
| ps | "Covered by provisional sum of $X — scope not fixed" |
| pc (below benchmark) | confidence high: "allowance below typical market range"; medium: "allowance appears low — worth querying"; low: no benchmark claim |
| not_required | "Not applicable to this site/project" |

Forbidden in customer-facing text: "ripoff", "hiding", "dodgy",
"underquoting", any imputation of intent. Findings describe documents,
never motives.

---

*End of PRD. Acceptance of this document authorises M0 commencement and the
Alembic migration set described in Section 8.*
