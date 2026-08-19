# Stage 19 — Email MCP tools and user-approved drafts

**Goal:** Agents can search, read, draft, and link project email. They
cannot send unattended, delete mail, or change mailbox rules. Sending a
draft requires an explicit user `actor_id` (D7).

**Ownership:** `backend/app/mcp_bridge/server.py` wrappers +
`backend/app/email/service.py` draft/send + REST for the UI.
Graph/Gmail adapters may grow real HTTP **only** behind configured
secrets; default remains FakeProvider.
**Forbidden:** `send_email_unattended`, delete-mail tools, mailbox-rule
tools, bulk-forward, speculative `EMAIL_ENABLED` flag, Clerk-core imports
from `backend/tender/`.
**Predecessor:** Stage 18 `[x]`.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D6, D7
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §9 MCP boundary
- `backend/app/mcp_bridge/server.py` `set_document_classification`
  (mutation authorizer pattern, 8B.3)
- `backend/tests/mcp_bridge/test_set_document_classification.py`
- `backend/app/email/providers/base.py` `send_draft(..., actor_id=)`
- `backend/AGENTS.md` §Security seams
- This file

---

## Allowed MCP tools (exact names)

```text
search_project_email
read_email_thread
get_email_attachment
list_project_correspondence
create_email_draft
reply_email_draft
forward_email_draft
link_email_to_project
propose_email_action
propose_project_decision
```

`propose_*` writes a **candidate** (Stage 18 JSONB or a draft artefact).
It does not mutate cost/programme/decisions.

## Forbidden names (assert absent)

```text
send_email_unattended
delete_email
change_mailbox_rules
bulk_forward
send_email          # too easy to call; sending goes through send_email_draft
```

Sending:

```text
REST  POST /projects/{id}/emails/drafts/{draft_id}/send
MCP   send_email_draft   # optional; if you add it, it MUST use
                         # authorize_project_mutation_with_claims and require
                         # the user actor from the turn — never a bare send
```

Prefer REST-only send for MVP so Pi cannot send without a UI confirm.
If MCP `send_email_draft` is added, tests must prove a turn without
mutation capability fails.

---

## Task 19.1 — Draft persistence

```text
project_email_drafts
  id, project_id, created_by_user_id,
  in_reply_to_email_id NULL,
  to_addresses JSONB, cc_addresses JSONB,
  subject, body_text,
  provider_draft_id NULL,
  provider_message_id NULL,        # set on successful send
  status  draft | sending | sent | send_failed | cancelled
  send_error TEXT NULL,
  sent_at NULL, sent_by_user_id NULL
```

(`sending` / `send_failed` come from the 19.2 ordering below — put them in
the CHECK constraint now rather than migrating twice.)

Alembic `054_email_drafts` (confirm head). Status transitions Python-side;
illegal send from `cancelled` raises.

`create_email_draft` / `reply_email_draft` / `forward_email_draft` only
insert `status=draft` and optionally push to `provider.create_draft`.

**Failing tests:** `backend/tests/email/test_email_drafts.py`

```text
test_create_draft_does_not_send
test_send_without_actor_raises
test_send_requires_project_owner
```

**Commit:** `feat: store email drafts that cannot send themselves`

---

## Task 19.2 — REST send with actor

```python
async def send_email_draft(
    session, *, project_id, draft_id, actor_id: uuid.UUID
) -> ProjectEmailDraft:
```

404 for other projects / non-owners (never 403). 409 if status ≠ `draft`.

**Sending is a dual write, and the naive order duplicates mail.** "Call
`provider.send_draft` then set `status=sent`" leaves a window: the provider
accepts the message, the commit then fails (deadlock, timeout, worker
restart), the row stays `draft`, the user retries, and the recipient gets
the email twice. Email cannot be unsent, so this is not a recoverable bug —
it is a message to a consultant that SiteWise sent twice.

Claim the draft **before** calling the provider:

```text
1. SELECT ... FOR UPDATE the draft; 409 unless status == 'draft'
2. status = 'sending', sent_by_user_id = actor_id, COMMIT
3. provider.send_draft(..., actor_id=actor_id)
4. status = 'sent', sent_at = now(), provider_message_id = <returned>, COMMIT
5. on provider error: status = 'send_failed', record the error, COMMIT
```

So `status` becomes `draft | sending | sent | send_failed | cancelled`.
A row stuck in `sending` is **not** auto-retried — it is surfaced for a
human, because "did this actually go out?" is a question only the mailbox
can answer. That is the D7-consistent answer: at-most-once delivery with an
honest unknown state, rather than at-least-once with silent duplicates.

`FOR UPDATE` in step 1 is what stops two concurrent sends of one draft.
Without it, both transactions read `draft` and both send.

No cron, no "send later", no retry worker that sends without a user.

**Failing tests:**

```text
test_concurrent_send_of_one_draft_sends_once
test_provider_failure_leaves_send_failed_not_draft
test_send_failed_draft_cannot_be_silently_resent
```

**Failing tests:** `backend/tests/test_email_draft_api.py`

```text
test_send_draft_on_another_project_returns_404
test_send_draft_by_non_owner_returns_404
test_send_already_sent_returns_409
```

**Commit:** `feat: send project email drafts only with an explicit actor`

---

## Task 19.3 — MCP wrappers

Each allowed tool:

- Search/read/list: `authorize_project_access_with_claims`
- create/reply/forward/link/propose/send: `authorize_project_mutation_with_claims`
- Cross-project email id → ToolError, no leakage

`get_email_attachment` returns metadata + existing workspace/source
document id from Stage 16, **not** a new parse.

**Failing tests:** `backend/tests/mcp_bridge/test_email_tools.py`

```text
test_search_project_email_is_project_scoped
test_create_email_draft_requires_mutation_capability
test_forbidden_email_tool_names_are_absent
```

Grep the live FastMCP registry (same style as the classification tool
test) for forbidden names.

**Commit:** `feat: MCP email search/read/draft/link without unattended send`

---

## Task 19.4 — Graph / Gmail adapters (optional HTTP, required stubs)

Fill `microsoft_graph.py` / `gmail.py` enough that a configured client
*could* list+get+draft+send. If `settings.microsoft_graph_client_id` (etc.)
is missing, methods raise `ProviderNotConfigured` — that is config, not a
feature flag.

Do **not** add `email_enabled: bool`. Do **not** call live APIs in tests.
Record in `TRACKER.md` if a human signed OD-4 for production credentials.

Factory:

```python
def email_provider_from_settings(settings) -> EmailProvider:
    if settings.email_provider == "fake":
        return FakeProvider()
    ...
```

Default `email_provider = "fake"` in `config.py`. Fail fast only when the
chosen provider's secrets are missing.

**Failing tests:**

```text
test_default_provider_is_fake
test_graph_without_secrets_raises_not_configured
```

**Commit:** `feat: select email provider from config without a kill-switch flag`

---

## Exit gate

- [ ] Forbidden MCP names absent
- [ ] Send path always carries `actor_id`
- [ ] Mutation tools use the mutation authorizer
- [ ] Equivalence test from Stage 16 still green
- [ ] Backend failures ⊆ baseline
- [ ] `pnpm typecheck` if any frontend draft UI shipped; UI is optional
      this stage (REST is enough). If you add UI, extend the existing
      cockpit — do not create `EmailApp.tsx`.

**After this stage:** Gate 3 stays closed for product email until Pulse
**and** this send boundary are live. Closed-loop procurement is
[`stage-20-closed-loop-procurement.md`](./stage-20-closed-loop-procurement.md)
and waits on **Stage 19 `[x]`**, not merely on the packet existing.
