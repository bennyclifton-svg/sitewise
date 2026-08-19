# Stage 13 — Project event spine

**Goal:** One closed project-verb vocabulary, written through existing
`activity_events`, idempotent, referencing canonical state rather than copying
it. Pulse (14) and email (15) read this; they do not invent a second log.

**Ownership:** single owner. This is a shared-vocabulary seam
(`90-downstream-stages.md`). No parallel agents in
`activity_events.py`, `activity_event.py`, or `event_spine.py`.
**Forbidden:** `pulse_*` tables, `backend/app/pulse/`, rewriting
`project_events` (artefact mutation log — different job), Pulse UI, email,
feature flags, changing `ingest/types.py`.
**Predecessor:** Stage 12 `[x]` (invoice verbs already seeded in
`invoice_service._record_invoice_event`).
**Parallelism:** 1.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D5, D6, D8, D10
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §8 Event spine
- `backend/app/database/activity_event.py`
- `backend/app/database/activity_events.py`
- `backend/app/cost_plan/invoice_service.py` `_record_invoice_event`
  (Stage 12.4 already writes `source="invoice.received"` etc.)
- `backend/app/inbox/service.py` `ACTIVITY_SOURCE = "document_ingest"`
- `backend/app/workflows/document_ingest.py` `_record`
- `backend/app/intake/sort_service.py` `file_single_document`
- `backend/app/projects/classification_override.py`
- `backend/app/retrieval/register.py` `DrawingRegisterRow`
- `backend/app/projects/events.py` — **read only.** Do not write Pulse
  verbs into `project_events`.
- This file

**Already true (do not rebuild):**

| Capability | Where |
|---|---|
| Workflow traces grouped by `run_id` | `record_activity_events` + `GET /projects/{id}/activity` |
| Invoice verbs on `ActivityEvent.source` | `invoice.received/needs_review/approved/rejected/posted/duplicate/conflict` |
| Artefact mutation log with `deduplication_key` | `project_events` — **not this spine** |
| ActivityFeed UI | `frontend/.../ActivityFeed.tsx` — workflow log; Pulse does not replace it |

**The two event tables:**

```text
activity_events   workflow traces + Pulse verbs (this stage owns the verbs)
project_events    artefact sequence / context version (leave alone)
```

Mixing Pulse into `project_events` would bump `event_sequence` and
`project_context_version` for every drawing revision. That is an artefact
concern. The Stage 12.4 card already chose `activity_events`.

---

## Contract (freeze at 13.1)

Closed `ProjectVerb` — write these exact strings into `ActivityEvent.source`
**and** `step`. Status is always `"complete"` for a recorded verb (the verb
*is* the fact; there is no in-flight Pulse event).

```text
document.received
document.extracted
document.classified
document.reclassified
document.filed
document.revised
invoice.received
invoice.needs_review
invoice.approved
invoice.rejected
invoice.posted
invoice.duplicate
invoice.conflict
email.received
email.linked
email.action_detected
project_signal.detected
project_signal.dismissed
```

`project_signal.dismissed` is the one addition vs the original card. Pulse
needs an append-only dismiss (D5) and a second table is forbidden. If you
omit it, Stage 14 will have nowhere legal to put dismissals.

`email.*` and `project_signal.*` are **in the Literal now** so Stages 14/15
do not extend this contract. Stage 13 does not emit them.

Workflow traces keep their existing sources (`document_ingest`,
`sort_files`, `create_pmp`, …). Those are **not** `ProjectVerb`s. Pulse
filters `source IN PROJECT_VERBS`. ActivityFeed continues to show everything.

---

## Task 13.1 — Vocabulary, helper, idempotency 🔒

Alembic revision id **≤ 32 chars** (Stage 5 note; `version_num` is
`varchar(32)`). Confirm head first:

```bash
cd backend && uv run alembic heads
```

Expected head today: `051_invoice_review_state`. If it is not, stop and
Integration-note — do not guess `down_revision`.

Revision: `052_activity_event_dedup`.

Add to `activity_events`:

```text
deduplication_key  VARCHAR(255) NULL
```

Partial unique index (Postgres):

```sql
CREATE UNIQUE INDEX uq_activity_events_project_dedup
  ON activity_events (project_id, deduplication_key)
  WHERE deduplication_key IS NOT NULL;
```

Existing workflow traces have `NULL` keys and stay insertable.

**Files:**
- Create: `backend/app/projects/event_spine.py`
- Create: `backend/tests/projects/test_event_spine.py`
- Create: `backend/alembic/versions/052_activity_event_dedup.py`
- Modify: `backend/app/database/activity_event.py` (column)
- Modify: `backend/app/database/activity_events.py` — see the two traps below

---

### ⚠ Two traps that will cost you the packet. Read before writing code.

**Trap 1 — `run_id` is `NOT NULL` and the sketch below never sets it.**
`ActivityEvent.run_id` is `UUID, nullable=False` with no default
(`app/database/activity_event.py:23`). A verb has no "run". Policy:
**mint a fresh `uuid.uuid4()` per verb call.** That is what
`_record_invoice_event` already does, and 13.7 explicitly does not group by
`run_id`, so a unique value per verb is correct and cheap. Do not try to
reuse a workflow's `run_id` — verbs outlive runs.

**Trap 2 — do NOT route verb writes through `record_activity_events`.**
Read `app/database/activity_events.py:96-118` first. That function wraps the
insert in `session.begin_nested()` and then **swallows every exception**,
logging `activity_events_record_failed`. If verbs go through it:

- a dedup collision logs an ERROR on every re-ingest — dedup becomes
  indistinguishable from failure, and the log fills with false alarms;
- a *genuine* failure (bad FK, oversized metadata) is silently invisible;
- `test_duplicate_dedup_key_is_noop` passes **for the wrong reason** and
  would keep passing if the unique index were dropped.

`record_project_verb` must do its own insert:

```python
stmt = (
    pg_insert(ActivityEvent)
    .values(...)
    .on_conflict_do_nothing(index_elements=["project_id", "deduplication_key"])
    .returning(ActivityEvent.id)
)
inserted_id = (await session.execute(stmt)).scalar_one_or_none()
```

`ON CONFLICT DO NOTHING` makes the second call a **true** no-op — no
exception, no savepoint, no swallow — and `RETURNING` gives you the
`ActivityEvent | None` the signature promises. Real errors still raise.

`record_activity_events` still gains the optional `deduplication_key`
parameter (workflow traces may want it later), but verbs do not use it.

**Index-elements note:** `on_conflict_do_nothing(index_elements=...)` must
match the *partial* index. SQLAlchemy needs the predicate too:
`index_where=ActivityEvent.deduplication_key.isnot(None)`. Without it
Postgres cannot infer the partial index and raises. Test this — it fails at
runtime, not at import.

```python
# event_spine.py — sketch; tests own the behaviour
from typing import Literal, Mapping, Any
import uuid
from sqlalchemy import select
from app.database.activity_event import ActivityEvent
from app.database.activity_events import record_activity_events
from app.schemas.projects import WorkflowTraceEvent

ProjectVerb = Literal[
    "document.received",
    "document.extracted",
    "document.classified",
    "document.reclassified",
    "document.filed",
    "document.revised",
    "invoice.received",
    "invoice.needs_review",
    "invoice.approved",
    "invoice.rejected",
    "invoice.posted",
    "invoice.duplicate",
    "invoice.conflict",
    "email.received",
    "email.linked",
    "email.action_detected",
    "project_signal.detected",
    "project_signal.dismissed",
]

PROJECT_VERBS: frozenset[str] = frozenset(ProjectVerb.__args__)  # type: ignore[attr-defined]

_ALLOWED_METADATA = frozenset(
    {
        "filename",
        "document_class",
        "document_subject",
        "drawing_number",
        "revision",
        "previous_revision",
        "invoice_number",
        "signal_type",
        "subject_key",
        "confidence",
        "issue_codes",
        "content_hash",
    }
)
_MAX_MESSAGE = 500


def verb_dedup_key(
    verb: str, *, reference_type: str, reference_id: uuid.UUID, extra: str = ""
) -> str:
    base = f"{verb}:{reference_type}:{reference_id}"
    return f"{base}:{extra}" if extra else base


async def record_project_verb(
    session,
    *,
    project_id: uuid.UUID,
    verb: ProjectVerb,
    reference_type: str,
    reference_id: uuid.UUID,
    message: str,
    deduplication_key: str,
    metadata: Mapping[str, Any] | None = None,
) -> ActivityEvent | None:
    """Append one Pulse verb. No-op if the key already exists. Never copies
    canonical row state — metadata is an allow-list of display refs."""
    ...
```

Rules the tests must lock:

1. Unknown verb raises `ValueError` (closed set).
2. Metadata keys outside `_ALLOWED_METADATA` are dropped, not stored.
   Passing `normalized_content` / `machine_extraction` / `body` must not
   persist those keys (D5 — events reference, they do not copy).
3. Message truncated to 500 chars.
4. Second call with the same `deduplication_key` inserts **zero** rows,
   returns `None`, and logs **nothing at ERROR**. Assert the log too — a
   silent swallow is the failure mode this packet exists to avoid.
5. `source == step == verb`, `status == "complete"`.
6. Exhaustiveness: every `ProjectVerb` is in `PROJECT_VERBS` and the
   original card list is a subset (signals dismissed is the extra).
7. A genuine insert failure (e.g. unknown `project_id`) **raises**. This is
   the guard against reintroducing the swallow.

**Failing tests:**

```text
test_unknown_verb_raises
test_duplicate_dedup_key_is_noop
test_duplicate_dedup_key_does_not_log_an_error
test_insert_failure_raises_rather_than_being_swallowed
test_metadata_allowlist_drops_canonical_payloads
test_project_verbs_is_closed_and_covers_the_card
```

**Commit:** `feat: freeze project-verb vocabulary on activity_events`

Do not emit document verbs in this packet.

---

## Task 13.2 — `document.received` / `extracted` / `classified`

Emit from the hosted ingest path after the workspace file exists and ingest
has a result. **Do not convert workflow traces into verbs.** Keep
`source="document_ingest"` traces for ActivityFeed.

Hook: `app/workflows/document_ingest.py` `ingest_project_document` after
`source_document_id` is known. Inbox upload (`inbox/service.py`) is
*received* if the file is stored even when ingest later fails.

| Verb | When | Dedup extra |
|---|---|---|
| `document.received` | workspace file stored (`inbox/service.py` after upsert) | `content_hash` |
| `document.extracted` | ingest completed and `source_document_id` set | `content_hash` |
| `document.classified` | same moment as extracted (hosted classifies before extract today — **do not reorder the pipeline**; that is an open Integration note) | `content_hash` + class + subject |

`skip_if_unchanged` / ingest status `skipped`: emit **nothing** new.
Received already fired on first upload; extracted/classified already keyed
on hash.

Reference: `reference_type="source_document"` when id exists, else
`"workspace_file"`. Metadata: `filename`, `document_class`,
`document_subject`, `content_hash` — not the file bytes, not
`normalized_content`.

**Files:**
- Modify: `backend/app/inbox/service.py`
- Modify: `backend/app/workflows/document_ingest.py`
- Test: `backend/tests/projects/test_event_spine.py` (ingest cases)
- Test: existing `backend/tests/inbox/test_document_ingest.py` —
  patch `record_project_verb` if traces become noisy; do not weaken them.

**Failing tests:**

```text
test_inbox_upload_emits_document_received
test_successful_ingest_emits_extracted_and_classified
test_unchanged_reingest_does_not_emit_again
```

**Commit:** `feat: emit document received/extracted/classified verbs`

---

## Task 13.3 — `document.reclassified`

Emit from `set_document_classification` (the one service REST and MCP
already share). Dedup extra: `{old_class}:{new_class}:{content_hash}` so a
second identical override is a no-op, but report→certificate then
certificate→report are two events.

Do not copy the full `document_metadata` dict into the event.

**Files:**
- Modify: `backend/app/projects/classification_override.py`
- Test: `backend/tests/projects/test_classification_override.py`

**Failing test:** `test_user_override_emits_document_reclassified`

**Commit:** `feat: emit document.reclassified from classification override`

---

## Task 13.4 — `document.filed`

Emit when `file_single_document` / Sort Files actually moves a file
(`outcome == "moved"`). `already-filed` is a no-op (dedup key includes
destination path, so a real second move to a new path still records).

Dedup: `document.filed:{source_document_id}:{destination_path}`.

**Files:**
- Modify: `backend/app/intake/sort_service.py` (the move success path
  around the existing `outcome="moved"` assignment)
- Test: `backend/tests/workflows/test_sort_files.py` or
  `backend/tests/workflows/test_document_ingest_auto_sort.py`

**Failing test:** `test_successful_file_move_emits_document_filed`

Do not emit from `repair_service` in this packet (outside ownership;
Integration-note if it also moves files).

**Commit:** `feat: emit document.filed when Sort Files moves a document`

---

## Task 13.5 — `document.revised`

When a newly ingested `document_class == "drawing"` has
`document_metadata.drawing_number` matching another drawing in the same
project with a **different** `revision`, emit `document.revised`.

Use `list_drawings` / the same metadata keys Stage 9.3 already trusts
(`drawing_number`, `revision`). First drawing for a number is not a
revision. Missing number → no event (do not guess from filename here;
filename revision lives in `app/inbox/sheet_titles.py` and is out of
scope unless metadata already copied it).

**Two correctness details the test must pin:**

- **Revisions are not ordered by ingest time.** Someone can upload Rev C
  before Rev B (backfilling an old sheet). "Newer revision arrived" is
  `new_revision > max(existing_revisions)` by revision comparison, not
  "a different revision exists". Ingesting Rev B when Rev C is already on
  file must emit **nothing** — it is a late arrival, not a revision.
  Compare revisions as strings case-insensitively (`A < B < C`); if a
  project uses numeric revisions (`1`, `2`, `10`), a naive string compare
  puts `10` before `2` — normalise numeric-looking revisions before
  comparing, and test `Rev 10` against `Rev 9`.
- **This query runs on every drawing ingest.** It filters on
  `document_metadata->>'drawing_number'`, which has no index. Confirm with
  `EXPLAIN` on a project-scoped query; if it seq-scans `source_documents`,
  add a partial expression index in the same 052 revision rather than
  discovering it under load.

**Failing tests (add to the one below):**

```text
test_earlier_revision_arriving_late_emits_nothing
test_numeric_revision_10_supersedes_9
```

Dedup: `document.revised:{drawing_number}:{new_revision}`.
Metadata: `drawing_number`, `revision`, `previous_revision`, `filename`.
`reference_id` = the new source_document id.

Acceptance scenario I in the product spec starts here; Pulse copy is Stage
14. This packet only records the verb.

**Failing test:** `test_later_drawing_revision_emits_document_revised`

```python
# S203 Rev B already on file; ingest S203 Rev C
# → one document.revised, previous_revision="B", revision="C"
# ingest Rev C again (same hash) → no second event
```

**Commit:** `feat: emit document.revised when a drawing number advances`

---

## Task 13.6 — Invoice verbs reuse the helper

Stage 12.4 already emits the invoice verbs via `_record_invoice_event`
with a fresh `uuid4` `run_id` and **no** dedup key. Duplicate approve
retries could double-write.

Replace the body of `_record_invoice_event` so it calls
`record_project_verb`. Dedup extra: `review_state` or the verb itself
(approve once). This is the **one** allowed edit to
`invoice_service.py` — same pattern as Stage 9.5's one-line signature
change. Do not retouch review transitions.

```python
await record_project_verb(
    session,
    project_id=project_id,
    verb=source,  # already "invoice.approved" etc.
    reference_type="cost_invoice",
    reference_id=invoice_id,
    message=message,
    deduplication_key=verb_dedup_key(
        source,
        reference_type="cost_invoice",
        reference_id=invoice_id,
    ),
    metadata={"invoice_number": invoice.invoice_number} if known else None,
)
```

If `source` is not a `ProjectVerb` (should not happen), raise — that is
how we catch drift.

**Failing test:** `test_approve_twice_does_not_duplicate_invoice_approved_event`
(drive `decide_invoice` into an illegal second approve, or call the
helper twice with the same key).

**Commit:** `fix: invoice activity events use the shared verb helper`

---

## Task 13.7 — List helper for Pulse (read path only)

```python
async def list_project_verbs(
    session,
    *,
    project_id: uuid.UUID,
    since: datetime | None = None,
    verbs: Sequence[str] | None = None,
    limit: int = 200,
) -> list[ActivityEvent]:
```

Filters `source IN PROJECT_VERBS` (or the requested subset). Orders by
`created_at desc`. Does **not** group by `run_id` — Pulse is not the
activity run feed.

No HTTP route in this stage. Stage 14 owns `GET /projects/{id}/pulse`.

**Failing test:** `test_list_project_verbs_excludes_workflow_trace_sources`

**Commit:** `feat: list project verbs without grouping workflow runs`

---

## Exit gate

- [ ] `uv run alembic upgrade head` then `downgrade -1` then `upgrade head`
      lands on `052_activity_event_dedup`
- [ ] `uv run pytest tests/projects/test_event_spine.py tests/projects/test_classification_override.py tests/cost_plan/test_invoice_decision_api.py tests/inbox/test_document_ingest.py tests/workflows/test_sort_files.py tests/database/test_activity_events.py -q`
- [ ] `uv run ruff check .`
- [ ] No `pulse_` table in `alembic/versions/052_*.py`
- [ ] `grep -n "create_table(\"pulse" backend/alembic` empty
- [ ] `project_events` / `publish_project_event` unchanged
- [ ] Backend failures ⊆ Stage 0 baseline names
- [ ] Email verbs exist in the Literal and have **zero** emitters
- [ ] `record_project_verb` uses `ON CONFLICT DO NOTHING`, **not**
      `record_activity_events`' exception swallow — a duplicate key logs
      nothing at ERROR, and a real insert failure raises
- [ ] Every verb row has a non-null `run_id`
- [ ] Stage 14 is now eligible to expand / implement

**After this stage:** implement [`stage-14-pulse-mvp.md`](./stage-14-pulse-mvp.md).
Do not start email (15) — that waits on Gate 3.
