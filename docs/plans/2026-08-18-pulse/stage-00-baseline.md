# Stage 0 — Baseline & Safety Harness

**Goal:** Know exactly what "working" means today, so every later stage can prove
it did not break anything. **No behavioural change in this stage.**

**Ownership:** whole repo, read-only, plus new files under
`backend/tests/fixtures/classification/` and `docs/acceptance/x1/`.

**Reading list (read nothing else):**
- [`00-doctrine.md`](./00-doctrine.md)
- [`01-ground-truth.md`](./01-ground-truth.md)
- `backend/AGENTS.md` §Tests

---

## Task 0.1 — Branch

```bash
cd "d:/AI Projects/clerk"
git rev-parse HEAD          # paste into TRACKER baseline table
git checkout -b x1/stage-0-baseline
```

Record in `TRACKER.md`. Do **not** work on `main`.

## Task 0.2 — Backend baseline

```bash
cd backend
uv run pytest -q 2>&1 | tail -40
```

Paste the last 40 lines into `TRACKER.md` verbatim.

Then capture failure names specifically:

```bash
uv run pytest -q 2>&1 | grep -E "^(FAILED|ERROR)" | sort > ../docs/acceptance/x1/baseline-backend-failures.txt
wc -l ../docs/acceptance/x1/baseline-backend-failures.txt
```

**This file is the contract for every later stage.** "Tests pass" from here on
means: *the set of failures is a subset of this file.*

> Context from repo memory: a pre-existing failure baseline is known to exist.
> Do not attempt to fix these. Record them and move on.

## Task 0.3 — Frontend baseline

```bash
cd frontend
pnpm typecheck 2>&1 | tail -20
pnpm test 2>&1 | tail -30
pnpm build 2>&1 | tail -10
```

Paste all three tails into `TRACKER.md`. Use `pnpm` only — never `npm`.

## Task 0.4 — Database census

Run against the dev database. Save as
`backend/scripts/x1_census.sql` and commit it.

```sql
-- 1. total
SELECT count(*) AS total FROM source_documents;

-- 2. by class
SELECT document_class, count(*) FROM source_documents
GROUP BY 1 ORDER BY 2 DESC;

-- 3. by ingest_mode
SELECT ingest_mode, count(*) FROM source_documents GROUP BY 1;

-- 4. THE KEY NUMBER: register_only rows that are hiding useful text
SELECT count(*) AS suppressed_with_text
FROM source_documents sd
WHERE sd.ingest_mode = 'register_only'
  AND length(btrim(sd.normalized_content)) >= 200;

-- 5. docs with text but zero chunks (the same wound, seen from the other side)
SELECT count(*) AS text_no_chunks
FROM source_documents sd
WHERE length(btrim(sd.normalized_content)) >= 200
  AND NOT EXISTS (SELECT 1 FROM document_chunks c WHERE c.document_id = sd.id);

-- 6. classes outside the declared Literal (known: inbox_pending, corpus_catalog)
SELECT document_class, count(*) FROM source_documents
WHERE document_class NOT IN (
  'unknown','contract','specification','tender_submission','trr','evaluation',
  'rft','addendum','eoi','tep','drawing','report','certificate',
  'correspondence','schedule','reference_guide','doctrine','planning_instrument'
) GROUP BY 1;

-- 7. legacy procurement classes (Stage 8 workload)
SELECT count(*) FROM source_documents
WHERE document_class IN ('tep','eoi','rft','addendum','tender_submission','evaluation','trr');

-- 8. null content_hash (blocks Stage 5 override key — see OD-3)
SELECT count(*) FROM source_documents WHERE content_hash IS NULL;
```

Fill every row of the `TRACKER.md` baseline table. Query 4 is the headline number
for Stage 2 — it is how many documents are currently invisible to retrieval.

## Task 0.5 — Fixture corpus

**The original plan named 14 fixtures but never said what is in them. That is a
guaranteed divergence point between agents. Fix it here.**

Create `backend/tests/fixtures/classification/manifest.yaml`:

```yaml
# Each fixture is a filename + a text body. Tests generate the PDF/MD at runtime;
# do not commit binaries. `expect` is the CANONICAL (post-Stage-3) answer.
fixtures:
  - filename: "Cost Plan.pdf"
    body: "ELEMENTAL COST PLAN\nStage: Concept\nTotal construction cost $4,120,000\nPreliminaries 12%"
    expect: { class: commercial, subject: cost, commercial_type: cost_plan }
    note: "regression for the \\bplan\\b bug"

  - filename: "Business Plan.pdf"
    body: "BUSINESS PLAN\nExecutive summary\nMarket analysis and funding strategy"
    expect: { class: report, subject: none }

  - filename: "Payment Plan.pdf"
    body: "PAYMENT PLAN\nProgress payment schedule against milestones"
    expect: { class: commercial, subject: cost }

  - filename: "Structural Specification Plan.pdf"
    body: "STRUCTURAL SPECIFICATION\nSection 0531 Structural Steelwork\nClause 1.1 Scope"
    expect: { class: specification, subject: structural }

  - filename: "A-101 Rev C.pdf"
    body: "GROUND FLOOR PLAN\nDRAWING A-101 REV C\nSCALE 1:100\nGENERAL NOTES: refer structural."
    expect: { class: drawing, subject: none }
    note: "notes MUST remain searchable after Stage 1"

  - filename: "Heritage Impact Statement.pdf"
    body: "HERITAGE IMPACT STATEMENT\nPrepared for the applicant\nSignificance assessment"
    expect: { class: report, subject: heritage }

  - filename: "Scan_20260815_001.pdf"
    body: "HERITAGE IMPACT STATEMENT\nThe subject site is listed as a local heritage item."
    expect: { class: report, subject: heritage, basis: content }
    note: "filename carries zero signal — forces Stage D content markers"

  - filename: "IMG_4471.pdf"
    body: ""
    expect: { class: unknown, subject: none }
    note: "no useful text -> register-only path, but NOT because of class"

  - filename: "Notice of Determination.pdf"
    body: "NOTICE OF DETERMINATION\nDevelopment Application DA-2026-114\nCONDITIONS OF CONSENT"
    expect: { class: certificate, subject: planning }

  - filename: "Council RFI response.pdf"
    body: "Dear Sir/Madam\nWe respond to your request for further information.\nYours sincerely"
    expect: { class: correspondence, subject: planning }

  - filename: "Invoice 0043.pdf"
    body: "TAX INVOICE\nABN 12 345 678 901\nInvoice No 0043\nSubtotal $8,500\nGST $850\nTotal $9,350"
    expect: { class: commercial, subject: cost, commercial_type: invoice }

  - filename: "Variation 017.pdf"
    body: "VARIATION 017\nAdditional structural works\nAmount claimed $12,400"
    expect: { class: commercial, subject: contract_admin, commercial_type: variation }

  - filename: "Tender - Builder B.pdf"
    body: "REQUEST FOR TENDER\nReturn by 5pm 12 September\nSchedule of prices attached"
    expect: { class: commercial, subject: none, procurement_stage: rft }

  - filename: "Builder B final.pdf"
    body: "TENDER SUBMISSION\nBuilder B Pty Ltd\nLump sum tender price $6,840,000"
    expect: { class: commercial, procurement_stage: submission }
    note: "filename says nothing about tender — content must carry it"
```

Then `backend/tests/fixtures/classification/__init__.py`:

```python
"""Shared classification fixture corpus. See manifest.yaml."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

MANIFEST = Path(__file__).parent / "manifest.yaml"


@dataclass(frozen=True, slots=True)
class Fixture:
    filename: str
    body: str
    expect: dict[str, str]
    note: str | None = None


def load_fixtures() -> list[Fixture]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return [
        Fixture(
            filename=item["filename"],
            body=item.get("body", ""),
            expect=item.get("expect", {}),
            note=item.get("note"),
        )
        for item in data["fixtures"]
    ]
```

Verify it loads:

```bash
cd backend
uv run python -c "from tests.fixtures.classification import load_fixtures; fs=load_fixtures(); print(len(fs)); print(fs[0])"
```

Expected: `14` then the `Cost Plan.pdf` fixture.

> These `expect` values are the **canonical** answers and will fail today. That
> is correct — Stage 4 makes them pass. Do not write assertions against them yet.

## Task 0.6 — LOC gate baseline

D8 requires classification LOC not to grow. Record the starting number:

```bash
cd "d:/AI Projects/clerk"
find backend/ingest backend/app/intake -name '*.py' \
  -not -path '*/__pycache__/*' -not -name 'test_*' \
  -exec wc -l {} + | tail -1
```

Paste the total into `TRACKER.md`. Stage 6.6 compares against it.

## Exit gate

- [ ] `docs/acceptance/x1/baseline-backend-failures.txt` exists and is committed
- [ ] Every row of the `TRACKER.md` baseline table is filled
- [ ] `load_fixtures()` returns 14
- [ ] `git diff --stat` shows **zero** changes under `backend/app/` and `backend/ingest/`

Last bullet is the point: Stage 0 adds tests and docs only.

## Commit

```bash
git add backend/tests/fixtures/classification backend/scripts/x1_census.sql docs/acceptance/x1 docs/plans/2026-08-18-pulse/TRACKER.md
git commit -m "test: add X1 classification fixture corpus and record baseline"
```
