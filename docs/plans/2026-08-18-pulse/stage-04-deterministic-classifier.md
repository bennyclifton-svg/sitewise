# Stage 4 — Deterministic Classifier

**Goal:** Classify accurately with zero LLM calls. Model fallback is not written
in this stage — it is not written *at all* until measurement justifies it.

**Ownership:** `backend/ingest/classify.py`, `backend/tests/ingest/`.
**Forbidden:** `ingest/types.py` (frozen at Gate 1), `app/intake/`, any model call.

**Predecessor:** Stage 3 `[x]` and tag `x1-gate-1` exists.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §Canonical vocabularies
- `backend/ingest/classify.py` (full)
- `backend/tests/fixtures/classification/manifest.yaml`
- `backend/ingest/drawing_parse.py` and `title_block.py` (interfaces only)

---

## The cascade

Cheap → expensive. Stop at the first confident answer.

| Stage | Signal | `basis` | Confidence |
|---|---|---|---|
| A | user override lookup | `user` | 1.00 |
| B | extension, native format, parsed title block | `structural` | 0.95 |
| C | scored filename/path rules | `filename` | 0.65–0.90 |
| D | deterministic markers in extracted text | `content` | 0.80–0.95 |
| E | model fallback | `model` | — **not built** |

Stage A arrives in Stage 5. Build B, C, D here and leave a clean seam for A.

## Task 4.1 — Structural signals (basis=`structural`, conf 0.95)

```python
_STRUCTURAL_EXTENSIONS: dict[str, DocumentClass] = {
    ".dwg": "drawing", ".dxf": "drawing",
    ".eml": "correspondence", ".msg": "correspondence",
    ".jpg": "photo", ".jpeg": "photo", ".png": "photo", ".heic": "photo",
}
```

Plus: a successfully parsed drawing title block (`ingest/title_block.py`) is a
structural drawing signal.

**Do not** map `.xlsx` → `schedule` structurally. The current code does, and it
is wrong: cost plans and tender schedules are `.xlsx` and belong in `commercial`.
Demote spreadsheet-ness to a weak Stage C signal.

## Task 4.2 — Scored filename rules (basis=`filename`)

Replace first-match-wins with additive scoring. The winner needs a **margin of
at least 2** over the runner-up, otherwise fall through to Stage D.

```python
_FILENAME_SIGNALS: list[tuple[re.Pattern[str], DocumentClass, int]] = [
    # strong
    (re.compile(r"\bcost plan\b", re.I),            "commercial", 5),
    (re.compile(r"\btax invoice\b|\binvoice\b", re.I), "commercial", 5),
    (re.compile(r"\bvariation\b|\bVO[- ]?\d+\b", re.I), "commercial", 5),
    (re.compile(r"\bfee proposal\b", re.I),         "commercial", 5),
    (re.compile(r"\bprogress claim\b", re.I),       "commercial", 5),
    (re.compile(r"\btender\b|\bRFT\b|\bEOI\b", re.I), "commercial", 4),
    (re.compile(r"\bspecification\b", re.I),        "specification", 5),
    (re.compile(r"\bcertificate\b|\bconsent\b|\bdetermination\b", re.I), "certificate", 5),
    (re.compile(r"\bcontract\b|\bagreement\b|\bdeed\b", re.I), "contract", 5),
    (re.compile(r"\bLEP\b|\bDCP\b|\bSEPP\b", re.I),  "statutory_instrument", 5),
    # drawing structure beats prose words
    (re.compile(r"\b[A-Z]{1,2}-?\d{3}\b"),          "drawing", 5),   # A-101, S203
    (re.compile(r"\b(floor|site|roof|landscape) plan\b", re.I), "drawing", 4),
    (re.compile(r"\belevation\b|\bsection\b|\bdetail\b", re.I), "drawing", 4),
    (re.compile(r"\brev [A-Z]\b", re.I),            "drawing", 3),
    # medium
    (re.compile(r"\breport\b|\bassessment\b|\bstatement\b", re.I), "report", 3),
    (re.compile(r"\bregister\b|\bschedule\b|\bmatrix\b", re.I), "schedule", 3),
    (re.compile(r"\bletter\b|\bnotice\b|\bRFI\b|\bminutes\b", re.I), "correspondence", 3),
    (re.compile(r"\bprogramme\b|\bgantt\b|\blookahead\b", re.I), "schedule", 4),
    # weak — must never decide alone
    (re.compile(r"\bplan\b", re.I),                 "drawing", 1),
    (re.compile(r"\bcost\b|\bbudget\b|\bestimate\b", re.I), "commercial", 2),
]
```

**The load-bearing line is the last-but-one.** `\bplan\b` scores 1. So:

- `Cost Plan.pdf` → commercial 5+2=7, drawing 1 → **commercial**, margin 6 ✓
- `A-102 Ground Floor Plan.pdf` → drawing 5+4+1=10 → **drawing**, margin 10 ✓
- `Business Plan.pdf` → drawing 1, nothing else → margin 1 → **falls to Stage D** ✓

That last outcome is correct behaviour, not a failure.

Score subject on a parallel axis with its own table (`heritage`, `structural`,
`hydraulic`, …). Subject scoring is independent of class scoring.

## Task 4.3 — Filename test matrix

`backend/tests/ingest/test_filename_scoring.py`. Minimum 40 cases. Table-driven:

```python
import pytest
from ingest.classify import score_filename

CASES = [
    ("Cost Plan.pdf",                    "commercial"),
    ("Business Plan.pdf",                None),          # deliberately ambiguous
    ("Payment Plan.pdf",                 "commercial"),
    ("A-101 Rev C.pdf",                  "drawing"),
    ("A-102 Ground Floor Plan.pdf",      "drawing"),
    ("S203 Rev B.pdf",                   "drawing"),
    ("Structural Specification.pdf",     "specification"),
    ("Heritage Impact Statement.pdf",    "report"),
    ("Notice of Determination.pdf",      "certificate"),
    ("Invoice 0043.pdf",                 "commercial"),
    ("Variation 017.pdf",                "commercial"),
    ("Scan_20260815_001.pdf",            None),          # no signal at all
    ("IMG_4471.pdf",                     None),
    ("Master Programme Rev 4.xlsx",      "schedule"),
    ("Waverley LEP 2012.pdf",            "statutory_instrument"),
    # ... at least 25 more, including every fixture in manifest.yaml
]

@pytest.mark.parametrize("filename,expected", CASES)
def test_filename_scoring(filename: str, expected: str | None) -> None:
    assert score_filename(filename).winner == expected
```

`None` means "no confident winner" — a legitimate, expected result.

## Task 4.4 — Content markers (basis=`content`, conf 0.80–0.95)

Bounded sample: **first 4000 characters** of extracted text. Never the whole
document — that is a latency trap.

```python
_CONTENT_MARKERS: list[tuple[re.Pattern[str], DocumentClass, DocumentSubject, dict[str, str], float]] = [
    (re.compile(r"\bTAX INVOICE\b", re.I),            "commercial", "cost",
     {"commercial_type": "invoice"}, 0.95),
    (re.compile(r"\bHERITAGE IMPACT STATEMENT\b", re.I), "report", "heritage", {}, 0.95),
    (re.compile(r"\bCONDITIONS OF CONSENT\b|\bNOTICE OF DETERMINATION\b", re.I),
     "certificate", "planning", {}, 0.95),
    (re.compile(r"\bREQUEST FOR TENDER\b", re.I),     "commercial", "none",
     {"procurement_stage": "rft"}, 0.90),
    (re.compile(r"\bTENDER SUBMISSION\b|\blump sum tender price\b", re.I), "commercial", "none",
     {"procurement_stage": "submission"}, 0.90),
    (re.compile(r"\bELEMENTAL COST PLAN\b|\bCOST PLAN\b", re.I), "commercial", "cost",
     {"commercial_type": "cost_plan"}, 0.90),
    (re.compile(r"\bVARIATION\b.{0,80}\$", re.I | re.S), "commercial", "contract_admin",
     {"commercial_type": "variation"}, 0.85),
    (re.compile(r"\bGEOTECHNICAL INVESTIGATION\b", re.I), "report", "geotechnical", {}, 0.90),
    (re.compile(r"^\s*Dear\b.*\bYours (sincerely|faithfully)\b", re.I | re.S | re.M),
     "correspondence", "none", {}, 0.85),
]
```

`Scan_20260815_001.pdf` (heritage body, meaningless filename) must resolve
`report` + `heritage` with `basis="content"`. That fixture exists precisely to
prove Stage D works.

**Reuse the already-extracted text.** Do not open the file (D2).

## Task 4.5 — Persist confidence and basis

Write `confidence` and `basis` into `document_metadata` (JSONB) — not new
columns (D: "no premature columns"). Verify the values survive a round-trip
through `ingest/persist.py`.

## Task 4.6 — Measure

Create `backend/tests/ingest/test_fixture_corpus_accuracy.py` — a **reporting**
test, not a pass/fail gate at first:

```python
def test_report_fixture_corpus_accuracy(capsys) -> None:
    fixtures = load_fixtures()
    correct_class = sum(1 for f in fixtures if classify(f).document_class == f.expect["class"])
    print(f"class accuracy: {correct_class}/{len(fixtures)}")
    # ... subject accuracy, unknown rate, low-confidence rate
    assert correct_class >= 11   # ratchet: raise this number, never lower it
```

```bash
uv run pytest tests/ingest/test_fixture_corpus_accuracy.py -s
```

Paste the numbers into `TRACKER.md` § Accuracy measurements. The assertion is a
**ratchet** — each improvement raises the floor.

## Task 4.7 — Model fallback stays unwritten

Grep proves it:

```bash
grep -rn "openai\|OpenAI\|completion" backend/ingest/classify.py
```

Expected: no output. `basis="model"` exists in the vocabulary as a reserved
value only. Stage E is unlocked by §53 of the spine plan — real measured
override rates — not by this stage.

## Exit gate

- [ ] ≥40 filename cases pass
- [ ] Content markers resolve `Scan_20260815_001.pdf` → report/heritage/content
- [ ] `confidence` + `basis` round-trip through persistence
- [ ] Accuracy numbers in `TRACKER.md`
- [ ] `grep` for model calls in `classify.py` returns nothing
- [ ] No new failures vs. baseline
