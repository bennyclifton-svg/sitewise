# Stage 15 — Email foundation

**Goal:** Provider-neutral, D5-split email records under
`backend/app/email/`. Raw headers/body never change after insert. No live
Microsoft or Google calls. No attachment parsing.

**Ownership:** `backend/app/email/` (new package of domain code — this is
not a second classifier; D8 forbids `email_classifier.py`, not an email
store).
**Forbidden:** live Graph/Gmail HTTP, sending, attachment extraction,
`email_classifier.py`, Pulse UI changes, TCM, feature flags, a second
ingest pipeline.
**Predecessor:** Gate 3 human signature in `TRACKER.md` (Pulse stable).
**Do not implement this file before that signature.** Planning is not
permission to start.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D1, D2, D5, D7, D8, D9
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §9 Email (raw stays
  raw, provider-neutral layout)
- [`stage-13-project-event-spine.md`](./stage-13-project-event-spine.md)
  `email.*` verbs (emitters are Stage 18, not here)
- `backend/app/cost_plan/models.py` machine vs reviewed split (copy the
  *idea*, not the invoice columns)
- `backend/app/config.py` (add provider settings later as real secrets,
  not a boolean `email_enabled`)
- `backend/AGENTS.md` §Configuration
- This file

---

## Layout (create these files; do not add extras)

```text
backend/app/email/__init__.py
backend/app/email/models.py
backend/app/email/schemas.py
backend/app/email/service.py
backend/app/email/providers/base.py
backend/app/email/providers/fake.py
backend/app/email/providers/microsoft_graph.py   # stubs only this stage
backend/app/email/providers/gmail.py             # stubs only this stage
```

---

## Task 15.1 — Immutable raw + derived overlay

Alembic: confirm `uv run alembic heads` (expected `052_activity_event_dedup`
after Stage 13; Pulse 14 should add **no** revision). Id ≤ 32 chars:
`053_project_emails`.

Two tables, one row-life story:

### `project_emails` (raw)

Written once. Application **refuses UPDATE** of raw columns after insert
(service guard + test). No Postgres trigger unless the guard is shown
insufficient.

```text
id                         UUID PK
mailbox_account_id         UUID NULL          # Stage 19/22 fill this
provider                   VARCHAR(16) NOT NULL   # fake | microsoft_graph | gmail | inbound_alias
provider_message_id        VARCHAR(255) NOT NULL
provider_thread_id         VARCHAR(255) NULL
internet_message_id        VARCHAR(255) NULL
from_address               VARCHAR(320) NOT NULL
to_addresses               JSONB NOT NULL DEFAULT '[]'
cc_addresses               JSONB NOT NULL DEFAULT '[]'
subject                    TEXT NOT NULL
sent_at                    timestamptz NOT NULL
body_text                  TEXT NOT NULL DEFAULT ''
headers                    JSONB NOT NULL DEFAULT '{}'
raw_storage_key            VARCHAR(512) NULL  # optional RFC822 in Storage; may be null for fake
content_hash               VARCHAR(64) NOT NULL
created_at                 timestamptz NOT NULL
```

Unique: `(provider, provider_message_id)`.

**Three schema decisions the sketch leaves open. Settle them here.**

- **`content_hash` — hash of what?** Providers hand back different
  envelopes for the same message, so hashing "the payload" makes the value
  provider-specific and useless for the cross-provider dedup someone will
  eventually want. Define it as `bytes_content_hash` over a canonical tuple:
  `internet_message_id | from_address | sent_at ISO | subject | body_text`,
  joined by `\n`. Same function as ingest (`ingest/hashing.py`) so there is
  one hashing story in the codebase. Write the helper in `service.py` and
  test that two providers delivering one message agree.
- **`sent_at NOT NULL` will bite you.** Malformed or absent `Date` headers
  are common in real mail and universal in test fixtures. Make it
  `NULL`-able and sort on `COALESCE(sent_at, created_at)`, or default it to
  the receipt time and store the raw header value in `headers`. Do not make
  the importer throw away a message because a header was malformed — that
  is evidence loss (D3's spirit).
- **`raw_storage_key NULL`** is right, but say what fills it: Stage 22's
  inbound webhook, if it keeps the RFC822. Stages 15–19 leave it null.

**The raw-immutability guard needs to be a mapper event, not just a service
check.** A service-layer `if` only protects callers who go through the
service; anything doing `session.execute(update(ProjectEmail)...)` walks
straight past it, and Stage 17/18 both write to adjacent rows. Register a
SQLAlchemy `before_update` listener on `ProjectEmail` that raises if any
raw column is in the changed set. That catches ORM mutation from anywhere
in the process, which is what "written once" actually means.

**Failing test:** `test_orm_update_of_raw_column_raises_from_any_caller`

### `project_email_interpretations` (derived, D5)

```text
email_id                   UUID PK FK → project_emails.id ON DELETE CASCADE
project_id                 UUID NULL FK → projects.id
match_confidence           NUMERIC(4,3) NULL
match_basis                VARCHAR(32) NULL   # contact | domain | thread | alias | subject | user
match_reviewed_by_user_id  UUID NULL
message_category           VARCHAR(32) NULL   # Stage 18 fills; closed set then
summary                    TEXT NULL          # optional; NEVER replaces body_text
updated_at                 timestamptz NOT NULL
```

`project_id` is nullable so unmatched mailbox mail can exist. Alias inbound
(Stage 22) always sets it. Stage 17 owns matching.

Register both in `app/database/models.py`.

**Failing tests:** `backend/tests/email/test_email_raw_immutable.py`

```text
test_updating_match_does_not_change_subject_or_body
test_service_refuses_raw_column_update
test_duplicate_provider_message_id_is_idempotent
```

**Commit:** `feat: persist raw project email separately from interpretation`

---

## Task 15.2 — Provider protocol + fake provider

```python
# providers/base.py
from typing import Protocol
from datetime import datetime

class EmailProvider(Protocol):
    name: str  # fake | microsoft_graph | gmail | inbound_alias

    async def list_messages(self, *, since: datetime | None) -> list[RawProviderMessage]:
        ...

    async def get_message(self, provider_message_id: str) -> RawProviderMessage:
        ...

    async def get_attachment_bytes(
        self, provider_message_id: str, attachment_id: str
    ) -> bytes:
        ...

    async def create_draft(self, draft: ProviderDraft) -> str:
        ...

    async def send_draft(self, provider_draft_id: str, *, actor_id: uuid.UUID) -> None:
        ...
```

`FakeProvider` is in-memory, used by every email test through Stage 19.
`microsoft_graph.py` and `gmail.py` raise `NotImplementedError` on every
method (or `ProviderNotConfigured`). **No `httpx` calls. No SDK.**

Do not add `EMAIL_ENABLED`. If Graph credentials appear in `config.py` this
stage, they must be optional and unused.

`send_draft` on FakeProvider records a send **only** when `actor_id` is
provided; a missing actor raises. That is the D7 seam for Stage 19 tests.

**Failing tests:**

```text
test_fake_provider_round_trips_a_message
test_graph_provider_is_not_callable_yet
test_send_draft_without_actor_raises
```

**Commit:** `feat: provider-neutral email interface with an in-memory fake`

---

## Task 15.3 — Sync service against the fake (no Pulse, no intake)

```python
async def import_provider_messages(session, *, provider: EmailProvider, actor_id: uuid.UUID | None) -> int:
    """Insert raw rows. Do not match projects. Do not ingest attachments."""
```

Attachments are stored as **references only** this stage:

### `project_email_attachments` (raw refs)

```text
id, email_id, provider_attachment_id, filename, content_type, size_bytes,
content_hash NULL,  # filled Stage 16 when bytes are pulled
source_document_id NULL
```

Pulling bytes is Stage 16. This packet must **not** call
`ingest_hosted_file` or `classify_entry`.

**Failing test:** `test_import_does_not_call_ingest_hosted_file`

**Commit:** `feat: import raw email and attachment refs without ingesting`

---

## Exit gate

- [ ] Alembic upgrade/downgrade/upgrade on `053_project_emails`
- [ ] Raw update guard covered
- [ ] `grep openai|httpx|msgraph|google.oauth backend/app/email` empty
      (except comments)
- [ ] No `email_classifier.py`
- [ ] Backend failures ⊆ baseline
- [ ] Stage 16 is unblocked

**After this stage:** [`stage-16-email-intake.md`](./stage-16-email-intake.md)
— the non-negotiable equivalence test.
