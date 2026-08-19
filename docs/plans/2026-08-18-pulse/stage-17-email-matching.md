# Stage 17 — Email project matching and threading

**Goal:** Every imported message gets `project_id + confidence + basis`, or
it sits in review. User correction outranks the machine (D4) and does not
rewrite raw headers (D5).

**Ownership:** `backend/app/email/` matching + interpretation updates.
**Forbidden:** sending, attachment ingest (already 16), document_class
invention, a contacts CRM product, live Graph/Gmail.
**Predecessor:** Stage 16 `[x]`.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D4, D5, D6
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §9 Project matching
- `backend/app/projects/consultant_facts.py` (firms; there is **no**
  contact directory — do not invent one)
- `backend/app/projects/snapshot.py` / project taxonomy (address, number)
- `backend/app/email/models.py` as built in 15
- Stage 5 override pattern (`document_classification_overrides`) — copy
  the *permanence* idea for match corrections
- This file

---

## Match basis (closed)

```text
alias          # Stage 22; treat as 1.00 when present
user           # explicit correction
thread         # prior message in provider_thread_id already matched
domain         # from_address domain matches an appointed consultant fact
subject        # project number / name in subject
contact        # reserved; only if a real stored address exists — do not
               # create a contacts table to make this fire
default        # unmatched
```

Confidence bands reuse classification doctrine: `< 0.65` needs review
(`match_basis="default"` or low subject/domain). `user` and `alias` are
1.00.

Python owns the score. An LLM may **not** pick `project_id`.

---

## Task 17.1 — `match_project`

```python
class ProjectMatch(BaseModel):
    project_id: uuid.UUID | None
    confidence: float
    basis: Literal["alias", "user", "thread", "domain", "subject", "contact", "default"]


def match_project(
    *,
    email: ProjectEmail,
    candidates: Sequence[ProjectMatchCandidate],
    prior_thread_project_id: uuid.UUID | None,
    user_override: ProjectMatch | None,
) -> ProjectMatch:
```

Pure function, easy to unit-test. `candidates` is assembled by a thin
loader from:

- projects the mailbox owner owns
- each project's slug / code / site address / client name
- consultant fact firm names (domain guess from firm is **weak** — only
  fire `domain` when an actual email domain is stored on a shared project
  object; if none is stored, skip `domain` and Integration-note it)

Priority: `user` > `alias` > `thread` > scored `domain`/`subject` >
`default`.

**Failing tests:** `backend/tests/email/test_project_matching.py`

```text
test_user_override_outranks_thread_and_subject
test_thread_association_wins_over_subject
test_unknown_sender_is_default_with_null_project
test_low_confidence_subject_match_is_below_review_threshold
```

**Commit:** `feat: score email-to-project matches in Python`

---

## Task 17.2 — Persist match on the interpretation row

`import_provider_messages` (15.3) plus a `link_email_to_project` service:

```python
async def link_email_to_project(
    session, *, email_id, project_id, actor_id, reason: str | None
) -> ProjectEmailInterpretation:
```

User link sets `match_basis="user"`, `match_confidence=1.0`,
`match_reviewed_by_user_id=actor_id`. Does not UPDATE raw columns.

**Import must never overwrite an existing interpretation row.** The exit
gate below requires "user correction survives re-import", and the only
thing standing between you and losing it is that `import_provider_messages`
(15.3) upserts the *raw* row idempotently. If the importer also writes a
default interpretation — `basis="default"`, `project_id=NULL` — on every
pass, a re-sync silently wipes the user's link and the machine's match
alike. This is the same defect Stage 8B.1 fixed for document overrides;
do not re-create it in email.

Rule: the importer inserts an interpretation row **only when none exists**
for that `email_id` (`ON CONFLICT (email_id) DO NOTHING`). Re-matching is
an explicit call, and it must refuse to downgrade `basis="user"`.

**Failing tests:**

```text
test_reimport_does_not_reset_a_user_link
test_rematch_refuses_to_downgrade_a_user_basis
```

REST (project-scoped, 404 cross-tenant):

```text
POST /projects/{project_id}/emails/{email_id}/link
```

Also used later by MCP `link_email_to_project`.

After a successful link with `confidence >= 0.65` **or** `basis=="user"`,
Stage 16 ingest may run for attachments (call the adapter; do not
reimplement it). Auto-ingest on a `< 0.65` machine match is forbidden.

**Failing tests:**

```text
test_link_email_does_not_rewrite_raw_subject
test_link_on_another_project_returns_404
test_low_confidence_match_does_not_auto_ingest_attachments
```

**Commit:** `feat: user email-to-project link outranks machine match`

---

## Task 17.3 — Threading

Group by `provider_thread_id` when present, else `internet_message_id`
In-Reply-To / References headers (already stored on raw `headers` JSONB).
Do not LLM-thread.

```python
def thread_key(email: ProjectEmail) -> str: ...
```

A later message in a matched thread inherits `project_id` at `basis=thread`
without a user click.

**Failing test:** `test_reply_in_matched_thread_inherits_project`

**Commit:** `feat: inherit project match from the email thread`

---

## Exit gate

- [x] User correction survives re-import of the same `provider_message_id`
      (idempotent raw insert + interpretation kept)
- [x] Unmatched messages remain `project_id IS NULL`
- [x] No contacts table added
- [x] Backend failures ⊆ baseline

**After this stage:** [`stage-18-email-intelligence.md`](./stage-18-email-intelligence.md).
