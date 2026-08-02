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

Clerk can already create evidence-grounded requests for fee proposal for
individual consultant disciplines, and it can separately compare a limited set
of residential builder tenders. It does not yet give a project team one place to
prepare priced requests for contractors, subcontractors, trades, suppliers, or
specialist service providers across the construction sequence.

Users therefore have to draft trade tender requests outside Clerk, manually
adapt generic templates for different packages, and keep a separate record of
who was invited and whose tender or quotation was received. The existing
consultant RFP artefacts are also discoverable in the document tree but are not
shown in the document schedule, which makes the same repository behave
differently depending on the selected view.

The product must distinguish three related but materially different intents:

- asking a consultant to propose services and fees;
- asking a trade contractor or supplier to tender or quote; and
- comparing responses that have already been received.

Conflating these intents risks generating the wrong contractual document or
routing a drafting request into Tender Comparison. Building separate,
duplicated workflows for every request type would create a second problem:
inconsistent project summaries, evidence handling, storage paths, versioning,
and document quality.

## Solution

Add a single **RFP / RFT** project workflow that covers client-issued
procurement requests while preserving the existing Tender Comparison workflow
as a separate downstream activity.

The workflow will:

- retain the existing consultant request-for-fee-proposal behaviour;
- add full Request for Tender and concise Request for Quotation variants for
  contractors, subcontractors, trades, suppliers, and specialist services;
- use a chronological, extensible trade-package catalogue that covers common
  residential, commercial, multi-residential, industrial, fitout, and
  specialist packages;
- allow a custom package when the catalogue does not contain the required
  trade, without inventing an unsupported scope;
- generate concise, evidence-grounded, versioned Markdown artefacts using the
  same project summary, citation, validation, storage, and review methodology as
  the existing Project Plan, Cost Plan, and consultant RFP workflows;
- provide package-specific price breakdowns and returnable schedules;
- surface material issue decisions and prevent a draft being marked ready for
  issue while blocking decisions remain unresolved;
- keep a durable register of recipients and received proposals, tenders, or
  quotations, including revised submissions and their source files;
- expose the workflow through both a dedicated project navigation item and
  natural-language chat triggers; and
- show the latest RFP, EOI, RFT, and RFQ artefacts in document schedule mode as
  well as tree mode, without treating generated artefacts as independent
  project evidence.

The initial product prepares and records procurement requests. It does not send
them externally, accept offers, award packages, execute contracts, or expand
Tender Comparison beyond its governed coverage.

## User Stories

1. As a project owner, I want one procurement-request area, so that I do not have to remember separate locations for consultant and trade requests.
2. As a project manager, I want consultant RFPs, head-contractor EOIs, trade RFTs, and RFQs shown together, so that I can understand current procurement activity at a glance.
3. As a user, I want Tender Comparison to remain a separate navigation item, so that creating a request is not confused with analysing received responses.
4. As a user, I want to ask Clerk in chat to prepare a request for tender, so that I can start the workflow without navigating through a form.
5. As a user, I want to ask for a quotation or RFQ in ordinary language, so that I do not need to know the internal workflow name.
6. As a user, I want requests for consultant services or fees to continue producing consultant RFPs, so that existing behaviour is preserved.
7. As a user, I want named trades and suppliers to route to RFT or RFQ drafting, so that they are not incorrectly treated as consultant disciplines.
8. As a user, I want “compare the tenders” to remain a comparison request, so that Clerk does not draft another invitation after tenders have been received.
9. As a user, I want Clerk to ask one concise question when the target or request type is genuinely ambiguous, so that it does not guess a contractual intent.
10. As a residential builder, I want requests for all common house trades, so that I can procure work from civil and structure through finishes and external works.
11. As a commercial project manager, I want packages for structure, façade, services, fitout, vertical transport, specialist equipment, and FF&E, so that the catalogue is not limited to Class 1 housing.
12. As an industrial project manager, I want packages such as structural steel, precast, services infrastructure, specialist doors, and process equipment to be supported, so that the workflow remains useful for warehouses and industrial projects.
13. As a user, I want trade packages presented in construction sequence, so that I can find the appropriate package without searching an arbitrary alphabetical list.
14. As a user, I want common aliases such as “windows”, “glazing”, and “aluminium windows” to resolve to the same package, so that duplicate request lineages are not created.
15. As a user, I want to enter a custom specialist package, so that an unusual trade does not block procurement.
16. As a user, I want a custom package to use a safe generic scope, so that Clerk does not fabricate specialist requirements.
17. As a project manager, I want the request to begin with the same concise Project Summary used by existing Clerk artefacts, so that the project identity is consistent.
18. As a tenderer, I want the package and procurement basis stated clearly, so that I know whether the request is supply-only, install-only, design-and-supply, or supply-and-install.
19. As a tenderer, I want the documents issued for pricing listed by document number and revision, so that I can identify the pricing baseline.
20. As a project manager, I want scope interfaces and responsibility boundaries stated, so that gaps between adjacent trades are visible before pricing.
21. As a project manager, I want project-specific scope statements cited to uploaded project evidence, so that the request can be audited.
22. As a user, I want missing project information labelled as unresolved rather than guessed, so that a plausible draft is not mistaken for an issue-ready document.
23. As a project manager, I want an RFT variant for material or risk-bearing packages, so that tender conditions, returnables, departures, and evaluation requirements are captured.
24. As a builder, I want a shorter RFQ variant for defined, lower-risk, or supply-only packages, so that simple quotation requests remain concise.
25. As a user, I want the package-specific pricing breakdown pre-populated, so that tenderers return prices in a comparable structure.
26. As a user, I want the price schedule to capture lump sum, GST, allowances, options, rates, exclusions, and qualifications, so that key commercial differences are not hidden.
27. As a project manager, I want applicable design, shop-drawing, sample, testing, commissioning, warranty, as-built, and O&M obligations included, so that post-award deliverables are priced.
28. As a user, I want key issue decisions shown as interactive controls, so that I can resolve the procurement basis without rewriting Markdown.
29. As a user, I want request decisions scoped to one procurement request, so that changing the roofing basis does not change the electrical request.
30. As a user, I want a request to remain a draft while blocking decisions are unresolved, so that incomplete documents are not represented as ready for issue.
31. As a user, I want non-blocking missing information marked TBC, so that I can create a useful working draft before every detail is known.
32. As a user, I want to record the companies or consultants invited, so that the intended market can be distinguished from actual responses.
33. As a user, I want to record when a response was received, so that I can see who responded before or after the closing time.
34. As a user, I want to attach multiple files to one response, so that a tender form, price breakdown, programme, and qualifications remain one submission.
35. As a user, I want to record revised responses without deleting earlier returns, so that the procurement audit trail is preserved.
36. As a user, I want to upload a response directly from the request register, so that it is stored under the correct package and submission folder.
37. As a user, I want to attach an existing repository file to a response, so that I do not have to upload the same document twice.
38. As a user, I want late, declined, withdrawn, and no-response outcomes distinguished, so that the register reflects what happened without rewriting history.
39. As a user, I want the register to show invited and received counts, so that I can see response coverage quickly.
40. As a user, I want each response file to remain project-scoped and private, so that commercially sensitive tender information cannot leak between projects.
41. As a user, I want each completed workflow to produce a normal Clerk artefact card in chat, so that I can open the draft from the conversation.
42. As a user, I want workflow progress and failure states to use the existing durable run controls, so that long-running drafting survives the chat turn and can be retried or cancelled.
43. As a user, I want the latest procurement draft shown in document schedule mode, so that schedule and tree users can both find it.
44. As a user, I want clicking a procurement artefact in schedule mode to open the Markdown review panel, so that it does not fail as though it were a source document.
45. As a user, I want historical revisions retained in tree mode, so that the audit trail is available without cluttering the document schedule.
46. As a user, I want generated artefacts visibly distinguished from uploaded evidence, so that I understand their evidentiary status.
47. As an existing user, I want earlier consultant RFP and contractor EOI drafts to appear in the new hub, so that the feature does not start with an empty history.
48. As an administrator, I want the backfill of existing procurement artefacts to be idempotent, so that rollout and retries do not create duplicate register entries.
49. As a maintainer, I want the consultant RFP output to remain regression-tested while shared renderer code is extracted, so that adding trade requests does not reduce existing quality.
50. As a maintainer, I want the trade catalogue validated for unique codes, aliases, ordering, and references, so that ambiguous package routing fails during development rather than in production.
51. As a maintainer, I want all request and response mutations protected by project ownership and entitlement checks, so that the new register follows Clerk’s existing security model.
52. As a maintainer, I want all tender arithmetic performed deterministically, so that language models never calculate totals, percentages, or commercial comparisons.

## Implementation Decisions

- The project navigation label is **RFP / RFT**. RFQ is a trade-request variant
  within that surface rather than a third navigation item.
- The new surface is a Procurement Requests hub. Tender Comparison remains a
  separate adjacent workflow and retains its existing deep links.
- Consultant RFPs continue to use the existing consultant workflow and naming
  lineage. New trade RFT/RFQ documents extend the shared procurement-document
  engine rather than duplicating retrieval, guidance selection, versioning,
  provenance, storage, or artefact publication.
- Head-contractor EOIs are included in the hub because they are client-issued
  procurement requests, but their current output and behaviour remain intact.
- The trade-package catalogue is Clerk core platform data. It is not imported
  from Tender Comparison because Tender Comparison is a bounded Class 1 module
  with a one-way integration boundary.
- The catalogue is chronological and data-driven. A package carries canonical
  identity, aliases, applicability, delivery modes, baseline scope prompts,
  typical interfaces, pricing breakdown lines, and returnable requirements.
- A custom-package fallback is required for long-tail coverage. It may organise
  user-provided and project-evidenced scope but must not invent specialist
  obligations.
- Request kinds are consultant RFP, contractor EOI, trade RFT, and trade RFQ.
  Internal names may differ, but the user-facing terminology remains explicit.
- Trade requests use the same hybrid compilation model as the improved
  consultant RFP: deterministic structure plus a bounded evidence-grounded
  narrative, followed by citation and completeness validation.
- The existing Project Summary renderer is the only source for the summary at
  the start of RFP/RFT/RFQ documents.
- RFT and RFQ share a document model. RFT includes the full conditions,
  departures, returnables, and evaluation context; RFQ omits inapplicable
  formality while preserving price, scope, programme, exclusions, and
  qualification controls.
- Blank price schedules are deterministic templates. If response figures are
  later captured, totals and comparisons are computed in Python rather than by
  an LLM.
- Trade request artefacts are stored in the package-specific procurement
  lifecycle structure under the tender-pack stage. Consultant RFP paths remain
  unchanged.
- A durable procurement register is introduced in Clerk core using
  procurement-prefixed data structures. It does not add tables to or import
  implementation code from Tender Comparison.
- The register distinguishes a request, its recipients, response revisions,
  and the files belonging to each response. Earlier response revisions remain
  immutable audit records when a later revision becomes current.
- Request lifecycle state is draft, ready for issue, issued, closed, or
  cancelled. External sending is manual in v1; marking a request issued records
  the human action and date.
- Recipient outcomes distinguish invited, received, declined, withdrawn, and
  no response. Lateness is derived from timestamps rather than stored as an
  editable opinion.
- Issue-readiness decisions are request-scoped. They reuse the interaction and
  optimistic-concurrency pattern of current project decisions but do not reuse
  project-global decision identifiers.
- Blocking issue decisions cover package identity and basis, scope/document
  baseline, pricing format, programme/closing dates, and contract/design
  responsibility. Other missing information may remain explicitly TBC.
- Chat starts a durable workflow run and returns normal status and artefact
  events. Chat does not synchronously generate a long document inside the turn.
- Chat intent routing includes negative cases so compare, evaluate, recommend,
  award, and analyse language does not start a new procurement request.
- Document schedule mode merges uploaded source-document rows with latest
  generated-artefact rows. Artefacts open through the draft-review path and are
  never passed to source-document deletion or evidence APIs.
- Schedule mode shows the latest revision per procurement request. Tree mode
  remains the version-complete repository view.
- Existing consultant RFP and contractor EOI artefacts are backfilled into the
  procurement register idempotently. Existing workspace paths are preserved.
- External issuance, email, tender portal functionality, automatic market
  invitations, and contractual acceptance require separate authority and are
  not inferred from creating a draft.

## Testing Decisions

- Tests assert externally observable behaviour through catalogue, service,
  workflow, API, MCP, and rendered UI interfaces. Tests should not assert
  private helper structure merely to freeze an implementation.
- The trade-package catalogue receives deterministic tests for unique package
  codes, unique normalised aliases, sequence ordering, valid applicability,
  valid delivery modes, and complete baseline price-breakdown data.
- Existing consultant RFP golden fixtures remain unchanged during shared
  renderer extraction. Their current workflow tests are the regression oracle.
- Trade request renderer tests cover one early works package, one structural
  package, one services package, one finishes package, one supply-only RFQ, and
  one custom specialist package.
- Narrative tests verify that project-specific claims use assigned citations,
  unsupported citations are rejected, validation retries are bounded, and no
  project evidence produces explicit gaps rather than invented facts.
- Procurement-register service tests cover request lifecycle transitions,
  optimistic decision updates, recipient outcomes, response revision history,
  late-response derivation, and cross-project isolation.
- Migration tests verify constraints, indexes, foreign keys, row-level security,
  and idempotent legacy backfill.
- Durable workflow tests follow existing Project Plan, Cost Plan, consultant
  procurement, and contractor EOI run tests: idempotent start, worker dispatch,
  result publication, retry, cancellation, and artefact metadata.
- MCP tests verify per-project authorization, capability gating, exact workflow
  parameters, natural-language entry tools, status events, and cross-project
  rejection.
- Chat prompt/acceptance tests cover positive RFP/RFT/RFQ triggers and negative
  Tender Comparison/evaluation triggers.
- Frontend component tests cover navigation order, request list and detail,
  creation form, chronological package picker, issue-readiness controls,
  recipients, response revisions, upload/link behaviour, and error states.
- Repository tests prove that existing RFPs and new RFT/RFQ artefacts appear in
  both views, schedule clicks open the draft review panel, source selection still
  works, and artefacts cannot enter source-document bulk deletion.
- End-to-end acceptance uses at least a consultant RFP, structural-steel RFT,
  supply-only windows RFQ, received multi-file response, revised response, and a
  “compare the tenders” request that remains routed to Tender Comparison.
- Unit and integration tests use no live network. Real model and storage checks
  remain explicit manual acceptance gates using a non-production project.

## Out of Scope

- Sending RFPs, RFTs, RFQs, invitations, addenda, reminders, or award notices by
  email or through an external tender portal.
- Electronic tender lodgement by external tenderers.
- Digital signatures, offer acceptance, subcontract execution, purchase-order
  issue, or automatic award.
- Automatically recommending or ranking tenderers from the receipt register.
- Expanding Tender Comparison to every commercial trade package or building
  class.
- Importing Tender Comparison’s taxonomy or internal services into Clerk core.
- Performing legal review or generating bespoke contract conditions without a
  confirmed contract basis and human review.
- Automatically treating generated procurement artefacts as independent
  project evidence.
- Automatically moving or linking an uploaded response based only on an
  inferred filename, respondent, or package without user confirmation.
- Market directories, licence-register integrations, financial checks, or
  automated tenderer discovery.
- Automatic contract-cost-plan handoff following an award.

## Further Notes

- This PRD supersedes the earlier “RFT later” placeholder in the
  head-contractor EOI plan while preserving the shared procurement-engine
  architecture established by that work.
- The current consultant-status follow-up should be absorbed into this generic
  request/recipient/response register rather than implemented as a second,
  consultant-only status system.
- “All trades” is satisfied through a reviewed common-package catalogue plus a
  safe custom-package route. No finite catalogue should be represented as
  exhaustive for every specialist construction sector.
- The feature should ship as a draft-and-register workflow first. External issue
  and award actions can be planned later after the internal audit trail and
  document quality are proven.
- The implementation sequence and file-level tasks are governed by the linked
  staged implementation plan.

## Linked Plan

- [Staged implementation plan](../../plans/2026-08-02-procurement-requests-rfp-rft-rfq.md)
