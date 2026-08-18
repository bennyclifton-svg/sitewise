# Stage 1 — Evidence Safety

**Goal:** Classification can no longer make valid text disappear (D3).

**This is the highest-value stage in the programme.** Every day it is not done,
`Cost Plan.pdf` and friends are invisible to Pi.

**Ownership:** `backend/ingest/router.py`, `backend/ingest/classify.py`
(one function only), `backend/tests/ingest/`.
**Forbidden:** taxonomy changes, `Classification` field changes, anything under
`backend/app/intake/`. Those are Stages 3, 6, 8.

**Predecessor:** Stage 0 complete, baseline table filled.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D3
- [`01-ground-truth.md`](./01-ground-truth.md) §"Where evidence gets suppressed"
- `backend/ingest/router.py` (58 lines — read all)
- `backend/ingest/classify.py` (`_looks_like_drawing` + `_ingest_mode_for_class` only)
- `backend/tests/ingest/test_classify.py`

---

## Task 1.1 — Write the failing test first

Create `backend/tests/ingest/test_evidence_safety.py`:

```python
"""D3: classification decides routing, never whether text is indexed."""
from __future__ import annotations

from pathlib import Path

from ingest.router import build_ingest_plan, should_persist_chunks
from ingest.types import Classification, ManifestEntry, ProjectContext


def _entry(filename: str, extension: str = ".pdf") -> ManifestEntry:
    return ManifestEntry(
        absolute_path=Path("/tmp") / filename,
        relative_path=f"01-cost/{filename}",
        project="demo",
        filename=filename,
        extension=extension,
        size_bytes=1024,
    )


def _context() -> ProjectContext:
    return ProjectContext(project="demo", phase="delivery", source_type="project_evidence")


def test_drawing_with_useful_text_still_persists_chunks() -> None:
    """A drawing's general notes are evidence. Class must not suppress them."""
    classification = Classification(
        document_class="drawing", ingest_mode="register_only", document_metadata={}
    )
    plan = build_ingest_plan(_entry("A-101 Rev C.pdf"), _context(), classification)

    assert should_persist_chunks(plan, extracted_text="GENERAL NOTES: refer structural. " * 20)


def test_document_without_useful_text_is_register_only() -> None:
    """No text is a legitimate reason to skip chunking. Class is not."""
    classification = Classification(
        document_class="drawing", ingest_mode="register_only", document_metadata={}
    )
    plan = build_ingest_plan(_entry("IMG_4471.pdf"), _context(), classification)

    assert not should_persist_chunks(plan, extracted_text="")


def test_useful_text_threshold_is_200_chars() -> None:
    classification = Classification(
        document_class="unknown", ingest_mode="full_text", document_metadata={}
    )
    plan = build_ingest_plan(_entry("Scan_001.pdf"), _context(), classification)

    assert not should_persist_chunks(plan, extracted_text="x" * 199)
    assert should_persist_chunks(plan, extracted_text="x" * 200)
```

Run it:

```bash
cd backend
uv run pytest tests/ingest/test_evidence_safety.py -v
```

**Expected: FAIL** — `should_persist_chunks() got an unexpected keyword argument
'extracted_text'`. If it passes, you have the wrong file open.

## Task 1.2 — The threshold helper

Add to `backend/ingest/router.py`, at the top:

```python
USEFUL_TEXT_MIN_CHARS = 200


def has_useful_text(text: str | None) -> bool:
    """D3: the single definition of 'worth indexing'. Do not fork this."""
    return bool(text) and len(text.strip()) >= USEFUL_TEXT_MIN_CHARS
```

## Task 1.3 — Rewrite `should_persist_chunks`

Replace the existing function in `backend/ingest/router.py`:

```python
def should_persist_chunks(plan: IngestPlan, *, extracted_text: str | None) -> bool:
    """Persist chunks when there is useful text. Class never decides this (D3)."""
    if plan.extractor == "unsupported":
        return False
    return has_useful_text(extracted_text)
```

Deleted by this change:
- `if ingest_mode == "register_only": return False`
- `if document_class in {"doctrine", "reference_guide"} and extension != ".md": return False`

The second deletion is deliberate. A doctrine PDF with real prose is evidence.
`source_type` already carries the doctrine distinction, and Stage 8 (OD-1)
finishes that job.

## Task 1.4 — Decouple the chunker

Still in `router.py`:

```python
def _chunker_for(classification: Classification) -> str:
    if classification.document_class == "specification":
        return "specification"
    if classification.document_class == "drawing":
        return "register"      # bounded chunker for title-block + notes
    return "prose"
```

`ingest_mode` no longer selects the chunker. Leave the `ingest_mode` field on
`Classification` alone for now — Stage 3 owns the type, and removing it here
would break `app/web_research/attachments.py:78,91`.

## Task 1.5 — Fix all callers

```bash
cd backend
grep -rn "should_persist_chunks" --include=*.py . | grep -v __pycache__
```

Every call site must now pass `extracted_text=`. Expect hits in
`ingest/pipeline.py` and `ingest/persist.py`. Pass the already-extracted text —
**do not re-extract**, that would violate D2.

## Task 1.6 — Narrow the `\bplan\b` trap (tactical)

In `backend/ingest/classify.py`, `_looks_like_drawing`. This is a *safety* fix,
not the Stage 4 scoring rewrite. Keep it to the exclusion list:

```python
_NOT_A_DRAWING_PLAN = (
    "implementation plan", "management plan", "quality plan",
    "cost plan", "business plan", "payment plan", "staging plan",
    "specification plan", "traffic plan", "waste plan", "project plan",
    "safety plan", "test plan", "communication plan", "procurement plan",
)
```

and use it in the existing `not any(skip in lowered for skip in ...)` branch.

> Stage 4 replaces this list with scoring. Leave a comment saying so:
> `# Superseded by scored filename rules in Stage 4. Tactical fix only.`

## Task 1.7 — Rewrite the four legacy assertions

`backend/tests/ingest/test_classify.py` lines 55, 67, 94, 114 assert
`classification.ingest_mode == "register_only"`.

**Do not delete these tests.** They encode which files are drawings. Change each
assertion from mode to class:

```python
assert classification.document_class == "drawing"
```

If a test's subject is now expected to be non-drawing (e.g. a `Cost Plan`),
change the expectation and add `# Stage 1: was misclassified as drawing`.

## Task 1.8 — Verify

```bash
cd backend
uv run pytest tests/ingest/test_evidence_safety.py -v      # expect: 3 passed
uv run pytest tests/ingest/ -q                              # expect: all pass
uv run pytest -q 2>&1 | grep -E "^(FAILED|ERROR)" | sort > /tmp/x1-s1.txt
diff /tmp/x1-s1.txt ../docs/acceptance/x1/baseline-backend-failures.txt
```

**The `diff` must be empty or show only removed lines.** Any *added* line is a
regression you caused. Fix it or mark the packet `[!]`.

Also confirm the drawing register still populates:

```bash
uv run pytest tests/ -q -k "register" 
```

## Exit gate

- [ ] `test_evidence_safety.py` — 3 passed
- [ ] `diff` against baseline shows no new failures
- [ ] `grep -rn "register_only" backend/ingest/router.py` returns **nothing**
- [ ] Drawing register tests still pass
- [ ] Verification output pasted into `TRACKER.md`

## Commit

```bash
git add backend/ingest/router.py backend/ingest/classify.py backend/ingest/pipeline.py \
        backend/ingest/persist.py backend/tests/ingest/
git commit -m "fix: index text on evidence, not document class

should_persist_chunks now keys on extracted text length (>=200 chars),
not ingest_mode or document_class. Drawings with general notes stay
searchable; Cost Plan / Business Plan / Payment Plan no longer fall into
the drawing branch.

Removes: class-driven register_only suppression in ingest/router.py."
```
