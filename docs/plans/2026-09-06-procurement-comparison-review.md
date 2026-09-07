# Procurement comparison: from submissions to a decision report

Status: implemented locally on 6 September 2026. Migration 062 and the new report language entries are installed in the configured shared Supabase database. A separately approved production worker hotfix isolates development jobs as recorded below. Staging acceptance and customer release approval remain outstanding; the new comparison feature has not been deployed to the hosted application.

### Procurement loading follow-up

The user reported a database error when opening procurement in the localhost app. A read-only reproduction confirmed that the configured database remained at revision 061: querying the new procurement row model failed with PostgreSQL `42703` because `submission_revision` did not exist. After the user's explicit approval, migration 062 completed successfully. The previously failing queries now pass, and the existing procurement service and response validation successfully loaded a saved grid with five rows and three firms, with no project changes saved. The existing idempotent seed loader also installed the 64 missing `procurement_review.*` report language entries; no existing entries were changed. Browser verification remains with the user.

### Comparison progress follow-up

The user confirmed procurement loads and linked the three quotes. Status polling then alternated between an optimistic reading message and an error. The status endpoint incorrectly called the synchronous `user_owns_project(project, user_id)` helper as an awaited three-argument database helper. Endpoint tests reproduced HTTP 500 for both owners and other users; the corrected call returns progress to the owner and 404 to other users.

The progress surface now retains the last successful status during polling failures, distinguishes connecting from confirmed reading, uses the existing tumbling cube, and shows measured page/file counts with a separate reading/preparation/ready sequence. Queue and retry states come from jobs; a worker without a recent heartbeat is shown as waiting. Polling reads page coverage from JSONB without loading the complete extraction ledger. Missing page totals remain unknown, and reading progress reaching 100% does not mean the report is ready. Tests cover reconnecting without flashing, unavailable comparisons, progress preservation, retry, source counts and stage transitions.

A read-only check of the actual Merricks run found all three ingestion jobs completed, followed by three failed legacy `classify_document` jobs. The intake payloads correctly requested `procurement_review: true`, but no document had the new native reader signature. The local in-process worker is disabled and no separate local tender worker was running. This is consistent with an older external worker consuming the shared queue. The interface now explicitly blocks futile retries through that incompatible pipeline. The shared processing service must be updated together with the API before the affected run can be recovered; do not simply retry the legacy classification jobs. This follow-up did not deploy or restart a worker, rerun AI extraction, or change the saved run.

### Queue isolation and rerun repair

Server inspection confirmed the deployed tender worker was four days old, did not contain `review_extraction.py`, and selected all queued tender jobs without an environment filter. Its `WORKFLOW_QUEUE_SCOPE` is `production`; localhost is `dev`. Tender enqueue, claim and stale-lease recovery now use the existing `WORKFLOW_QUEUE_SCOPE` through the job payload. Unscoped historical jobs remain in the production queue. Local comparison snapshots include their scope, and an explicit rerun only reuses a processing comparison when it still has queued/running jobs. Failed comparisons can therefore be replaced without relinking files.

The production repair is restricted to those three queue changes in its existing `jobs.py`; it does not deploy the new comparison feature or unrelated working-tree changes. After explicit user approval, the patch was applied and the tender worker restarted at 05:58 UTC on 6 September. Preflight confirmed zero running tender jobs. The restarted worker's compiled claim query filters to `production`. The original source, exact patch and SHA-256 manifest are saved under `output/procurement-worker-repair/`; the original also remains beside the patched file in the container. The patched SHA-256 is `09dbbd50ce13941e14bcd96a4f2dfa899170a4b478f123a16bd2828e5a22e1d5`. This container hotfix must be retained by the next image build using the repository's scoped queue implementation.

Local in-process processing is enabled and its startup log includes the queue scope. Merricks was restarted through the intake service from the existing three file links at 06:00 UTC. The fresh comparison uses `dev` jobs, and all three ingestion jobs were confirmed claimed by the updated local process. The previous failed comparison remains intact. Initial focused queue, ingestion, progress, intake and worker regressions passed (59 tests); subsequent live findings and completion are recorded below.

The live run exposed a second handoff fault: when not all documents were ready, the continuation rolled back its read transaction, expiring the job object. `jobs.complete()` then accessed expired attributes without an awaited refresh. The completed document remained saved while the job's heartbeat stopped. A failing regression reproduced the expired-instance access; completion now refreshes expired jobs using the same helper as failure handling. Success telemetry is recorded after the continuation so its rollback cannot discard the timing. All 60 focused tests passed. The local worker was paused for the correction; after confirming its old process had stopped, only its three jobs in this comparison were requeued. Coastal's 12 pages, Montique's 14 pages and Toussaint's first three pages were retained.

That recovered run completed all seven jobs and published a three-page report. Final content inspection exposed two reconciliation defects in the fresh extraction: Toussaint's 77 summary categories were not marked as rollups, so earlier detail was also counted; Coastal's printed GST differed slightly from a straight 10% calculation even though its printed subtotal plus printed GST equalled its total. Reconciliation now recognises the explicit source statement about category totals, bounded by the closing total, when rollup flags are missing. Inclusive comparison uses a unique printed GST figure linked to the same subtotal on the same page/document. These changes leave the original prices intact. Regression tests failed before both corrections and passed after them. The actual saved source data now reconciles Coastal's 36 categories exactly and Toussaint's 77 categories to $2,753,255.26, with an apparent 15.00% uplift. The combined focused suite passed 81 tests.

The corrected Merricks report is published as revision 2, comparison `aaac8068-beb4-4197-a029-3373c12b8283`. Verification confirmed all 63 pages complete, all seven jobs done, the current Main Works recommendation link, its generated Markdown repository file, and a three-page export whose pages were visually inspected. All three reading telemetry records show zero new LLM calls: the corrected run reused saved extraction. The earlier report remains in revision history. The report and verification files are under `output/procurement-worker-repair/`. This confirms the local recovery; the broader customer release gate remains unchanged.

### Seven Hills consultant comparison follow-up

The Electrical review for Seven Hills Townhouse (`21f2a965-f5ac-40c7-b267-36dca97a46cd`) exhausted three reading attempts on `flux-services-fee-proposal.md`, while its other submission completed. Both Flux pages had ingested successfully. Retrieving the existing provider responses reproduced the exact failure without submitting another analysis request: the text attempt failed excerpt matching, and the image retry supplied an impossible `issued_on` date (`2606-26-26`). Calendar validation ran before the existing source-date normalizer could replace that model value with the printed 26 June 2025 date.

Reading now grounds the date fields before validating the extraction. Normalization tolerates an out-of-window page identifier so the existing source validation can reject it explicitly; it does not bypass page, quotation, amount or coverage checks. Regressions cover correction from a printed date, removal when no source date exists, and rejection of an invalid page reference. The exact captured Flux responses now pass through the reader, yielding 27 facts, both pages, the correct date and no unmatched amounts. The focused backend suite passed 81 tests and lint passed. No prompt, model, schema, upload or original source was changed.

The fix is installed in the local development code. Automatic approval review initially rejected the live retry because the earlier external-processing approval was specific to Mornington. The user then explicitly approved retrying Seven Hills through the configured OpenAI service. The existing failed step was resumed using the normal retry endpoint, retaining Gridworks' completed extraction and both original file links. All five jobs completed. The consultant report is saved as revision 1, linked to Electrical and the repository; its one-page PDF and five-stage fee table were verified and visually inspected. The saved Flux validity fact contains the printed `2025-06-26` date, and the quoted totals remain $158,000 and $186,000 excluding GST. Diagnostic response replays and the verified report are stored under `output/seven-hills-tender-debug/`.

## Implementation and verification

The existing plan was sufficient. The user subsequently confirmed that the first output should be a standard Markdown artefact, using the existing Word/PDF download service and PMP-style numbered citations. A firm can hold many canonical source files. The consultant profile includes a compact fee matrix. These decisions supersede the earlier proposal to generate separate HTML/PDF assets during publication.

Implemented in the existing procurement core, `backend/tender/` and React cockpit:

- Candidate file links, visible linking/unlinking controls, multiple selected files, repository drag/drop and Ctrl/Command-click. Receipt is distinct from extraction progress.
- One-action comparison from the procurement row, including one submitted firm. The old comparison list directs new work to this grid; existing historical comparisons remain readable.
- Immutable submission snapshots, project-scoped validation, file hashes, resumable page/window extraction and bounded image retries. All original pages are retained; scans receive images. Prompts, schema, parser and model participate in the production extraction-cache signature.
- Worker lease renewal and ownership checks; completion cannot be published by a worker that has lost its lease. Review continuation is queued before the reading job is marked done.
- Python money/date interpretation, summary-schedule reconciliation, conditional conclusions, firm-specific questions, price matrices and source ledgers. The provider can choose only valid source references. This uses the documented structured-output enum limit, with a constrained pattern for larger reference sets: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
- Markdown publication through the existing artefact adapter, per-row report revision streams, repository storage, review/progress links and standard Word/PDF export. The same renderer enforces the report profile's A4 page budget before publication. Word retains explicit page breaks; final Word pagination still requires checking in the production office renderer.
- File replacement/deletion marks recommendations stale through migration `062_procurement_comparison`; older successful reports remain readable during a new run.

Verification recorded for this implementation:

- 107 backend checks passed, including existing evaluation-harness checks, money/date/source validation, single/multiple-document intake, interrupted-window recovery, lease fencing, report profiles and shared exports. A legacy OpenDataLoader completeness check failed locally because Java is absent; it was explicitly excluded from the subsequent focused run. The new native reader does not depend on that Java path.
- 101 frontend tests passed across linking, comparison launch, progress/retry, downloads, procurement, repository and cockpit routing. Type checking and lint passed.
- Tender seed validation passed (181 taxonomy cells, 70 rules, 2,580 synonyms, 188 benchmarks and six golden documents). Alembic has one head and generated the new migration SQL successfully offline. This initial verification preceded the approved database update recorded above.
- The user expressly authorized transmitting the three Mornington quotes to the configured OpenAI service. The local evaluation accounts for all 63 original pages and 803 facts, preserves `$9,5556.80` as unresolved, reproduces all three headline prices, reconciles Toussaint's 77 summary categories to $2,753,255.26 and the apparent 15% difference, reconciles Coastal's 36 categories exactly, and flags all expired offers at the fixed date. The final source selection passed without fabricated references. Its final warm synthesis took approximately 65 seconds; this is not a cold-run or production latency guarantee.
- The resulting Mornington Markdown/Word/PDF samples are under `output/procurement-review-qa/mornington/`. The PDF was rendered and inspected at three pages; synthetic consultant/trade/head-contractor fixtures fit 1/2/3 pages. A fallback PDF background-overdraw issue exposed during visual checking was corrected by rendering explicit sections independently.

The real-document evaluation reused validated extraction checkpoints while the reader/selector was being corrected. It is evidence for this regression, not a full cold evaluation of every supported file type or approval of the protected release corpus. Broader QS review, production timing, real database concurrency/RLS and end-to-end upload/reload acceptance remain release checks. The existing `data/tender/evaluation_release.yaml` remains blocked and unchanged.

For any separate deployment database, apply Alembic migration 062 and idempotently reload tender seeds (`python -m tender.seeds.load`) so the language catalogue is installed. These prerequisites are complete for the configured shared database. Deploy the API, frontend and existing tender worker together; exercise consultant, trade and head-contractor submissions in staging, including several files per firm, replacement, navigation/reload and retry. Do not mark the customer release approved based on these local tests alone.

## Outcome

Upload a quote to the existing right-hand repository, link it to a firm in the procurement grid, and select **Compare firms**. SiteWise reads the complete submissions and produces a useful recommendation, qualification questions and a price matrix. The result opens in the middle panel and remains available from both the repository and the procurement row.

The approved reference is `output/pdf/Mornington_Builder_Quote_Review.pdf`: three pages reviewing Montique, Toussaint and Coastal. Its content and reasoning are the reference, including its disclosed uncertainties; its provisional recommendation is not a hard-coded expected winner.

| Procurement package | Maximum report length | Content |
| --- | --- | --- |
| Consultant | 1 page | Recommendation or clarification-first conclusion; headline fee table; material scope/fee differences; a small fee matrix where relevant; 3-4 priority questions, attributed to the relevant firms. |
| Trade or supplier | 2 pages | Page 1: recommendation, totals, material differences and priority questions. Page 2: price matrix and any essential firm-specific clarifications. |
| Head contractor | 3 pages | Page 1: recommendation, quoted totals, what each total means, 3-4 differences that could change the decision. Page 2: up to four common questions and up to three specific questions per firm. Page 3: selected price matrix with pricing basis and source notes. |

These are caps, not a requirement to fill empty pages. Every material uncertainty affecting a recommendation must survive condensation. Detailed evidence and the complete ledger remain accessible in the app rather than being appended to the summary PDF.

One submitted quote is a valid input: produce a **Quote review**, with no relative ranking, cheapest-price claim or assertion that the market was tested. Missing prices do not become zero. If the documents cannot support a recommendation, the output recommends obtaining the named clarifications first.

## What the current implementation establishes

The existing module is substantial and should be refactored in place. Preserve its project authorisation, canonical files, immutable input snapshots, typed extraction, arithmetic, job queue, source ledgers and artefact publication.

| Finding | Evidence in the repository | Consequence |
| --- | --- | --- |
| Starting requires a separate save, region/specification inputs and sometimes storeys. | `frontend/src/components/project/tender/TenderQuoteSelectionPanel.tsx`; `backend/tender/services/project_context_adapter.py` | Removing the form alone will not remove the backend gate. |
| Selection and readiness require at least two quote groups. The procurement grid checks the number of named firms, rather than submitted quotes. | `backend/app/schemas/document_selections.py`; context adapter; `ProcurementStrategyGrid.tsx` | A single-quote review needs boundary, service and UI changes. |
| The grid supplies its selected row, but the control-board callback discards it and opens the general tender route. | `ProcurementRequestPanel.tsx`; `ProjectControlBoard.tsx`; `ProjectCockpitPage.tsx` | Comparisons are not anchored to the chosen discipline and its firms. |
| Current context validation is residential Class 1a and NSW/VIC/QLD oriented. | `backend/tender/services/project_context_adapter.py`; `backend/tender/schemas.py` | Consultant/trade reviews must not inherit building-benchmark eligibility as a prerequisite. |
| Firm records have no attached-submission relationship. Existing submission links point to an issued request, not a strategy candidate. | `backend/app/database/procurement_strategy.py`; `procurement_request_submission.py` | A stable, explicit firm-to-file link is needed. |
| Report assembly uses two default narrative strings or previously edited narrative blocks; it is not performing the contextual synthesis seen in the reference report. | `backend/tender/services/report.py` | Shortening the existing template will not create the required analytical quality. |
| The HTML template includes nine sections, including complete ledgers. The Markdown renderer omits the questions section. | `backend/tender/report_templates/base.html`; `render_draft_markdown` | The centre-panel artefact and PDF need one shared report model. |
| Extraction processes overlapping windows serially and retries missing figures at page level. Its image fallback reads local filesystem paths. | `backend/tender/services/extraction.py`; ingestion stores cloud image keys | Cloud images do not reach the retry through this path. Empty extracted text has no currency census to trigger a retry. |
| Jobs already support retries, immutable intake, stale-lock reclamation and concurrent worker lanes. Stale reclamation uses lock age; no renewal heartbeat appears in the inspected worker path. | `backend/tender/services/intake.py`, `jobs.py`, `continuations.py`; `backend/tender/worker.py` | Extend the queue with bounded work and lease ownership; do not introduce another worker framework. Test live-worker reclamation separately. |

Local checks completed:

- Existing context, extraction and report-assembly tests: **20 passed**.
- A one-quote/no-setup probe returned `ready=False`, with region and specification missing.
- A public extraction-service probe with four monetary tokens and a cloud page-image key retried without an image. A blank-text page received one text-only call and no image retry.
- Actual ingestion was attempted with the three supplied PDFs. The local OpenDataLoader path stopped because `java` was not available on PATH. This is a local prerequisite failure, not evidence of the production timeout cause.
- Production timeout duration, provider latency and worker-restart behaviour have **not** been measured in this session. Treat the queue/latency concerns below as hypotheses until the fault-injection and staging runs establish them.

The working tree already contained other UI edits and extensive document removals. Those changes were not restored or replaced. The canonical Pi/TCM plan files named in AGENTS.md were unavailable in this checkout; the tracked architecture was inspected from HEAD. The root/stack instructions and the user's new product direction govern this specification.

## Interaction contract

### Upload and link

1. Continue to upload through the existing right-hand repository. Retain the original file in canonical project storage.
2. Select a file, then choose **Link quote** beside a firm, or drag an existing repository file onto that firm's cell. Ctrl-click on Windows/Linux and Command-click on macOS are optional shortcuts for the same action.
3. A linked file is attached by stable candidate ID, not its display name. Renaming a firm does not break the link. The grid shows a small document marker with an accessible label such as **Quote linked: 2 files**. Clicking it opens the linked files and unlink/replace actions.
4. When no file is selected, the same action opens a filtered picker. Touch and keyboard users can complete the entire flow without a modifier key or dragging.
5. Multiple files can belong to one submission, for example a quote and its exclusions schedule. Revisions are distinguishable from supporting documents. Do not silently combine two alternative quotes or count the same file twice. Obvious ambiguous revisions require a short inline choice at linking time.
6. Linking establishes receipt. Display extraction state separately: uploaded/reading/ready/attention. A link marker must not imply that the document has already been successfully read.

Keep the current discipline rows, firm columns, row ordering and status presentation. Remove quote-group merge/reordering controls from the comparison flow; this does not remove unrelated discipline-management controls.

### Compare

- With at least one linked submission, the existing **Compare firms** action starts the run directly. It does not open another setup form or ask the user to save a selection.
- Use the row's linked firms, ordered by their existing slots. Ignore unsubmitted firm names. More than one supporting file does not become more than one bidder.
- With no submissions, the action offers the inline link/picker state instead of starting an empty job.
- Derive consultant/trade/head-contractor report type from the procurement row's package identity. Treat contractor procurement explicitly; do not infer it solely from the generic `participant_type`, which currently has no head-contractor value. Supplier quotes use the trade report cap.
- Region, specification and storeys are optional contextual facts. Read them from the existing project or submitted documents if relevant. An unknown fact remains unknown. Do not invent defaults to satisfy the old validator.
- Open the run in the middle panel, leaving the right repository and navigation mounted. Show plain stages: **Reading quotes**, **Checking prices**, **Comparing scope**, **Preparing report**. Progress reflects actual completed work, without made-up percentages or an unmeasured time promise.
- The run continues after navigation or refresh. Returning to the procurement row shows **Preparing recommendation**, **Review recommendation**, or a specific retryable failure.

### Return to the result

- Publish one versioned Markdown artefact with structured source provenance through the existing publisher boundary. Generate Word/PDF on demand through the standard download service.
- The report opens automatically when the initiating view is still active. If the user has moved elsewhere, show completion without taking over their current work.
- The right repository lists the report under the relevant procurement package. **Review recommendation** in the grid opens the same artefact/version in the middle panel.
- Replacing a quote marks the previous result as based on earlier submissions. It remains readable until a new result is ready. A failed rerun does not destroy the last successful report.
- Repeated clicks with the same active input snapshot attach to the existing run. Opening an unchanged completed comparison reuses its report; an explicit rerun can refresh it against the current review date.

## The procedure to codify

### 1. Freeze the submission set

Resolve the chosen row, candidate IDs, original workspace file IDs, hashes, active revisions, source filenames and document order under project authorisation. Record review date, report profile, relevant project context, parser/prompt/model versions and a fingerprint. The job uses this snapshot even if the procurement grid is subsequently edited.

### 2. Read complete documents with page fidelity

For a born-digital PDF, first extract text and layout blocks with the already-installed PyMuPDF. Retain original page numbering, raw text, table/position information and a canonical page-image reference. Record coverage for every original page, including blank and image-only pages. Use OpenDataLoader when layout needs it, and OCR/vision for scanned or low-quality pages. This is a measured routing strategy, not a silent fallback that labels incomplete text as success.

Introduce an injected page-image loader that resolves canonical storage keys asynchronously, validates ownership and returns bytes. Never treat a storage key as a local file path. Schedule image review for empty text, failed numeric coverage, malformed figures, contradictory totals and material qualification pages. Bound the number/size of images per request.

Avoid project RAG chunk retrieval for the commercial review. The selected submissions are the corpus; every page must be accounted for. Platform knowledge can inform a question, but must be labelled guidance and never presented as evidence of what a bidder included.

Untrusted PDF wording is source content. Instructions addressed to an assistant inside a tender have no authority to change the review, hide exclusions, contact anyone or select a winner.

### 3. Extract facts and commercial qualifications

Separate two outputs:

- **Monetary ledger:** quoted amounts, totals/subtotals, rates, quantities, taxes, margins, allowances, alternatives, options, duplicates and parent/child package relationships.
- **Commercial facts:** contract/pricing basis, validity, included scope, explicit exclusions, owner supply, assumptions, product/specification departures, programme, fees, services, interfaces and conflicting statements.

Each fact retains source document, original PDF page, excerpt/position, printed wording, confidence and extraction status. Preserve malformed values verbatim and leave their numeric value unresolved. In particular, do not turn Montique's `$9,5556.80` into a silently corrected price.

No important qualification should have to masquerade as a priced line item to survive extraction. Cross-reference a clarification to both sources when two statements conflict.

### 4. Reconcile in Python

Use integer cents and Decimal rates. Compute all sums, differences, percentages, GST and margin transformations. Distinguish:

- the bidder's printed headline total;
- the counted commercial ledger;
- printed totals repeated elsewhere;
- non-additive allowances/subtotals already inside a package;
- options whose inclusion is unresolved;
- unexplained residuals;
- an illustrative, explicitly labelled comparison adjustment.

Never add an allowance to a total a second time. Never infer exclusion from the absence of a separate price. Do not replace a printed headline with a guessed corrected total.

An apparent margin can be detected arithmetically and offered as a question. Toussaint's 77 categories sum to $2,753,255.26 ex GST and its displayed subtotal is $3,166,243.55; Python derives an apparent 15% uplift. That is an inference to confirm, not a licence to apply another margin to the headline.

Preserve currency and tax basis per amount. Different currencies require an explicit sourced conversion basis or separate presentation. Unknown GST remains visible. If an illustrative adjusted matrix uses an inferred margin, the header/notes must state the assumption. Primary reported totals remain as quoted.

### 5. Align scope into a useful matrix

Use a small taxonomy suited to the selected package and the actual documents:

- Consultants: stages, deliverables, design iterations, approvals, site visits, inspections, hourly extras and disbursements.
- Trades: work sections, quantities/rates, supply/install boundaries, preliminaries, interfaces, exclusions, testing and commissioning.
- Head contractors: major work packages, allowances, owner costs, design departures and completion scope.

Retain the full ledger separately. The compact matrix shows decision-relevant rows, not every repeated monetary token. A model proposes mappings and groupings; Python validates membership, calculates aggregates and prevents duplicate counting. Every displayed aggregate has a drill-down to its constituent source amounts.

Use explicit statuses: **priced**, **allowance**, **bundled**, **owner supplied**, **explicitly excluded**, **not stated**, **unclear**. Keep supply-only and supply-and-install amounts distinguishable. Never spread a bundled price across smaller rows using invented allocations. If rows overlap, label the matrix non-additive and identify the overlapping bundles.

### 6. Prepare the recommendation and questions

Create structured findings first, each with severity/materiality, affected firms, source IDs, computed-value IDs and a proposed clarification. Then ask a versioned synthesis prompt to select and explain the most consequential findings within the report profile.

The model may assess scope and express a conditional recommendation. It cannot introduce numeric results, unverified credentials or claims about a firm's workmanship, financial health or motives. Numeric references are resolved from the verified ledger after generation. References are validated before publication.

Possible conclusions include **preferred for clarification**, **preferred subject to conditions**, **clarification required before selection**, and **single-quote review**. Do not automatically recommend the lowest headline or use a fabricated weighted score. If price bases or material omissions prevent comparison, say what must be clarified.

Use report-language keys from `data/tender/report_language.yaml` for headings, standard findings, statuses, questions and qualifications. New analytical wording belongs in versioned language templates with source-backed parameters. A model selects/orders those findings rather than bypassing the language catalogue with ungoverned customer-facing prose. If richer free narrative is later desired, change that policy explicitly and evaluate it.

### 7. Render, validate and publish

One `ProcurementReview` presentation model drives the centre-panel view, Markdown artefact, HTML and PDF. It contains the recommendation, bidder headline explanations, selected findings, questions grouped by addressee, matrix rows, assumptions and citations.

The Python renderer selects the one-/two-/three-page template. It measures overflow, verifies the resulting page count and checks that totals, material findings and source references are present. Condense wording and select matrix rows by materiality before shrinking text. Do not clip content, drop a critical qualification or silently add a fourth page. Detailed material remains linked in the app.

If the source is ambiguous, publish a clearly qualified review where useful. If a document was never read or the rendered output fails validation, keep the report unready and show the exact actionable failure. Producing a report does not award a contract or send questions to firms.

## Data and module boundaries

Keep the stack and Pi runtime. No second agent runtime, queue framework or RAG path is required.

| Owner | Proposed responsibility |
| --- | --- |
| Procurement core (`backend/app/`) | Candidate-to-submission links, active source revision, procurement row association and row-level report projection. Use stable IDs and project authorisation. These are procurement tables, not tables owned by TCM. |
| TCM (`backend/tender/`) | Frozen comparison inputs, structured commercial facts, monetary ledger, matrix, findings, report model, durable review jobs and report versions. New persisted tables use `tender_*`. |
| Existing artefact adapter | Publish the review into core drafts/workspace and update the procurement-row projection. Core does not import TCM internals to assemble the report. |
| React cockpit | Linking, state display, one-action launch, viewing the same report, opening evidence and retrying. No financial calculations or extraction in the browser. |

Do not introduce TCM foreign keys to procurement candidates. Carry authorised candidate/row identifiers in immutable provenance and use the adapter contract; retain the existing restriction on cross-core FKs. The procurement core owns its own relational links.

Suggested typed boundaries:

- `SubmissionSnapshot`: firm ID/name, selected document versions, hashes and page coverage.
- `CommercialFact`: kind, status, source references, optional printed amount and uncertainty.
- `MoneyFact`: original printed amount, cents/currency/tax basis, semantic role, parent/duplicate relationships and provenance.
- `ComparisonFinding`: evidence IDs, computed-value IDs, affected firms, severity, language key and parameters.
- `ReviewMatrixRow`: common item plus one typed price/status cell per submitted firm.
- `ProcurementReview`: schema/version/profile, recommendation, headline table, selected findings/questions, matrix, assumptions, citations and input fingerprint.

These are interfaces to protect, not a class hierarchy. Extend existing schemas where they already express the same concept.

## API and durable execution

Proposed boundary shapes, to align with existing router conventions during implementation:

- Link/unlink a canonical file through a project-scoped candidate-submission endpoint in procurement core. Validate the candidate, row and file all belong to the authorised project. Use the row/submission revision to reject stale destructive replacements.
- Start through a TCM endpoint given the project ID, strategy row ID, expected submission revision and idempotency key. The server derives the report profile and freezes the submissions; no required benchmarking inputs appear in the request.
- Return a run/comparison ID immediately after committing the intake. Processing is not inside the HTTP request or dependent on an active chat turn.
- Extend existing progress/result endpoints and the artefact publisher; avoid parallel report registries. A completed event invalidates the repository and procurement-row queries.

The worker stages are `read -> extract facts -> reconcile -> align scope -> synthesise -> validate/render -> publish`.

Persist page/window completion and provider responses under a content/version cache key. Retry a failed unit without re-extracting successful pages. Cache invalidation includes parser, prompt, schema and model configuration, with project tenancy preserved. Reading layout may be cached independently of the dated final recommendation.

Use bounded concurrency across independent documents/windows and bounded context for continuations. Preserve heading/layout context without serialising every expensive request unnecessarily. Limit per-call duration, attempts and output size, and preserve a useful final error.

Renew the running job lease. Reclamation must check lease expiry, and completion must be fenced to the current lease owner so an old worker cannot publish after another worker takes over. Test retries, restarts and duplicate clicks before claiming timeout resilience. Durable progress replaces dependence on a single long browser request.

Do not bypass the existing customer release/evaluation gate or silently auto-accept extraction problems to achieve one-click UX. Automate verified low-risk work; represent unresolved commercial questions in the report and reserve blocking review for genuinely missing/unreadable evidence or invalid output.

## Implementation sequence and acceptance

1. **Reference corpus and failure tests.** Add restricted/local Mornington source references plus expected facts, and small consultant/trade fixtures. Reproduce cloud-image and blank-text failures at the extraction service boundary. Add rendering/content parity checks. Establish a staging latency baseline before making a performance claim.
2. **Read/extract reliability.** Route native text appropriately, account for every page, load cloud images correctly, retain non-price qualifications, checkpoint expensive units and add lease renewal/fencing. Fault-injection tests must pass.
3. **Commercial review model.** Extend deterministic reconciliation and shared matrix mappings, introduce the typed findings/review model, language catalogue and versioned prompts. Run the existing eval harness plus the new acceptance cases.
4. **Compact report publication.** Implement the three report profiles and shared artefact/PDF rendering. The three source types must produce readable documents within their page caps, with questions present in every representation.
5. **Procurement integration.** Add candidate-file links and row projection; preserve row identity through callbacks; enable single-quote launch; remove setup/merge/reorder friction; show markers, progress and **Review recommendation**. Test pointer, keyboard and touch-accessible paths.
6. **End-to-end acceptance.** Upload/link/compare each package type, navigate away/reload, replace a submission, retry an injected failure and open the same result from the row and repository. Complete prompt/model/taxonomy eval and the existing release review before production rollout.

Each step is a vertical, testable change. Do not ship a form-only simplification while the extraction/report gates still prevent the promised workflow.

### Mornington regression facts

| Check | Expected result |
| --- | --- |
| Original page coverage | Montique 14; Toussaint 37 including cover; Coastal 12. No silent page loss or shifted citations. |
| Headline prices incl. GST | Montique $3,605,841.00; Toussaint $3,482,867.91; Coastal $3,547,495.00. |
| Toussaint reconciliation | 77 categories = $2,753,255.26 ex GST; displayed subtotal $3,166,243.55; $412,988.29 apparent uplift = 15%. Label as inferred; do not add a second margin to the headline. |
| Montique ambiguity | Preserve `$9,5556.80` as malformed. Other listed provisional sums total $1,106,362.20; tax/margin basis remains unconfirmed. |
| Coastal reconciliation | 36 categories reconcile exactly to $3,547,495.00. The $46,100 demolition price is described separately; its inclusion requires clarification, not automatic addition. |
| Allowances | Coastal PC $18,095.15 + PS $269,315.99 = $287,411.14. These are not extra costs on top of the headline. |
| Solar | Montique owner supplied; Coastal $90,576.51 included; Toussaint $82,342.28 ex GST/before the apparent margin. Preserve the bases. |
| Scope differences | Paving quantities/bases; tank capacities; two- versus three-phase power; joinery specifications; owner-supplied lights/alfresco equipment; omitted pool equipment room. |
| Currency-date sensitivity | At the fixed review date 6 September 2026, all three validity periods have elapsed. A different review date is evaluated deterministically. |
| Result | Three-page cap, cited findings and grouped questions, transparent matrix, conditional conclusion. The evaluator scores the reasoning and source coverage, not an immutable winning builder. |

Additional cases must include: one quote; consultant fee split across 3-4 stages; hourly fee with no total; two trade quotes with supply-only versus installed scope; scanned/rotated tables; nil/negative values and credits; malformed numbers; duplicated summary pages; options and addenda; multi-document firms; replacement revisions; unresolved GST; other currencies; malicious document instructions; a cancelled/expired worker; and a cross-project file-link attempt.

Release evidence should record factual coverage, numerical accuracy, citation validity, page/render quality, recommendation grounding, per-stage latency, provider calls, cache reuse, retry recovery and actual processing cost. A fluent PDF and passing mocked unit tests alone do not establish equivalence to the approved manual review.

## Product decisions resolved by this specification

- Python owns workflow, validation and arithmetic; models perform bounded reading, classification/mapping and source-backed selection/synthesis.
- Consultant/trade/head-contractor type comes from the procurement package, with no extra form for region/specification/storeys.
- The report is generated automatically from linked submissions, including a single quote.
- A visible link action and drag/drop are primary; Ctrl/Command-click is a shortcut.
- Report caps are 1/2/3 pages, with full evidence and ledger available in the app.
- Source uncertainty remains visible; reduced interaction does not mean guessed prices or automatic acceptance of extraction failures.
- The current runtime/module boundaries, evaluation policy and unrelated working-tree changes are preserved.
