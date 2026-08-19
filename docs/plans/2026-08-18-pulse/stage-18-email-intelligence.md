# Stage 18 — Email classification boundary and candidates

**Goal:** The email *body* is `document_class = correspondence`. Semantic
labels (`rfi`, `instruction`, …) are **message metadata**, never new
document classes. Cost/commitment/decision inferences are candidates with
evidence. No silent canonical mutation (D6, D7).

**Ownership:** `backend/app/email/` interpretation fields + Stage 13
`email.*` emitters.
**Forbidden:** adding values to `DocumentClass`, `email_classifier.py`,
calling `set_document_classification` from a detector, sending, TCM.
**Predecessor:** Stage 17 `[x]`.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D1, D6, D7 canonical vocabularies
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §9 Classification
  boundary / Intelligence not automation
- `ingest/types.py` `DocumentClass` (frozen — correspondence only)
- `backend/app/projects/event_spine.py` `email.received|linked|action_detected`
- `backend/app/projects/pulse.py` — Stage 18 may **emit verbs**; it may
  not add Pulse signal types (that is Stage 21)
- This file

---

## Message category (closed, 14 values)

Stored on `project_email_interpretations.message_category`. **Not**
`source_documents.document_class`.

```text
action_required
decision_required
design_change
rfi
instruction
programme_change
document_transmittal
approval
invoice_notice
fee_proposal
tender_submission
meeting
information_only
unknown
```

If you need a 15th, Integration-note it. Do not quietly extend the
Literal inside this packet.

---

## Task 18.1 — Category is metadata, not a class

When an attachment is ingested (Stage 16), the **file** is classified by
`classify_entry` as usual (invoice → `commercial`, drawing → `drawing`).
The **message** independently gets `message_category`.

A transmittal email with a drawing PDF:

```text
email.message_category = document_transmittal
attachment document_class = drawing
```

A test that sets `document_class = "rfi"` or `"document_transmittal"` must
fail the exhaustiveness contract — those strings are illegal classes.

**Failing tests:** `backend/tests/email/test_message_category.py`

```text
test_message_category_is_not_a_document_class
test_transmittal_email_leaves_drawing_class_on_the_attachment
test_rfi_email_body_is_correspondence_not_an_rfi_class
```

If email *bodies* are themselves stored as `source_documents` (only if you
need retrieval — YAGNI otherwise), they **must** be `correspondence`.
Prefer not to duplicate the body into `source_documents` this stage; the
raw `project_emails.body_text` is enough.

**Commit:** `feat: email categories stay off the document_class vocabulary`

---

## Task 18.2 — Emit `email.*` verbs

| Verb | When | Dedup |
|---|---|---|
| `email.received` | raw insert | `provider:provider_message_id` |
| `email.linked` | interpretation `project_id` set | `email_id:project_id` |
| `email.action_detected` | a candidate action is recorded | `email_id:action_type` |

Metadata allow-list already has `filename` etc. Add **nothing** to the
Stage 13 allow-list without an Integration note. Use `signal_type` for
the action type string, `subject_key` for the email id. Message is a
short human line (`"RFI detected in thread"`), not the body.

**Failing tests:**

```text
test_import_emits_email_received_once
test_link_emits_email_linked
test_action_candidate_emits_email_action_detected
```

**Commit:** `feat: emit email.received/linked/action_detected verbs`

---

## Task 18.3 — Action candidates, no mutation

Closed `EmailActionType`:

```text
reply_required
decision_required
commit_date
cost_signal
document_transmittal
```

Store as JSONB on the interpretation row (`actions: list[{type, excerpt,
locator, confidence}]`) or a child table. JSONB is enough (invoice issues
precedent).

Rules:

- Excerpt ≤ 280 chars, copied from the raw body (a quote, not a rewrite).
- `cost_signal` does **not** call `book_invoice` or change a cost plan.
- `commit_date` does **not** write the programme.
- `decision_required` does **not** insert `project_decisions`.

Deterministic first: subject/body markers (`RFI`, `instruction`, `please
advise`, `$` + number near `variation`/`VO`). Model fallback is **Stage E
territory** and is forbidden here even if accuracy is poor.

**Failing tests:**

```text
test_cost_signal_candidate_does_not_book_an_invoice
test_commit_date_candidate_does_not_write_programme_rows
test_action_excerpt_is_bounded
```

**Commit:** `feat: record email action candidates without mutating the project`

---

## Exit gate

- [x] `grep document_class backend/app/email` only reads attachment
      documents, never writes a non-canonical class
- [x] `ingest/types.py` DocumentClass unchanged
- [x] `email.action_detected` does not appear as a Pulse attention type
      yet (Stage 21)
- [x] Backend failures ⊆ baseline

**After this stage:** [`stage-19-email-mcp-drafts.md`](./stage-19-email-mcp-drafts.md).
