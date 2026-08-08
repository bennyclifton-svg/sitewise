---
target: PMP, RFP, RFT, RFQ and cost-plan artifact output
total_score: 23
max_score: 40
na_heuristics:
p0_count: 1
p1_count: 3
timestamp: 2026-08-06T09-58-46Z
slug: ontend-src-components-project-draftreviewpanel-tsx
---
Method: dual-agent (A: artifact_design_review · B: artifact_implementation_review)

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 3 | Version, evidence, change and workflow states exist; issue readiness and export status do not. |
| 2 | Match System / Real World | 3 | Construction language and registers are credible, but generator and internal-QA language leaks into customer-facing output. |
| 3 | User Control and Freedom | 2 | Section editing and decisions exist; users cannot reliably copy, download or export every artifact. |
| 4 | Consistency and Standards | 2 | The web shell follows the new tokens, while print, PDF and Excel use separate palettes and renderers. |
| 5 | Error Prevention | 2 | Evidence/conflict states help, but unresolved TBCs can remain dispersed and selected decisions disappear from print. |
| 6 | Recognition Rather Than Recall | 2 | Navigation helps, but repeated facts and citations force readers to reconcile sections mentally. |
| 7 | Flexibility and Efficiency | 2 | Experts have anchors and trace disclosure, but no exception-first view and dense tables slow scanning. |
| 8 | Aesthetic and Minimalist Design | 2 | The shell is restrained; the artifact body is generic Markdown with excessive rows and internal prose. |
| 9 | Error Recovery | 3 | Save, rebase and conflict handling are actionable and generally preserve work. |
| 10 | Help and Documentation | 2 | Provenance exists; issue/export guidance and format availability are unclear. |
| **Total** |  | **23/40** | **Acceptable foundation; significant issuance and export gaps** |

## Design Specificity Verdict

**LLM assessment:** The content feels authored for Australian construction management: appointments, NCC and approval pathways, procurement, document revisions, fee stages, price schedules and evidence states are materially specific. The presentation is much less distinctive. The artifact body is a generic Markdown reader inside a strong SiteWise shell, and customer-visible phrases such as scaffold status, profile emphasis, loaded seed sections and repository instructions expose the generation machinery. RFT and RFQ are particularly interchangeable because they share nearly the same structure and differ mostly by title and a few conditions.

**Deterministic scan:** `detect.mjs --json frontend/src/components/project` returned zero findings. That is a useful negative result, not a clean bill of health: the detector does not cover backend renderer duplication, inaccessible exports, blocking conversions, document semantics or cross-format parity.

**Visual overlays:** No reliable user-visible overlay was available because the browser evaluation surface was read-only. DOM, computed-style and screenshot inspection at 1280×720 showed the PMP as a narrow Markdown surface rather than an isolated issue document, lower content partly obscured by the chat rail, controls measuring roughly 24–36px, and no visible Word, PDF or Excel export actions.

## Overall Impression

Clerk has a credible evidence-aware construction document model, but it currently optimizes for proving how the artifact was generated rather than helping a recipient understand what is true, what is required and what must happen next. The largest opportunity is to establish one concise issue-document model and one visual/export contract, then derive web, copy, Word, PDF and Excel representations from it without additional LLM calls.

## What's Working

- **Credible domain structures:** Appointment boundaries, approval gates, scope interfaces, cost bases, risks, actions and document revisions reflect real construction workflows.
- **Honest provenance:** Status, source and conflict labels are explicit and do not rely on colour alone. That supports trust and auditability.
- **Useful deterministic foundations:** The adaptive ten-section PMP, semantic navigation, collapsed workflow trace and typed cost-plan workbook are sound bases for a shorter system.

## Priority Issues

### [P0] There is no canonical export contract

**Why it matters:** PMP, RFP, RFT and RFQ have web Markdown but no product Word/PDF export. PMP alone has plain-text copy. Cost Plan creates XLSX server-side but has no visible download, and its web preview drops workbook layout metadata. Parallel Markdown, print CSS, Jinja/WeasyPrint and openpyxl renderers cannot satisfy visual parity.

**Fix:** Define one revisioned artifact content contract and a shared document theme generated from `frontend/public/style-guide/tokens.json`. Use a single artifact DOM for web and PDF; provide rich HTML plus plain-text clipboard data for Word; generate editable DOCX from the same semantic blocks; expose the existing XLSX and make its preview contract carry widths, merges, formats and styles. Cache exports by draft, revision, format and content hash and create them on demand/off the generation-critical path.

**Suggested command:** `$impeccable harden`

### [P1] Repetition and internal QA content dilute the issued document

**Why it matters:** Budget, pathway, appointments, role boundaries and project identity recur across summary, narrative, risk, action and audit sections. PMP annexures can dominate the complete output while being excluded from the word count. Scaffold/profile/seed language makes a professional artifact feel machine-generated.

**Fix:** Establish one canonical position register for project identity, budget, pathway and appointments. Reference stable position IDs downstream instead of restating prose. Keep the adaptive PMP, but move the internal audit and full evidence ledger to a companion QA/evidence schedule. Count and test the complete export, not only the primary body.

**Suggested command:** `$impeccable distill`

### [P1] Issue readiness and selected decisions are not reliably carried into exports

**Why it matters:** TBCs are distributed through trade requests, so users cannot tell quickly whether a document is safe to issue. Interactive decision selection lives in controls hidden by print CSS, meaning the consequential selected position can disappear from Word/PDF.

**Fix:** Add an exception-first issue panel containing document metadata, readiness, at most five blockers and critical current positions. Consolidate unresolved TBCs there. Render every selected decision as a static export row containing position, status/source, rationale, owner and due date. Block or visibly watermark unresolved issue exports according to the agreed policy.

**Suggested command:** `$impeccable clarify`

### [P1] RFT and RFQ do not express different procurement intent

**Why it matters:** Both currently use roughly the same twelve-section skeleton. A formal competitive tender needs particulars, addenda, departures, validity, evaluation basis and formal schedules; a quotation request should be substantially lighter. Interchangeability increases reading time and legal/commercial ambiguity.

**Fix:** Retain shared deterministic primitives, but create distinct profiles. RFT: issue particulars, scope/interfaces, issued information, programme, price and return schedules, departures/addenda/validity, conditions. RFQ: compact issue summary, scope, price, programme, assumptions and acceptance. RFP should use a lifecycle matrix combining stage, service, deliverable, input/interface and optional/excluded scope.

**Suggested command:** `$impeccable shape`

### [P2] The artifact surface is less polished and accessible than the surrounding shell

**Why it matters:** Dense five-to-six-column tables overflow the reading pane, the section rail disappears at smaller breakpoints, editing is partly hover-discovered, common controls are below 44px, and the current rounded Markdown cards conflict with the new square/faceted style direction. Workbook and tender print palettes still use legacy Office/slate styling.

**Fix:** Add an isolated document-reading mode with a SiteWise issue title block, square geometry, restrained facet-blue keylines, document headers/footers and a light document/print subtheme. Split wide registers into compact primary tables plus detail schedules. Preserve visible focus states and make controls at least 44px where touch applies. Drive web, print and workbook styles from the same export-token map.

**Suggested command:** `$impeccable polish`

## Persona Red Flags

**Alex — expert project manager:** Cannot filter directly to exceptions and must scan 10–14 PMP sections, 55–84 table rows and potentially fifteen decisions. Repeated positions, horizontal table scrolling and hover-revealed editing slow keyboard-first review.

**Sam — low-vision user:** Semantic headings, header cells, text status labels and busy states are good. Risks remain: 9pt print tables, wide schedules, a disappearing compact section navigator, sub-44px controls and selected decisions missing from print.

**Australian construction professional issuing a package:** Will value role boundaries, citations and revision-controlled registers. Will distrust visible scaffold/seed language, repeated facts that may diverge, dispersed TBCs, and an RFT without clear issue reference, close time, contact, tender validity, departures and addenda acknowledgement.

## Minor Observations

- The consultant RFP renderer ignores its `max_pages` argument, so the intended limit is not enforced structurally.
- PMP primary word counts exclude annexures and collapsed detail; reported length can materially understate the recipient's full document.
- The implemented public style guide and the repository `DESIGN.md` disagree: the guide uses void/panel/facet-blue/bone and square facets, while `DESIGN.md` still describes the former orange/paper Drawing Office system.
- Stable `PMP.md` storage may overwrite bytes while revision records remain; immutable downloadable export bytes need an explicit rule.
- Current print CSS intentionally changes the dark screen surface to white/black. That is practical for print, but it means literal pixel identity is not the current behavior.
- Portable visuals should be native tables, status cells, phase bands and labelled indicators—not canvas charts or complex SVG—so they survive Word/PDF copy and remain accessible.

## Questions to Consider

- Should an issued artifact prove the generation audit, or should it communicate the approved position while a companion record carries the proof?
- Should “identical” mean pixel identity, or consistent content, hierarchy, tokens and geometry within the limits of Word and Excel rendering engines?
- What is the shortest useful RFQ if it is no longer forced through the RFT structure?
- Should any artifact with a critical unresolved position be exportable without a visible draft/not-for-issue state?
