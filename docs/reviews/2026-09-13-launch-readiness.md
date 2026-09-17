# SiteWise first-customer launch review — 13 September 2026

**Decision: not yet cleared for customer launch.** Fixes are implemented locally;
production has not been changed. Passing unit tests is not a security certification.

## Scope and attribution

Reviewed `main` at `7d13c13dd655f39f166cd0a4bb25695bebbb0d0f`, the same commit as
the previous review; origin is `bennyclifton-svg/sitewise`. Changes remain
uncommitted. Existing Landing/terrace/frontend work was excluded from the fixes.
The normal `pnpm build` prebuild regenerated the already-dirty coordination
viewer and colour exports; no frontend source was hand-edited for this review.
Other work continued in the shared tree, so do not stage everything together.

Read root/backend/frontend AGENTS.md. Referenced architecture, Pi-only plan,
TCM PRD, CONTEXT.md and docs/agents/domain.md are absent in this checkout.
Used current code and DEPLOYMENT.md; did not restore Hermes or remove legacy chat.

## Confirmed findings and implemented changes

| Area | Finding and change | Verification |
| --- | --- | --- |
| Email | Mailgun existed but Settings rejected it. Accept Mailgun, require its key/domain, reject fake email at production startup and provider selection. Production Compose/example now default to production/Mailgun. | Reproduced before fix; local config/provider tests pass, including provider rejection. Real delivery unverified. |
| Queued chat | Registration followed semaphore acquisition. Register first; wait at most 30 seconds by default; reject duplicate threads immediately; clean up without leaking capacity. | Cancellation by turn/thread, timeout and duplicate tests pass. |
| Execution/retries | Reused message IDs could execute again. Return 409 for an existing message; serialize durable start with cancellation. Profile writes and title generation wait for admission. Queued failures persist a visible terminal message and release quota via `not_started`; started attempts remain chargeable. Token lifetime includes queue allowance. | API failure-path and durable claim tests pass. Real PostgreSQL concurrency still needs staging verification. |
| Web delivery | Live hashed JS was uncompressed and had no explicit cache policy. Add gzip/static types, immutable hashed assets, revalidation for HTML/unhashed files, and 404 for missing chunks. API compression stays off and proxy buffering stays off. Candidate web images can retain previous hashed assets. | Live defect verified; configuration tested locally. New nginx behaviour has not run locally or live. Docker smoke added. |
| Releases | Routine path was blocked; DB smoke was manual-only. CI now requires automatic disposable DB smoke before image gate, builds the selected SHA and records image IDs. Compose uses SHA tags; health reports BUILD_SHA. Updated release procedure covers migrations, promotion without rebuild and rollback. | Local configuration/runner tests pass. CI execution, branch protection and rollout remain operator gates. |
| Models | Compose advertised Balanced/Complex instead of app Fast/Thorough and omitted xAI key forwarding. Align app/example/Compose defaults, including legacy model defaults. | Contract and Pi model tests pass. Saved deployment overrides and actual provider availability unverified. |
| Additional boundaries | Pi inherited database, billing and service-role secrets: replaced blanket environment inheritance with OS paths plus explicit model/turn credentials. Replayed checkout could reactivate cancelled billing: synchronize current Stripe subscription under a DB lock. Unknown Stripe prices no longer grant access. | All three defects reproduced before fixing; local regressions pass. No real Stripe operation or charge. |

Fast is `openai:gpt-5.6-luna`; Thorough is `xai:grok-4.6`. Exact create/update PMP
commands queue application workflows and bypass the chat selector. With no
explicit chat selection, task routing may choose Luna/Sol/Terra. Workflow,
tender extraction/adjudication, embeddings and title calls have independent
models. Details and operator commands: [release procedure](../releases/launch-release.md).

Stripe synchronization follows its documented lack of webhook delivery ordering:
[Stripe webhook guidance](https://docs.stripe.com/webhooks). An accepted Mailgun
request is not proof that a recipient received the email.

## Executed checks

Used Python 3.12.12, uv 0.11.25 with `uv run --frozen`, Node 22.20.0 and pnpm
11.5.2. Existing frontend packages matched lockfile versions (Vite 8.0.16,
TypeScript 6.0.3). No dependencies/lockfiles changed. Backend network containment
was enabled; no production database was used.

| Check | Result |
| --- | --- |
| Backend Ruff (`app ingest tender tests`) | Pass, before and after changes. |
| Initial complete offline pytest attempt | Missing acceptance corpus failures, then Windows process-tree hang; interrupted. |
| Broad final offline run, excluding acceptance and process-tree modules | 3,041 passed, 9 pre-existing failures, 2 skipped, 34 deselected. |
| Final targeted agent/billing/email/inbox/token/config/containment/runner suite | 350 passed, 1 skipped, 1 deselected. |
| Deferred profile-update/API tests | 41 passed. |
| Original-commit reproduction of remaining backend failures | 9 failed, 29 passed in isolated Git archive. Same nine failures as working code. |
| Frontend baseline typecheck / lint | Both pass. |
| Frontend baseline tests | 862 passed, 5 failed across 3 files before frontend build. |
| Frontend production build and bundle budget | Pass. |
| Tender seed validator | Pass: 181 cells, 70 rules, 2,580 synonyms, 188 benchmarks, 6 golden documents. |
| Migration graph tests / Alembic heads | 6 passed, 2 integration tests deselected; one head, `063_prompt_library`. No migration executed. |
| Docker web smoke script | Python syntax/Ruff pass only; Docker unavailable. |
| Authored diff whitespace check | Pass. |

Existing backend failures: four greenfield/PMP scaffold checks, one scope-label
expectation, one minimal-PMP lifecycle check, a tender classification expected
payload mismatch, and two missing PDF/evaluation fixture/tool failures. Missing
`docs/acceptance/agent-prompt-scenarios.yaml` also blocks the complete acceptance
suite. The process-tree hang was localized to Windows subprocess waiting; Linux
CI must verify real process cleanup. Frontend failures were a procurement fixture
assertion plus four timing failures in landing controls/ProjectControlBoard.
These are not silently waived release checks.

An intermediate regression in the Windows child-environment containment test
was corrected with nonempty dummy sentinels; the final targeted suite passes.
The initial uv cache permission failure was resolved with repository `.uv-cache`;
pytest cache ACL warnings remain nonfatal.

## Boundary review and remaining gates

Project ownership is checked before upload/download; workspace lookup is scoped
by project ID. Added cross-owner/cross-project download tests; existing upload,
path traversal and MCP wrong-project token tests pass. Stripe verifies raw-body
signatures; actual SDK tampering/expiry tests pass. Inbound email uses HMAC or
timestamped Mailgun signatures. Email sending uses a locked draft state and does
not automatically resend an ambiguous failed send. Chat retries do not repeat
execution. These findings do not verify live Supabase RLS/storage policies,
network exposure, credential validity or provider behaviour.

Live observation only: on 12 September 2026 at 22:49 UTC,
`/assets/index-7P-U5A1s.js` returned 200, 451,227 bytes, nginx/1.27.5, without
Content-Encoding, Cache-Control or Vary despite `Accept-Encoding: gzip`.
Public HTML also had no explicit cache policy. No fix is marked verified live.

Before onboarding: resolve the baseline failures/missing corpus; run the required
CI and Docker database/image/stream smoke for a clean selected commit; configure
required checks; reconcile persistent production email/model/billing settings;
verify two-account access, cancellation/quota, paid/read-only transitions,
provider test-mode retries and old-tab asset loading in staging. Review pending
migrations against the actual deployed revision, secure a recoverable backup,
then obtain rollout approval. After rollout verify the reported SHA and public
headers. Keep legacy chat until the documented live acceptance gate passes.

Authored scope: `.dockerignore`, CI, DEPLOYMENT.md, agent concurrency/process,
chat API, billing usage/webhooks/entitlements, config, email provider factory,
turn tokens, health, their tests, deploy files, database runner, new Docker smoke
script and these review/release documents. Local logs and an authored-file
manifest are retained under `.tmp/launch-review/`; they are not staged for release.
