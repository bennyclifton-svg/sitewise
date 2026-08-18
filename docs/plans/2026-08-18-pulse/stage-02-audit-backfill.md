# Stage 2 — Historical Audit & Backfill

**Goal:** Every document already suppressed by the Stage 1 bug becomes
retrievable, without duplicating chunks and without a second run doing damage.

**Ownership:** `backend/scripts/x1_*.py`, `docs/acceptance/x1/`.
**Forbidden:** any change under `backend/app/` or `backend/ingest/`. This stage
is a script, not a refactor.

**Predecessor:** Stage 1 `[x]`. Backfilling before the fix would re-suppress.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D3
- `backend/scripts/x1_census.sql` (from Stage 0)
- `backend/ingest/persist.py`
- `backend/app/database/source_document.py`

---

## Task 2.1 — Read-only audit script

Create `backend/scripts/x1_audit.py`. **It must not write.** Give it no
session `commit()` at all — that is the safety mechanism.

```python
"""X1 read-only audit. Writes nothing. Run before any backfill."""
from __future__ import annotations

import asyncio
import json
from sqlalchemy import func, select, text

from app.database.session import get_sessionmaker   # verify this import path
from app.database.source_document import SourceDocument


async def audit() -> dict[str, object]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        report: dict[str, object] = {}

        report["total"] = (
            await session.execute(select(func.count()).select_from(SourceDocument))
        ).scalar_one()

        report["by_class"] = dict(
            (await session.execute(
                select(SourceDocument.document_class, func.count())
                .group_by(SourceDocument.document_class)
            )).all()
        )

        report["by_ingest_mode"] = dict(
            (await session.execute(
                select(SourceDocument.ingest_mode, func.count())
                .group_by(SourceDocument.ingest_mode)
            )).all()
        )

        # The headline number: suppressed but carries useful text.
        report["suppressed_with_text"] = (
            await session.execute(text("""
                SELECT count(*) FROM source_documents
                WHERE ingest_mode = 'register_only'
                  AND length(btrim(normalized_content)) >= 200
            """))
        ).scalar_one()

        # Same wound, other side: has text, has no chunks.
        report["text_without_chunks"] = (
            await session.execute(text("""
                SELECT count(*) FROM source_documents sd
                WHERE length(btrim(sd.normalized_content)) >= 200
                  AND NOT EXISTS (
                    SELECT 1 FROM document_chunks c WHERE c.document_id = sd.id
                  )
            """))
        ).scalar_one()

        report["legacy_procurement_classes"] = (
            await session.execute(text("""
                SELECT count(*) FROM source_documents
                WHERE document_class IN
                  ('tep','eoi','rft','addendum','tender_submission','evaluation','trr')
            """))
        ).scalar_one()

        report["planning_instrument"] = (
            await session.execute(text(
                "SELECT count(*) FROM source_documents WHERE document_class='planning_instrument'"
            ))
        ).scalar_one()

        report["undeclared_classes"] = dict(
            (await session.execute(text("""
                SELECT document_class, count(*) FROM source_documents
                WHERE document_class IN ('inbox_pending','corpus_catalog')
                GROUP BY 1
            """))).all()
        )

        report["null_content_hash"] = (
            await session.execute(text(
                "SELECT count(*) FROM source_documents WHERE content_hash IS NULL"
            ))
        ).scalar_one()

        return report


if __name__ == "__main__":
    print(json.dumps(asyncio.run(audit()), indent=2, default=str))
```

> Verify `get_sessionmaker` — grep `backend/app/database/` for the real session
> factory name before running. Do not guess.

```bash
cd backend
uv run python scripts/x1_audit.py | tee ../docs/acceptance/x1/audit-pre-backfill.json
```

## Task 2.2 — Commit the report

```bash
git add docs/acceptance/x1/audit-pre-backfill.json backend/scripts/x1_audit.py
git commit -m "chore: add X1 read-only audit and record pre-backfill state"
```

Copy `suppressed_with_text` and `text_without_chunks` into `TRACKER.md`. These
two numbers must both be **0** when Stage 2 closes.

## Task 2.3 — Backfill, dry-run by default

Create `backend/scripts/x1_backfill.py`.

Non-negotiable design rules:

1. `--dry-run` is the **default**. Writing requires `--apply`.
2. Selection is by evidence, never by class: `has_useful_text(normalized_content)`
   and zero existing chunks.
3. Delete-then-insert chunks per document inside one transaction. Never append.
4. Print `would re-index N documents` in dry-run; print `re-indexed N` on apply.
5. Process in batches of 100 with a progress line, so a killed run is resumable.
6. Re-use `ingest/persist.py` chunk-writing helpers. Do not hand-roll chunking —
   that would be a D8 violation.

```python
"""X1 backfill: re-index documents whose text was suppressed by the pre-Stage-1 bug.

Idempotent. Dry-run unless --apply.
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select, text

from ingest.router import has_useful_text
# from ingest.persist import <the existing chunk-write helper>   # grep for it


CANDIDATES_SQL = text("""
    SELECT sd.id
    FROM source_documents sd
    WHERE length(btrim(sd.normalized_content)) >= 200
      AND NOT EXISTS (
        SELECT 1 FROM document_chunks c WHERE c.document_id = sd.id
      )
    ORDER BY sd.created_at
""")


async def run(*, apply: bool, batch_size: int = 100) -> None:
    ...
    # 1. select candidate ids
    # 2. for each batch:
    #      load doc, assert has_useful_text(doc.normalized_content)
    #      DELETE FROM document_chunks WHERE document_id = :id
    #      re-chunk + re-embed via the existing persist helper
    #      set ingest_mode = 'full_text'
    # 3. if not apply: rollback the whole thing


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="actually write (default: dry-run)")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply, batch_size=args.batch_size))
```

```bash
cd backend
uv run python scripts/x1_backfill.py            # dry-run
```

Expected: `would re-index N documents` where `N` matches
`text_without_chunks` from Task 2.1.

## Task 2.4 — Idempotency test

Create `backend/tests/scripts/test_x1_backfill.py`. Assert, against a seeded
test session:

```python
def test_backfill_twice_produces_identical_chunk_counts():
    # seed one doc with 500 chars of text and no chunks
    # run backfill --apply -> chunk count == N (N > 0)
    # run backfill --apply again -> chunk count still == N, no duplicates
```

```bash
uv run pytest tests/scripts/test_x1_backfill.py -v
```

**Repo memory warning:** a plain pytest run once dropped live tender tables 32
times. Confirm this test binds to the test database, not a live one, before
running it. Check `backend/tests/conftest.py` for the DB guard and do not
bypass it.

## Task 2.5 — Apply and prove

```bash
cd backend
uv run python scripts/x1_backfill.py --apply
uv run python scripts/x1_audit.py | tee ../docs/acceptance/x1/audit-post-backfill.json
```

Then diff the two reports:

```bash
cd ..
diff <(python -c "import json,sys;d=json.load(open('docs/acceptance/x1/audit-pre-backfill.json'));print(d['text_without_chunks'])") \
     <(python -c "import json,sys;d=json.load(open('docs/acceptance/x1/audit-post-backfill.json'));print(d['text_without_chunks'])")
```

Post-value must be `0`.

## Rollback

The backfill only **adds** chunks for documents that had none, and flips
`ingest_mode` to `full_text`. To reverse:

```sql
-- capture the affected ids BEFORE applying:
CREATE TABLE x1_backfill_log AS
SELECT id, ingest_mode AS prior_ingest_mode, now() AS captured_at
FROM source_documents
WHERE length(btrim(normalized_content)) >= 200
  AND NOT EXISTS (SELECT 1 FROM document_chunks c WHERE c.document_id = source_documents.id);

-- to roll back:
DELETE FROM document_chunks WHERE document_id IN (SELECT id FROM x1_backfill_log);
UPDATE source_documents s SET ingest_mode = l.prior_ingest_mode
FROM x1_backfill_log l WHERE s.id = l.id;
```

**Create `x1_backfill_log` before Task 2.5, not after.** Record in `TRACKER.md`
that you did.

## Exit gate

- [ ] `audit-pre-backfill.json` and `audit-post-backfill.json` both committed
- [ ] `text_without_chunks` post-value is `0`
- [ ] `suppressed_with_text` post-value is `0`
- [ ] Idempotency test passes
- [ ] `x1_backfill_log` table exists (rollback is possible)
- [ ] Backend suite failures still ⊆ baseline
- [ ] A previously-suppressed `Cost Plan` document returns from a real retrieval
      query (spot-check one document by hand and paste the result)
