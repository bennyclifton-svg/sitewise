# Stage 22 — Project email aliases

**Goal:** Consultants can CC `PROJECTCODE@in.sitewise.au` and the message
lands on that project through the Stage 15–16 spine. Last because it is
an inbound operations surface, not a product experiment.

**Ownership:** inbound webhook + alias matching (`basis=alias`).
**Forbidden:** a second attachment pipeline, authed-send from the alias,
catch-all that files into a guessed project, speculative flags.
**Predecessor:** Stage 19 `[x]`. Stage 21 is not a hard dependency but
should be `[x]` so Pulse can show inbound mail.

**Reading list:**
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §9 Later: project
  aliases
- [`stage-15-email-foundation.md`](./stage-15-email-foundation.md) raw
  tables + `inbound_alias` provider
- [`stage-16-email-intake.md`](./stage-16-email-intake.md) ingest adapter
- [`stage-17-email-matching.md`](./stage-17-email-matching.md) `basis=alias`
- `backend/app/config.py` (secrets as settings, fail fast if the route
  is mounted without a webhook secret — same pattern as Stripe)
- `backend/app/api/` billing webhook (copy signature-checking *shape*,
  not Stripe code)
- Project `slug` / taxonomy code fields on `projects`
- This file

---

## Alias format

```text
{project_code}@in.sitewise.au
```

`project_code` is the project's existing slug, lowercased, `[a-z0-9-]`.
Reject aliases that do not match a single project (404 at the matcher,
not 200-and-guess).

Document DNS/MX in `TRACKER.md` as **ops**, not as a code packet. This
stage ships the HTTP inbound endpoint the MTA/provider will POST to.

---

## Task 22.1 — Resolve alias → project

```python
def project_code_from_alias(address: str) -> str | None: ...

async def project_for_inbound_alias(session, *, address: str) -> Project | None:
```

Only `to` / `cc` / `bcc` local-part @ `settings.email_inbound_domain`
(default `in.sitewise.au`). Other domains ignore.

**Failing tests:** `backend/tests/email/test_inbound_alias.py`

```text
test_known_slug_alias_resolves_project
test_unknown_alias_resolves_none
test_alias_is_case_insensitive
```

**Commit:** `feat: map PROJECTCODE@in.sitewise.au onto a project slug`

---

## Task 22.2 — Inbound webhook

```text
POST /internal/email/inbound
```

- Auth: HMAC or shared secret in `settings.email_inbound_webhook_secret`.
  If the secret is unset, the route returns **404** (not 500, not a
  feature flag). If set, bad signatures return 401.
- Body: provider-neutral JSON (`from`, `to`, `cc`, `subject`, `sent_at`,
  `body_text`, `headers`, `attachments[{filename, content_base64}]`) **or**
  raw RFC822 — pick JSON for tests.
- **Cap the request, not just the attachment.** `content_base64` inlines
  every attachment into one JSON body that FastAPI fully materialises in
  memory before your handler sees it, and base64 inflates by ~33%. A
  40 MB drawing set becomes a ~54 MB string held per concurrent request —
  an unauthenticated memory-exhaustion surface, since the signature is
  checked *after* the body is read.

  Enforce a total request-size limit at the ASGI/proxy layer (reject with
  **413** before parsing), and verify the HMAC over the raw body **before**
  JSON-decoding it. Then apply the per-attachment limit from 22.3. Order
  matters: size → signature → parse → ingest.

**Failing tests:**

```text
test_oversized_inbound_payload_is_rejected_before_parsing
test_signature_is_verified_against_raw_body_not_reserialised_json
```

The second one is a real trap: verifying the HMAC against
`json.dumps(parsed_body)` rather than the bytes on the wire passes your own
tests and fails against every real sender, because key order and whitespace
will not round-trip.
- Inserts via Stage 15 `import` with `provider="inbound_alias"`.
- Sets interpretation `project_id` immediately, `match_basis="alias"`,
  `match_confidence=1.0`.
- Then Stage 16 ingest for each attachment (project is known).
- Emits `email.received` + `email.linked`.

Never send from this address automatically. Outbound remains Stage 19
user-approved drafts from the user's connected mailbox (or a future
explicit "send as project" packet — not this one).

**Failing tests:**

```text
test_inbound_without_secret_returns_404
test_inbound_bad_signature_returns_401
test_inbound_alias_ingests_attachment_through_canonical_intake
test_inbound_does_not_send_mail
```

Reuse Stage 16 equivalence: inbound attachment bytes vs inbox upload on
another project.

**Commit:** `feat: inbound project alias webhook files through canonical intake`

---

## Task 22.3 — Collision and abuse

- Two projects with the same slug cannot exist (already true for slugs).
  If it ever happens, matcher returns none + log (do not file twice).
- Max attachment size: use existing inbox upload limits; do not invent a
  larger email-only cap.
- Strip executable extensions the inbox already rejects.

**Failing test:** `test_inbound_rejects_the_same_filenames_inbox_rejects`

**Commit:** `feat: inbound alias reuses inbox rejection rules`

---

## Exit gate

- [ ] Alias match is `basis=alias` at 1.00
- [ ] Unset secret → 404
- [ ] Attachment path is Stage 16 adapter (no PDF parser in the webhook)
- [ ] Stage 16 equivalence still green
- [ ] No outbound send from the alias
- [ ] Backend failures ⊆ baseline
- [ ] Ops note in `TRACKER.md`: MX/DNS is out of band

**After this stage:** the numbered programme is done. Stage E remains a
card until accuracy measurements exist. Cleanup milestone in the product
spec §15 is a separate, later packet — do not delete `app/assistant/` here.
