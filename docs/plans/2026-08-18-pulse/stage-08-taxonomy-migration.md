# Stage 8 — Taxonomy Data Migration 🔒

**Goal:** The database's `document_class` values match the frozen Stage 3
vocabulary, all 14 consumers read canonical values, and every shim is deleted.
**This stage closes Gate 2.**

**Good news from [`01-ground-truth.md`](./01-ground-truth.md):**
`document_class` is `String(64)`, **not a Postgres enum**. There is no schema
migration — only a data migration and consumer updates. The original plan
over-scoped this.

**Ownership:** one migration, plus the 14 consumer files listed below.
**Concurrency:** the migration is single-owner. Consumer updates may fan out
*after* the migration lands.

**Predecessor:** Stages 6 and 7 `[x]`.

**Reading list:**
- [`01-ground-truth.md`](./01-ground-truth.md) §"Consumers of `document_class`"
- `TRACKER.md` § Legacy → canonical mapping (written at Stage 3.7)
- `TRACKER.md` § Open decisions (OD-1, OD-2)
- `docs/acceptance/x1/audit-post-backfill.json`

---

## Task 8.0 — Resolve the open decisions first

**Blocking.** Do not write the migration until OD-1 and OD-2 have answers
recorded in `TRACKER.md`. Defaults, if a human has not answered within the
packet's life:

- **OD-1** `doctrine` / `reference_guide` → `report` +
  `document_metadata.reference_kind`. Lossless; `source_type` already carries the
  real distinction.
- **OD-2** `corpus_catalog` → `schedule` + `document_metadata.synthetic = true`.
  It is a generated index, not an artefact.

Flag whichever default you used in Integration notes.

## Task 8.1 — Migration with counts and dry-run

`backend/alembic/versions/049_canonical_document_taxonomy.py`.

**Print counts before and after, inside the migration.** A silent data migration
is unauditable.

```python
MAPPING: dict[str, tuple[str, dict[str, str]]] = {
    "tep":               ("commercial",           {"procurement_stage": "tep"}),
    "eoi":               ("commercial",           {"procurement_stage": "eoi"}),
    "rft":               ("commercial",           {"procurement_stage": "rft"}),
    "addendum":          ("commercial",           {"procurement_stage": "addendum"}),
    "tender_submission": ("commercial",           {"procurement_stage": "submission"}),
    "evaluation":        ("commercial",           {"procurement_stage": "evaluation"}),
    "trr":               ("commercial",           {"procurement_stage": "trr"}),
    "planning_instrument":("statutory_instrument", {}),
    "doctrine":          ("report",               {"reference_kind": "doctrine"}),        # OD-1
    "reference_guide":   ("report",               {"reference_kind": "reference_guide"}), # OD-1
    "corpus_catalog":    ("schedule",             {"synthetic": "true"}),                 # OD-2
    "inbox_pending":     ("unknown",              {}),                                    # + ingest_status
}
```

**This table must be byte-identical to `_LEGACY_TO_CANONICAL` in
`ingest/classify.py`.** Add a test that asserts it:

```python
def test_migration_mapping_matches_code_mapping() -> None:
    from ingest.classify import _LEGACY_TO_CANONICAL
    # import MAPPING from the migration module and compare
```

Preserve existing `document_metadata` — **merge**, never replace:

```sql
UPDATE source_documents
SET document_class = :new_class,
    document_metadata = COALESCE(document_metadata, '{}'::jsonb) || :extra_metadata::jsonb
WHERE document_class = :old_class;
```

`||` is a shallow merge with the right-hand side winning. That is what you want.

## Task 8.2 — `inbox_pending` is a lifecycle state, not a class

`backend/app/api/projects.py:593` writes `document_class="inbox_pending"`.

Replace with `document_class="unknown"` plus the existing ingest status field.
Valid statuses:

```text
uploaded  queued  extracting  classifying  ready  needs_review  failed
```

`document_class` must always answer *"what kind of artefact is this?"* — never
*"where is it in the pipeline?"*

Grep for readers before changing the writer:

```bash
grep -rn "inbox_pending" backend/ frontend/src/ | grep -v __pycache__
```

## Task 8.3 — Migrate the 14 consumers

One commit each. Tick them off here **and** in `TRACKER.md`:

- [x] `backend/app/retrieval/queries.py:43` — filter accepts canonical class
- [x] `backend/app/retrieval/register.py:48,93` — `== "drawing"` still valid, verify
- [x] `backend/app/retrieval/inventory.py` — display strings
- [x] `backend/app/retrieval/catalog.py:110` — stop writing `corpus_catalog`
- [x] `backend/app/projects/document_register.py:162` — `== "specification"` verify
- [x] `backend/app/projects/consultant_facts.py:125-171` — `== "certificate"` verify
- [x] `backend/app/projects/identity_bootstrap.py:35` — `planning_instrument` → `statutory_instrument`
- [x] `backend/app/cost_plan/consultant_appointment.py:527`
- [x] `backend/app/mcp_bridge/server.py:4128` — **writes** `planning_instrument`
- [x] `backend/app/mcp_bridge/server.py:697,4363` — reads
- [x] `backend/app/grounding/validator.py:35`
- [x] `backend/app/api/projects.py:494,558,593,644,877,909`
- [x] `backend/app/assistant/agent.py:231`
- [x] `backend/ingest/persist.py` + `pipeline.py`

> `app/assistant/` is legacy but **must not be deleted** — root `AGENTS.md`
> blocks that until the production cutover gate. Migrate it; do not remove it.

Retrieval must keep returning `unknown` documents. A document nobody could
classify is still evidence (D3).

## Task 8.4 — Rollback rehearsal

Before applying to any shared database:

```bash
# 1. snapshot the pre-migration class distribution
psql "$DATABASE_URL" -c "\copy (SELECT id, document_class, document_metadata FROM source_documents) TO 'x1_pre_taxonomy.csv' CSV HEADER"

cd backend
uv run alembic upgrade head
uv run python scripts/x1_audit.py            # confirm zero legacy classes remain
uv run alembic downgrade -1
uv run python scripts/x1_audit.py            # confirm distribution matches the CSV
uv run alembic upgrade head
```

`downgrade()` must restore both `document_class` **and** remove the metadata keys
this migration added. Write it properly.

Record all three audit outputs in `TRACKER.md`.

## Task 8.5 — Delete the shims

```bash
grep -rn "LegacyDocumentClass\|_LEGACY_TO_CANONICAL" backend/ | grep -v __pycache__
```

Once the data migration has run and consumers are green, both must go. Then
`TRACKER.md` § Shims outstanding must be **empty**.

A shim that survives Gate 2 becomes permanent. That is exactly the "parallel v2
system" D8 forbids.

## Task 8.6 — Verify no legacy values remain

```sql
SELECT document_class, count(*) FROM source_documents
WHERE document_class NOT IN (
  'drawing','specification','report','certificate','correspondence','contract',
  'commercial','schedule','statutory_instrument','photo','unknown'
) GROUP BY 1;
```

Expected: **zero rows.** Paste the empty result into `TRACKER.md`.

## Exit gate — this is Gate 2

- [ ] OD-1 and OD-2 answered and recorded
- [ ] Migration mapping identical to code mapping (test proves it)
- [ ] `document_metadata` merged, not overwritten
- [ ] `upgrade → downgrade → upgrade` rehearsed, distributions match
- [ ] All 14 consumers migrated, one commit each
- [ ] Zero non-canonical `document_class` values in the database
- [ ] `LegacyDocumentClass` deleted; § Shims outstanding empty
- [ ] `uv run pytest` failures ⊆ baseline
- [ ] `pnpm typecheck && pnpm test && pnpm build` clean
- [ ] GATE 2 signed by a human in `TRACKER.md`

## After Gate 2

Open [`90-downstream-stages.md`](./90-downstream-stages.md) and expand Stage 9
into packets — now that the contract is real and proven, the expansion will be
accurate rather than speculative.
