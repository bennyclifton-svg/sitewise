# M4 — Expectations, silence inference, analysis & flags

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Two sessions.** Part A: expectation engine + silence inference (§9.4, §9.5, App A/B/C). Part B: analysis + flags (§9.6, §9.7). Branch `feature/tcm-main`.

**Prerequisite for Part A:** M3 merged. **For Part B:** Part A merged.

---

# Part A — Expectation engine + silence inference

**Goal:** Deterministic expected-scope computation from `ProjectContext`; every expected-but-unmapped cell adjudicated into `{excluded, bundled, ps_covered, not_required, ambiguous}` with an Appendix B evidence packet.

## Design decisions (made; do not relitigate)

1. **The expectation engine is a pure function.** `evaluate_rules(rules, context) -> list[FiredRule]`. No DB writes inside the evaluator; no document input; no LLM. The job handler around it does the persistence.
2. **DSL comparators** (App A): `eq, in, gte, lte, before, exists`; combinators `all, any, not`. Plus `contains_concept` (seen in taxonomy `applicability`): **v1 semantics = case-insensitive substring match of any phrase from a fixed concept→phrases map** in `data/tender/concepts.yaml` (new seed file, ~10 concepts, e.g. `cut_and_fill: [cut and fill, cut & fill, benching, earthworks]`). Unknown comparator or malformed predicate → raise at load time (validate.py extension), never silently false.
3. **Rule filtering:** a rule applies iff (`region_tags` empty or contains `context.state`-derived tag) and (`build_type_tags` empty or contains `context.build_type`). Tag matching for `"QLD:regional"`-style tags: `state` or `state:region` both supported.
4. **Cell-status grid:** `run_expectations` upserts `tender_cell_status` rows keyed `(comparison_id, quote_id, cell_code)` for the union of (expected cells × quotes) ∪ (mapped cells × quotes). Mapped cells get status from item statuses (included / pc / ps / excluded_explicit from explicit exclusion items). Expected-but-unmapped cells get a provisional `silent_ambiguous` and are queued for `infer_silence`. Re-runs never overwrite rows with `qa_state in ('confirmed','corrected')`.
5. **Silence evidence assembly is deterministic and ordered** (PRD §9.5 steps 1–4):
   1. Explicit-exclusions check: T0-style match (exact + trigram on normalized phrases) of the cell's synonyms against line items with `item_status='excluded'`. Hit → `excluded_explicit` **with page ref**, no LLM call at all.
   2. PS candidates: cosine similarity between cell synonym embeddings and PS-item embeddings ≥ `TENDER_SILENCE_PS_SIM` (default 0.60) → candidate list.
   3. Bundling headroom: for each `bundling_parents` cell present in the quote with an amount: `headroom = parent_amount_cents − (p50_parent + p50_cell)` using benchmark rows resolved at exact key (state, region, build_type, spec_level); missing benchmark → "unknown headroom" recorded as such, never guessed. Express assessment as the PRD's comparative string.
   4. `not_required` candidacy: cell `applicability` predicate evaluates false against context.
6. **One adjudication call per silent cell** via `adjudicate()` with prompt `infer_silence_v0.1.0.md`, packet exactly per Appendix B JSON shape. `confidence < TENDER_SILENCE_REVIEW_CONF (0.75)` or outcome `ambiguous` → `needs_review` **always**.
7. **Binding downgrade:** outcome `excluded` from the adjudication path is stored as `silent_ambiguous` + `needs_review`. Only step-1 explicit matches may write `excluded_explicit`. Encode this as a unit test with a fake LLM that answers `excluded` — the stored status must be `silent_ambiguous`. This test is the product's reputation; it never gets deleted.
8. **Silence classes never auto-pass in v1** (PRD §20 mitigation): every silence-derived status enters `needs_review` regardless of confidence — confidence only orders the queue. (Yes, this supersedes the 0.75 threshold for auto-pass purposes; the threshold still routes `ambiguous`.)

## Tasks (Part A)

1. **Concepts seed + DSL evaluator.** Files: `data/tender/concepts.yaml`, `backend/tender/services/expectations.py`, `backend/tests/tender/test_expectations.py`. Table-driven tests: every comparator, every combinator, nested predicates, tag filtering, the four Appendix A example rules verbatim against crafted contexts, malformed predicate → load-time error. Commit per green group.
2. **`run_expectations` handler + grid builder.** Files: `expectations.py` (cont.), `worker.py` registration, `backend/tests/tender/test_cell_status_grid.py`. Tests: union logic, provisional statuses, upsert idempotency, QA-state protection.
3. **Evidence packet assembly.** Files: `backend/tender/services/silence.py`, `backend/tests/tender/test_silence_packet.py`. Pure functions per design decision 5; tests per step including the no-benchmark case and the explicit-exclusion short-circuit (asserts zero LLM invocations — pass a fake that raises if called).
4. **Adjudication + persistence.** Files: `backend/tender/llm/prompts/infer_silence_v0.1.0.md`, `silence.py` (cont.), `worker.py` registration, `backend/tests/tender/test_infer_silence.py`. Tests: each outcome mapped to correct `tender_cell_status.status`, the binding downgrade test (decision 7), never-auto-pass (decision 8), `evidence` jsonb stores the full packet + adjudication metadata.
5. **Eval extension.** `SilencePredictionRunner` in `backend/tender/eval/runners.py` (deterministic steps with fake adjudicator for offline runs; live mode behind the `tender_eval` marker). Record per-class precision/recall baseline in this doc.

## Exit criteria (Part A)

- [ ] DSL evaluator: 100% comparator/combinator coverage, Appendix A examples pass verbatim
- [ ] Downgrade test and never-auto-pass test exist and are green

## Part A eval baseline

Offline smoke baseline (`SilencePredictionRunner` with fake adjudicator, no live model):
`bundled_precision=1.0`, `bundled_recall=1.0`, `ambiguous_precision=1.0`,
`ambiguous_recall=1.0`; excluded / ps_covered / not_required have no observations
in the smoke fixture yet, so their precision and recall are unset.
- [ ] Explicit-exclusion path provably LLM-free
- [ ] Full suite green (output pasted); silence eval baseline recorded

---

# Part B — Analysis, benchmarks, flags (deterministic; zero LLM)

**Goal:** Gap matrix, true-comparable-price ledger, allowance realism, cross-quote outliers, flags, and the builder question list — all pure Python over typed data.

## Design decisions (made; do not relitigate)

1. **Everything is integer cents.** Percentile values from `benchmarks` are `Numeric`; convert via `int(round(...))` at the edge, once. Ranges are `(low_cents, high_cents)` tuples, never floats.
2. **Benchmark resolution:** exact key `(benchmark_key, state, region, build_type, spec_level)`, non-superseded, latest `effective_date`. No fuzzy fallback in v1. Missing benchmark → adjustment skipped + info-severity note in the ledger ("no benchmark available"); never a guessed number.
3. **True comparable price** (PRD §9.6) per quote: `stated_total + Σ fill_at_benchmark(cells excluded_explicit or confirmed gap) + Σ topup(PC/PS where allowance < p25, top-up to p50 − allowance)`. `metric` handling: `absolute` → cents directly; `per_m2` → × `floor_area_m2` (skip + note if context lacks it); `pct_of_build` → × stated_total; `ratio` rows are framework-internal, never directly priced into the ledger.
4. **Confidence → claim strength (binding, PRD §9.7):** benchmark `high` → point adjustment + strong phrase key; `medium` → range `(p25..p75)`-based adjustment + hedged phrase key; `low` → adjustment **excluded from the headline comparable** (shown only in an "unquantified items" note) and never cited in customer-facing text. Phrase keys resolve via `report_language` — analysis emits keys, never English.
5. **Outliers:** per-cell across quotes, n ≥ 3 only, z-score on cents; |z| ≥ 2 → `price_outlier` flag, severity always `info`.
6. **Flags carry evidence jsonb** with everything needed to render: cell, amounts, benchmark row id, percentile band, page refs. Severity scaling for `low_pc_allowance`/`unrealistic_ps`: gap < 25% of p50 → `caution`; ≥ 25% → `warning`; benchmark confidence `low` → cap at `info` (and exclude from report per decision 4).
7. **Question list:** every `warning`/`caution` flag emits one question string built from `report_language.yaml` templates keyed by flag_type, parameterized (builder name, cell name, amount). New seed keys → add to `report_language.yaml` in the same session, validated by validate.py.
8. **Idempotency:** `run_analysis`/`generate_flags` delete-and-rewrite their own outputs per comparison, except flags with `qa_state in ('confirmed','suppressed')`, which are preserved by `(flag_type, quote_id, cell_code)` identity.

## Tasks (Part B)

1. **Benchmark resolution service.** Files: `backend/tender/services/benchmarks.py`, `backend/tests/tender/test_benchmarks.py`. Tests: exact-key hit, supersession, effective-date ordering, missing-key behavior, each metric conversion (hand-computed cents).
2. **Comparable-price ledger.** Files: `backend/tender/services/analysis.py`, `backend/tests/tender/test_analysis_ledger.py`. Table-driven: a 3-quote synthetic comparison fixture with hand-computed expected ledgers covering fill, top-up, range emission (medium confidence), low-confidence exclusion, per_m2 with and without floor area.
3. **Realism + outliers + gap matrix.** Files: `analysis.py` (cont.), `backend/tests/tender/test_analysis_flags.py`. Tests: severity scaling table, confidence cap, z-score threshold edges, n<3 produces nothing.
4. **`generate_flags` + question list + handlers.** Files: `analysis.py` (cont.), `worker.py` registration (comparison-level stages per §7.2), `report_language.yaml` additions, `backend/tests/tender/test_questions.py`. Tests: every flag type → a question; phrasing comes from seed keys (assert no hardcoded English in analysis module — grep test).
5. **End-to-end fixture run.** One integration test: synthetic comparison → expectations → (faked) silence outcomes → analysis → flags; assert the full `tender_cell_status` grid and ledger match a checked-in expected JSON.

## Exit criteria (Part B)

- [ ] All analysis math covered by hand-computed table-driven tests
- [ ] No English strings in analysis/silence modules (language only via report_language keys)
- [ ] Integration fixture green; full suite green (output pasted)
- [ ] **Human gates scheduled, not coded:** QS red-pen day (PRD §11.3) booked; benchmark calibration pass done by Ben — both block M6, not M5

## Baseline (fill in at completion)

- silence per-class P/R: _
- ledger fixture hash: `sha256:26345c25c82aec9951217ea4b616955e9451ed0023b7b0adc0e1c07fa909afab`
