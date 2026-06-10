# System skill: progress-claim-assessment-system

**Job:** End-to-end residential progress claim assessment workflow. Orchestrates the Sec. 2 declaration gate, seed loading, evidence sweep, contract clause check, physical-completion assessment, claim arithmetic, register-row drafting, and reviewable payment response into one workflow. Produces drafts under `07-construction/05-progress-claims/` with contractual register, and drafts related rows in the progress claim, cost, action, risk, EOT, defects, inspection, RFI, or notice registers where the assessment creates them.

This skill inherits the `seed-targeted-read` -> `evidence-sweep` -> content assessment -> `markdown-draft-for-review` / `register-row-draft` -> gaps and escalations -> return-summary skeleton documented in `contract-setup-system.md` and reused in `cost-plan-system.md`, `risk-register-system.md`, and `procurement-evaluation-system.md`.

The executed contract is the source of truth. Seeds explain the mechanism; they do not supply project-specific entitlement. If the executed contract, special conditions, or clause text needed for the assessment is missing, the skill stops and asks. It does not substitute generic HIA, MBA, AS, ABIC, or NSW Fair Trading wording.

## When called

Called by:
- the agent when the user asks to assess, review, certify, respond to, or draft a payment schedule for a progress claim;
- the agent when a builder, owner-builder, architect-PM, or D&C contractor receives a claim from another party and needs an evidence-based recommendation;
- the agent when a builder is preparing an internal check before issuing a claim to an owner;
- as a re-run when new evidence arrives, the claim is revised, or the project lead asks for a superseding assessment.

The skill is **idempotent**. Re-running on a project with an existing assessment does not overwrite a reviewed assessment. It produces `claim-assessment-<stage-or-claim-id>-v<NN+1>.md` or a new claim-specific draft, and marks earlier drafts superseded only through `markdown-draft-for-review` where the caller explicitly uses the supersede behaviour.

## Caller passes

- **Active project folder path** - required.
- **Claim reference** - required where known. May be a claim number, stage, invoice number, subcontractor reference, or filename.
- **Assessment mode** - one of:
  - `advice-only` - conversation summary only, no draft file;
  - `markdown-only` - assessment draft to `07-construction/05-progress-claims/`;
  - `markdown-then-response` - assessment draft plus a draft payment schedule, evidence request, or withholding response. The human reviews and issues.
- **Claim role** - optional if obvious from evidence: `head-claim-to-owner`, `subcontractor-claim-to-builder`, `owner-builder-subcontractor-claim`, or `administrator-assessment`. If ambiguous, ask.
- **Stage hint** - optional for stage-payment claims: `deposit`, `base`, `slab`, `frame`, `lockup`, `fixing`, `completion`, or a contract-specific stage name.

The skill reads everything else it needs from the active project folder.

## Pre-flight - Step 0: Sec. 2 declaration gate

Before any work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC` per `../../AGENTS.md Sec. 2` and `../../00-doctrine/doctrine.md Sec. seed-consultation-discipline`.
3. **If any is missing, blank, or `TBC`:** stop. Return:
   > Cannot assess a progress claim: the README is missing one or more required overlay declarations. Please declare `archetype`, `user_role`, and `state` in the frontmatter before any progress claim assessment. Per `../../AGENTS.md Sec. 2` and `../../00-doctrine/doctrine.md Sec. seed-consultation-discipline`, the agent does not guess these from project name, address, budget, site, or any other proxy.
4. Do not load seeds, run evidence-sweep, draft, or produce a payment recommendation until the gate passes.

The gate is checked here and again by `seed-targeted-read`. That redundancy is intentional. Progress claim assessment is phase-gate contract administration under `../../AGENTS.md Sec. 9`.

## Steps

### Step 1 - seed-targeted-read

Invoke `../atomic/seed-targeted-read.md` with task subject `residential progress claim assessment`.

The skill loads:

- **Tier 2 archetype seed** - one of `new-dwelling-guide.md`, `renovation-guide.md`, `multi-dwelling-guide.md`, `ancillary-guide.md`, or `small-commercial-guide.md` per `archetype:`.
- **Tier 3 role overlay** - one of `role-owner-builder.md`, `role-architect-pm.md`, `role-builder.md`, or `role-d-and-c.md` per `user_role:`.
- **Cross-cutting topic seeds**:
  - `contract-administration-guide.md` - required for payment mechanism, clause-citation discipline, notice mechanics, and contract family posture.
  - `cost-management-principles.md` - required for HIA stage-payment assessment, cumulative claim arithmetic, signed variations, GST basis, and cost-register links.
  - `program-scheduling-guide.md` - required where the claim turns on stage timing, programme status, EOT, cashflow, or completion readiness.
- **Optional cross-cutting seeds** where the evidence points to them:
  - `procurement-quoting-guide.md` if a subcontractor claim depends on scope awarded through a quote comparison.
  - `sustainability-energy-guide.md` if BASIX / NatHERS evidence is material to a completion-stage claim (slice 12, when present).
  - `defects-and-dlp-guide.md` if completion-stage withholding depends on defects / DLP classification (slice 13, when present).

For non-NSW states, flag state-coverage gaps where the loaded seeds rely on NSW-specific HIA, HBCF, LSL, BASIX, or Security of Payment assumptions without a state callout. Do not silently extend NSW guidance.

Hold the loaded seed list for `seed_consulted:` frontmatter on every draft this skill produces.

### Step 2 - evidence-sweep

Invoke `../atomic/evidence-sweep.md` with task subject `residential progress claim assessment for <claim reference>`.

High-relevance evidence:

- active project README frontmatter;
- executed head contract and special conditions in `07-construction/02-fioa-contract/`;
- contract summary in `00-brief-pmp/contract-summary.md`, if already drafted;
- stage payment schedule, cost-plus claim schedule, subcontract payment schedule, or administrator assessment mechanism;
- current progress claim, invoice, supporting statement, cover letter, or subcontractor claim;
- prior progress claims and prior assessments in `07-construction/05-progress-claims/`;
- progress claim register;
- cost register, cost plan, and current claimed-to-date position in `01-cost/`;
- signed variation register and signed variation forms in `07-construction/06-variations/`;
- EOT register and granted EOT evidence in `07-construction/07-programme-eot/`;
- trade inspection records, structural inspection certificates, certifier/BPA records, conformance certificates, and site reports in `07-construction/09-cc-pc-oc/` and `07-construction/12-reports/`;
- dated photos in `07-construction/13-photos/`;
- programme, lookahead, and milestone tracker in `06-programme/`;
- for D&C design-fee or design-milestone claims, the design fee basis, design programme, design deliverables register, design responsibility matrix, consultant deliverable evidence, and certifier submission status;
- defects records in `07-construction/11-defects/` for completion-stage claims;
- BASIX, OC, commissioning, or authority evidence where a completion-stage claim depends on them.

Medium-relevance evidence:

- drawings and specifications defining physical stage requirements;
- procurement records that explain subcontractor scope;
- owner-supplied items register where late owner supply affects completion or withholding;
- RFI / notice records where an unresolved technical question blocks physical completion.

The sweep returns a relevance-ranked inventory and a gap report. Gaps are not papered over. They become assessment qualifications, action rows, evidence-request drafts, or refusal-to-assess blockers depending on severity.

### Step 3 - Identify claim role, contract family, and claim type

From the sweep and caller input, classify:

| Question | Required classification |
|---|---|
| Who submitted the claim? | builder to owner, subcontractor to builder, consultant/administered claim, owner-builder paying trade |
| Who is assessing? | builder, owner-builder, architect-PM, D&C, Superintendent / administrator where named |
| Contract family | HIA Lump Sum, HIA Renovation, HIA Cost Plus, HIA Trade, MBA equivalent, NSW Fair Trading prescribed, AS 4000, AS 4902, ABIC, other |
| Claim mechanism | stage payment, actual-cost substantiation, measured work, milestone, completion / final claim, retention / security release |
| Payment pathway | amount claimed, assessment date, response due date, payment due date, statutory timing concerns |

If classification is ambiguous, ask before drafting. Do not infer a Superintendent, payment schedule, or statutory response path from general knowledge where the executed contract does not establish it.

### Step 4 - Contract evidence gate

Before any clause-cited assessment:

1. Confirm the executed contract is available.
2. Confirm any special conditions affecting payment, variation, withholding, EOT, defects, PC, or dispute timing have been read.
3. Confirm the claim / payment / assessment clause text is available.
4. Confirm the relevant stage definition text is available for stage-payment claims.

If any required clause text is missing, stop. Return:

> Cannot produce a clause-cited progress claim assessment yet: the executed contract or relevant clause text is missing from project evidence. I can describe the generic residential mechanism from the seeds, but I cannot recommend payment, withholding, or issue a payment response until the executed clause text is available.

The generic explanation may be `advice-only` and must be labelled as general guidance. It must not be filed as a project-specific assessment.

### Step 5 - Select the assessment path

Choose one of the following paths.

#### Path A - HIA / MBA Lump Sum or Renovation stage-payment claim

Assess against the executed stage definition, not percentage complete.

Required checks:

- stage claimed matches a contract stage;
- stage definition quoted or excerpted from the executed contract;
- physical stage achieved according to the contract definition;
- supporting trade evidence is present;
- prior claims for earlier stages are assessed / paid / disputed;
- cumulative claimed amount plus this claim does not exceed contract sum plus signed variations;
- unsigned variations are excluded from payable contract value;
- retentions, security, defects withholding, set-off, or special condition adjustments are applied only where supported by the executed contract;
- response and payment dates match contract and statutory timing.

Typical evidence by stage:

| Stage | Evidence to look for | Common gap |
|---|---|---|
| Deposit | executed contract, HBCF / HOW evidence where required before deposit, deposit cap check | deposit sought before HBCF / HOW certificate |
| Base / slab | reinforcement inspection, certifier inspection, CFT / concrete conformance, slab photos, survey if required | slab poured but inspection certificate missing |
| Frame | structural inspection, bracing evidence, frame photos, engineer sign-off where required | "frame complete" claimed before bracing / engineer sign-off |
| Lockup | roof, external cladding, windows, external doors, lockable / weatherproof evidence | missing external door / window, not actually lockup |
| Fixing | internal linings, internal doors, architraves, cabinetry, wet-area / trade sign-offs | partial fixing claimed as complete |
| Completion | PC readiness, defects position, final inspection, BASIX final / OC pathway evidence where required | completion claim before PC / OC / BASIX evidence is ready |

#### Path B - HIA / MBA Cost Plus claim

Assess actual costs incurred, not stage achievement.

Required checks:

- claim period stated;
- invoices, supplier statements, subcontractor claims, wage records, timesheets, plant records, and margin calculation attached;
- costs are within the contracted scope or written directions;
- margin and GST basis match the executed contract;
- duplicate invoices and already-paid items are excluded;
- owner inspection rights / substantiation rights are acknowledged where the contract provides them;
- provisional or unevidenced costs are not certified as Fact.

#### Path C - NSW Fair Trading prescribed small-job contract

Assess against the simplified payment mechanism in the executed prescribed form.

Required checks:

- written contract value and payment instalments;
- deposit cap;
- completion / milestone evidence;
- any special payment terms;
- statutory written contract requirements;
- payment response timing.

This path is intentionally lighter, but still uses the executed contract. Do not import HIA stage definitions into a prescribed small-job contract.

#### Path D - AS 4000 / AS 4902 / ABIC / administrator-assessed claim

Assess within the named administrator / Superintendent / architect pathway.

Required checks:

- administrator role named in the contract;
- claim submitted to the correct party in the required form;
- claim period and supporting evidence;
- Superintendent / architect assessment timeframes;
- security, retention, set-off, latent condition, EOT, or variation interactions;
- for AS 4902 / D&C design-fee claims, the design fee basis, design deliverable status, DRM responsibility, consultant evidence, and certifier submission status where the milestone depends on them;
- certificate draft content, if the project lead is the administrator.

Do not let a builder self-certify an administrator-assessed claim unless the contract makes that role theirs.

### Step 6 - Assess physical completion and evidence quality

For stage-payment claims, prepare an assessment table with at least:

| Field | Requirement |
|---|---|
| Stage claimed | Contract stage name, not a site nickname |
| Contract definition / clause reference | Clause number and exact quoted or excerpted text from executed contract |
| Evidence required | Evidence needed to prove the stage |
| Evidence found | Project evidence paths |
| Evidence gap | Missing proof, unclear scope, or conflicting evidence |
| Fact / Assumption / Judgement label | Per `../../00-doctrine/doctrine.md Sec. evidence-discipline` |
| Assessment result | achieved, partly achieved, not achieved, cannot assess, or cost-plus substantiation result |
| Recommended response | pay, part-pay, withhold, request evidence, dispute, or escalate |

For cost-plus and measured claims, replace physical stage with substantiation checks:

- cost item;
- invoice / wage / subcontract evidence;
- scope basis;
- margin basis;
- GST basis;
- prior payment duplication check;
- Fact / Assumption / Judgement label;
- assessment result.

Every unevidenced item remains an Assumption or gap. Do not certify assumptions.

### Step 7 - Assess arithmetic, cumulative position, and withholding

Prepare a cumulative payment table:

| Item | Requirement |
|---|---|
| Original contract sum | Fact from executed contract |
| Signed variations to date | Fact from signed variation register only |
| Current contract value | Judgement: contract sum plus signed variations |
| Prior assessed / certified amount | Fact from prior assessments or claim register |
| Prior paid amount | Fact from payment records where available |
| Amount claimed now | Fact from current claim |
| Amount assessable now | Judgement based on contract entitlement and evidence |
| Amount recommended payable | Recommendation |
| Amount withheld / disputed | Recommendation with reason and clause / evidence basis |
| Claim balance after assessment | Judgement |

Rules:

- Unsigned variations do not increase the contract value for payment entitlement.
- Pending PC sums, owner-supplied items, or forecast costs may be noted as risk or forecast only.
- Withholding must cite the contract basis, evidence gap, defects basis, or set-off basis. Do not withhold punitively.
- GST basis must be explicit.
- If the arithmetic cannot reconcile, stop and surface the mismatch before recommending payment.

### Step 8 - Draft the progress claim assessment

For `markdown-only` and `markdown-then-response`, invoke `../atomic/markdown-draft-for-review.md` with:

- **Target folder** - `07-construction/05-progress-claims/`;
- **Target filename** - `claim-assessment-<stage-or-claim-id>-v<NN>.md`;
- **Asserted voice** - `contractual`;
- **Seed list consulted** - the seeds loaded at Step 1;
- **Evidence references** - the evidence from Step 2 used in the assessment.

Required sections:

1. **Project and claim header** - project slug, claim reference, claimant, assessor role, contract family, claim stage / period, date, status draft.
2. **Source evidence used** - evidence list with paths and relevance.
3. **Contract mechanism and clause excerpts** - contract form, edition/date if available, payment clause, stage definition, assessment / response timing, withholding / defects / set-off clause where relied on.
4. **Claim summary** - amount claimed, GST basis, stage / period, date submitted, response due date, payment due date.
5. **Assessment table** - stage-completion or cost-substantiation assessment with evidence labels.
6. **Cumulative payment table** - contract sum, signed variations, prior claims, assessed amount, payable recommendation.
7. **Evidence gaps and qualifications** - specific missing evidence, not generic "more info needed".
8. **Recommendation** - pay, part-pay, withhold, request evidence, dispute, or escalate. Label as Recommendation.
9. **Draft payment response / evidence request** - where mode is `markdown-then-response`; this is a draft only.
10. **Register rows proposed** - progress claim row and any linked rows.
11. **Escalations** - time, cost, defect, compliance, owner decision, or notice triggers.
12. **Next action** - owner, due date, and exact next step.

The draft remains `status: draft`. The agent does not certify payment, approve a claim, issue a payment schedule, or mark any source-of-truth record reviewed.

### Step 9 - Draft payment response or evidence request

For `markdown-then-response`, include a formal response section or separate draft in the same folder, depending on project convention.

Minimum content:

- addressed party and contract role;
- claim reference and received date;
- amount claimed;
- amount assessed;
- amount recommended payable;
- amount withheld / disputed, with reasons;
- clause references and clause text relied on;
- evidence relied on;
- evidence still required, with due date;
- payment due date or response due date;
- draft status and human review note.

If the project uses a statutory payment schedule regime, confirm the applicable state legislation and contract trigger before using statutory terms. If this is unclear, ask. Do not invent Security of Payment mechanics from NSW guidance for non-NSW projects.

### Step 10 - Draft register rows

Use `../atomic/register-row-draft.md` for each row the assessment creates.

At minimum:

- **Progress claim register** - one row for the claim, status `issued`, `assessed`, `certified`, `paid`, or `disputed` as appropriate.

Where triggered:

- **Cost register** - if the assessed amount changes the current cost position.
- **Variation register** - if the claim includes unregistered variation content; usually create an action to regularise rather than treating it as signed.
- **EOT register** - if the claim or response depends on granted / pending time relief.
- **Action register** - for missing evidence, response chasing, or human review.
- **Risk register** - for repeated unsupported claims, cashflow pressure, or entitlement uncertainty.
- **Defects register** - where completion-stage withholding is defect-based.
- **Inspection register** - where inspection evidence is missing or must be booked.
- **RFI register** - where a technical answer is needed before assessment.
- **Contractual notices register** - where the response is a formal notice or payment dispute notice.

Each row must satisfy the seven-field register schema: ID, description, owner, status, due date, source, next action. Do not produce placeholder rows with `TBC` owner, due date, or source.

### Step 11 - Surface gaps and escalations

Surface all gaps from the evidence sweep and assessment. Escalations commonly include:

- claim submitted before the stage is physically achieved;
- executed contract or clause text missing;
- special condition alters payment / EOT / withholding timing;
- HBCF / HOW or LSL evidence missing where deposit / mobilisation payments are being claimed;
- cumulative claimed amount exceeds contract value plus signed variations;
- unsigned variations included in a claim;
- cost-plus claim lacks invoice / wage substantiation;
- completion-stage claim made before BASIX final, OC, PC walk, or defects position is clear;
- D&C design-fee or design-milestone claim lacks design deliverable, DRM, consultant, or certifier submission evidence;
- response deadline is close or missed;
- payment dispute or statutory payment schedule deadline may apply;
- repeated unsupported claims indicate contract administration risk.

Escalation routing follows the loaded role overlay:

- `builder` - owner or owner's representative under the contract, consultant / engineer for technical questions, formal notices via `07-construction/08-rfi-notices/`.
- `architect-pm` - owner-facing recommendation summary plus formal assessment record where appointed.
- `owner-builder` - self-flag log and subcontractor response path.
- `d-and-c` - as builder, plus design-side escalation to the certifier, responsible consultant, owner, or PI insurer where claim evidence depends on design compliance, consultant responsibility, PPR choices, or design liability.

Route each escalation through `escalation-note-system.md` and report the trigger, route and recommended action in the return summary.

Do not suppress an escalation to keep the workflow moving. Per `../../00-doctrine/doctrine.md Sec. escalation-triggers`.

### Step 12 - Return summary

Return:

- mode used;
- claim reference and contract family;
- seeds loaded and `seed_consulted:` list used in drafts;
- evidence found and evidence gaps;
- assessment result;
- payable recommendation;
- payment response / evidence request drafted, if any;
- register rows proposed;
- escalations surfaced;
- next action, owner, and due date.

## Rule

This skill is the canonical SiteWise entry point for residential progress claim assessment. Other manual paths are valid, but they lose the discipline this skill enforces: Sec. 2 gate, seed consultation, executed-contract clause check, evidence sweep, Fact / Assumption / Judgement / Recommendation labelling, register rows, draft-only output, folder-driven contractual voice, and active-project boundary.

This skill **does not approve, certify, issue, pay, or reject** a claim as a contractual act. It drafts an assessment and a response for human review.

This skill **does not rewrite the executed contract or source-of-truth payment records**. It reads them and drafts reviewable outputs.

This skill **does not treat stage names as proof of completion**. The contract definition and physical evidence decide entitlement.

This skill **respects `../../AGENTS.md Sec. 11` active-project boundary**. It reads and writes only inside the active project folder.

## Skill skeleton inheritance

This skill inherits the slice-06+ skeleton:

1. Pre-flight: Sec. 2 declaration gate.
2. Step 1: `seed-targeted-read` with task subject.
3. Step 2: `evidence-sweep` with task subject.
4. Steps 3-10: claim-specific classification, contract evidence gate, assessment, draft, and register rows.
5. Step 11: surface gaps and escalations.
6. Step 12: return summary.

The sibling `variation-management-system.md` uses the same skeleton for variations. `handover-pc-system.md` in slice 13 consumes completion-stage evidence and final claim context; this skill references that evidence but does not become the handover system.

## See also

- `../../AGENTS.md Sec. 1` (authority stack), `Sec. 2` (declaration gate), `Sec. 3` (seed loading rules), `Sec. 5` (output discipline), `Sec. 6` (voice register), `Sec. 8` (state handling), `Sec. 9` (skill invocation), `Sec. 11` (active-project boundary)
- `../../00-doctrine/doctrine.md Sec. seed-consultation-discipline`, `Sec. evidence-discipline`, `Sec. register-discipline`, `Sec. decision-discipline`, `Sec. escalation-triggers`, `Sec. voice-and-style`, `Sec. owner-communication`
- `../../01-seed/role-builder.md` - builder-side progress claim issuance and subcontractor claim posture
- `../../01-seed/contract-administration-guide.md` - payment mechanism, clause citation, notice timing, contract family differences
- `../../01-seed/cost-management-principles.md` - HIA stage-payment assessment, signed variations, GST, claim arithmetic
- `../../01-seed/program-scheduling-guide.md` - programme stage, EOT support, and cycle-time context
- `../../01-seed/new-dwelling-guide.md` or other Tier 2 archetype seed per `archetype:`
- `../atomic/seed-targeted-read.md` - loaded at Step 1
- `../atomic/evidence-sweep.md` - loaded at Step 2
- `../atomic/markdown-draft-for-review.md` - used for claim assessments and payment response drafts
- `../atomic/register-row-draft.md` - used for progress claim, cost, action, EOT, defects, RFI, and notice rows
- `contract-setup-system.md` - opens claim-related registers and records the payment mechanism
- `cost-plan-system.md` - consumes claim totals and updates the cost position after review
- `variation-management-system.md` - sibling system for variations, including variations that appear inside claims
- `risk-register-system.md` - consumes repeated or material claim risks
- (Slice 13) `handover-pc-system.md` - future system for PC, OC, defects, DLP, and final claim packaging
