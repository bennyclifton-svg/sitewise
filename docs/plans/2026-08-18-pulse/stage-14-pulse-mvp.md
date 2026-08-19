# Stage 14 — Pulse MVP

**Goal:** Pulse answers **"What changed?"** and **"What needs me?"** from
the Stage 13 verb log plus current canonical rows. If the UI ever renders
`48 emails · 26 documents · 12 events` without synthesis, this stage has
failed.

**Ownership:** three lanes after 14.1 lands — signals, backend API,
frontend. 14.1 is single-owner (signal vocabulary).
**Forbidden:** `pulse_*` tables, business logic in the React tree (no
`decide_invoice` arithmetic, no classification rules), email, TCM,
feature flags (OD-4: Pulse has no external provider), mutating project
state from a detector, replacing `ActivityFeed.tsx`.
**Predecessor:** Stage 13 `[x]`.
**Parallelism:** 3 after 14.1 (signals / API / fixture UI).

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D5, D6, D7, D8, D9
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §8 Signals / Pulse
- [`stage-13-project-event-spine.md`](./stage-13-project-event-spine.md)
  contract (`ProjectVerb`, allow-list, `list_project_verbs`)
- `backend/app/projects/event_spine.py` (as built)
- `backend/app/cost_plan/invoice_service.py` `decide_invoice`
- `backend/app/cost_plan/invoice_issues.py` (`UNAPPROVED_VARIATION`,
  `COST_PLAN_OVERRUN`, `AMOUNT_EXCEEDS_COMMITMENT`)
- `backend/app/projects/classification_override.py`
- `backend/app/retrieval/register.py`
- `ingest/router.py` `REVIEW_CONFIDENCE_MIN` (0.65)
- `frontend/src/pages/ProjectCockpitPage.tsx` (Pulse strip lives **above**
  the repository, not inside `ActivityFeed`)
- `frontend/src/components/project/InvoiceReviewPane.tsx` (card action
  target)
- This file

**Kill-switch:** OD-4 default stands. **No flag.** Pulse is ordinary
authenticated product code.

---

## Product shape (non-negotiable)

```text
PROJECT PULSE                         3 items need attention

01 · STRUCTURE   Revised structural drawing received. S203 Rev C supersedes Rev B.
02 · COMMERCIAL  Builder Invoice 009 includes $8,400 against an unapproved variation.
03 · PLANNING    Notice of Determination received.

OTHER ACTIVITY   6 documents filed · 2 invoices ready for review
```

Never:

```text
48 emails · 26 documents · 12 events
```

**Attention items** are synthesised signals. **Other activity** is a
rollup of verbs that did not raise a signal. Counts may appear in the
rollup line; they must not be the headline.

---

## Task 14.1 — Signal vocabulary + synthesizer 🔒

Closed `PulseSignalType` — MVP subset of the product list. Stage 21 may
add types via an Integration note, not by silently extending this file
during 14.x.

```text
drawing_revision
approval_received
invoice_review_required
potential_cost_change
document_needs_classification
```

Deferred to Stage 21 (do not invent detectors now):
`programme_risk`, `decision_required`, `consultant_action_due`,
`unanswered_correspondence`, `tender_received`.

**Files:**
- Create: `backend/app/projects/pulse.py`
- Create: `backend/tests/projects/test_pulse.py`

Signals are **derived at read time** from (a) current canonical rows,
(b) Stage 13 verbs, (c) later `project_signal.dismissed` verbs. They are
not a table.

```python
from typing import Literal
from pydantic import BaseModel
import uuid
from datetime import datetime

PulseSignalType = Literal[
    "drawing_revision",
    "approval_received",
    "invoice_review_required",
    "potential_cost_change",
    "document_needs_classification",
]

PulseAttentionKind = Literal["attention", "other"]


class PulseEvidenceRef(BaseModel):
    reference_type: str  # source_document | cost_invoice | activity_event
    reference_id: uuid.UUID
    label: str


class PulseItem(BaseModel):
    id: str  # stable subject_key, not a table pk
    kind: PulseAttentionKind
    signal_type: PulseSignalType | None  # None for rollup rows
    title: str
    body: str
    domain: str  # STRUCTURE | COMMERCIAL | PLANNING | ...
    evidence: list[PulseEvidenceRef]
    actions: list[str]  # closed: review_invoice | classify_document | view_evidence | dismiss
    confidence: float | None = None
    created_at: datetime


class PulseFeed(BaseModel):
    attention: list[PulseItem]
    other: list[PulseItem]  # rollups, not one row per document
    attention_count: int
    generated_at: datetime
```

`subject_key` format: `{signal_type}:{reference_type}:{reference_id}`.
Dismiss records `project_signal.dismissed` with metadata
`signal_type` + `subject_key`. Synthesizer excludes dismissed keys.

---

### ⚠ `attention` must be bounded. This is the stage's own failure mode.

The product shape at the top of this file promises **"3 items need
attention"**. Nothing in the contract as drafted stops it rendering 200.

`document_needs_classification` fires on every document with
`document_class == "unknown"` **or** `confidence < REVIEW_CONFIDENCE_MIN`.
That is a standing population, not an event — before Stage 8B.8 ran it was
43% of the corpus, and every future low-confidence upload rejoins it. A
detector over a standing population produces one card per row forever.
`invoice_review_required` has the same shape: invoices sit in
`ready_for_review` until someone acts.

So the contract needs two more rules, and they belong here in 14.1 where
the shape is frozen — not retrofitted in 14.2 once the detectors exist:

```python
MAX_ATTENTION_ITEMS = 7          # tune later; a number, not "all"
MIN_GROUPED = 3                  # below this, show them individually
```

1. **Group before capping.** When one `signal_type` produces
   `>= MIN_GROUPED` items, collapse them into a single `PulseItem` whose
   `body` names the count (`"12 documents need classification"`), whose
   `evidence` carries the first few refs, and whose `id` is the grouped
   subject key `{signal_type}:group`. Event-shaped signals
   (`drawing_revision`, `approval_received`) group per subject too — five
   revised drawings is one card, not five.
2. **Then cap.** After grouping, `attention` is truncated to
   `MAX_ATTENTION_ITEMS`, ordered most-recent-evidence first. Anything
   truncated is counted in the `other` rollup, never dropped silently.
   `attention_count` is the count **before** truncation, so the headline
   stays honest.

Dismissing a grouped card dismisses the group key, not the members — a new
member re-raises the group. Say so in the docstring; it is the behaviour a
user will test first.

---

**Failing tests:**

```text
test_pulse_signal_types_are_closed
test_dismissed_subject_key_is_excluded
test_synthesizer_does_not_write_canonical_rows
test_forty_unclassified_documents_produce_one_grouped_card
test_attention_never_exceeds_max_attention_items
test_truncated_items_appear_in_other_rollup
test_attention_count_reflects_pre_truncation_total
```

For `test_synthesizer_does_not_write_canonical_rows`, inspecting
`session.dirty` is too weak — it is empty if a detector issued a raw
`session.execute(update(...))`. Pass a session wrapper whose `execute`
raises on any non-`SELECT` statement, and assert `build_pulse_feed`
completes. That catches raw DML, which is the way a detector actually goes
wrong.

The third test: run `build_pulse_feed` against a session; assert no
`UPDATE`/`INSERT` on `cost_invoices` / `source_documents` (patch session
or inspect `session.dirty` / use a recording session). Detectors are
pure readers plus optional dismiss events.

**Commit:** `feat: Pulse synthesizer contract with dismissible subject keys`

---

## Task 14.2 — Five MVP detectors

Python only (D6). No LLM. Each detector returns `list[PulseItem]` of
`kind="attention"`.

| Type | Evidence | Title sketch |
|---|---|---|
| `drawing_revision` | `document.revised` verbs | `{drawing_number} Rev {revision} supersedes Rev {previous_revision}` |
| `invoice_review_required` | invoices with `review_state in {ready_for_review, needs_attention}` | `{supplier} invoice {number} needs review` |
| `potential_cost_change` | same invoices whose `issues` contain `UNAPPROVED_VARIATION` / `COST_PLAN_OVERRUN` / `AMOUNT_EXCEEDS_COMMITMENT` | `{supplier} Invoice {n} includes {amount} against an unapproved variation` (acceptance G) |
| `document_needs_classification` | `document_class=="unknown"` **or** `confidence < 0.65` (`REVIEW_CONFIDENCE_MIN`) | `{filename} needs classification` |
| `approval_received` | newly classified `certificate` (prefer `document_subject=="planning"`) from `document.classified` / `document.reclassified` | `Notice of Determination received` only when title/filename supports it; otherwise `Planning certificate received` |

`potential_cost_change` and `invoice_review_required` may both fire for
one invoice. Synthesizer **merges onto one attention card** (cost change
wins the title; review remains an action). Two cards for one invoice is
a defect.

Detectors **never** call `decide_invoice`, `set_document_classification`,
`file_single_document`, or ingest.

**Query budget.** `build_pulse_feed` runs on every `GET /pulse`, and the
cockpit will poll it. Five detectors each free-running over their own rows
is an N+1 waiting to happen — especially `drawing_revision`, which needs the
superseded drawing for each revised one.

Load once, then detect in memory:

```text
1 × list_project_verbs(since=..., limit=200)
1 × invoices for the project where review_state in (ready_for_review, needs_attention)
1 × documents where class = unknown or confidence < REVIEW_CONFIDENCE_MIN
1 × dismissed subject keys
```

Four queries, fixed, regardless of row counts. Detectors receive the loaded
collections as arguments — that also makes them pure and trivially testable
without a database.

**Failing test:** `test_build_pulse_feed_issues_a_fixed_number_of_queries`
(count via a SQLAlchemy `before_cursor_execute` listener; assert it does not
grow when you add 50 more documents to the fixture).

**Failing tests:**

```text
test_drawing_revision_detector_uses_document_revised_verb
test_invoice_with_unapproved_variation_is_potential_cost_change
test_low_confidence_document_needs_classification
test_certificate_classified_is_approval_received
test_one_invoice_does_not_produce_two_attention_cards
test_detectors_do_not_call_decide_invoice
```

**Commit:** `feat: derive Pulse attention from events and canonical rows`

---

## Task 14.3 — Pulse API

```text
GET  /projects/{project_id}/pulse
POST /projects/{project_id}/pulse/dismiss      # subject_key in the JSON body
```

**Do not put `subject_key` in the path.** It is
`{signal_type}:{reference_type}:{reference_id}` — colons in a path segment
need encoding, the grouped form adds a second colon, and a UUID pushes the
segment past what some proxies pass through cleanly. A JSON body
(`{"subject_key": "..."}`) has none of those problems and is trivially
extensible when Stage 21 adds chain keys. Validate the shape server-side
and reject an unknown `signal_type` prefix with 422.

`GET` returns `PulseFeed`. Optional `?since=` is **Stage 21** — ignore
it now (do not parse-and-noop a since filter that Stage 21 will need to
mean something; omitting the param is clearer).

Authorization: copy Stage 5.4 / 12.2 — **404** for other projects and
non-owners, never 403.

`POST dismiss` requires the project owner, writes
`record_project_verb(verb="project_signal.dismissed", ...)` with
`subject_key` in the allow-list metadata. Idempotent via the Stage 13
dedup key `project_signal.dismissed:pulse:{subject_key}`.

Does not change invoice `review_state` or document class.

**Dismiss is permanent for that subject key — decide now whether that is
what you want.** For `drawing_revision` it is right: the key contains the
new document id, so Rev D raises a fresh card. For
`invoice_review_required:cost_invoice:{id}` it is wrong: dismissing hides
that invoice forever, even after new `severity=error` issues land on it.

**Resolution:** for signals derived from a mutable row, append a state
discriminator to the subject key —
`invoice_review_required:cost_invoice:{id}:{review_state}`. The card
returns when the state changes, and stays dismissed while nothing has. Do
this in 14.1's key builder, not per detector.

**Failing test:** `test_dismissed_invoice_card_returns_when_review_state_changes`

**Files:**
- Create: `backend/app/api/pulse.py`
- Modify: `backend/app/main.py` (`include_router`)
- Create: `backend/tests/test_pulse_api.py`
- Modify: `backend/app/schemas/projects.py` **or** a new
  `backend/app/schemas/pulse.py` — prefer a new schema file so Pulse
  does not bloat `projects.py`.

**Failing tests:**

```text
test_pulse_on_another_project_returns_404
test_dismiss_is_idempotent_and_drops_the_card
test_dismiss_does_not_change_invoice_review_state
```

**Commit:** `feat: project-scoped Pulse feed and dismiss API`

---

## Task 14.4 — Pulse UI against fixtures (parallel with 14.2)

Same trick as Stage 12.3: the panel takes a `PulseFeed` fixture until
14.5 wires the query.

**Files:**
- Create: `frontend/src/components/project/PulsePanel.tsx`
- Create: `frontend/src/components/project/PulsePanel.test.tsx`
- Modify: `frontend/src/pages/ProjectCockpitPage.tsx` — render the panel
  at the top of the main column. Do **not** put it inside
  `DocumentRepositoryPanel` / `ActivityFeed`.

Vitest must lock the failure mode:

```text
test_pulse_does_not_headline_raw_event_counts
```

Fixture: 26 `document.filed` rollup + 1 drawing revision + 1 invoice
cost-change. Headline is attention_count `2` (or `2 items need
attention`), **not** `28` / `26 documents` as the H1. Other-activity
line may say `26 documents filed`.

Also: `test_review_invoice_action_is_a_button_not_inline_logic` — the
component calls `onAction(item, "review_invoice")`; it does not POST
to `/decision` itself.

**Commit:** `feat: Pulse panel synthesises attention, not event counts`

---

## Task 14.5 — Wire UI to API

`frontend/src/lib/api.ts` + a TanStack query in
`frontend/src/lib/queries/pulse.ts`. Invalidate Pulse on dismiss, on
invoice decision, and on classification override (those already have
mutation hooks — add the query key there; do not duplicate the
mutations).

**Commit:** `feat: load Pulse from GET /projects/:id/pulse`

---

## Task 14.6 — Card actions call existing services

| Action | Calls |
|---|---|
| `review_invoice` | navigate/open existing `InvoiceReviewPane` for `reference_id` |
| `classify_document` | existing `ClassificationChip` / PUT classification |
| `view_evidence` | existing repository selection |
| `dismiss` | `POST .../pulse/{subject_key}/dismiss` |

`Ask SiteWise` / `Draft reply` / `Update programme` are **not** MVP
(Stage 21). Do not stub fake buttons that do nothing.

No `decide_invoice` from the Pulse panel itself — Approve still lives
on the three-pane review (D7: explicit approval). The card's job is to
get the user there.

**Failing test (frontend):** clicking Review invoice selects the invoice
id; it does not fire hold/reject/approve.

**Commit:** `feat: Pulse card actions open existing review surfaces`

---

## Task 14.7 — Acceptance G + I (without email)

Product scenarios G and I, email-free:

- **G:** invoice booked with `UNAPPROVED_VARIATION` → Pulse attention
  `potential_cost_change` + action `review_invoice`.
- **I:** drawing S203 Rev C after Rev B → Pulse attention
  `drawing_revision`.

Backend tests on `build_pulse_feed`. No browser.

**Commit:** `test: Pulse attention for unapproved variation and drawing revision`

---

## Exit gate

- [ ] `uv run pytest tests/projects/test_pulse.py tests/test_pulse_api.py tests/projects/test_event_spine.py -q`
- [ ] `pnpm typecheck && pnpm test` (PulsePanel tests included)
- [ ] `pnpm build` respects existing cockpit gzip budget
- [ ] `grep pulse_ backend/alembic/versions` empty of new tables
- [ ] Detectors do not import `decide_invoice` / `set_document_classification`
      as callees (actions are UI → existing routes)
- [ ] No feature flag added to `app/config.py`
- [ ] **Attention is bounded** — 40 unclassified documents produce one
      grouped card, `attention` never exceeds `MAX_ATTENTION_ITEMS`, and
      `attention_count` reports the pre-truncation total
- [ ] `build_pulse_feed` issues a fixed number of queries that does not grow
      with row count
- [ ] Dismiss takes `subject_key` in the body, not the path
- [ ] ActivityFeed still renders workflow traces
- [ ] Backend failures ⊆ baseline
- [ ] Gate 3 is now eligible for a human signature (Pulse in production)

**After this stage:** wait for Gate 3 in `TRACKER.md`. Then implement
email from [`stage-15-email-foundation.md`](./stage-15-email-foundation.md).
Do not start 15–22 against unsigned Gate 3.
