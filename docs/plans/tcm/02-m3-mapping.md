# M3 — Mapping cascade (T0–T3) + correction flywheel

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Every extracted line item resolves to one or more taxonomy cells via the PRD §9.3 tier cascade, with the correction→synonym loop live and a recorded eval baseline.

**Architecture:** Two new job stages (`embed_items`, `map_items`) registered in the worker's handler registry; a `services/mapping.py` orchestrating T0 (synonym match) → T1 (pgvector) → T2 (small-model MC) → T3 (frontier); `adjudicate()` added to the LLM client protocol. All thresholds in config. All LLM calls mockable.

**Prerequisites:** Stage 0 complete; branch `feature/tcm-main`.

**PRD anchors:** §9.3 (cascade), §7.5 (LLM strategy, adjudicate signature, config keys), §8.6 (`tender_mappings`), §14 (eval gates).

---

## Design decisions (made; do not relitigate)

1. **Normalization is shared.** Reuse `normalize_phrase()` from `backend/tender/seeds/load.py` for line-item descriptions, T0 lookups, and embedding inputs. One normalizer everywhere or T0 silently degrades.
2. **Synonym embeddings, not cell-centroid embeddings.** Migration 012 adds `embedding vector(1536)` (nullable) to `taxonomy_synonyms`. T1 = cosine search over synonym embeddings; aggregate to cells by **max** similarity per cell; take top-5 cells. (Per-synonym beats centroid: cells have heterogeneous phrasing.)
3. **T0 = exact `phrase_norm` match, then trigram.** Migration 012 also ensures `pg_trgm` extension and a trigram index on `taxonomy_synonyms.phrase_norm`. Trigram accept threshold: `TENDER_T0_TRGM_THRESHOLD` (default 0.92). Multiple distinct cells matched at T0 → not a T0 result; fall through to T1 (ambiguous exact matches are real: "site costs").
4. **Thresholds (config keys, defaults):**
   - `TENDER_T1_ACCEPT_SIM = 0.80`, `TENDER_T1_ACCEPT_MARGIN = 0.10` (accept top cell iff sim₁ ≥ 0.80 AND sim₁ − sim₂ ≥ 0.10)
   - `TENDER_T2_ACCEPT_CONF = 0.80` (below → needs_review, not escalation; only `none_of_these` escalates to T3 — PRD §9.3)
   - `TENDER_T3_REVIEW_CONF = 0.70` (T3 below this → needs_review)
5. **Idempotency / QA protection:** `map_items` deletes and rewrites a line item's mappings **only** when no existing mapping for that item has `tier='human'` or `qa_state in ('confirmed','corrected')`. Protected items are skipped on re-run.
6. **Splits:** only T3 (and humans) may emit multiple mappings per item. Python validates fractions sum to 1.0 ± 0.001; on violation, renormalize if all fractions > 0, else mark `needs_review` with the raw response preserved in `adjudication`.
7. **Correction flywheel:** a human mapping correction inserts `taxonomy_synonyms (phrase=description_raw, phrase_norm=normalize_phrase(...), source='correction', confidence=1.0, correction_id=...)` immediately active (PRD §9.3 — "this is the cost flywheel; it must work from day one"). Weekly batch *promotion/pruning* is deferred to M5+. Duplicate (cell_code, phrase_norm) → no-op.
8. **Embedding dims pinned:** assert `len(vector) == 1536` at write time; startup assert already required by PRD §7.5 — add it to config validation if absent.

## Tasks

### Task 1: Migration 012 — embeddings + trigram

**Files:** `backend/alembic/versions/012_tender_mapping_support.py`; extend `backend/tender/models.py` (`TaxonomySynonym.embedding`, `pgvector.sqlalchemy.Vector(1536)` — match how `tender_line_items.embedding` is declared; **first verify it exists in migration 007, add it here if not**); extend `backend/tests/tender/test_migrations.py`.

Steps: failing chain test → migration (up/down; `CREATE EXTENSION IF NOT EXISTS pg_trgm` and `vector` if missing; GIN trigram index on `phrase_norm`; ivfflat or plain index on embedding — plain is fine at seed scale) → roundtrip verify → commit.

### Task 2: `adjudicate()` on the LLM client

**Files:** `backend/tender/llm/client.py`, `backend/tender/llm/openai_client.py`, `backend/tests/tender/test_openai_client.py`.

Protocol addition (mirror PRD §7.5 exactly):

```python
@dataclass(frozen=True)
class LLMAdjudicationResponse:
    choice: str
    confidence: float
    rationale: str
    model: str
    prompt_version: str
    request_id: str | None = None

async def adjudicate(self, question: str, choices: Sequence[str],
                     evidence: dict[str, Any], context: ProjectContext,
                     *, prompt_version: str, model_key: str) -> LLMAdjudicationResponse: ...
```

JSON-schema-enforced structured output; `choice` constrained to the enum given. Tests use a fake transport — no network.

### Task 3: `embed_items` stage

**Files:** `backend/tender/services/embedding.py`, register in `worker.py` handler registry, `backend/tests/tender/test_embedding.py`.

- Embeds `normalize_phrase(description_raw)` for items with `embedding IS NULL` (idempotent resume), batch ≤ 256, model from `TENDER_EMBED_MODEL`.
- Also a CLI/loader path to backfill synonym embeddings: `python -m tender.seeds.embed_synonyms` (same batching; only NULL rows). Seed-loading itself must NOT require network — embedding backfill is a separate explicit step.
- Tests: fake embedder; idempotency (second run embeds nothing); dim assertion.

### Task 4: T0 + T1 matchers (pure DB, no LLM)

**Files:** `backend/tender/services/mapping.py` (start), `backend/tests/tender/test_mapping_t0_t1.py`.

```python
@dataclass(frozen=True)
class CellCandidate:
    cell_code: str
    similarity: float
    via: str  # synonym phrase or "exact"

async def t0_match(session, phrase_norm: str) -> list[CellCandidate]  # exact then trigram
async def t1_candidates(session, embedding: list[float], limit: int = 5) -> list[CellCandidate]
```

Tests run against the test DB with a tiny seeded taxonomy fixture (3 cells, 6 synonyms): exact hit, trigram hit at 0.92+, multi-cell exact → empty T0, T1 ordering and margin math.

### Task 5: T2 prompt + adjudication

**Files:** `backend/tender/llm/prompts/map_items_t2_v0.1.0.md`, `mapping.py` (cont.), `backend/tests/tender/test_mapping_t2_t3.py`.

Prompt contract (multiple-choice): given item description, section_path, qty/unit/amount, ProjectContext summary, and T1's top-5 candidate cells (code + name + description), choose one **or** `none_of_these`. The taxonomy block must be a stable string ordering (cache-friendly, PRD §7.5).

### Task 6: T3 prompt + splits

**Files:** `backend/tender/llm/prompts/map_items_t3_v0.1.0.md`, `mapping.py` (cont.), same test file.

Open mapping over the full active cell list (code+name only, stable order), may return 1–4 `(cell_code, allocation_fraction)` pairs. Python validates per design decision 6. Unknown cell codes in the response → `needs_review`, never invented rows.

### Task 7: `map_items` job handler — cascade orchestration

**Files:** `mapping.py` (orchestrator), `worker.py` registration, `backend/tests/tender/test_map_items_handler.py`.

Per line item: T0 hit → write mapping `(tier=t0_exact, confidence=1.0, qa_state=auto_pass)`. Else T1: margin-accept → `(t1_embedding, confidence=sim₁, auto_pass)`; else T2 with T1 top-5; `none_of_these` → T3. Write `adjudication` jsonb (candidates, model, prompt_version, request_id, rationale) on every LLM-tier row. `qa_state=needs_review` per thresholds. Honor idempotency rule (decision 5). Checkpoint per item (job re-run resumes at unmapped items).

Tests: full cascade with fake LLM client — one scenario per tier, escalation, threshold edges, re-run protection of human rows.

### Task 8: Correction → synonym loop

**Files:** `backend/tender/services/corrections.py`, `backend/tests/tender/test_corrections.py`.

```python
async def record_mapping_correction(session, *, mapping_id, corrected_cell_code,
                                    reviewer_id, reason: str | None) -> None
```

Writes `tender_corrections` (before/after jsonb), updates the mapping (`tier=human`, `qa_state=corrected`), inserts the synonym row (decision 7). Tests: correction row shape; synonym created; duplicate phrase no-op; T0 picks up the new synonym on next run (the flywheel test — this is the one that matters).

### Task 9: Eval baseline

**Files:** `backend/tender/eval/runners.py` (`MappingPredictionRunner` implementing the existing `PredictionRunner` protocol over T0+T1 only — offline, deterministic), extend `backend/tests/tender/` eval tests.

Run `uv run pytest -m tender_eval` against the golden set (however small) and **record the mapping accuracy@1 / split F1 numbers in this doc** under "## Baseline (date)". This is the M3 eval gate baseline; later prompt changes are measured against it.

### Task 10: Real-document checkpoint (operator + model together)

PRD M3 exit: **5 real quote sets end-to-end, however rough.** Requires ingestion (Stage 0.5 if it was found stubbed) and extraction working. Run the pipeline on real sets, note QA pain points in this doc. This is deliberately manual — do not skip, do not synthesize.

## Baseline (2026-06-13)

Command: `uv run pytest -m tender_eval`

- Documents evaluated: 0
- Mapping accuracy@1: null (no annotated golden mapping items)
- Split F1: null (no annotated golden mapping pairs)
- Mapping gold pair count: 0
- Mapping predicted pair count: 0
- Note: `data/tender/golden/manifest.yaml` currently contains no documents, so this is an infrastructure baseline only. The first real/synthetic golden annotations must replace these null metrics before they can be used as a quality gate.

## Real-document checkpoint (2026-06-13)

Not run. Blockers found in `feature/tcm-main`:

- No real quote payloads or annotated golden documents are present in `data/tender/`.
- `backend/tender/services/ingestion.py` still raises `NotImplementedError("ingest_document lands in the next commit")`.
- Stage 0.5 remains required before the PRD M3 checkpoint can process 5 real quote sets end-to-end. No synthetic substitute was used.

## Exit criteria

- [ ] All tier tests green; full suite green (output pasted)
- [ ] Migration 012 roundtrip verified
- [ ] Flywheel test proves correction → synonym → next-run T0 hit
- [ ] Eval baseline numbers recorded above
- [ ] 5 real quote sets processed end-to-end (notes recorded)
- [ ] New config keys documented in `backend/app/config.py` style alongside existing TENDER_ keys
