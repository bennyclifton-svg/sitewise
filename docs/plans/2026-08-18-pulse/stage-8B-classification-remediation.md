# Stage 8B — Classification Remediation

**Goal:** Close the defects found by review of Stages 0–8 (2026-08-19) before
Wave 2 builds consumers on top of them. Nothing here is new capability. Every
task either restores a doctrine invariant that Stages 1–8 claimed and did not
deliver, or removes state that will mislead Stage 9/13/14.

**This stage exists because Gate 2's checklist was satisfiable without being
true.** "All 14 consumers read canonical classification" was literally correct
and materially wrong: the consumer list in `01-ground-truth.md` never named
`source_documents.document_type`, so nobody looked at it. Do not treat the
checklist as the specification — treat the doctrine as the specification.

**Ownership:**
`backend/ingest/classify.py`, `backend/ingest/router.py`,
`backend/ingest/chunkers/register.py`, `backend/ingest/embed.py`,
`backend/app/projects/classification_override.py`,
`backend/app/intake/classifier.py` (`filing_destination` only),
`backend/app/intake/sort_service.py`,
`backend/app/mcp_bridge/server.py` (the `set_document_classification` tool only),
`backend/app/web_research/attachments.py` (the two `document_type` writes only),
`backend/scripts/x1_reclassify.py` (new),
`frontend/src/components/project/ClassificationChip.tsx`.

**Forbidden:**
- `ingest/types.py` **vocabularies**. Frozen at Gate 1 (tag `x1-gate-1`). No new
  class, subject or basis value. Adding one is a Gate 1 reopen, not a packet.
- **A new Alembic revision.** Stage 10 owns the next one and migration ordering
  is a single-owner seam (`90-downstream-stages.md`). Everything here fits in
  JSONB or in code. If you believe you need a migration, raise an Integration
  note and stop.
- `app/retrieval/schemas.py`, `app/retrieval/queries.py` — Stage 9.1 owns these.
- `app/cost_plan/` — Stages 10–12.
- A second classifier, a `classifier_v2.py`, or a "compat" module (D8).

**Predecessor:** Stage 8 `[x]` (`6fc7a9d2`). Wave A (8B.1–8B.4) runs **before**
the Gate 2 signature — see OD-10. Wave B runs before Stage 9.1.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D1, D2, D4, D5, D6, D8 and
  §Canonical vocabularies
- `TRACKER.md` § Gate 2, § Open decisions (OD-5…OD-10), § Integration notes
- [`stage-05-user-override.md`](./stage-05-user-override.md) Task 5.2 and 5.3 —
  **read these before 8B.1.** Task 5.3's sketch literally specifies the bug
  8B.1 removes. It is wrong. Do not restore it.
- This file. Per-task source files are named in each task.

**LOC budget (D8).** Stage 0.6 baseline `5609`; Stage 8 measured `6073`
(+8.3%). The gate is +10% = **6170**. That leaves 97 lines. Tasks 8B.5, 8B.6,
8B.7 and 8B.10 are net-negative by design; schedule at least one of them before
the additive tasks so the gate never goes red mid-stage. Measure with the exact
Stage 0.6 command.

---

# Wave A — blocks the Gate 2 signature

These four corrupt data or bypass authorisation every time the feature is used.
They compound with usage, so they cannot sit behind a signature that reads
"canonical classification live".

## Task 8B.1 — A user override must merge onto the machine classification

**Defect (verified).** `classification_from_override`
(`app/projects/classification_override.py:31`) builds a `Classification` whose
`document_metadata` is only `{basis, confidence, subject}`. On the hosted path
`classify_entry` returns it *instead of* the machine result
(`ingest/classify.py:449`), so every observed field is destroyed.

Reproduced against HEAD:

```text
machine:  commercial  meta={commercial_type: fee_proposal, discipline: structural,
                            title: "Acme Structural Fee Proposal"}   -> 02-consultant/structural
override: commercial  meta={basis, confidence, subject}              -> 01-cost
```

For a drawing the override wipes `drawing_number`, `revision`, `title`,
`format` — precisely the fields `app/retrieval/register.py:48` selects on.
**Correcting a drawing's class removes it from the drawing register on the next
re-ingest.**

**The rule (OD-5 default): an override replaces interpretation and preserves
observation.** Replace `document_class`, `document_subject`, `basis`,
`confidence`. Preserve every other `document_metadata` key untouched.

`drawing_number` is an observation about the file. It does not become false
because a human corrected what kind of document it is. That is D5.

Change the signature so the machine answer is available:

```python
def classification_from_override(
    row: object, *, machine: Classification | None = None
) -> Classification:
```

`_hosted_override` (`ingest/hosted.py:70`) must therefore resolve the machine
classification first and pass it in. Keep `classify_entry` pure and sync — the
caller still does the lookup, exactly as Stage 5.3 intended.

**Then close the routing hole this exposes.** `filing_destination`
(`app/intake/classifier.py:158`) consults `commercial_type`, `brief_kind` and
`due_diligence` *before* the class, so preserved metadata from a superseded
class would now dominate the user's correction. Guard each on the class that
produces it:

| Metadata key | Only consulted when |
|---|---|
| `commercial_type` | `document_class == "commercial"` |
| `brief_kind` | `document_class == "report"` |
| `due_diligence` | `document_class == "report"` |
| `procurement_stage` | `document_class == "commercial"` |

This is a latent bug independent of overrides: a filename hint currently
outranks a strong structural class signal.

**Failing tests (write first, confirm RED):**

```text
tests/projects/test_classification_override.py
  test_override_preserves_machine_drawing_identity
  test_override_preserves_discipline_and_commercial_type
  test_overridden_drawing_stays_in_drawing_register
tests/intake/test_filing_destination.py
  test_stale_commercial_type_does_not_route_an_overridden_report
```

```bash
cd backend && uv run pytest tests/projects/test_classification_override.py \
  tests/intake/ tests/ingest/ -q
```

```text
fix: user overrides preserve machine-observed document metadata
```

## Task 8B.2 — Preserve the machine opinion (D5)

**Defect.** `previous_class = document.document_class`
(`classification_override.py:126`) reads the *current* value, which after one
override is already the user's. A second correction overwrites the only record
of what the machine thought. The machine's answer is then unrecoverable.

This is not academic. `90-downstream-stages.md` § Stage E says *"Stage 5
overrides are the labelled set"* and requires `deterministic filename accuracy`
and `deterministic content accuracy` before a model fallback is built. You
cannot compute either against labels whose prediction was deleted.

**Storage (OD-6 default): JSONB keys, not a column.** Doctrine
§Canonical vocabularies is explicit — *"Non-class metadata lives in
`document_metadata` JSONB, not in new columns"* — and a column would need the
Alembic revision this stage is forbidden from creating.

On every classification write in `ingest/persist.py`, record the machine answer
once and never overwrite it:

```text
document_metadata.machine_class       # DocumentClass the classifier chose
document_metadata.machine_subject     # DocumentSubject
document_metadata.machine_confidence  # "0.90"
document_metadata.machine_basis       # structural | filename | content | default
```

`set_document_classification` must not touch the `machine_*` keys. Keep
`previous_class` on the override row as-is — it is the audit of the *last*
value, which is a different and also useful fact. Do not conflate them.

**Failing tests:**

```text
tests/ingest/test_persist_metadata.py::test_machine_answer_recorded_on_first_persist
tests/projects/test_classification_override.py
  test_second_override_does_not_erase_machine_answer
  test_override_leaves_machine_keys_untouched
```

```text
feat: record the machine classification alongside the human correction
```

## Task 8B.3 — The MCP override tool must use the mutation authorizer

**Defect.** `set_document_classification` (`app/mcp_bridge/server.py:4239`)
calls `authorize_project_access_with_claims` — the **read** authorizer. It
mutates `source_documents.document_class` and inserts an override row while
skipping `require_active_mutation_turn`, i.e. the durable turn capability and
scope check. All 28 other mutating tools in that file use
`authorize_project_mutation_with_claims`.

Doctrine D6 and root `AGENTS.md` both place MCP authorisation in deterministic
Python. This is the one tool that opted out.

Swap the authorizer. Also wrap the unguarded `uuid.UUID(project_id)` at
`server.py:4226` in the same `ToolError` handling the `document_id` parse
already has.

**Failing test (confirm RED — it will currently pass the mutation):**

```text
tests/mcp_bridge/test_set_document_classification.py
  test_tool_refuses_without_an_active_mutation_turn
  test_tool_rejects_malformed_project_id_as_tool_error
```

```bash
cd backend && uv run pytest tests/mcp_bridge/test_set_document_classification.py -q
```

```text
fix: require a mutation turn capability for the MCP classification override
```

## Task 8B.4 — The confidence floor must sit below the review gate

**Defect (verified).** `_filename_confidence` (`ingest/classify.py:340-345`)
floors at exactly **0.65**. The review gate is `confidence < 0.65`
(`app/intake/sort_service.py:223` and `:572`). So the *weakest possible*
filename guess lands precisely on the auto-file side of the boundary and never
prompts a human.

Second defect, same cascade: `classify_entry` returns at `classify.py:520` as
soon as a filename winner exists, so content markers can never fire when any
filename signal matched. Verified:

```text
Statement.pdf containing "TAX INVOICE"  ->  report @ 0.65   (basis=filename)
                          content marker would give commercial @ 0.95
```

`report @ 0.65` then auto-files, silently, to the wrong folder.

**OD-8 default: lower the floor, leave the gate and the published bands
alone.** Doctrine's bands are a contract other stages read; moving the gate
silently reclassifies the entire 0.65 band. Instead:

1. `_filename_confidence` weak case returns **0.55**, not 0.65. A single weak
   signal is now honestly "needs review", which is what the doctrine band
   already says `< 0.65` means.
2. When a filename winner exists **and** a content marker matches, take the
   higher confidence and set `basis` accordingly. Doctrine orders `basis`
   cheapest-to-most-expensive — that is a statement about cost, not precedence.
   Comparing confidence is legitimate and is what makes Stage 4.4's content
   markers reachable in production at all.

**Note the scope limit.** This task does *not* make content markers run on the
hosted path — `hosted.py:44` and `pipeline.py:76` still call `classify_entry`
without `extracted_text`, so Stage D remains dead in production ingest. That is
a real gap; it is **out of scope here** because it means classifying after
extraction, which reorders the pipeline. Raise it as an Integration note for
Stage 9 — it is listed in TRACKER already.

**Failing tests:**

```text
tests/ingest/test_filename_scoring.py::test_single_weak_signal_is_below_the_review_gate
tests/ingest/test_classify.py::test_strong_content_marker_beats_a_weak_filename_guess
tests/workflows/test_sort_files.py::test_weak_filename_guess_reports_needs_review
```

```bash
cd backend && uv run pytest tests/ingest/ tests/workflows/test_sort_files.py -q
```

Re-run the fixture ratchet and **record the new numbers in TRACKER § Accuracy
measurements**. If the ratchet drops below 14/14, do not lower the ratchet —
fix the classifier or raise an Integration note.

```text
fix: weak filename guesses fall below the review gate
```

---

## 🔒 Wave A exit — Gate 2 may now be signed

- [ ] 8B.1–8B.4 all `[x]` with pasted output
- [ ] Backend failures ⊆ `docs/acceptance/x1/baseline-backend-failures.txt`
- [ ] Fixture accuracy re-recorded in TRACKER
- [ ] LOC gate ≤ 6170

---

# Wave B — before Stage 9.1's first production packet

## Task 8B.5 — Retire `document_type`

**Defect.** `source_documents.document_type` is a third vocabulary on the same
row. Migration 049 rewrote `document_class` only, so `document_type` still
holds `reference_guide`, `doctrine`, `planning_instrument`,
`tender_submission` — and it is **user-visible** as the register title fallback
(`app/api/projects.py:506`, `app/projects/document_register.py:168`,
`app/agent/document_context.py:102`). Two writers still emit the legacy value
today (`app/web_research/attachments.py:77,89`;
`app/mcp_bridge/server.py:4134`) while setting `document_class =
"statutory_instrument"` on the same row.

`infer_document_type` (`ingest/metadata.py:44-55`) returns `document_class`
verbatim whenever it is not `"unknown"`. The column is a copy with a stale tail.
This is a D1 violation — a subsystem holding a private opinion.

**OD-7 default: deprecate in place. Stop writing it, stop reading it, leave the
column.** Dropping it is a schema migration this stage is forbidden from
creating, and the data is harmless once unread.

1. Delete the two `document_type = "planning_instrument"` writes.
2. Stop `ingest/persist.py` populating it from `infer_document_type`.
3. Remove it from the three read sites; fall through to the existing filename
   derivation. Users stop seeing legacy vocabulary immediately.
4. Add a TRACKER Integration note that the column is dead and may be dropped in
   a later cleanup packet with an owned migration.

**Failing test:**

```text
tests/test_project_evidence.py::test_register_title_ignores_legacy_document_type
tests/web_research/test_attachments.py::test_official_attachment_writes_no_document_type
```

```text
refactor: stop reading and writing the legacy document_type column
```

## Task 8B.6 — `ingest_mode` follows text, not class

`_ingest_mode_for_class` (`ingest/classify.py:284`) still returns
`register_only` for every drawing. No consumer gates retrieval on it any more —
so D3 holds functionally — but every newly ingested drawing rewrites the state
Stage 2 backfilled away, and `scripts/x1_audit.py` reports it as
`suppressed_with_text`. The next agent to run the audit will see a regression
that is not one, and "fix" it.

Derive it from the same helper that already owns the decision:

```python
ingest_mode = "full_text" if has_useful_text(extracted_text) else "register_only"
```

`has_useful_text` (`ingest/router.py:6`) is the single D3 definition. Do not
fork it. Where no text is available at classify time, `register_only` is the
honest default and `persist` corrects it.

```text
refactor: derive ingest_mode from useful text rather than document class
```

## Task 8B.7 — Migration 049: test the SQL, assert the post-condition, drop the data shim

Three problems in `alembic/versions/049_canonical_document_taxonomy.py`:

1. **The executed SQL is untested.** `test_taxonomy_migration.py` covers
   `apply_class_mapping` / `revert_class_mapping`. The real `downgrade()`
   strips `extra` keys unconditionally; `revert_class_mapping` strips them only
   when the value matches. Two behaviours, one tested.
2. **No post-condition.** Nothing asserts zero non-canonical classes remain.
   Verified empirically on dev; unverified anywhere else.
3. **`_legacy_document_class` is permanent.** It is written into
   `document_metadata` on every migrated row and never removed. TRACKER
   § Shims outstanding says "None" — true of the code, not of the data.

Add a test that runs `upgrade()` and `downgrade()` against a real session and
asserts the round trip. Add an `assert` in `upgrade()` that no row holds a class
outside `get_args(DocumentClass)`. Strip `_legacy_document_class` at the end of
`upgrade()` — the downgrade path is already rehearsed and recorded, and
`docs/acceptance/x1/audit-post-backfill.json` is the durable record.

**Do not write a new revision.** Amend 049 and re-run the rehearsal:

```bash
cd backend
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
uv run python scripts/x1_audit.py
```

```text
test: cover the taxonomy migration SQL and clear the legacy class marker
```

## Task 8B.8 — Re-classify the historical corpus

Stage 2 backfilled chunks. Stage 8 renamed classes. **Nothing has ever run
Stage 4's classifier over the stored rows.** 234 of 543 (43%) are `unknown` and
will not route, will not filter, and will produce no Pulse signal.

`backend/scripts/x1_reclassify.py`, modelled on `scripts/x1_backfill.py`:
`--dry-run` default, batched, idempotent, prints before/after class counts, and
writes a rollback log table exactly as `x1_backfill.py` does.

**OD-9 default: `unknown` rows only.** Select rows where
`document_class = 'unknown'` **and** `document_metadata->>'basis'` is null or
`'default'`. Never touch a row with `basis = 'user'` — that is D4 and it is not
negotiable. Widening the scope to re-decide confident machine rows is a separate
decision, and should wait until Stage E has accuracy numbers to justify it.

Record before/after counts in TRACKER § Accuracy measurements. If the unknown
rate does not move materially, that is a finding about the classifier, not a
reason to widen the scope — raise an Integration note.

```bash
cd backend
uv run python scripts/x1_reclassify.py            # dry run
uv run python scripts/x1_reclassify.py --apply
uv run python scripts/x1_reclassify.py            # must report 0
```

```text
feat: re-classify historical unknown documents onto the Stage 4 classifier
```

## Task 8B.9 — Bound drawing chunking and embedding

`chunk_register` (`ingest/chunkers/register.py`) emits **exactly one chunk
holding the entire document**, and `embed_texts` (`ingest/embed.py`) has no
token cap — it passes chunk text straight to the embeddings API, which raises
rather than truncates above the model limit.

Before Stage 1 this path was unreachable for drawings. It is now the default for
all 200 of them. Stage 2's backfill happened to succeed, so this is a latent
failure, not an active one — a text-heavy drawing set will fail ingest outright
where it used to degrade quietly.

Note also what Stage 2's spot-check actually proved: it used
`cost-plan-system.md`, a markdown file on the **prose** chunker. The programme's
founding claim — *"any file classified `drawing` loses all searchable text"* —
was fixed and then verified against a case that never had the bug. Re-verify it
properly here on a real drawing.

1. Give `chunk_register` a token ceiling and split beyond it, preserving
   `page_or_section` so title-block provenance survives.
2. Give `embed_texts` an explicit guard that raises a typed, logged error naming
   the offending `relative_path` instead of an opaque API error.

**Failing tests:**

```text
tests/ingest/test_chunk_register.py::test_long_drawing_text_splits_into_bounded_chunks
tests/ingest/test_embed.py::test_oversized_chunk_raises_a_named_error
```

```text
fix: bound the register chunker and guard embedding input size
```

## Task 8B.10 — One vocabulary, one threshold

`ClassificationChip.tsx:6-35` hardcodes both frozen vocabularies in TypeScript
with nothing asserting they match `ingest/types.py`. `0.65` now exists in four
places (`classify.py`, `sort_service.py` twice, `ClassificationChip.tsx`).

1. Serve the vocabularies from the existing project options endpoint, or
   generate the TS constant from `ingest/types.py`. Either is acceptable;
   duplication with no test is not.
2. Add a test that fails when the two lists diverge.
3. Name the threshold once in Python (`REVIEW_CONFIDENCE_MIN` beside
   `USEFUL_TEXT_MIN_CHARS` in `ingest/router.py`) and once in TS, covered by the
   same contract test.
4. `_classification_from_document` (`sort_service.py:113`) casts DB strings into
   the canonical `Literal` with `# type: ignore` and no validation. Validate at
   that read boundary and log + fall back to `unknown` on a miss.

```bash
cd backend && uv run pytest tests/ingest/ -q
cd frontend && pnpm typecheck && pnpm test
```

```text
refactor: single source of truth for the classification vocabulary and review threshold
```

## Task 8B.11 — Filing must not silently re-classify

`_move_workspace_file` (`app/intake/sort_service.py:459-470`) re-runs
`ingest_hosted_file` at the destination with `skip_if_unchanged=False`, after
`_resolve_destination_filename` may have renamed the file. The class that chose
the folder and the class stored afterwards can therefore differ — a D1 split on
a single row. It is also a full download + re-extract + re-embed per move, which
is the D2 cost Stage 7.3 claimed to have removed from the Sort path.

Reuse the classification that made the routing decision instead of recomputing
it. Move storage and update `relative_path`; do not re-derive
`document_class` from the new path.

**Failing test:**

```text
tests/workflows/test_sort_files.py
  test_filed_document_keeps_the_classification_that_routed_it
  test_move_does_not_reextract_or_reembed
```

```text
fix: filing preserves the classification that chose the destination
```

---

## Exit gate

- [ ] 8B.1–8B.11 each `[x]` with pasted verification output in `TRACKER.md`
- [ ] `uv run pytest -q --tb=line --import-mode=importlib` — failures ⊆
      `docs/acceptance/x1/baseline-backend-failures.txt`
- [ ] `uv run ruff check .` clean
- [ ] `pnpm typecheck && pnpm test && pnpm build` clean
- [ ] LOC gate ≤ **6170** (Stage 0.6 command, exact)
- [ ] Fixture accuracy + historical unknown rate recorded in TRACKER
- [ ] `alembic upgrade → downgrade → upgrade` succeeds; `x1_audit.py` shows zero
      non-canonical classes and zero `_legacy_document_class` rows
- [ ] Grep proves one classifier, one vocabulary, one review threshold:
      `grep -rn "0\.65" backend/ frontend/src/` returns only the named constants
- [ ] OD-5…OD-10 recorded in TRACKER as answered or explicitly defaulted
