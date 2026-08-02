---
title: Procurement Requests (RFP, RFT, and RFQ)
status: needs-triage
type: PRD
triage_label: needs-triage
labels: [needs-triage, enhancement, procurement, agent, backend, frontend]
source: product-planning-conversation-2026-08-02
---

# Procurement Requests (RFP, RFT, and RFQ) — Product Requirements

## Problem Statement

Clerk can create evidence-grounded requests for consultant fee proposals and a
head-contractor expression of interest. It can also compare a governed subset
of residential builder tenders. It cannot yet prepare priced requests for the
broad range of contractors, subcontractors, trades, suppliers, and specialist
service providers used across residential and commercial construction.

Users therefore adapt generic templates outside Clerk. That loses the
consistent Project Summary, project-evidence grounding, citations, price
schedule, revision history, and workspace publication already established by
Project Plan, Cost Plan, and consultant procurement.

The product must distinguish:

- asking a consultant to propose services and fees;
- asking a contractor, trade, supplier, or specialist to tender or quote;
- short quotation requests from full tenders; and
- comparing responses that have already been received.

Conflating those intents can create the wrong contractual document or send a
drafting request into Tender Comparison. Building a separate workflow per trade
would duplicate the existing procurement engine and make document quality
inconsistent.

Generated consultant requests are also visible in repository tree mode but not
schedule mode. Users should be able to find and open current artefacts from
either repository preference without representing generated work as project
evidence.

## Solution

Add a lean **RFP / RFT** project workflow while preserving Tender Comparison as
a separate adjacent activity.

V1 will:

- retain the existing consultant request-for-fee-proposal and head-contractor
  EOI behaviour;
- add full RFT and concise RFQ variants for main works, trades, suppliers, and
  specialist services;
- accept any non-empty trade/package name through free text;
- tailor a small set of frequently used packages with in-code profiles and use
  a safe generic fallback for everything else;
- generate evidence-grounded, versioned Markdown using the existing Project
  Summary, retrieval, citation, validation, storage, and review methodology;
- provide deterministic package-appropriate price and returnable schedules;
- use a three-page nominal target for both RFT and RFQ without rejecting a
  complete document that reasonably runs longer;
- expose creation through natural-language chat and a small in-place cockpit
  panel;
- keep a slim project-scoped history of requests and their current draft;
- let users review, edit, accept, and copy the Markdown into Outlook or Word;
  and
- show latest Project Plan, Cost Plan, RFP, EOI, RFT, and RFQ artefacts in
  document schedule mode as well as tree mode without treating artefacts as
  evidence.

V1 does not send documents or manage invitees and responses. Users continue to
use Outlook and their existing document process. Recipient/response tracking,
DOCX export, and a dedicated requests route have recorded migration paths but
are not prerequisites for proving document quality.

## User Stories

1. As a project owner, I want one RFP / RFT area, so that consultant and trade request drafting is easy to find.
2. As a user, I want Tender Comparison to remain a separate navigation item, so that drafting is not confused with analysis.
3. As a user, I want existing Tender Comparison links to continue working, so that the new workflow does not break active comparisons.
4. As a user, I want to ask Clerk in chat to prepare a request for tender, so that I can begin without navigating to a form.
5. As a user, I want “request for quotation”, “RFQ”, and ordinary quote language to start the short quotation workflow.
6. As a user, I want requests for consultant services or fees to continue producing consultant RFPs.
7. As a user, I want a head-contractor shortlist or EOI request to retain the existing EOI workflow.
8. As a user, I want named trades and suppliers to route to RFT/RFQ rather than consultant procurement or contractor EOI.
9. As a user, I want “compare these tenders” to remain a comparison intent and never generate a new request.
10. As a user, I want one concise clarification when “request for services” does not establish consultant versus trade intent.
11. As a residential builder, I want to name any trade from civil and substructure through finishes and external works.
12. As a commercial project manager, I want to name structure, façade, services, fitout, equipment, FF&E, and specialist packages.
13. As an industrial project manager, I want to name structural steel, precast, services infrastructure, specialist doors, and process equipment.
14. As a user, I want common trade aliases resolved where Clerk has a curated profile.
15. As a user, I want an unknown specialist package accepted rather than blocked by a finite list.
16. As a user, I want a custom package to remain generic when project evidence does not support specialist obligations.
17. As a project manager, I want every request to begin with Clerk’s existing concise Project Summary.
18. As a tenderer, I want the package and procurement basis stated clearly.
19. As a tenderer, I want the documents issued for pricing listed by document number and revision.
20. As a project manager, I want evidenced scope interfaces and responsibility boundaries made visible.
21. As a project manager, I want project-specific scope claims cited to uploaded project evidence.
22. As a user, I want missing issue information shown as TBC rather than guessed.
23. As a project manager, I want a full RFT for packages needing formal conditions, departures, returnables, and evaluation context.
24. As a builder, I want an RFQ with the same core procurement coverage as an RFT, tailored in language for a quotation.
25. As a user, I want both RFT and RFQ to aim for proportionate, clear documents without a hard page limit that can truncate a complete request.
26. As a user, I want a package-appropriate price breakdown pre-populated with blank/TBC return cells.
27. As a user, I want price controls for lump sum, GST, allowances, options, rates, exclusions, and qualifications where applicable.
28. As a project manager, I want design, shop-drawing, sample, testing, commissioning, warranty, as-built, and O&M returnables included only when applicable.
29. As a user, I want to edit unresolved details directly in the draft before sending it.
30. As a user, I want RFP, EOI, RFT, and RFQ drafts to support the same revise and accept workflow.
31. As a user, I want a copy action so that I can move the approved content into Outlook or Word.
32. As a user, I want each completed workflow to produce a normal artefact card in chat.
33. As a user, I want long-running generation to use the existing progress, retry, cancellation, and failure controls.
34. As a user, I want a compact dashboard panel rather than a separate procurement application.
35. As a user, I want to select a previous request and open its current draft from the same panel.
36. As a user, I want latest generated drafts shown in repository schedule mode.
37. As a user, I want clicking an artefact schedule row to open Markdown review rather than a source-document action.
38. As a user, I want historical revisions retained in tree mode without cluttering schedule mode.
39. As a user, I want generated artefacts visibly distinguished from uploaded evidence.
40. As an existing user, I want earlier consultant RFP and contractor EOI artefacts represented in the new request history.
41. As an administrator, I want legacy backfill to be idempotent.
42. As a maintainer, I want consultant RFP and contractor EOI fixtures protected while shared content code is generalised.
43. As a maintainer, I want project authorization and row-level security applied to every request record and mutation.
44. As a maintainer, I want all tender arithmetic performed deterministically rather than by an LLM.

## Implementation Decisions

- The project navigation label is **RFP / RFT**. RFQ is a variant inside that
  surface.
- Add a new tile before the existing Tender Comparison tile. Do not rename or
  repurpose Tender Comparison’s load-bearing `procurement` tile ID.
- V1 uses an in-place `ProjectControlBoard` branch rather than a dedicated
  route or component subsystem.
- The panel contains kind, free-text target, create, compact request list,
  workflow progress, draft review, and trace.
- Consultant RFP and contractor EOI keep their existing adapters and naming
  lineages.
- Trade RFT/RFQ extends the shared `ProcurementDocument` engine. Retrieval,
  platform guidance, versioning, provenance, storage, and publication are not
  reimplemented.
- RFT and RFQ use one deterministic renderer with ordered section contracts and
  the same core procurement coverage. RFQ uses quotation-oriented wording and
  may use lighter formality where suitable.
- Both variants use bounded narrative with a three-page nominal target. The
  target guides concision but is not a hard output limit or failure condition.
- The existing narrative and evidence-validation modules are generalised over
  target/output fields rather than copied into trade-specific equivalents.
- The existing Project Summary renderer remains the only source for the opening
  summary.
- A small `TRADE_PACKAGES` map lives with the trade adapter. It covers common
  early-use packages and aliases. Any unknown non-empty target receives a
  generic profile.
- There is no YAML catalogue, loader, validator, package database, or catalogue
  CI gate in v1.
- Cost-plan rows may provide grouping language but are not used as package
  identity because they are too coarse for trade procurement.
- Blank price schedules and returnables are deterministic. The model never
  calculates prices, totals, percentages, or comparisons.
- V1 introduces one `procurement_requests` table with project, creator, kind,
  target, status, current draft, issue/close timestamps, revision, and
  timestamps.
- Request status is draft, issued, closed, or cancelled. Recording issued does
  not send anything.
- Missing issue information remains visible as TBC in editable Markdown. V1
  does not introduce request-specific decision tables or readiness controls.
- Recipient, contact, response, and response-file records are deferred. The v1
  request row is their future FK anchor.
- Markdown plus the existing copy action is the delivery format. DOCX export is
  deferred until content and formatting are stable.
- Chat starts a durable workflow run and returns normal progress and artefact
  events.
- Negative intent tests protect comparison/evaluation language from starting a
  drafting run.
- Contractor EOI and the new trade workflow families are registered in the
  artefact edit/accept policy and platform-knowledge parity list.
- Document schedule mode merges source-document and latest generated-artefact
  presentation rows. Artefacts never enter evidence selection or deletion.
- Project Plan and Cost Plan artefacts are included because they have the same
  schedule-mode presentation gap.
- Existing consultant RFP and contractor EOI artefacts are backfilled
  idempotently without changing their paths or revisions.
- Tender Comparison remains a bounded downstream module. Clerk core does not
  import implementation code from `backend/tender/`.
- External email, tender portals, issue, lodgement, acceptance, and award remain
  human/out-of-product actions in v1.

## Testing Decisions

- Existing consultant RFP golden fixtures and contractor EOI tests are the
  regression gate for shared renderer/narrative changes.
- Tests prove the old consultant duplicate-helper chain is unused before it is
  deleted.
- Trade tests cover main-works RFT, structural-steel RFT, electrical RFQ, and a
  custom specialist package.
- RFT/RFQ tests assert complete core sections, quotation-oriented RFQ wording,
  and that generation remains successful when a document reasonably exceeds
  the nominal three-page target.
- Narrative tests validate assigned citations, reject unsupported citations,
  bound retries, and turn missing evidence into explicit gaps.
- Price schedule tests assert blank/TBC commercial values and no model-derived
  arithmetic.
- Artefact-policy tests cover revise/accept for existing contractor EOI and new
  RFT/RFQ workflows.
- Knowledge-catalog tests cover existing head-contractor and new trade workflow
  keys.
- Durable workflow tests cover idempotent start, worker dispatch, result
  publication, retry, cancellation, and artefact metadata.
- MCP/chat tests cover project authorization, trade-shaped consultant redirect,
  positive RFP/RFT/RFQ triggers, and negative comparison/evaluation triggers.
- Migration/service tests cover the single-table constraints, indexes, FKs,
  RLS, lifecycle transitions, optimistic revision, same-project attachment,
  and cross-project isolation.
- Frontend tests cover exact nav order, unchanged Tender Comparison identity,
  corrected workflow routing, procurement progress, compact creation/list
  states, edit/accept/copy, and error states.
- Repository tests prove source interactions remain unchanged, latest artefacts
  open in schedule mode, and artefacts cannot enter evidence actions.
- Backfill tests prove provenance-first grouping and idempotency.
- End-to-end acceptance chat-queues an electrical RFQ, observes progress, opens
  it in the cockpit, edits a section, accepts it, and copies the content.
- Unit and integration suites use no live network. Real model/storage and
  construction-professional red-pen checks remain explicit manual gates.

## Out of Scope

- Sending requests, invitations, addenda, reminders, or award notices through
  Outlook, email, or a tender portal.
- Recipient, consultant, trade, or supplier contact management.
- Recording received submissions, response revisions, lateness, or response
  files in v1.
- Per-request decision controls or a separate ready-for-issue state.
- Electronic tender lodgement by external tenderers.
- DOCX/PDF tender export in v1.
- A dedicated `/requests` route or full procurement application.
- A governed YAML/database trade catalogue or re-authoring every TCM alias.
- Digital signatures, offer acceptance, subcontract execution, purchase-order
  issue, or automatic award.
- Automatically recommending/ranking tenderers from received documents.
- Expanding Tender Comparison to all trade packages or building classes.
- Importing Tender Comparison implementation code into Clerk core.
- Legal review or bespoke contract conditions without a confirmed basis and
  human review.
- Treating generated procurement artefacts as independent project evidence.
- Market directories, licence integrations, financial checks, or automated
  tenderer discovery.
- Automatic contract/cost-plan handoff following award.

## Further Notes

- The lean staging and deferred migration paths are outcomes of the
  [peer review](../../plans/2026-08-02-procurement-requests-rfp-rft-rfq-review.md).
- “All trades” is satisfied by accepting any non-empty target, not by claiming a
  finite catalogue is exhaustive.
- If recipient/response tracking is later prioritised, new tables attach to the
  slim request row without reshaping its identity.
- If per-request decisions are later needed, reuse `project_decisions` with
  namespaced decision IDs rather than creating a duplicate decisions table.
- A future bulk catalogue may use existing tender taxonomy and synonym data as
  a curation source, but Clerk core must not import TCM runtime code.
- DOCX export follows document red-pen validation; the v1 user journey is
  generate, edit, accept, and copy into Outlook or Word.
- The linked staged plan governs implementation order and file-level work.

## Linked Plan

- [Revised staged implementation plan](../../plans/2026-08-02-procurement-requests-rfp-rft-rfq.md)
