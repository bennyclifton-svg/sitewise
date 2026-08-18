# Verified Codebase Map

> Every claim below was read from the repo on 2026-08-18 at commit `acb10131`.
> Line numbers drift — **re-grep before trusting a line number**, but the file
> paths and shapes are correct.
>
> Read this once when you start a stage. It replaces exploration.

## The two classifiers (this is the whole problem)

### Classifier A — semantic, corpus-side

**`backend/ingest/classify.py`** → `classify_entry(entry: ManifestEntry) -> Classification`

- Decides `document_class` from extension + filename + path.
- Emits `ingest_mode` via `_ingest_mode_for_class` (`classify.py:~135`).
- **Reads no document content at all.** Filename and path only.

### Classifier B — filing, app-side

**`backend/app/intake/classifier.py`** → `classify_inbox_destination(...) -> str | None`

- Returns a destination folder string (e.g. `"03-design/structural"`) directly.
- Uses `INBOX_PACKAGE_DESTINATIONS`, then ~9 ordered regex families.
- **Does read content** via `preview_snippet` (first 4096 bytes).
- Has zero knowledge of `Classification`.

**These two never talk.** That is the duplication Stage 6 removes.

## Where evidence gets suppressed

`backend/ingest/router.py`:

```python
def _chunker_for(classification):
    if classification.ingest_mode == "register_only":
        return "register"
    ...

def should_persist_chunks(plan) -> bool:
    if ingest_mode == "register_only":
        return False          # <-- evidence dies here
    if document_class in {"doctrine", "reference_guide"} and extension != ".md":
        return False          # <-- and here
    return True
```

Combined with `classify.py`'s `drawing → register_only`, any file classified
`drawing` loses all searchable text.

**Important nuance the original plan missed:** extraction still happens.
`_extractor_for` returns `"pdf_odl"` for *any* `.pdf` before the drawing branch
is reached, so the text is extracted and then discarded at chunk time. The fix
is in `router.py`, **not** in the extractors.

## The `plan` bug, exactly

`backend/ingest/classify.py`, `_looks_like_drawing`:

```python
if re.search(r"\bplan\b", lowered) and not any(
    skip in lowered for skip in ("implementation plan", "management plan", "quality plan")
):
    return True
```

Three exclusions only. So these are all misclassified `drawing` → `register_only`
→ unsearchable:

`Cost Plan.pdf` · `Business Plan.pdf` · `Payment Plan.pdf` ·
`Structural Specification Plan.pdf` · `Staging Plan.pdf` · `Traffic Plan.pdf`

## Current `DocumentClass` vs. target

`backend/ingest/types.py` declares 18 values:

```text
unknown contract specification tender_submission trr evaluation rft addendum
eoi tep drawing report certificate correspondence schedule reference_guide
doctrine planning_instrument
```

**Two values are written to the DB but are NOT in the Literal — existing type violations:**

| Value | Written at |
|---|---|
| `inbox_pending` | `backend/app/api/projects.py:593` |
| `corpus_catalog` | `backend/app/retrieval/catalog.py:110` |

Stage 8 must handle both. The original plan mentioned only `inbox_pending`.

## Persistence

`backend/app/database/source_document.py`:

```python
document_class: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
ingest_mode:    Mapped[str | None] = mapped_column(String(32))
document_metadata: Mapped[dict | None] = mapped_column(JSONB)
content_hash:   Mapped[str | None] = mapped_column(String(64))
source_type:    Mapped[str | None] = mapped_column(String(64))
normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
```

**`document_class` is `String(64)`, not a Postgres enum.** This is load-bearing
good news: the Stage 8 taxonomy change needs **no schema migration**, only a
data migration. The original plan over-scoped this.

`content_hash` is nullable — Stage 5 keys overrides on it, so Stage 5 must
handle the null case explicitly.

## Sort Files path

```text
frontend ProjectCockpitPage.tsx
  → POST (app/api/projects.py:3400 post_sort_files)
  → app/workflows/sort_files.py:100 run_sort_files_workflow
  → app/intake/sort_service.py:413 sort_inbox_files
```

Also auto-invoked post-ingest: `app/workflows/document_ingest.py:128`.

### What already exists (do not rebuild it)

`sort_service.py` already models per-file outcomes:

```python
SortOutcome = Literal["moved", "already-filed", "unresolved", "skipped", "refused"]

@dataclass
class SortFilesCounts:
    inspected: int; moved: int; already_filed: int
    unresolved: int; skipped: int; refused: int
```

and already distinguishes skip reasons in free text (`sort_service.py:~446`):

- `"Prior intake manifest"`
- `"Ingestion is still in progress"`  ← the "0 moved" case
- `"Ingestion failed; retry the upload before sorting"`

**So the backend is ~80% of the way to the plan's §15 acceptance criteria.**
The real gaps are:
1. `"still in progress"` is a *reason string*, not a machine-readable outcome,
   so the UI cannot distinguish "waiting" from "genuinely skipped".
2. The frontend collapses everything into one count.
3. Sorting re-reads file previews instead of using persisted classification (D2).

Scope Stage 7 accordingly. Do not write a new outcome model.

## Invoice code that already exists

`backend/app/cost_plan/`: `invoice_extraction.py`, `invoice_mapping.py`,
`invoice_service.py`, `invoice_candidates.py`, `evidence_reconciliation.py`,
`calculations.py`, `models.py`, `schemas.py`.

Stages 10–12 **extend** these. Adding an `invoice/` package is a D8 violation.

## Consumers of `document_class` (Wave 2 blast radius)

```text
backend/app/retrieval/queries.py:43       filter
backend/app/retrieval/register.py:48,93   == "drawing"
backend/app/retrieval/inventory.py        display
backend/app/retrieval/catalog.py:110      writes "corpus_catalog"
backend/app/projects/document_register.py:162  == "specification"
backend/app/projects/consultant_facts.py:125-171  == "certificate"
backend/app/projects/identity_bootstrap.py:35     == "planning_instrument"
backend/app/cost_plan/consultant_appointment.py:527
backend/app/mcp_bridge/server.py:697, 4128, 4363  writes "planning_instrument"
backend/app/grounding/validator.py:35
backend/app/api/projects.py:494,558,593,644,877,909
backend/app/assistant/agent.py:231
backend/ingest/router.py, persist.py, pipeline.py
```

**14 files.** Every Wave 2 packet must be checked against this list.

## Commands (use these exactly)

```bash
# Backend — run from backend/
uv run pytest                                  # full suite
uv run pytest tests/ingest/test_classify.py -v # targeted
uv run pytest -m "not integration" -q          # fast subset
uv run ruff check .
uv run alembic upgrade head

# Frontend — run from frontend/, pnpm only
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

## Test files you will touch

```text
backend/tests/ingest/test_classify.py          (asserts register_only 4x — Stage 1 rewrites)
backend/tests/workflows/test_sort_files.py     (~630 lines)
backend/tests/workflows/test_document_ingest_auto_sort.py
backend/tests/inbox/test_upload.py
frontend/src/components/project/ProjectControlBoard.test.tsx
```

`backend/tests/ingest/test_classify.py` lines 55, 67, 94, 114 all assert
`ingest_mode == "register_only"`. Stage 1 **must** rewrite these, not delete them.
