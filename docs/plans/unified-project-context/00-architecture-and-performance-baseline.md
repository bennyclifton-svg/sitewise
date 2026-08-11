# Unified project context: Stage 0 baseline

Date: 2026-08-10

This is the execution baseline for
`2026-08-10-Unified-Project-Context-Addressable-Artefacts-Inc-Gen-High-Perf-Editing.md`.
It records the system that exists before the later incremental-generation and
addressable-block stages change behaviour.

## Generation path map

All agent and cockpit launches should converge on `workflow_runs`. The older
synchronous endpoints remain live as the pre-cutover safety path.

| Artefact operation | HTTP / MCP entry | Durable workflow | Context and taxonomy | Retrieval / seed routing | Generation / validation | Persistence / UI refresh |
| --- | --- | --- | --- | --- | --- | --- |
| Create PMP | `POST /projects/{id}/workflow-runs/project-plan`; MCP `start_project_plan` | `workflows.runs.start_workflow_run` -> `worker._dispatch` -> `run_create_pmp_workflow` | Frozen `ProjectSnapshot`; canonical `ProjectGenerationContext`; legacy `pmp_taxonomy_context` remains inside PMP renderers | `retrieve_create_pmp_sources`, `pmp_seed_routing`, corpus sweep, knowledge catalog | deterministic scaffold or bounded narrative/hybrid compiler; evidence, claim-support, coverage and length checks | `draft_artifacts`, workspace Markdown, workflow progress preview; cockpit polls run/bootstrap state |
| Update PMP | `POST /projects/{id}/workflow-runs/project-plan/refresh`; MCP `refresh_project_plan` | `run_update_pmp_workflow` | Frozen snapshot and expected artefact version | evidence delta retrieval | update workflow with validation | new draft version; result reference on run |
| Create Cost Plan | `POST /projects/{id}/workflow-runs/cost-plan`; MCP `start_cost_plan` | `run_create_cost_plan_workflow` | Frozen snapshot; canonical generation context; typed dependency snapshot | `retrieve_create_cost_plan_sources`, cost seed selection | deterministic typed rows plus bounded narrative/hybrid compiler | typed Cost Plan + draft artefact + workbook export |
| Update Cost Plan | `POST /projects/{id}/workflow-runs/cost-plan/refresh`; MCP `refresh_cost_plan` | worker reconciles evidence then calls `cost_plan.service.refresh_cost_plan` | Snapshot/revision checks and dependency snapshot | structured evidence reconciliation | Python mutations and calculations | new typed revision; workbook synchronised after publish |
| Create consultant RFP | `POST /projects/{id}/workflow-runs/consultant-procurement`; MCP `start_consultant_procurement` | `draft_consultant_procurement_artifact` -> shared `draft_procurement_request` | Frozen run brief now carries canonical context; renderers still read `Project` until Stage 2 migration | targeted project queries plus applicable/required platform knowledge | deterministic RFP scaffold plus validated narrative | draft artefact, procurement request, workspace Markdown |
| Create trade RFT/RFQ | `POST /projects/{id}/workflow-runs/trade-procurement`; MCP `start_trade_procurement` | `draft_trade_procurement_artifact` -> shared `draft_procurement_request` | Same durable context boundary as RFP | package queries plus required platform knowledge | deterministic RFT/RFQ scaffold plus validated narrative | draft artefact, procurement request, workspace Markdown |
| Structured Cost Plan edit | project/MCP Cost Plan mutation endpoints | direct typed service mutation | expected revision + dependency checks | none | Python validation and arithmetic; zero LLM/RAG | delta state returned; workbook remains an export concern |

The durable request boundary freezes:

- the full `ProjectSnapshot`;
- one canonical `ProjectGenerationContext`;
- profile, decision, evidence and artefact revisions;
- the caller's parameters and model choice.

This is the seam later stages should consume. They should not create another
project-state store.

## Duplicate logic found

The audit found useful but overlapping context construction:

| Concern | Current implementations | Migration direction |
| --- | --- | --- |
| Profile loading | `projects.profile.read_profile`, `projects.snapshot.get_project_snapshot` | Snapshot remains the consistency unit; generation context interprets it. |
| Taxonomy formatting | `sitewise.pmp_taxonomy_context`, `sitewise.archetype_bridge`, prompt-local formatting in PMP/Cost Plan and procurement renderers | Migrate artefact prompts through Stage 2 lenses; do not delete the existing renderer helpers until their callers move. |
| Identity | snapshot identity plus `projects.identity.resolve_project_identity` | Preserve evidence-aware identity resolution; make its confirmed result an input to canonical context rather than duplicating heuristics. |
| Seed routing | PMP seed router, Cost Plan required paths, procurement knowledge-catalog selection | Stage 3 should provide one selector over the existing knowledge catalog and retain workflow-specific section requirements. |
| Retrieval | PMP and Cost Plan source loaders plus sequential procurement evidence queries | Stage 4 should share bounded evidence pools and parallelise only independent queries. |
| Draft versions | `next_draft_version`, artefact revision services, workflow expected-version checks | Keep `draft_artifacts` authoritative and converge mutations on one revision contract. |
| Progress | workflow trace events, run progress previews, frontend elapsed-time estimator | Stage 8 should promote real section events and remove invented percentages only after producers exist. |

## Regression project matrix

`backend/tests/projects/test_generation_context.py` resolves these representative
shapes through the same model:

1. Residential new house.
2. Residential renovation.
3. Commercial office fitout.
4. Commercial refurbishment.
5. Multi-residential apartments.
6. Industrial warehouse.
7. Commercial remediation.
8. Complex staged occupied healthcare project.

The fixture suite asserts applicable schema selection, stable context version,
known scope, relevant unknowns, explicit exclusions, not-applicable state and
request-local cache reuse.

## Performance baseline

Recorded on the Windows development host on 2026-08-10:

| Measurement | Baseline / guardrail | Evidence |
| --- | --- | --- |
| Existing focused workflow/render regression suite | 136 passed in 6.84 s | `pytest` over snapshot, durable runs, PMP/Cost Plan renderers and consultant/trade procurement |
| Canonical context resolution | average under 25 ms across 100 uncached resolutions | architectural test in `test_generation_context.py` |
| PMP deterministic renderer | average under 500 ms | existing `test_pmp_renderer.py` guardrail |
| Cost Plan deterministic renderer | average under 500 ms | existing `test_cost_plan_renderer.py` guardrail |
| Workflow stages | retrieval, generation, persistence, workbook and total duration persisted | `workflow_runs.stage_durations_ms` from trace durations |
| Retrieval | embedding, semantic, lexical, fusion, neighbour and total timings exposed | `retrieval.retriever` result timings |
| Tender pipeline | duration, LLM calls and token counts per stage | TCM telemetry ledger |

The new `context_ready` trace event records canonical-context build duration and
critical-unknown count for PMP and Cost Plan. It flows into the existing
`stage_durations_ms` ledger; no second telemetry store was introduced.

## Known instrumentation gaps

F9 closed the producer and CI-guardrail gaps for interaction measurement:

| Measurement | Guardrail / producer | Evidence |
| --- | --- | --- |
| Paragraph edit | `measureLocalMutation("paragraph-edit")` + p95 budget 120 ms | `DraftReviewPanel`, `interaction-budgets.ts` |
| Cost Plan amount/item edit | `measureLocalMutation("cost-plan")` + p95 budget 120–180 ms | `CostPlanGrid`, `interaction-budgets.ts` |
| Block delta payload | delta ≤ 1/3 of full draft JSON | `test_block_delta_payload.py` |
| TTFC / TTFU | `scaffold_ready` / `section_completed` marks | `performance.ts`, workflow progress strip |
| Query shape (Cost Plan / latest draft) | single select + `selectinload` items | `test_query_budgets.py` |
| Large Cost Plan render | virtualize at ≥ 40 rows | `COST_PLAN_VIRTUALIZE_THRESHOLD` |

Recorded benchmark metadata: suite `unified-context-f9`, repeats 20,
date 2026-08-11 (see `frontend/src/lib/interaction-budgets.ts`). Live browser
p50/p95 timing still depends on a running app session; CI enforces the
deterministic payload, query-shape and budget-constant guardrails above.

Remaining open outside F9:

- profiler field save wall-clock in a live browser session;
- TCM-adjacent LLM-call counts (owned by tender telemetry).

## Stage 0 exit status

- Architecture paths mapped: complete.
- Duplicate context/retrieval/seed/version seams recorded: complete.
- Representative regression fixtures: complete.
- Backend context/workflow baseline: complete.
- Interaction producers and CI guardrails: complete in F9; live browser p50/p95
  capture remains an operational measurement against a running environment.

## F10 simplification closeout (2026-08-11)

Verified mutation and helper consolidation after F1-F9:

| Removed / restricted | Replacement | Evidence |
| --- | --- | --- |
| `PATCH /projects/{id}/drafts/{id}` + FE `patchDraft` | `POST .../drafts/{id}/blocks` / `apply_artefact_operations` | `test_project_draft_versioning.py`, `test_f10_simplification.py` |
| MCP whole-document draft rewrite via `write_workspace_file` | Rejected; block/Cost Plan ops required | `test_workspace_tools.py` |
| Unused `app.retrieval.profiles` | Deleted (no production importers) | `test_f10_simplification.py` |
| Unused FE sync wrappers `runCreatePmp` / `runCreateCostPlan` / `runUpdatePmp` / `runSortFiles` | Cockpit already uses `startWorkflowRun` | FE `api.ts` search |

Still retained on purpose (not F10 deletions):

- Phase 8.5 legacy chat/orchestrator and its retrieval helpers;
- hybrid/legacy PMP and Cost Plan compiler flags and sync HTTP safety endpoints;
- seed-routing adapters and taxonomy helpers still called by renderers;
- workbook flush-on-preview / coalesced rebuild (read path, not a mutation alias).

Final suite counts and browser acceptance evidence are recorded in the F10
completion section of `01-post-implementation-follow-up.md`.
