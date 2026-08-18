# Stage 3 — Canonical Classification Contract 🔒

**Goal:** One frozen `Classification` type that every downstream consumer can
build against. **This stage is Gate 1.** Nothing in Wave 2 may start until 3.6.

**Ownership:** `backend/ingest/types.py` — and this stage is the **only** time
that file changes. One agent. No concurrency.
**Forbidden:** classifier *logic* (Stage 4), filing (Stage 6), data migration
(Stage 8). This stage changes types and the sites that construct them, nothing else.

**Predecessor:** Stage 1 `[x]`. (Stage 2 may run in parallel — it touches only scripts.)

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §Canonical vocabularies
- [`01-ground-truth.md`](./01-ground-truth.md) §"Current `DocumentClass` vs target"
- `backend/ingest/types.py` (full — 70 lines)
- `backend/ingest/classify.py` (construction site at the bottom)

---

## Task 3.1 — The closed vocabularies

Replace `DocumentClass` in `backend/ingest/types.py`:

```python
DocumentClass = Literal[
    "drawing",
    "specification",
    "report",
    "certificate",
    "correspondence",
    "contract",
    "commercial",
    "schedule",
    "statutory_instrument",
    "photo",
    "unknown",
]

DocumentSubject = Literal[
    "planning", "heritage", "structural", "services", "hydraulic", "fire",
    "geotechnical", "survey", "cost", "programme", "contract_admin",
    "defects", "sustainability", "access", "acoustic", "none",
]

ClassificationBasis = Literal[
    "user", "structural", "filename", "content", "model", "default",
]
```

**Keep the legacy values reachable for Stage 8 only:**

```python
# Stage 8 migrates these out of document_class. Delete this alias when
# TRACKER.md packet 8.9 closes. Tracked as a shim.
LegacyDocumentClass = Literal[
    "tender_submission", "trr", "evaluation", "rft", "addendum", "eoi", "tep",
    "reference_guide", "doctrine", "planning_instrument",
    "inbox_pending", "corpus_catalog",   # never declared, but present in the DB
]
```

**Record `LegacyDocumentClass` in `TRACKER.md` § Shims outstanding immediately.**

## Task 3.2 — Extend `Classification`

```python
@dataclass(frozen=True, slots=True)
class Classification:
    document_class: DocumentClass
    ingest_mode: IngestMode
    document_metadata: dict[str, str] = field(default_factory=dict)
    document_subject: DocumentSubject = "none"
    confidence: float = 0.0
    basis: ClassificationBasis = "default"
```

New fields carry defaults so existing construction sites keep compiling. That is
intentional: it keeps this packet small.

`ingest_mode` **stays**. It still has real callers
(`app/web_research/attachments.py:78,91`). It is no longer allowed to gate
indexing (Stage 1 already removed that) — it is now descriptive only.

## Task 3.3 — Fix construction sites

```bash
cd backend
grep -rn "Classification(" --include=*.py . | grep -v __pycache__
```

Expected sites: `ingest/classify.py`, `ingest/pipeline.py`, and tests.
For each, decide `document_subject` / `confidence` / `basis` explicitly — do not
lean on defaults except in tests.

For now `classify_entry` should emit:

```python
return Classification(
    document_class=document_class,
    ingest_mode=ingest_mode,
    document_metadata=metadata,
    document_subject="none",           # Stage 4 fills this
    confidence=0.5 if document_class != "unknown" else 0.0,
    basis="filename" if document_class != "unknown" else "default",
)
```

Legacy class values still produced by `classify_entry` will now fail the type
check. **Map them here, provisionally**, using the Stage 8 mapping table:

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

> **OD-1 is an open decision.** If a human has answered it in `TRACKER.md`, use
> their answer. If not, use the mapping above and flag it in Integration notes.

## Task 3.4 — Exhaustiveness test

Create `backend/tests/ingest/test_classification_contract.py`:

```python
from typing import get_args
from ingest.types import ClassificationBasis, DocumentClass, DocumentSubject
from ingest.router import _chunker_for, _extractor_for
from ingest.types import Classification


def test_document_class_vocabulary_is_frozen() -> None:
    """Changing this set is a Gate-1 breaking change. Update the plan first."""
    assert set(get_args(DocumentClass)) == {
        "drawing", "specification", "report", "certificate", "correspondence",
        "contract", "commercial", "schedule", "statutory_instrument",
        "photo", "unknown",
    }


def test_document_subject_vocabulary_is_frozen() -> None:
    assert len(get_args(DocumentSubject)) == 16
    assert "none" in get_args(DocumentSubject)


def test_basis_vocabulary_is_frozen() -> None:
    assert set(get_args(ClassificationBasis)) == {
        "user", "structural", "filename", "content", "model", "default",
    }


def test_every_class_has_a_chunker() -> None:
    """No DocumentClass may fall through to an undefined chunker."""
    for document_class in get_args(DocumentClass):
        classification = Classification(
            document_class=document_class, ingest_mode="full_text", document_metadata={}
        )
        chunker = _chunker_for(classification)
        assert chunker in {"prose", "specification", "register"}, document_class


def test_every_class_has_an_extractor_for_pdf() -> None:
    for document_class in get_args(DocumentClass):
        classification = Classification(
            document_class=document_class, ingest_mode="full_text", document_metadata={}
        )
        assert _extractor_for(classification, ".pdf") != "unsupported", document_class
```

The `test_every_class_has_a_chunker` case is the guard the original plan asked
for. It is what stops a future class silently landing in `prose`.

```bash
uv run pytest tests/ingest/test_classification_contract.py -v
```

## Task 3.5 — Type check

```bash
cd backend
uv run ruff check .
uv run pytest tests/ingest/ -q
uv run pytest -q 2>&1 | grep -E "^(FAILED|ERROR)" | sort | diff - ../docs/acceptance/x1/baseline-backend-failures.txt
```

## Task 3.6 — 🔒 FREEZE

When 3.1–3.5 are green:

```bash
git commit -m "feat: freeze canonical Classification contract (X1 Gate 1)

document_class reduced to 11 canonical values. Adds document_subject,
confidence and basis. Legacy procurement/doctrine classes map through
_LEGACY_TO_CANONICAL until Stage 8 migrates the data.

CONTRACT FROZEN. Downstream consumers may now build against:
  classification.document_class
  classification.document_subject
  classification.confidence
  classification.basis
  classification.document_metadata

Changing ingest/types.py after this commit requires a Gate 1 re-open
recorded in docs/plans/2026-08-18-pulse/TRACKER.md."
git tag x1-gate-1
```

Then in `TRACKER.md`:
- tick 3.6
- write the tag and SHA under Integration notes
- tick the **GATE 1** checklist and get a human signature

## Task 3.7 — Publish the mapping table

Copy `_LEGACY_TO_CANONICAL` into `TRACKER.md` verbatim under a new
`## Legacy → canonical mapping` heading. Stage 8's data migration must use the
exact same table — if the two drift, the DB and the code disagree.

## Exit gate

- [ ] All five contract tests pass
- [ ] `ruff check` clean
- [ ] No new failures vs. baseline
- [ ] Tag `x1-gate-1` exists
- [ ] Mapping table in `TRACKER.md`
- [ ] `LegacyDocumentClass` recorded in § Shims outstanding
- [ ] GATE 1 signed by a human

## After this stage

Wave 2 agents may start — but only against the five frozen fields. If a consumer
needs a sixth field, it files an Integration note. It does **not** edit
`ingest/types.py`.
