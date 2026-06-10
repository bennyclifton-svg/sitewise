---
title: Clerk Practice Intelligence Integration PRD
date: 2026-06-07
status: accepted
author: agent
target_repo: D:/AI Projects/clerk
source_repo: D:/AI Projects/CMA04/practice-intelligence
triage_label: needs-triage
labels: [needs-triage, enhancement, clerk, sitewise, frontend, workflows, migration]
seed_consulted: []
evidence_refs:
  - D:/AI Projects/clerk/AGENTS.md
  - D:/AI Projects/clerk/backend/AGENTS.md
  - D:/AI Projects/clerk/frontend/AGENTS.md
  - D:/AI Projects/clerk/docs/architecture.md
  - D:/AI Projects/clerk/docs/plans/2026-06-07-phase-4-frontend.md
  - D:/AI Projects/clerk/docs/plans/2026-06-07-phase-6-ingestion.md
  - D:/AI Projects/clerk/docs/plans/2026-06-07-workflows-and-tender.md
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/README.md
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/src/server/storage/storageAdapter.ts
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/src/server/agentRuntime.ts
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/src/server/contextBuilder.ts
---

# Clerk Practice Intelligence Integration PRD

## Problem Statement

Clerk and Practice Intelligence currently solve adjacent parts of the same product problem, but they do it through different architectures.

Clerk is the better long-term hosted product foundation. It already has a Python FastAPI backend, Supabase Auth, Supabase Postgres, PydanticAI orchestration, a document ingestion pipeline, hybrid retrieval, grounded chat, citations, and a React SPA with authenticated streaming chat.

Practice Intelligence is the stronger project-management cockpit and SiteWise workflow harness. It has a richer workspace frontend, project dashboards, workflow launch surfaces, local file preview, draft review, run traces, and working SiteWise workflow patterns. However, it is tied to a local filesystem workspace and a Node backend that uses the repository itself as the source of truth.

The integration problem is to migrate the Practice Intelligence frontend and SiteWise workflow model into Clerk without preserving two competing product brains. The end state is a VPS-hosted Clerk product where the Practice cockpit is the visual project workspace, Clerk chat is the agent interface, and Clerk's ingestion and workflow runtime power evidence-grounded SiteWise outputs.

## Solution

Make Clerk the canonical application repo and hosted product. Treat Practice Intelligence as migration source material: SiteWise doctrine, seed knowledge, skills, project templates, workflow behavior, local frontend patterns, and test examples.

The migration should be a strangler migration, not a wholesale copy. Clerk's backend remains authoritative. Practice's Node backend becomes a reference implementation for workspace and workflow contracts, then is retired. Practice's frontend is ported into Clerk's frontend conventions as a project cockpit, not copied across as a separate Vite app.

The first product slice should prove the hosted architecture in a small path:

1. Authenticated user opens Clerk.
2. User sees a project list.
3. User opens one SiteWise project cockpit.
4. Chat is scoped to that project by default.
5. Clerk answers with citations from project evidence plus shared SiteWise doctrine and seed knowledge.

The second product slice should prove the full workflow path:

1. User launches Create PMP from the project cockpit.
2. Clerk enforces the SiteWise three-overlay gate.
3. Clerk retrieves doctrine, seed, skill, and active project evidence.
4. Clerk runs a typed PydanticAI workflow.
5. Clerk emits trace events into chat and the project cockpit.
6. Clerk saves a versioned draft artefact with provenance.
7. The draft opens in the centre cockpit for review.

## User Stories

1. As a product owner, I want Clerk to become the canonical app repo, so that future product work lands in one hosted architecture.
2. As a product owner, I want Practice Intelligence treated as migration source material, so that valuable cockpit and workflow work is preserved without carrying the local-only architecture forward.
3. As a product owner, I want Hermes retired as a separate runtime once Clerk can run equivalent workflows, so that there is one product brain.
4. As a project lead, I want to sign in to Clerk and see my project workspace, so that my work is durable and private.
5. As a project lead, I want projects to be first-class records, so that I do not depend on a parsed local README to know which projects exist.
6. As a project lead, I want each project to retain a SiteWise workspace path model, so that files and generated artefacts remain familiar and auditable.
7. As a project lead, I want the UI to feel like a project cockpit rather than a generic chat app, so that I can navigate project documents and workflows efficiently.
8. As a project lead, I want the centre pane to show documents, dashboards, and drafts, so that review work happens in a stable workspace.
9. As a project lead, I want chat to remain visible beside the project cockpit, so that I can ask questions and watch workflow runs without leaving the project.
10. As a project lead, I want chat scoped to the active project by default, so that another project's evidence is never used by accident.
11. As a project lead, I want global or cross-project search to be explicit, so that broad retrieval cannot silently weaken the active-project boundary.
12. As a project lead, I want Clerk to ingest doctrine, seed knowledge, skills, and project evidence before answering, so that answers are grounded in the SiteWise authority stack.
13. As a project lead, I want Clerk to distinguish platform knowledge from project evidence, so that doctrine and seed do not masquerade as project facts.
14. As a project lead, I want Clerk to cite project evidence for factual claims, so that I can verify the answer.
15. As a project lead, I want Clerk to label assumptions, judgement, recommendations, and facts, so that missing evidence is not presented as certainty.
16. As a project lead, I want the three-overlay gate to block phase-gate workflows when archetype, user role, or state is missing, so that the agent does not guess.
17. As a project lead, I want general chat to remain available when overlays are missing, so that I can still ask non-deliverable questions.
18. As a project lead, I want Create PMP to be the first full workflow migrated, so that the hardest integration risks are proven early.
19. As a project lead, I want Create PMP to read current project evidence and shared SiteWise knowledge, so that the draft reflects the actual project.
20. As a project lead, I want generated PMP drafts saved as versioned draft artefacts, so that they can be reviewed outside chat.
21. As a project lead, I want workflow outputs to have status, version, author, provenance, seed consulted, and evidence refs, so that the document is auditable.
22. As a project lead, I want workflow runs to appear in chat as traceable events, so that I can see what the agent did.
23. As a project lead, I want workflow drafts to open in the centre cockpit for review and editing, so that chat is not the document editor.
24. As a project lead, I want draft acceptance and re-opening to be explicit, so that the agent never silently approves project records.
25. As a project lead, I want file previews for Markdown, PDFs, Word, and Excel where supported, so that I can inspect evidence in-app.
26. As a project lead, I want binary source documents preserved as files, so that project evidence remains downloadable and inspectable.
27. As a project lead, I want imported SiteWise projects to preserve their folder structure, so that migration does not destroy filing discipline.
28. As a project lead, I want Clerk ingestion to record content hashes and extraction versions, so that stale evidence can be detected.
29. As a project lead, I want Clerk to retrieve from extracted evidence records rather than raw files during workflows, so that workflow grounding is deployable and repeatable.
30. As a team owner, I want project records scoped to my organisation, so that tenant isolation is enforced.
31. As a team owner, I want users, projects, documents, workflow runs, context packs, and drafts tied to org membership, so that collaboration can grow safely.
32. As a developer, I want the existing Clerk frontend stack retained, so that the migrated cockpit fits Clerk's React, Tailwind, shadcn, and pnpm conventions.
33. As a developer, I want the existing Clerk backend stack retained, so that FastAPI, SQLAlchemy, Alembic, Supabase, PydanticAI, and OpenAI remain the core platform.
34. As a developer, I want the Practice Node storage adapter treated as a contract reference, so that the hosted backend can recreate the behavior without inheriting local filesystem coupling.
35. As a developer, I want the Practice agent runtime treated as workflow reference material, so that Clerk tools can be implemented cleanly in Python.
36. As a developer, I want workflow modules to expose small typed interfaces, so that Create PMP, Cost Plan, Programme, and later workflows can share infrastructure.
37. As a developer, I want backend tests around ingestion, retrieval, gates, workflow outputs, and draft persistence, so that high-risk behavior is tested without live model calls.
38. As a developer, I want frontend verification to follow Clerk conventions, so that the UI is manually verified with typecheck and lint rather than importing Practice's frontend test harness.
39. As a deployer, I want the VPS deployment to serve one Clerk frontend and one Clerk backend, so that operations are simple.
40. As a deployer, I want model keys and Supabase service credentials to remain backend-only, so that secrets never reach the browser.

## Implementation Decisions

- Ratified in the Clerk repo on 2026-06-07 as the governing migration document for the CPI issue pack.
- Clerk is the canonical product repo after migration.
- Practice Intelligence is migration source material and reference implementation, not a long-term sibling runtime.
- Hermes is retired as a separate agent/runtime once Clerk can perform the same project-scoped workflows.
- The long-term app is hosted Clerk first. Local filesystem mode is retained only for development, internal migration, fixture generation, and import paths.
- Practice's frontend is ported into Clerk's existing frontend conventions rather than copied wholesale.
- The first UI migration is a thin project cockpit slice: authenticated home, project list, one project dashboard, project-scoped chat, and evidence preview.
- The full workflow ribbon, workbook views, advanced tabs, accept/reopen controls, and admin surfaces follow after the first project cockpit slice.
- SiteWise doctrine, seed knowledge, system skills, and project template are shared platform knowledge, versioned with the deploy and read-only at runtime.
- Tenant project data is project evidence and generated artefacts, scoped to organisation and project.
- The hosted product preserves the folder-shaped SiteWise mental model through stable workspace paths even when the backend uses database and object-storage records.
- Project identity lives in database project records. Imported README frontmatter populates metadata but is not the only source of truth in hosted mode.
- Project records include declared archetype, user role, and state.
- The SiteWise three-overlay gate remains a hard blocker for phase-gate workflows.
- General chat can answer non-deliverable questions when overlays are incomplete, but deliverable workflows must stop and ask.
- Chat is project-scoped by default when a project is active.
- Cross-project search is a separate explicit mode.
- Workflow runs appear in chat as traceable events.
- Draft review, editing, file preview, and project cockpit navigation happen in the centre workspace.
- Create PMP is the first migrated workflow.
- Generated workflow outputs are first-class draft artefacts, not merely chat messages.
- Clerk's ingestion pipeline becomes the evidence source for hosted workflows.
- Raw file reads are limited to import, preview, download, and fallback extraction.
- Clerk's current "deliverable workflows are deferred" assistant contract must be updated once workflow runtime support lands.
- The backend owns retrieval, workflow execution, tool execution, validation, draft persistence, and privileged Supabase access.
- The browser owns interaction, local UI state, streaming display, and authenticated API calls only.
- No model calls, service-role Supabase calls, or tool execution happen in the browser.
- The VPS deployment runs one Clerk frontend and one Clerk FastAPI backend, with API calls proxied to the backend.

### Deep Modules To Build Or Modify

- Workspace catalog: owns org-scoped workspaces, projects, folder-shaped paths, project metadata, and first-class overlays.
- Platform knowledge ingestion: imports SiteWise doctrine, seed, skills, and template as shared reference knowledge.
- Project evidence ingestion: imports uploaded or migrated project evidence into source document and chunk records with hashes and extraction metadata.
- Workspace API: exposes project lists, project dashboards, file previews, file downloads, document metadata, and draft artefact access to the frontend.
- Project-scoped chat context: attaches active workspace and project scope to chat threads and retrieval filters.
- Workflow runtime: runs bounded project workflows with typed inputs, trace events, model calls, validation, and persistence.
- SiteWise gate service: checks archetype, user role, and state before phase-gate workflows.
- Provenance and artefact service: creates versioned draft artefacts, stores status and provenance, and links evidence and context packs.
- Cockpit frontend shell: ports the Practice project cockpit into Clerk's React/Tailwind/shadcn conventions.
- Workflow trace UI: renders workflow progress and results in chat and project cockpit surfaces.

## Testing Decisions

- Backend tests should focus on external behavior and trust boundaries rather than internal implementation details.
- Existing Clerk backend test style remains preferred: unit tests with mocked service boundaries, no network and no live database for the fast suite.
- Integration tests that need live Supabase or OpenAI stay behind an integration marker.
- Ingestion tests should cover SiteWise path classification, platform knowledge versus project evidence, overlay extraction, content hash behavior, and idempotent re-ingestion.
- Retrieval tests should prove project-scoped chat retrieves active project evidence plus shared SiteWise knowledge without leaking other project evidence.
- Gate tests should prove phase-gate workflows fail when archetype, user role, or state is missing.
- Workflow runtime tests should cover Create PMP request construction, trace emission, validation failure handling, provenance metadata, and draft artefact persistence.
- Draft artefact tests should cover version incrementing, status, accepted/reopened transitions, and evidence/context references.
- API tests should cover project list, project dashboard metadata, file preview, draft access, and workflow run status.
- Frontend verification follows Clerk's rules: manual browser verification plus TypeScript typecheck and lint.
- Do not import the Practice frontend Vitest harness into Clerk.
- The first manual verification path should be: sign in, open project list, open one project, ask a project-scoped question, inspect citations, run Create PMP, inspect trace, open saved draft.

## Out of Scope

- Directly copying the Practice dashboard app as a second Clerk frontend.
- Keeping Hermes as a parallel runtime.
- Keeping the Practice Node backend in production.
- Completing all Practice workflows in the first migration slice.
- Full local filesystem mode as an equal product target.
- Moving all historical Practice tests into Clerk.
- Self-hosting Supabase on the VPS.
- Payments, billing, pricing, or plan enforcement.
- Real-time collaborative editing.
- OCR and full drawing interpretation.
- GraphRAG or a dedicated graph database.
- External correspondence sending.
- Automatic approval or issue of project documents.

## Further Notes

The migration should be sequenced so each slice proves one architectural risk and leaves the product usable:

1. SiteWise knowledge import into Clerk ingestion.
2. Hosted project model and project-scoped retrieval.
3. Thin project cockpit UI in Clerk frontend.
4. Project-scoped streaming chat inside the cockpit.
5. Create PMP workflow runtime and draft artefact persistence.
6. Draft review/opening in the cockpit.
7. Sort Files, Cost Plan, Programme, and procurement workflows.

The key product discipline is to keep the old SiteWise authority stack while changing the substrate underneath it. Project evidence remains above doctrine. Doctrine remains above seed knowledge. Seed knowledge remains above general model knowledge. The hosted database and object store should make that stack easier to audit, not easier to bypass.

The key engineering discipline is to migrate behavior across stable contracts rather than copy implementation shape. Practice's local storage adapter and agent runtime are useful because they define what the product already does. Clerk should implement those capabilities through its own backend, data model, and frontend conventions.
