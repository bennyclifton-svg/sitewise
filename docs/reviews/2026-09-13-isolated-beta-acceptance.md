# Isolated beta acceptance — 13 September 2026

**Verdict: NO-GO for customer beta.** Several reproduced blockers are fixed and locally retested, and a reusable isolated environment now exists. The remaining financial, delivered-export and recovery acceptance gaps are material. This is not a claim that every requested blocker has been closed. Production was not changed during this pass.

## Candidate and isolation

- Base commit: `7d13c13dd655f39f166cd0a4bb25695bebbb0d0f`, branch `main`, origin `bennyclifton-svg/sitewise`. Tests used the dirty working tree, including earlier launch/architecture fixes. No release commit was created. Unrelated landing/terrace changes were preserved. A private file-hash manifest accompanies this run under `.tmp/beta-acceptance/`.
- Pinned Python 3.12.12, uv 0.11.25, Node 22.20.0, pnpm 11.5.2; frozen backend dependencies and installed frontend lockfile dependencies. Current repository instructions were read; newer canonical plans referenced by AGENTS.md are absent from this checkout.
- WSL Ubuntu Docker environment, Supabase CLI 2.117.0, separate Postgres/storage/auth and test-environment marker. Local Postgres is **17**, while the existing CI target is 16: matching the release database remains a gate.
- Frontend production Vite build at `http://127.0.0.1:5179`; API `127.0.0.1:8019`; Supabase `127.0.0.1:55321`, database `127.0.0.1:55322`. Services use the dedicated `clerk-acceptance-local` network with loopback host bindings. Real local Supabase sign-in, no authentication bypass.
- API image `sitewise-acceptance:7d13c13-dirty`, read-only mounts of current backend code, CPU limit 2/memory 2 GB. Separate OCR container CPU 2/memory 3 GB. Worker concurrency remains 1. These limits are configuration, not measured capacity.
- Only model credentials were carried into the private local environment. Email is fake, billing disabled, email domain `acceptance.invalid`; no production database/storage, Stripe or email-provider credentials were used. Model calls and platform embeddings used the configured external model service.
- The original first-stage scan was uploaded through the browser into a newly created local project. No answer key, private extracted text or future-stage evidence was uploaded. Reports contain no source-document extracts or confidential screenshots.

## Reproduced defects and changes

| Finding | Severity / reproduction | Implemented and verification |
|---|---|---|
| Unknown budgets became confirmed-looking zero totals/variances in API and workbook | High: generate an unpriced plan; inspect totals and formulas | Nullable totals propagate through backend, optimistic frontend calculations, Markdown and workbook previews. Dependent Excel formulas display TBC unless all necessary budgets are numeric. Explicit zero remains numeric. Red tests reproduced the problem; regression tests and real LibreOffice recalculation passed. Local generated grid visibly shows TBC. |
| Empty scanned PDF could finish as unchanged/unclassified evidence | High: PDF extraction returns only markers/no readable text | Empty PDF extraction now fails explicitly; persisted status reaches the document list. Browser showed a durable retry instruction after reload. The original 18-page scan subsequently succeeded with isolated Tesseract OCR. |
| Failed intake could not be retried after project inputs changed | High: re-upload failed file after project/profile changes; HTTP 500 `WorkflowRunConflict` | Terminal attempts receive a new retry idempotency key. Active same-hash work returns its existing run instead of re-executing. Browser retry proceeded without that conflict; failure and active-run unit cases pass. |
| Re-upload after automatic filing created another source row | Medium: upload original filename after intake moved it | Project/name/hash lookup reuses completed evidence, with a project lock around duplicate checking and storage. Actual browser re-upload left one ingested source and no additional intake run. Explicit folder uploads and changed content retain their existing behavior. |
| Failed processing was hidden behind an unclassified badge; progress claimed completion too early | Medium: OCR fails or continues after upload request | API exposes ingest status; repository shows failure/retry, waiting and reading states. Progress copy distinguishes upload completion from processing. Failure state browser-tested; final waiting/progress changes regression-tested and production build passed. |
| Fresh isolated migration appeared successful but rolled back | High operational blocker: create marked empty database and migrate | Commit the marker-check transaction before Alembic begins its migration transaction. Existing fresh-database integration test reproduced missing migration state, then passed. Database-runner test now checks the actual validated lease rather than a target changed after fixture setup. |

Principal changed areas: `backend/app/inbox/service.py`, `app/database/workspace_files.py`, `app/workflows/runs.py`, `ingest/extract.py`, `alembic/env.py`, cost-plan calculations/schemas/renderers/workbook, project evidence schema/API, and frontend cost-plan/document/progress components. Earlier model-selection, PDF fallback and programme-assumption fixes remain in the candidate. No runtime application dependency or alternate agent runtime was introduced.

The upload lock now covers storage as well as duplicate detection. This favors correctness; upload throughput under simultaneous batches remains unmeasured. No concurrency increase was made.

## Browser acceptance matrix

| Scenario | Result in this isolated pass |
|---|---|
| Local sign-in, create isolated project, save profile, navigate panels | Passed |
| Original scanned consent upload and classification | Passed after OCR environment repair; one source, 18 distinct page headings, 41,934 extracted characters. Spot checks found expected condition terms. This does not establish perfect OCR or legal interpretation. |
| Failed intake visible after reload; re-upload retry | Passed |
| Duplicate original upload after automatic filing | Passed; database inspection corroborated one ingested source and no new intake run |
| Fast/Thorough factual questions with unreadable evidence | Both correctly stated unknown budget and no supported appointments/invoices; no writes requested or observed |
| Cost-plan generation with platform guidance | First failed truthfully when mandatory platform seeds were missing; UI retry succeeded after environment seeding, creating revision 1 |
| Unknown costs in generated grid | TBC visible |
| Excel download through menu | **Unverified**: no download event within 10 seconds and no new workbook in the ordinary Downloads directory. This alone does not prove an application defect. |
| Network interruption / API restart | Transient connection failure visible; subsequent reload recovered. Full in-flight save/stream interruption not exercised |
| PMP manual/AI edit/regeneration preservation | Previous online report contains a pass; **not rerun against this local candidate** |
| Appointments, invoice allocation, variations, tender revisions, financial reconciliation | **Not executed** in this pass; later evidence withheld to preserve chronology |
| Citation source/revision accuracy after successful OCR | **Not completed**; extraction spot checks are not citation acceptance |
| Concurrent edits, worker restart during financial work, provider timeout/rate-limit, queue cancellation | Unit coverage exists in selected suites; **end-to-end browser scenarios incomplete** |
| Incoming signed email and draft-versus-delivered behavior | Local regression checks only; no outgoing email or real recipient action |

## Measurements and limits

Actual chat models were checked in local `agent_turns`, not inferred from task-routing telemetry. Identical read-only financial-evidence questions were sent in fresh conversations against the same unreadable evidence state:

| Operation | Samples | Observed duration |
|---|---:|---|
| Fast, `gpt-5.6-luna` | 1 | Server turn 12.310 s; first text 10.719 s |
| Thorough, `gpt-5.6-sol` | 1 | Server turn 14.104 s; first text 11.990 s |
| Successful 18-page OCR intake | 1 | Workflow 162.017 s |
| Successful cost-plan workflow | 1 | 1.560 s total; retrieval 251 ms, generation stage 79 ms, draft save 64 ms, workbook export 1,131 ms |

For each n=1 measurement the median/range is the single observation; no p95 or comparative speed claim is justified. Fast ran before Thorough, so cache states were not controlled. Both answers were appropriately cautious; this small failed-evidence test does not compare substantive document reasoning quality. The cost-plan generation-stage duration is not proof of an LLM call or dedicated-model latency. Local dedicated configuration is PMP Terra and cost-plan Luna; selected chat models do not override those workflows.

Automation observation time is excluded. One file-chooser call stalled for approximately 37 minutes before application request processing; it is not counted as application latency. No valid before/after benchmark, 100 ms edit-feedback result, 200 ms cached-navigation result, browser long-task/request/bytes profile, resource-use sample or 1/2/4-workflow capacity result was obtained. Do not infer production capacity.

## Executed checks

- Final backend selection: **81 passed**, 15.48 s: typed cost plan, workbook, empty extraction, uploads, evidence API and workflow runs.
- Earlier intake selection: **20 passed**. Earlier relevant backend selection: **41 passed**. These overlap the final selection and must not be summed as unique coverage.
- Fresh marked-database integration selection: **2 passed**, 3,129 deselected. Full database suite was not run.
- Boundary selection: **362 passed, 4 skipped**, 253.24 s, covering billing, Mailgun inbound/provider, agent and MCP bridge. Passing tests are not a security assessment or proof of cross-account isolation in production.
- Frontend cost/model/programme selection: **105 passed**. Final document/progress selection: **44 passed** across two files. Earlier 40-test document result is superseded.
- Final targeted Ruff and ESLint passed; TypeScript build and production Vite build passed (1.96 s Vite build). Existing large-chunk warning remains.
- Two synthetic workbooks recalculated through LibreOffice: known budgets remain numeric; unknown budget, variance and remaining/grand totals remain TBC; no Excel error cells; sheet names and merged-heading ranges preserved.
- Visual print inspection found summary columns split over pages and cramped category labels in LibreOffice PDF output. Formula changes did not alter page setup, but a matched baseline render was not made: treat this as an unresolved print/export presentation issue, not a proven new regression. Application PDF export follows a different path.
- Full-suite pre-existing failures remain in the earlier launch/architecture reports; this pass does not claim a clean full suite. The existing anyio pytest rewrite warning remains. One mistyped test filename ran no tests; the corrected selection is the 81-pass result above.

Private logs, synthetic workbooks and setup scripts are under `.tmp/beta-acceptance/`; they are not committed fixtures. Deliberate failing regression tests preceded the fixes. OCR setup failures and test-invocation errors are separate from application regressions.

## Environment interventions and reproduction

Docker tooling was installed from Ubuntu repositories in the existing WSL distribution. The repository backend image was built using a small curated context excluding secrets and private corpus files. Local Supabase was initialized separately, the database marked for tests, migrations applied and a local auth user/private storage bucket created directly. These are environment preparation, not successful UI workflows.

The bundled hybrid OCR defaults lacked EasyOCR; RapidOCR also lacked its runtime. The isolated OCR image adds Tesseract and `libgl1`, selects the Tesseract engine, and uses a named writable model cache. An initial cache ownership error and missing native library were repaired directly. Successful browser extraction used that repaired container. The final Dockerfile includes the native-library repair and rebuild succeeded; repeat extraction from a newly created final-image container remains a reproducibility check before release.

Platform guidance was dry-run inventoried and then ingested via `python -m ingest platform --execute`: **50 persisted, zero failed**. It remains separate platform-scoped reference knowledge, not project evidence. Missing guidance caused the first cost generation failure; seeding was not hidden as a UI success.

Private restart/build material: `prepare.py`, `migrate.py`, `seed_local.py`, `start-app.sh`, `ocr.Dockerfile`, and frontend local configuration in `.tmp/beta-acceptance/`. These contain or reference local credentials; do not commit or copy them to production. Reuse existing named containers/volumes rather than re-running creation blindly. WSL required a keepalive session during testing. Local services and private evidence are retained for continuation; no volumes were purged.

## Practical release conditions

1. **Engineering:** freeze an attributable candidate commit excluding unrelated work; run the selected-commit migration/image/smoke gate against the intended Postgres version. Prove OCR and required platform guidance from a clean environment, not a repaired running container.
2. **Engineering acceptance:** complete the chronological financial oracle and browser scenarios for proposal versus appointment, commitments versus invoices/variations, allocations, retries and edit preservation. No production financial operations are needed.
3. **Engineering acceptance:** capture actual downloaded Excel/Word/PDF files; reconcile formulas, invoice links and presentation against source values and intended formatting. Resolve the print presentation concern or explicitly define supported output behavior.
4. **Engineering acceptance:** finish provider timeout/rate-limit, interruption, queued cancellation, concurrent edits and worker-restart recovery; verify ownership/download boundaries with distinct local users. Record any direct repair separately.
5. **Release operator, only after those pass:** separately authorize deployment of that exact candidate with rollback readiness, then run narrow live acceptance. No deployment was attempted here.

Further broad refactoring is not justified by this pass. The useful changes were bounded corrections to authoritative state, retry identity and truthful presentation. The next work is closing the above acceptance gaps, not rewriting the product.

Automatic approval review rejected a full local-log capture because it could retain confidential content; filtered diagnostics were used instead. Platform embedding execution was initially rejected, then approved after a dry-run inventory and the repository's explicit platform-ingestion authorization established scope. No review rejection was bypassed, and no approval request remains pending.
