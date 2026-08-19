# Stage 20 — Closed-loop procurement

**Goal:** RFT/RFP already generated in Clerk can be issued as a **user-
approved** cover email, returns detected as `procurement_stage=submission`,
and listed for Tender Comparison **without** email duplicating procurement
logic or Clerk merging into `backend/tender/` classifiers.

**Ownership:** `backend/app/procurement/requests.py` (state) + a thin
`backend/app/email/` caller. Email drafts stay in the email service.
**Forbidden:** procurement state machine inside `app/email/`, imports from
`backend/tender/` except the existing FastAPI/MCP mount, unattended send,
new document classes (`tender_submission` is dead — Stage 8).
**Predecessor:** Stage 19 `[x]`.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D1, D7, D8
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §9 Closed-loop
  procurement
- `backend/app/procurement/requests.py`
  (`transition_procurement_request`, statuses `draft|issued|closed|cancelled`)
- `backend/app/database/procurement_request.py`
- `backend/app/workflows/procurement_request.py` (generation — do not
  rewrite)
- Stage 9.7: Clerk lists submissions via
  `RetrievalFilters(document_class="commercial", procurement_stage="submission")`
- Stage 19 `create_email_draft` / `send_email_draft`
- This file

**Loop (email must not own this):**

```text
generated RFT draft artefact
  → recipients + cover email draft (status=draft)
  → user send (actor_id) → procurement_request.status=issued
  → inbound attachments classified commercial + procurement_stage=submission
  → linked to the issued request
  → Clerk-side list for TCM (9.7)
  → missing bidders: another draft email, still user-sent
```

---

## Task 20.1 — Cover email draft from an existing request

```python
async def draft_procurement_issue_email(
    session,
    *,
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    actor_id: uuid.UUID,
    to_addresses: list[str],
    body_text: str | None = None,
) -> ProjectEmailDraft:
```

- Request must be `status=draft` with `current_draft_artifact_id` set.
- Creates an email draft (Stage 19) whose attachments/references include
  the artefact workspace path — **do not** re-render the RFT in email
  code; attach/link what procurement already generated.
- Does **not** call `transition_procurement_request`.
- Default body may be a short template in Python. No LLM required. If you
  add a model draft, it is a proposal the user edits; send still needs
  actor_id.

**Failing tests:** `backend/tests/procurement/test_closed_loop_issue.py`

```text
test_draft_issue_email_leaves_request_in_draft
test_draft_issue_email_without_artefact_raises
```

**Commit:** `feat: draft a cover email for an unsent procurement request`

---

## Task 20.2 — Send issues the request (one transaction)

```python
async def send_procurement_issue_email(
    session, *, project_id, request_id, draft_id, actor_id, expected_revision: int
) -> ProcurementRequest:
```

**⚠ This paragraph previously gave two contradictory orders. Corrected
2026-08-19 — implement exactly what follows and ignore any recollection of
"send first".**

Reuse the Stage 19.2 send state machine; do not build a second one here.
The procurement transition rides on top of it:

```text
1. Validate: request.status == 'draft', draft.status == 'draft',
   expected_revision matches           → else 409
2. send_email_draft(...)               # 19.2 owns claim → send → sent
3. if the draft reached 'sent':
       transition_procurement_request(..., 'issued')
   else:
       leave the request 'draft' and surface the draft's send_failed
```

Send-then-transition is correct **here** precisely because Stage 19.2 made
sending safe. The email is the irreversible act; the request status is
local and re-derivable. Inverting them — issuing first — would leave a
request marked `issued` when nothing was ever sent, which is the worse
failure: a user believes bidders have the RFT and they do not.

If step 3 fails after a successful send, do **not** invent a compensating
unsend. Leave the request `draft`, log it, and let the operator re-run —
`transition_procurement_request` is idempotent from `draft`, and the draft
is already `sent` so 19.2's guard stops a second email. Assert that.

404/409 as Stage 12.2.

**Failing tests:**

```text
test_send_issue_email_sets_status_issued
test_send_failure_leaves_request_draft
test_send_issue_on_another_project_returns_404
test_retry_after_transition_failure_does_not_send_a_second_email
```

**Commit:** `feat: issuing procurement requires a user-approved send`

---

## Task 20.3 — Detect returns as submissions

When Stage 16 ingests an attachment for a project that has an **issued**
procurement request, and classification is `commercial` with
`procurement_stage=submission` (classifier already emits this — Stage 8
mapping / Stage 4 filename+content; do not add an email-only guess):

```python
async def link_submission_to_request(
    session, *, project_id, source_document_id
) -> ProcurementRequest | None:
```

Link rule (first match):

1. Email thread of this attachment's parent message matches the issue
   draft's `provider_thread_id` / in-reply-to.
2. Else `target_slug` / target_name appears in filename or email subject.
3. Else leave unlinked (still a submission document; TCM can still see it
   via 9.7). Do not invent a request.

Store the link as JSONB on the request or a small
`procurement_request_submissions (request_id, source_document_id)` table.
A table is justified (many submissions). Alembic `055_procurement_submissions`
if needed — confirm head.

Email code calls this service; it does not set `procurement_stage` itself.

**Failing tests:**

```text
test_reply_attachment_classified_submission_links_to_issued_request
test_unrelated_quote_does_not_link
test_email_module_does_not_write_procurement_stage
```

**Commit:** `feat: link classified submissions back to issued procurement requests`

---

## Task 20.4 — Chase missing bidders is another draft

List issued requests with fewer linked submissions than `to_addresses`
count (or an explicit recipient list stored on the issue draft). Produce
`create_email_draft` only. **No send.**

**Failing test:** `test_chase_missing_bidders_creates_draft_without_sending`

**Commit:** `feat: draft chase emails for missing procurement returns`

---

## Task 20.5 — TCM boundary

Do not start a tender job from email. Prove with a test that
`link_submission_to_request` does not import `tender`.

Regression: Stage 9.7 filter still lists `commercial` +
`procurement_stage=submission` including email-ingested files (Stage 16
equivalence already proves class; this proves the filter sees them).

**Forbidden files:** `backend/tender/services/classification.py`

**Commit:** `test: email submissions stay on the Clerk commercial filter`

---

## Exit gate

- [ ] Request status still owned by `procurement/requests.py`
- [ ] `grep procurement_stage backend/app/email` empty (or read-only)
- [ ] No `backend/tender/` imports from `app/email` or new procurement
      helpers
- [ ] Send still requires `actor_id`
- [ ] Backend failures ⊆ baseline

**After this stage:** [`stage-21-advanced-pulse.md`](./stage-21-advanced-pulse.md).
