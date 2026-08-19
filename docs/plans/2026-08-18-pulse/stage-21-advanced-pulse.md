# Stage 21 — Advanced Pulse

**Goal:** Pulse can answer **"since yesterday"** and show **cross-domain
chains** as one card, still without a Pulse database and still without
business logic in the UI.

**Ownership:** `backend/app/projects/pulse.py` + `PulsePanel.tsx`.
**Forbidden:** new tables, new invoice math, email send, extending
`DocumentClass`, detectors that mutate.
**Predecessor:** Stage 19 `[x]` (email verbs exist). Stage 20 is useful
for tender chains but **not** required if 19 is done — implement 21 after
19; if 20 is also `[x]`, include the tender_received detector.

**Reading list:**
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §8 Pulse +
  acceptance G, I, H
- [`stage-14-pulse-mvp.md`](./stage-14-pulse-mvp.md) synthesizer contract
- `backend/app/projects/event_spine.py` `email.*`
- Stage 18 action candidates
- This file

---

## Task 21.1 — `since` window

`GET /projects/{id}/pulse?since=ISO-8601`

- Verbs and canonical rows are considered **if the triggering event is
  `>= since`**.
- Attention cards whose evidence is older drop out of attention but may
  remain dismissed (dismiss keys still apply).
- Default if omitted: last 7 days (document the default in the schema).
  Do not default to "all time" — that recreates the raw inbox.

Frontend: a control labelled in product language (**Since yesterday** /
**Last 7 days** / **Last 30 days**), not `since=`.

**Failing tests:**

```text
test_since_yesterday_hides_older_drawing_revision
test_omitted_since_is_seven_days_not_unbounded
```

**Commit:** `feat: Pulse since-window filters attention by event time`

---

## Task 21.2 — Cross-domain chains

One attention card when evidence is the same story:

| Chain | Inputs | Title sketch |
|---|---|---|
| Cost + variation (G) | already MVP; keep merge | Invoice … unapproved variation |
| Drawing + transmittal (I+email) | `document.revised` + `email.received` with `message_category=document_transmittal` same drawing_number | Structural drawing revised; issued on transmittal |
| Invoice via email (H) | `invoice.needs_review` + parent `email.received` | Invoice arrived by email (same review action) |
| Tender return | `commercial` submission linked to issued request (if Stage 20 `[x]`) | Submission received from {filename} |

Merging key: drawing_number, invoice_id, or procurement request id.
Never show 3 cards that are the same fact.

New signal types (extend `PulseSignalType` **in this packet**, with
exhaustiveness test update):

```text
tender_received
unanswered_correspondence
```

`unanswered_correspondence`: `message_category in {rfi, action_required}`
and no outbound `project_email_drafts.status=sent` in the same thread
within 5 days. Python only.

Two dependencies to wire explicitly, because neither is obvious:

- **"Same thread" means Stage 17.3's `thread_key(email)`**, not
  `provider_thread_id` alone — a reply that arrives without a provider
  thread id still belongs to the thread via `In-Reply-To`. Join drafts to
  the thread through `project_email_drafts.in_reply_to_email_id` →
  `project_emails` → `thread_key`. A draft with a null
  `in_reply_to_email_id` (a fresh outbound message) answers nothing; do not
  let it clear the signal.
- **Stage 19.2 added `sending` and `send_failed`.** `status == "sent"` is
  the only state that counts as answered. A `send_failed` draft must leave
  the correspondence *unanswered* — that is exactly the case the user needs
  to see, and treating any non-draft row as an answer would hide it.

**Failing test:** `test_failed_send_does_not_clear_unanswered_correspondence`

Deferred still: `programme_risk`, `consultant_action_due` (need programme
write-path confidence we do not have). Integration-note them; do not stub
always-empty detectors.

**Failing tests:**

```text
test_drawing_revision_and_transmittal_email_are_one_card
test_email_invoice_is_one_card_not_email_plus_invoice
test_unanswered_rfi_is_attention_after_five_days
```

**Commit:** `feat: Pulse chains cross-domain evidence into one card`

---

## Task 21.3 — Other-activity rollup includes email

Other-activity line may now mention emails **as a rollup**:

```text
6 documents filed · 2 consultant replies · 1 invoice ready for review
```

Headline remains attention_count. Vitest: 48 emails + 26 documents + 12
events in the fixture still cannot appear as the H1.

**Commit:** `feat: roll email into Pulse other-activity without count headlines`

---

## Task 21.4 — Optional card actions unlocked by email

Now legal (they call Stage 19 services, not new logic):

| Action | Calls |
|---|---|
| `draft_reply` | `reply_email_draft` then open the draft — **does not send** |
| `view_thread` | `read_email_thread` / REST equivalent |

Still no `Update programme` (no detector should write programme rows).

**Commit:** `feat: Pulse draft-reply action creates a draft only`

---

## Exit gate

- [ ] `since` covered by tests
- [ ] Chain merge tests green
- [ ] Stage 14 failure-mode test still green (raw counts)
- [ ] Detectors still do not call send / decide_invoice
- [ ] Backend failures ⊆ baseline
- [ ] `pnpm typecheck && pnpm test && pnpm build`

**After this stage:** [`stage-22-project-email-aliases.md`](./stage-22-project-email-aliases.md)
— last on purpose.
