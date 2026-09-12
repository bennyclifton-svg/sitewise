# Seven Hills local lifecycle benchmark

## Run state

**Follow-up:** The cost evidence repair is implemented and verified locally. Cost Plan v2 is saved with all ten QS elements and source links; v1 remains preserved. Programme v2 now contains the seven source milestones. See the follow-up results below. Later lifecycle acceptance remains outstanding.

**Subsequent performance pass:** Cost Plan v3 reproduces v2's values and sources using the optimized workbook save/export path. Versions 1–3 and their workbook exports were verified. See `2026-09-09-performance-workbook-results.md` for controlled before/after measurements and validation.

Acquisition intake, cost-plan creation and consultant-RFP creation have run. All 14 recorded workflow runs are complete. This is a partial lifecycle baseline, not completed acceptance or a measured before/after improvement.

- Isolated project: Seven Hills Performance Benchmark 2026-09-09.
- Project ID: `443b7212-5322-4755-9062-1ac3b0a65c64`.
- Frontend: production-build preview at `http://127.0.0.1:4173`.
- Backend: `http://localhost:8000`, remote Supabase services, development workflow queue.
- Existing Seven Hills demonstration was not modified. No outbound correspondence was sent.

## Environment recovery

The initially empty local PI_MCP_ADAPTER_PATH now points to the installed adapter version 2.19.0, matching the deployment Dockerfile. Allowed origins now include the production preview. After the user's restart, the health endpoint returned the matching CORS origin and Pi successfully searched project evidence. It distinguished the $9.8 million client construction budget from the $10.07 million QS forecast. Recovery is verified; no further restart is pending.

## Completed

1. Corpus validation passed: 140 ingestible evidence documents, 52 current drawings, 13 reports, 25 consultant invoices and three builder tenders. Control answer keys and future-stage evidence remain outside the baseline.
2. Created the isolated residential/new/townhouses project: NSW, 3,240 square metres, initial 12-dwelling acquisition case.
3. Uploaded client brief, pre-DA meeting record and feasibility cost/programme advice. Four acquisition attachments entered through canonical fake-provider email import/link/intake. Seven source documents are available. Two retried attachment rows show skipped, although their content was found through search.
4. Ran profile setup. Pi applied supported profile updates despite being asked to propose them for review. This is a review-flow correctness finding.
5. Created cost plan v1, draft `21ceb5e7-424f-48c4-b602-e956b26b2525`, and generated Cost_Plan_v01.draft.xlsx. Inspected its grid and Trace & QA.
6. Opened Program. It still contains default stages; corpus milestones have not been applied or validated.
7. Created five unique v1 RFP drafts: architecture, town planning, structural, civil/stormwater and building services. Six workflow runs were issued because town planning ran twice; both chat links identify the same town-planner draft. Verified that the civil RFP opens in the document view. Detailed content acceptance and downloads remain outstanding.

## Persisted workflow timings

These are single samples from durable workflow timestamps, excluding chat preparation before workflow creation and browser orchestration. They do not establish typical latency or percentiles.

| Workflow | Created to started | Started to completed | Total |
| --- | ---: | ---: | ---: |
| Cost plan | 6.5 s | 34.8 s | 41.3 s |
| Architectural RFP | 7.8 s | 68.1 s | 75.9 s |
| Town-planning RFP | 13.2 s | 78.3 s | 91.4 s |
| Structural RFP | 32.8 s | 81.4 s | 114.2 s |
| Civil/stormwater RFP | 44.4 s | 96.2 s | 140.6 s |
| Building-services RFP | 77.5 s | 60.3 s | 137.8 s |
| Repeated town-planning run | 89.0 s | 25.0 s | 114.0 s |

All five unique RFPs completed about 3 minutes 44 seconds after the first workflow was created. Initial three document ingests took 16.5–28.6 seconds after starting. Two of four email-attachment ingests required a second attempt. A transient OperationalError was observed, but its cause was not retained in completed run records. Attachment staging preceded transaction commit, so their created-to-started durations are not pure queue waits.

Raw snapshot: `output/performance-review/lifecycle-status.json`. Read-only collector: `output/performance-review/benchmark_status.py`. Guarded handover fixture: `output/performance-review/seed_benchmark_handover.py`.

## Findings and recommended implementation

### Repair cost evidence before later cost updates

The grid totals $10,699,000 across generic allowances. It includes categories beyond construction and must not be compared directly with the $10.07 million construction forecast. The actionable issue is that the extractor reports owner_brief_on_file=false despite citing the client brief, and fails to extract the construction budget ceiling. Offline reproduction with the same documents returns False and None.

`backend/app/sitewise/cost_plan_evidence.py` identifies briefs through narrow wording such as “owner project brief” and “working budget ceiling”; the corpus uses “Client Development Brief”. The generated plan does not carry through supplied QS element allocations. The evidence-grounded trace therefore needs validation.

Next implementation: add a regression case with the acquisition documents, correct brief/budget recognition, and trace the QS allocation path. Verify numerical allocations and provenance before appointments, invoices and change reconciliation. Preserve this initial draft as baseline evidence.

### Investigate intake retries and multi-RFP delay

Capture step timings and retained retry reasons for storage, database operations, retrieval, model generation and artifact persistence. Investigate repeated town-planning dispatch and increasing queue delays before changing concurrency. These observations establish delays, not their root cause.

### Preserve profile review intent

Reproduce the request-to-propose flow and ensure review intent is preserved before profile mutation. This run affected only the disposable project, but immediate application contradicted the instruction.

## Remaining lifecycle and limits

Resume after the cost baseline repair: sourced programme, proposals, four appointments, planning revision/PMP, civil appointment, inline PMP edit, invoices, design/tender baseline, construction claims and reviewed changes. Keep correspondence as drafts.

No reliable browser render timings were captured. Earlier blank-view observations and slow file-chooser automation are not used as application latency measurements. This local production build uses remote services; these are not deployed production measurements. No application source changes, deployment or new full test-suite run occurred during this benchmark. Earlier phase reports describe their separate validation.

## Follow-up implementation and verification

Implemented after approval to proceed:

- Recognise a Client Development Brief and its construction-budget field. A budget on file no longer clears the separate brief-signoff gap unless a signed date is evidenced.
- Parse an explicit ex-GST Construction forecast table, reconcile its line amounts in Python, and preserve the source element labels and document references. Incomplete prices, missing GST basis, multiple forecasts and non-reconciling totals stop generation instead of falling back to generic allowances.
- Use those source rows in the typed compiler instead of the construction/PC scaffold. Preserve the client budget separately and calculate its difference from the source forecast. The source amounts remain proposed and uncommitted. This parser currently supports the explicit two-column forecast-table format; it is not a general PDF or free-text QS extractor.
- Add eight regression cases using the actual Seven Hills acquisition documents, including contradictory totals, missing prices, competing forecasts and exclusion of evidence carrying another project ID.

Validation: eight new cases, eight existing evidence tests and 62 related compiler/renderer/reconciliation tests passed (78 total); Ruff and diff whitespace checks passed. No new dependency or migration. No deployment or commit.

Live acceptance:

- New draft: `a486e996-bded-4538-8e59-b11bd4c1c6b2`, revision 2.
- Read-only database assertions verified ten construction elements totalling $10,070,000, all proposed, all uncommitted, with source document references. Revision 1 remains in history.
- UI shows the same construction total and the $350,000 OSD allowance with “scope not defined”. Other unevidenced fees remain null in storage; the current grid displays those as 0.00, which remains a presentation concern.
- The saved narrative distinguishes the $9,800,000 client budget and $270,000 forecast excess. These are construction figures, not a complete development budget.
- Excel download completed with HTTP 200 (about 2.2 seconds server request time). Workbook cell/layout acceptance was not performed.
- Evidence: `output/performance-review/cost-baseline-v2-verified.json`; reproducible scoped checker: `output/performance-review/verify_cost_baseline.py`.

The first regeneration attempt did not queue a job while the local auto-reloading backend was unresponsive. Health probes timed out. The verified local backend process tree was stopped and restarted without the file watcher. The subsequent retry succeeded. This establishes recovery, not the root cause of the reload stall. The backend is running in the agent terminal on port 8000; future code changes require a restart for that process.

The successful v2 run took 12.3 seconds before starting and 39.4 seconds after starting (51.7 seconds overall). Recorded stages: context 1.5 s, retrieval 5.7 s, generation including preview publication 8.5 s, draft save 7.9 s, workbook export 7.7 s. No speed improvement is claimed from this correctness repair. Draft persistence, preview publication and workbook export are concrete next profiling targets; avoid assuming all “generation” time is model computation.

The existing civil RFP preserves the OSD volume uncertainty, but its summary shows $8,830,000 as Budget, derived from the original cost allocation. Existing RFPs have not been regenerated. Budget-versus-forecast propagation needs verification before RFP content acceptance.

Programme baseline acceptance also passed: version 2 replaces the three default stages with a Baseline milestones stage. Database assertions verified all seven milestone dates from the acquisition advice (14 March 2025 through 30 April 2027), zero milestone durations, assumption=true, and no dependencies. Programme source notes are empty even though the chat response cites the advice; persistent source attribution remains a follow-up. Cost Plan v2 remains unchanged. Consultant proposals/appointments, PMP, invoices and later changes have not yet been exercised.

## Proposal intake and concurrency follow-up

The next staged lifecycle pass imported all 15 consultant proposals through the canonical fake-provider email attachment intake, scoped to the disposable benchmark project. No correspondence was sent. A read-only checkpoint confirms 22 source documents (seven acquisition documents plus 15 proposals), all 15 proposal ingestion runs complete, Cost Plan v3 unchanged, and no consultant commitments. The v3 workbook performance verification is recorded separately in `2026-09-09-performance-workbook-results.md`.

The first import attempt exposed a PostgreSQL deadlock (SQLSTATE 40P01). Concurrent transactions inserted project child records, acquiring foreign-key key-share locks, and then attempted to upgrade to exclusive project row locks. A two-transaction, rollback-only reproduction failed before the fix. Project mutation and event publication now request FOR NO KEY UPDATE: writers remain serialized while foreign-key references remain compatible. The same reproduction completed both transactions after the fix. This establishes the specific lock-upgrade repair; it does not establish that all possible application deadlocks are eliminated or identify the cause of earlier unretained OperationalErrors.

Validation: 71 targeted project-event, workflow, upload and email-attachment tests passed, including two new lock-mode regression cases; Ruff passed. The local backend was restarted with the fix and the remaining proposal batches completed. No migration, new dependency, commit or production deployment.

Evidence and repeatable harnesses:

- `output/performance-review/reproduce_intake_lock.py`, `intake-lock-before.json`, `intake-lock-after.json`: concurrent transaction reproduction; all probe writes rolled back.
- `output/performance-review/seed_lifecycle_stage.py`: idempotent, project-guarded intake staging.
- `output/performance-review/lifecycle_checkpoint.py`, `proposals-complete.json`: read-only persisted acceptance checkpoint.

Classification acceptance has not passed. The proposals retain document class `unknown`; inspected metadata also identifies the client as issuing firm and misses several disciplines, despite recognising the fee-proposal subtype. Sort Files consumes persisted classification and routes low-confidence documents to review, so it is not a remedy for the underlying extraction problem. Resolve and verify proposal classification and issuer attribution before comparing proposals and applying appointment letters. Initial appointments, planning/PMP revisions, invoices and subsequent lifecycle stages remain untested. The deadlock repair removes an observed failure and retry source; no percentage latency improvement is claimed from this pass.

### Classification repair and live acceptance

The subsequent regression loop reproduced all 15 failures through `ingest_plan`, using real Markdown extraction and chunking while replacing network embedding and persistence in the offline test. The pipeline classified filenames before extraction and never revisited the result with the available content. The filename's hyphenated `fee-proposal` did not match the class signal, although the separate subtype signal matched. Register metadata also ignored the explicit Proponent table row and fell back to the client's company name.

The pipeline now classifies extracted content before chunking/persistence, retaining explicit user overrides. Proposal headings supply the offered discipline ahead of incidental coordination references. Register metadata recognises labelled Proponent, Issuing firm and Prepared by fields. Existing machine-answer audit metadata remains preserved. Building services retains the general Services discipline with canonical subject `none`, because the taxonomy has no combined building-services category; it is not mislabelled as one specialist discipline.

Validation: 312 ingest, classification-override, MCP correction and intake-routing tests passed, including 15 corpus regressions and a user-override preservation case. Ruff and targeted diff whitespace checks passed. The local backend was restarted with the fix. All 15 existing proposals were re-ingested through hosted ingestion with unchanged source hashes and document IDs; persisted class and proponent assertions passed for every document. The refreshed browser register shows all 15 as Commercial and the four supported specialist categories correctly. Evidence: `output/performance-review/proposal-classification-verified.json`; guarded replay: `reingest_proposals.py`. No production changes or outgoing correspondence. This is a workflow correctness repair, not a measured latency improvement.

### Initial appointment acceptance and further findings

The in-app comparison used 43 tool activities but omitted Span Theory Engineers and counted Basinworks in both structural and civil sections. A corrective request identified the missing source; the comparison is not accepted as complete. No model/prompt change was made in this pass.

Four appointment letters then entered through canonical fake-email intake. The agent appointment run exposed incorrect allocations: Axis's fee was initially assigned to Structural and Flux's to Electrical, with the client appearing as supplier. The run was interrupted. The appointment extractor trusted inferred metadata ahead of the explicit letter heading and did not recognise appointment headings or the labelled Consultant table row. Four failing corpus cases reproduced the issue. The extractor now resolves explicit document fields before machine metadata, retains explicit caller overrides, and recognises the combined Building Services register label. This does not add a combined document-taxonomy category.

Repair also reproduced another PostgreSQL 40P01 lock upgrade in `write_shared_project_object`. That writer now uses FOR NO KEY UPDATE. A failing offline lock-options regression was added. The rollback-only concurrent reproduction failed before and completed both transactions after the fix. An initial after-run hit the probe's four-second lock timeout; the final run allowed 15 seconds for serialized remote database work. Evidence: `shared-lock-before.json` and `shared-lock-after.json`. The appointment, consultant-fact and project-lock test group passed all 25 tests; Ruff passed.

The mistaken electrical commitment was reversed and its row removed through versioned cost operations, its shared fact marked Not appointed, and the mistaken client candidate cleared from procurement. No historical revisions were deleted. Correct appointments were then applied through the domain service, using each letter without nominated fee overrides:

| Consultant | Discipline | Commitment ex GST | Cost revision |
| --- | --- | ---: | ---: |
| Axis Studio | Architect | $286,000 | 8 |
| Civic Pattern Planning | Town Planner | $48,000 | 9 |
| Northline Structures | Structural | $132,000 | 10 |
| Flux Services | Building Services | $158,000 | 11 |

Read-only assertions verify four commitments totalling $624,000, the correct suppliers and appointment-letter source references, and exactly those four Appointed shared facts. All ten construction rows retain their financial values and source references. Their cost codes and display order were renumbered by the existing mutation path; full object equality therefore did not pass, and is not claimed. Programme remains v2; no PMP or civil appointment exists. Evidence: `initial-appointments-verified.json`; repeatable read-only checker: `verify_initial_appointments.py`. The guarded repair harness records the interrupted revision and supports resuming specifically from correction v7.

The browser grid shows the corrected allocations. The v11 Excel request returned HTTP 200 in approximately 3.0 seconds. Intermediate rebuild failures and repeated uploads for the same revisions were observed while the service harness and local app were both active. V11 uploaded three times within eight seconds; this is a concrete duplicate-work investigation target, not yet a proven production rate or root cause. No workbook cell/layout acceptance was performed.

The local backend was restarted with all fixes; no deployment or commit. Remaining checks include appointment register labels/reference parsing (some still show misleading metadata), complete proposal-comparison coverage, workbook rebuild coordination, planning/PMP revisions, the later civil appointment and invoices. These results do not close the overall performance review.
