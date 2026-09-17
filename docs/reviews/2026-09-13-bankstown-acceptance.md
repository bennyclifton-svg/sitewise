# Bankstown acceptance testing — 13 September 2026

**Launch verdict: blocked.** Real browser testing found model-routing, scanned-evidence and unknown-budget defects. Several editing and recovery paths worked, but financial reconciliation, complete source chronology, exports and operational recovery are not established. This is not a security certification or a production-capacity test.

## Tested environment and attribution

- Browser: authenticated Codex in-app browser at `https://sitewise.au`.
- The product owner explicitly authorized the online environment and a new test project, then authorized continuing without further questions. Project: `Acceptance Only — Bankstown — 2026-09-13`, ID `2b77138a-3d04-455c-95f9-3c5a442a6e56`.
- This is a logically isolated project in the online service, **not a separate database or storage environment**. Existing projects were not opened or modified. No database repair, direct database access, deployment, real payments or external correspondence was performed.
- Local candidate: `main`, `7d13c13dd655f39f166cd0a4bb25695bebbb0d0f`, plus existing uncommitted launch/architecture changes and unrelated work. All were preserved. **The deployed commit remains unknown**: browser health navigation was blocked. Local fixes are not claimed to be running online.
- New acceptance changes: model preference/request handling in `frontend/src/lib/agent-model.ts` and `ChatPanel.tsx`, model regression tests in `ChatComposer.test.tsx` and `ChatPanel.test.tsx`; PDF marker parsing and tests in `backend/app/document_intake/odl_pdf.py` and `backend/tests/document_intake/test_odl_pdf.py`; assumption disclosure and tests in `ProgramGantt.tsx`/`.test.tsx`; nullable budget display/rollups and tests in `CostPlanGrid.tsx`/`.test.tsx` and `frontend/src/lib/cost-plan.ts`/`.test.ts`. Earlier cancellation changes in ChatPanel remain separately attributable to the architecture review. No commit was made.

## Source preparation and chronological boundary

The supplied delivery package contains 195 substantive files (179 PDF, two legacy Word, one DOCX, 13 JPEG), 240,567,333 bytes, and 1,376 PDF pages. Another 195 AppleDouble companion files were excluded. No byte-identical substantive duplicates were found; different-format copies and revisions still exist.

Local extraction identified 231 pages with fewer than 50 text characters. Those pages were rendered and processed using Windows OCR locally, without another cloud service. Inventory, hashes, extracted content, OCR images, financial/date candidates and answer keys remain Git-ignored under `.tmp/acceptance-bankstown/private/`; they were not uploaded or committed. Reports omit source parties, addresses and monetary amounts.

Only the verified earliest planning consent, private ID **D008**, was admitted to the application, followed by an identical retry. It is dated 31 December 2014 and expressly requires deferred-commencement conditions to be satisfied before operation; a construction certificate is required before works. The private stage-one oracle records the relevant pages and treats adopted budget, appointments and invoices as **unknown, not zero**. Consent fees are not an adopted project budget or proof of payment.

Later requirements and contract documents were held back. The requirements document has a July-to-October 2015 revision history. A contract PDF contains a filled sum and an included provisional allowance, while its Word counterpart leaves the sum blank; execution/authority and precedence remain unverified. Neither was treated as an appointment or uploaded ahead of its stage. Filename screening found no clearly named invoice/proposal/appointment/tender-return files; this is not proof of their absence. **The complete financial and revision answer key remains unfinished.** No financial totals have been invented.

## Acceptance matrix

| Scenario | Actual result |
|---|---|
| Sign-in and new project | Passed online using existing signed-in session; isolated acceptance project created |
| Missing context / unknown amounts | PMP initially gated on missing class/work type; both baseline answers said budget, commitments and invoices unknown, not zero |
| Stage 1 upload and retrieval | Stored online; failed substantive scan extraction. Document viewer showed only 18 page markers. Answer honestly disclosed it could not read the conditions |
| Duplicate upload | Executed. Original classified record plus another filename row remained visible after completion; one planning correspondence item remained. Canonical/DB deduplication is unverified |
| Profile edit and save | Mixed use/new build saved and survived reload; later residential + retail subclass saved. These facts were entered manually from the source, not extracted by SiteWise. Budget left blank |
| PMP creation | Completed online as draft v1; missing facts/budget labelled assumptions. This is a workflow pass, not a source-grounding pass |
| Inline PMP edit / add row | Edited address wording and added a marked test row; edit survived reload |
| Targeted AI edit | Changed only the requested wording; added row remained visible; draft v4 |
| PMP Update / regeneration | Completed as v5; marked edit and added row survived. Added row exposed a refresh-conflict action, rather than silently disappearing |
| Delete test row | Disposable added row deleted through UI; draft advanced to v6. Final reload confirmed the row absent and the marked manual edit retained. Existing source records were not deleted |
| Programme | Panel usable, but seeded dated stages were not visibly labelled assumptions; local fix added disclosure |
| Cancel / retry | Cost-plan chat cancellation returned “Turn interrupted”; no plan was visible immediately afterwards; normal UI retry completed as one visible cost-plan v1; backend exactly-once accounting unverified |
| Cost-plan unknowns / invoice ledger | Failed: grid showed zero budgets despite unknown-budget context. Invoice tab correctly showed no invoices in the register. No financial records were fabricated |
| Word / Excel export | Both attempted through actual download menus. No Word event in 20 seconds or Excel event in 15 seconds. No matching recent Word download or browser error found. File contents, formulas and formatting unverified |
| Incoming email / Pulse | Upload produced a planning item under Correspondence. This does not validate actual inbound-email signatures, attachment handling or approvals. No email was sent |
| Stages 3–6, proposals/appointments/invoices/variations | Not executed: source authority/chronology and complete financial oracle not established; earlier scan failure remains open |
| Fast vs Thorough | Attempted identical clean-chat baseline questions; **invalid as a model comparison** because effective model identity and selection were unreliable |
| Concurrent edits, provider timeout/429, worker restart, network outage | Not fault-injected in the shared online service. Requires isolated environment; ordinary reload and navigation were exercised |
| Cross-project ownership / billing boundaries | No adversarial live test against working projects or real billing. Earlier local boundary checks do not establish live security |

## Confirmed defects and changes

**A01 — High: model selection and actual request diverge.** Select Thorough: neither tier appears selected. Following a tier change, a live request failed with `Unsupported Pi model 'xai:grok-4.6'`; the error listed Luna, Sol and Terra as allowed. Refresh with Fast selected recovered the read-only query. Code inspection and failing regressions identified two defects: the browser silently rewrote Sol to a different provider, and the transport captured an earlier selection. Implemented locally: retain the configured ID and read the preference at request time. Tests cover both advertised Thorough IDs, changing an existing transport's selection, and returning to the server default. This replaces the initial cosmetic-only hypothesis. No live fixed rerun is claimed.

**A02 — High: unreadable scanned evidence reported as ingested.** Upload D008, then open its Markdown view or ask for consent conditions. Expected: readable conditions or a clear extraction failure. Actual: completion message, “Current” document, page markers only. Locally reproduced the parser treating marker-only output as substantive text and preventing valid JSON fallback. Fixed that parser condition; two new tests failed before and pass after. **OCR availability, persistent unreadable-document warning, reprocessing the live file and end-to-end extraction remain unresolved.** The parser fix alone does not make scans readable.

**A03 — Medium: default programme looks established.** Open Program without programme evidence: Planning 90 days, Procurement 60, Delivery 365 appear with dates beginning on the test date. Code confirms `seed.py` explicitly marks these `assumption=True`; the Gantt ignored the field. Implemented a visible assumption count in both editing and embedded figure views. Tests verify disclosure and its absence when no activities are assumptions. Dates, arithmetic and document export formatting were not changed. Not deployed.

**A04 — High: unknown budget becomes confirmed-looking zero.** Generate a cost plan with no adopted budget. Chat explicitly says figures should remain TBC, but the grid renders budgets and their derived totals as `0.00`. Code reproduces the display failure independently: nullable budget is passed as an empty string to MoneyInput, which converts it to zero; line rollups do likewise. Two new regressions failed before the fix. Implemented locally: blank/TBC for unknown budget; null propagation through budget, variance and remaining rollups/subtotals; an explicit zero still persists; clearing a budget stores null; new rows begin unpriced. Tests cover unknown totals, explicit zero, unchanged blank and clearing. **This does not retroactively recover data already stored as zero, prove the live request payload was null, or fix server/export arithmetic.** Backend totals still sum unpriced rows as zero; customer-facing API/export treatment and appointment/commitment authority remain release gates. No arithmetic or known financial amount was changed online.

**Open observations:** duplicate-upload residue; weak background-work visibility after the queue acknowledgement; unobserved Word/Excel downloads. These require diagnosis, not invented root causes. No infrastructure or security changes were made to work around them.

## Measurements and limitations

These are automation-assisted observation bounds, including browser-tool overhead and gaps while inspecting code. They are not instrumented server timings or device-render latency. Each generation/operation below has **n=1**; no meaningful p95 or model-speed ranking is claimed.

| Operation | Observation |
|---|---|
| Empty-evidence baseline 1 | Running at 16.9 s; complete by 43.1 s |
| Empty-evidence baseline 2 | Complete by 34.0 s; actual model unverified |
| Planning query after refresh | Running at 13.5 s; complete by 41.2 s |
| Profile save | Saving visible by 0.38 s; Saved by 9.94 s |
| PMP creation | No saved draft at 70.3 s; available by 118.3 s |
| Targeted AI edit | Updated draft visible by 15.6 s |
| PMP Update | Updated v5 visible by 92.6 s |
| Repeated panel navigation during work | n=3, median 3.307 s, range 3.304–3.456 s, dominated by automation observation; not browser latency |
| Cancel request | Click operation returned in 0.80 s; interrupted state visible in the same observation |
| Cost-plan retry | Queued at 28.4 s; generated artefact visible by 85.5 s |
| Word / Excel export | Download events not observed within 20 s / 15 s |

The edit fill/blur calls returned quickly, but the subsequent visual observation adds tool latency; this does not establish the 100 ms target. No 200 ms cached-content claim is made. Queue/retrieval/model/validation/save/export components, transferred bytes, request counts, browser long tasks, CPU/database utilization and 1/2/4-user capacity were not instrumented. No before/after live performance comparison is possible without deploying the candidate under matching conditions.

## Executed local checks

Pinned Python 3.12.12/uv 0.11.25 and Node 22.20.0/pnpm 11.5.2 were used with installed locked dependencies; no new dependency was added.

- Model tests: reproduced three failures before the final fix; related composer/panel/selector checks pass.
- PDF tests: reproduced two marker/fallback failures before the fix; document-intake, PDF extraction, evidence-safety and upload selection: **28 passed**. Existing pytest anyio rewrite warning remains.
- Frontend model/Gantt selection: **73 passed**; cost-grid, calculations and invoice UI selection: **40 passed** across four additional files (**113 total**).
- Backend typed cost-plan, operations, evidence reconciliation and workbook selection: **28 passed**, additional to the 28 PDF/intake/upload tests (**56 total**).
- TypeScript build, targeted ESLint, targeted Ruff, production Vite build and scoped whitespace check passed. Vite's existing large-chunk warning remains.
- Earlier baseline results and pre-existing unrelated failures remain documented in the launch/architecture reports. This acceptance pass did not rerun or claim a clean full suite.

## Release conditions

1. Select and identify an exact release commit; run the existing release gate and deploy only through a separately authorized release process. Re-run A01–A04 in the deployed browser.
2. Make scanned evidence readable or explicitly unavailable throughout intake, retrieval and generation; re-run the untouched original consent. Do not replace it silently with the private answer key or derived OCR text.
3. Establish a separate acceptance database/storage and test billing/email channels for timeout, rate-limit, restart, concurrency, authorization and idempotency tests.
4. Finish source chronology, execution/revision authority and the financial oracle; then run appointments, invoice allocations, variations and workbook formula/formatting reconciliation. Missing source coverage must remain explicit. Unknown budgets must remain distinguishable in API totals and exported workbooks, as well as the grid.
5. Verify actual downloads and inspect the delivered files; investigate duplicate-upload residue and background progress/cancellation after a workflow is queued.

Implemented means local code changed. Tested locally means isolated regression/build checks passed. Verified online means the listed browser outcome was observed on the existing service. None of these means the local candidate was deployed or production capacity/security was established.


Tooling limitations: the first chooser attempt timed out; Upload files worked. Automatic approval review blocked one stale-index correspondence click; fresh DOM inspection established the read-only target and navigation succeeded. No permissions were weakened. An invocation using nonexistent test filenames ran no tests; the corrected discovered selection is counted above. Initial new-test TypeScript option/import errors were corrected before the final passing check. Tooling failures and deliberate red tests are not counted as product regressions.
