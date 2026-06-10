# System skill: procurement-evaluation-system

**Job:** End-to-end residential procurement evaluation workflow. Orchestrates seed loading, evidence sweep, role-driven branch detection, and stage-aware drafting into a single workflow. Branches on `user_role:` — **Branch A** for informal subcontractor quote comparison (builder / D&C sourcing subbies), **Branch B** for formal head-builder selection (owner-builder, architect-PM). Produces deliverables under `05-procurement/0X-*` subfolders per the project template, with voice register driven by the destination subfolder per `../atomic/markdown-draft-for-review.md`'s voice / folder table.

This is the **third system skill in SiteWise**, inheriting the `seed-targeted-read` → `evidence-sweep` → content atomics → drafts → registers → return-summary skeleton documented in `contract-setup-system.md §"Skill skeleton — for slices 06+ to inherit"` and applied in `cost-plan-system.md`. The skeleton is load-bearing.

This skill enforces the §2 three-overlay declaration gate at its pre-flight. It enforces the role-overlay-must-exist precondition for Branch B at its branch detection. It refuses to substitute general LLM knowledge for an absent role overlay seed (per `../../00-doctrine/doctrine.md §seed-consultation-discipline`).

## When called

Called by:
- the agent when the user asks for a procurement strategy, tender pack, quote comparison, EOI invitation, RFT pack, evaluation matrix, or tender recommendation;
- the agent when the user asks "which subbie should I award?" (Branch A) or "which builder should the owner sign with?" (Branch B);
- the agent when the user asks for a procurement re-run after a clarification, addendum, or new submission;
- as a stage advance when a formal tender has progressed (e.g. EOI shortlist settled, now produce the RFT pack).

Boundary note:

- Formal EOI / RFT / tender-period / evaluation / recommendation stages are procurement-process stages for contractor or subcontractor selection. They are not the project delivery stage regime.
- Consultant procurement for architect, structural, civil, hydraulic, services, BASIX, certifier or similar design-side appointments is controlled by `consultant-coordination-system.md` and filed under `02-consultant/`, even where this procurement skill's evaluation logic is useful by analogy.
- Consultant RFP scope and fee stages must map to the PMP programme / staging regime. A saved consultant RFP must be for one selected discipline and saved as `consultant_procurement_<discipline>_vNN.draft.md` under `02-consultant/`. If the target consultant discipline is not selected, the consultant workflow must build the appointment / status tracker first and ask which discipline should be procured next; it must not save a generic multi-discipline choice list as the RFP.

The skill is **idempotent** — re-running on a project with an existing procurement draft does not duplicate; it produces `<file>-v<NN+1>.md` and marks the prior `status: superseded` per `../atomic/markdown-draft-for-review.md §"Step 5 — Write to the target folder + filename"`'s supersede behaviour.

## Caller passes

- **Active project folder path** — required.
- **Trade or package name** (optional for Branch B; typically required for Branch A) — e.g. `framing`, `roofing`, `electrical`, or `head-contract`. Drives the comparison matrix filename and the evidence sweep focus.
- **Mode** — one of `advice-only` (commentary only, no draft file), `markdown-only` (draft markdown to `05-procurement/`), or `markdown-then-issue` (draft markdown + flag the next-step issuance task such as RFT distribution or subbie award notification). Required. The user's intent is captured at the mode-confirmation step within each branch.
- **Stage hint** (Branch B only, optional) — one of `eoi`, `rft`, `tender-period`, `evaluation`, `recommendation`. Defaults to auto-detect from evidence sweep; the user can override.

The skill reads everything else it needs from the project folder.

## Pre-flight — Step 0: §2 declaration gate

Before any work:

1. Read the project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC` (per `../../AGENTS.md §2` and `../../00-doctrine/doctrine.md §seed-consultation-discipline`).
3. **If any is missing, blank, or `TBC`:** **stop**. Return:
   > Cannot run procurement evaluation: the README is missing one or more required overlay declarations. Please declare `archetype`, `user_role`, and `state` in the frontmatter before any phase-gate work. Per `../../AGENTS.md §2` and `../../00-doctrine/doctrine.md §seed-consultation-discipline`, the agent does not guess these from project name, address, budget, site, or any other proxy.
4. **Do not load any seed, do not run evidence-sweep, do not draft.** The gate is binary.

The gate is enforced at the system-skill level **and** at the seed-loading boundary (`../atomic/seed-targeted-read.md` also enforces it). The redundancy is intentional — system skills are the canonical entry point for phase-gate work per `../../AGENTS.md §9`, and the gate is checked at the boundary the user typically crosses.

If the user is mid-flow and wants the gate bypassed, the gate is **not** bypassed. Offer to help complete the declaration, but do not proceed with procurement work until it is complete.

## Steps

### Step 1 — Detect branch from `user_role:`

Read `user_role:` from the project README (already confirmed declared at Step 0).

| `user_role:` | Branch | Notes |
|---|---|---|
| `builder` | **Branch A** (informal subbie quote comparison) | Builder is sourcing subcontractors for trade packages |
| `owner-builder` | **Branch B** (formal head-builder selection) **or** **Branch A** (subbie comparison) | Owner-builder is both principal and contractor; the caller's task signal (trade name vs head-builder request) determines branch. If ambiguous, ask. |
| `architect-pm` | **Branch B** (formal head-builder selection) | Architect-PM is running tender for owner |
| `d-and-c` | **Branch A** (subcontractor or design-side consultant comparison) **or** clarifying question | If the task is sourcing a subcontractor or a consultant for the D&C's design responsibility, Branch A. If the task is "we are the procuree being evaluated by an owner", **return a clarifying question** — do not guess. The D&C is not running their own procurement against themselves. |

**Branch B precondition.** Before entering Branch B, confirm the required role overlay seed exists in `../../01-seed/`:

- For `user_role: owner-builder`, confirm `role-owner-builder.md` exists.
- For `user_role: architect-pm`, confirm `role-architect-pm.md` exists.

**If the required role overlay seed does not yet exist:** **stop**. Return:
> Cannot run Branch B for `user_role: <role>`: the role overlay seed `<role-overlay.md>` has not yet been authored (slice 07 / 08 will author it). Per `../../00-doctrine/doctrine.md §seed-consultation-discipline`, this skill does not substitute general LLM knowledge for an absent role overlay. Branch B requires the role overlay loaded. Either author the role overlay first (see issue 07 / 08 in `../../../issues/`) or proceed with Branch A if the task is subcontractor procurement only.

This refusal is not papered over. The agent does not silently fall back to general LLM knowledge for role-specific obligations.

For `user_role: d-and-c` with ambiguous task subject:
> Cannot determine procurement branch for `user_role: d-and-c`. Are you sourcing a subcontractor or design consultant (Branch A), or are you the head contractor being procured by an owner (in which case this skill does not apply — the owner is the procurer, not you)? Please clarify the procurement task and re-invoke.

### Step 2 — `seed-targeted-read`

Invoke `../atomic/seed-targeted-read.md` with task subject:
- Branch A — `residential subcontractor quoting` or `D&C consultant procurement`;
- Branch B — `residential head-builder selection`.

The skill loads:

- **Tier 2 archetype seed** — one of `new-dwelling-guide.md`, `renovation-guide.md`, `multi-dwelling-guide.md`, `ancillary-guide.md`, or `small-commercial-guide.md` per `archetype:`.
- **Tier 3 role overlay** — one of `role-builder.md`, `role-architect-pm.md`, `role-owner-builder.md`, or `role-d-and-c.md` per `user_role:`. The role overlay carries the role-divergent procurement responsibilities (who issues tender, who evaluates, who awards) and the escalation routing. For `user_role: d-and-c`, `role-d-and-c.md` adds design-side consultant procurement, PI evidence, design responsibility matrix, and certifier submission consequences to the builder-style Branch A comparison.
- **Cross-cutting topic seeds** — required for procurement work:
  - `procurement-quoting-guide.md` — required (this skill's primary topic seed);
  - `contract-administration-guide.md` — required for Branch B (the contract form to be executed after recommendation), recommended for Branch A (variation mechanism reference for subbie scope discipline);
  - `setup-and-commission-guide.md` — required for Branch B (the commissioning workflow procurement feeds into at contract execution);
  - `cost-management-principles.md` — required for both branches (PC sums, owner-supplied items, variation pricing inform the comparison and the recommendation).
- **Optional cross-cutting seeds** — loaded if the task subject signals:
  - `program-scheduling-guide.md` if procurement decisions touch the master programme (typical at RFT issue and at recommendation);
  - `sustainability-energy-guide.md` if BASIX / energy compliance method is a material evaluation factor (slice 12; loaded when present).
- For non-NSW states, the agent **flags state-coverage gaps** where the seeds reference NSW-specific instruments without callouts (per `../../AGENTS.md §8`). Common gaps for procurement work: HBCF (NSW) vs DBI (VIC) vs QBCC HWI (QLD); LSL (NSW) vs CoINVEST (VIC); Security of Payment regime mechanics; builder registration body (NSW Fair Trading vs VBA vs QBCC).

The loaded seed list is held for use in `seed_consulted:` frontmatter on every deliverable this skill produces. Empty `seed_consulted:` on a procurement deliverable is a §seed-consultation-discipline failure per `../../00-doctrine/doctrine.md`.

### Step 3 — `evidence-sweep`

Invoke `../atomic/evidence-sweep.md` with the task subject from Step 2.

For **Branch A** (subbie procurement), the sweep returns high-relevance artefacts including:

- the executed head contract (defines scope to be subcontracted, PC sums, owner-supplied items, programme);
- drawings and specification in `03-design/04-ifc/` (the scope baseline for the trade package);
- BASIX certificate in `04-planning-and-authorities/` (drives specification cost — windows, HW, insulation, PV);
- prior trade package quotes if any (`05-procurement/<trade>/04-submissions/` or similar);
- subbie register if open (`05-procurement/subcontractor-register.md`);
- prior subbie comparison drafts (for re-run idempotency);
- existing site management plans (`07-construction/04-management-plans/` — affects subbie WHS, hours, access).
- for `user_role: d-and-c`, consultant appointment / novation evidence, design responsibility matrix, design programme, design deliverables register, consultant PI evidence, and certifier submission schedule where the package is design-side consultant procurement rather than trade procurement.

For **Branch B** (head-builder selection), the sweep returns high-relevance artefacts including:

- brief and design package in `00-brief-pmp/`, `03-design/`;
- specification, drawings, BASIX certificate, planning approvals;
- contract-form decision (recorded in `00-brief-pmp/contract-summary.md` if commissioning has run, else inferred from project scale and architect-PM advice);
- prior EOI responses (`05-procurement/01-eoi/04-submissions/` or similar) for re-run idempotency;
- existing tenderer longlist or shortlist (in decision register or correspondence);
- prior RFIs and addenda (`05-procurement/03-rfi-addendum/`);
- prior evaluation matrix drafts (`05-procurement/05-evaluation/`);
- owner decision log entries relating to procurement (`08-meetings-reporting/decision-register.md`).

The sweep also returns a **gap report** — expected-but-missing artefacts. Common gaps for procurement work: BASIX certificate not yet issued (tender pack must label as Assumption or hold issuance); specification not finalised (tender pack premature); contract form not decided (RFT cannot draft the Conditions of Contract); financial standing evidence not gathered (cannot evaluate fully).

### Step 4 — Confirm mode with the project lead

Before producing any draft, the skill confirms with the user which mode applies (caller may have specified at invocation):

- **`advice-only`** — produce commentary or a structured response in the conversation. No file written. Used when the user wants quick procurement advice without creating a draft (e.g. "is this tender response complete enough to evaluate?").
- **`markdown-only`** — produce procurement draft(s) at the appropriate `05-procurement/0X-*` path via `../atomic/markdown-draft-for-review.md`. No external issuance flagged.
- **`markdown-then-issue`** — produce procurement draft(s) as above; surface the next-step issuance task explicitly (e.g. "RFT pack ready for issue to shortlisted tenderers — confirm distribution list and closing date before issue", or "subbie award recommendation ready — confirm contractual notification path before contacting the awarded subbie"). The skill **does not** issue tender packs or award notifications itself — those are contractual acts done by the project lead.

The mode confirmation is a contractual moment. **Do not draft beyond the agreed mode.**

### Step 5 — Branch A: Informal subbie quote comparison

Branch A produces a single primary deliverable: a comparison matrix.

1. **Identify the trade package** (from caller's `trade or package name`).
2. **Establish the scope baseline.** From the evidence sweep, gather the drawings and specification references that define the trade scope. If the scope baseline is not established (no IFC drawings yet, specification still in draft), flag the premature procurement and ask the builder to confirm proceeding with explicit scope-as-stated.
3. **Draft the comparison matrix** via `../atomic/markdown-draft-for-review.md` with:
   - **Target folder** — `05-procurement/05-evaluation/`;
   - **Target filename** — `<trade>-comparison-v<NN>.md` (e.g. `framing-comparison-v01.md`, `electrical-comparison-v01.md`);
   - **Asserted voice** — `stakeholder` (the audience is the builder, not the owner; per `../atomic/markdown-draft-for-review.md`'s voice / folder table, `05-procurement/05-evaluation/*comparison*` is stakeholder);
   - **Seed list consulted** — the seeds loaded at Step 2;
   - **Evidence references** — the artefacts found at Step 3.

   #### Required columns in the comparison matrix

   Per `../../01-seed/procurement-quoting-guide.md §2`:

   - Quoter (subbie name + contact);
   - Quote reference (email date, PDF filename);
   - Lump sum or schedule of rates (pricing basis stated);
   - Scope inclusions;
   - Scope exclusions (the scope-gap risk);
   - Programme (start availability and duration);
   - Lead time (material order time);
   - References (past projects, recency, reachability);
   - Licence + insurance check (builder's licence where applicable, public liability, workers comp);
   - Payment terms;
   - Total compared (after scope normalisation);
   - Risk flags (scope gaps, capability concerns);
   - Fact / Assumption / Judgement label per row (per `../../00-doctrine/doctrine.md §evidence-discipline`).

4. **Surface scope gaps explicitly.** If quote 2 is silent on a scope item that quote 1 priced, the matrix records this as a scope gap **before** the total-compared column is calculated. Silent scope imputation is a §evidence-discipline failure. Per `../../01-seed/procurement-quoting-guide.md §2`.
5. **Optional recommendation paragraph** on request from the builder. If the builder wants a recommendation, the skill produces a short paragraph naming the recommended subbie, the reasoning (price-normalised vs capability vs availability), and the risk flags. If not requested, the matrix stands without a recommendation — the award decision is the builder's.
6. **Update the subcontractor register** (if it exists) via `../atomic/register-row-draft.md` once the builder has awarded. The register row carries the subbie ID, trade, contract sum, lead time, status (`quoted`, `awarded`, `mobilised`, `on-site`, `complete`).

Branch A does **not** auto-issue any subcontract notification. The builder awards manually — the skill provides the comparison, not the award act.

### Step 6 — Branch B: Formal head-builder selection (stage-aware)

Branch B is stage-aware. The skill identifies the current stage from the evidence sweep and produces the stage-appropriate deliverable. If the stage is ambiguous, ask before drafting.

#### 6.1 — Stage detection

From the evidence sweep:
- If `05-procurement/01-eoi/` is empty or has only a draft EOI pack, current stage is **EOI**.
- If `05-procurement/01-eoi/04-submissions/` has EOI responses but `02-tender-pack/` is empty, current stage is **EOI evaluation / shortlist** (Branch B Stage 1 evaluation; treated as part of EOI stage).
- If `02-tender-pack/` has a draft RFT pack but `04-submissions/` is empty, current stage is **RFT**.
- If `04-submissions/` has tender returns but `05-evaluation/` is empty, current stage is **Evaluation**.
- If `05-evaluation/` has an evaluation matrix but `06-recommendation/` is empty, current stage is **Recommendation**.
- If `06-recommendation/` has a recommendation, the skill is operating in re-run mode — flag and ask whether to refresh the recommendation or to take the next contract-execution action (handled by `contract-setup-system`).

Caller's `stage hint` overrides auto-detection.

#### 6.2 — EOI stage

Produce `05-procurement/01-eoi/eoi-pack-v<NN>.md` via `../atomic/markdown-draft-for-review.md` (asserted voice **contractual**, folder `05-procurement/01-eoi/`).

Required content per `../../01-seed/procurement-quoting-guide.md §5.1`:

- project summary, indicative scope, indicative programme;
- EOI response template (qualifications-only — no price);
- qualification criteria (capability, capacity, references, financial standing, builder's licence, HOW capacity);
- return date and lodgement format;
- contact protocol (RFIs anonymised and circulated, addenda mechanism);
- owner privacy notes (the owner's identity may or may not be disclosed at EOI — confirm with owner);
- evaluation criteria for shortlist (qualitative weighting).

On EOI responses received, produce `05-procurement/05-evaluation/eoi-evaluation-v<NN>.md` (contractual). Shortlist decision recorded in `08-meetings-reporting/decision-register.md` via `../atomic/register-row-draft.md`.

#### 6.3 — RFT stage

Produce `05-procurement/02-tender-pack/rft-pack-v<NN>.md` via `../atomic/markdown-draft-for-review.md` (contractual, folder `05-procurement/02-tender-pack/`).

Required content per `../../01-seed/procurement-quoting-guide.md §5.2` and §6:

- Conditions of Tender (closing date, lodgement, validity, evaluation criteria summary, RFI protocol, addenda mechanism, evaluation rights);
- Form of Tender (binding offer template);
- Draft Conditions of Contract reference (the contract form decided in commissioning — HIA / MBA / NSW Fair Trading / AS — with Particulars pre-filled and Special Conditions flagged);
- Scope of Works (prose, cross-referenced to drawings and specification);
- Drawings reference (IFC or near-IFC set listed by drawing number and revision);
- Specification reference (NATSPEC or project-specific; finishes schedule with PC items identified);
- Programme (indicative; tenderers refine);
- Schedule of Rates for Variations (rates the builder will use for future variations);
- Returnable Schedules list (Trade Breakdown, Schedule of Rates, Key Personnel, Programme, Departures, Insurance evidence, HOW evidence, References);
- Information documents list (geotechnical, dilapidation, BAL, BASIX, planning consent — "for information only, not part of the contract").

On RFT issued, the tender period begins. RFIs and addenda are tracked in `05-procurement/03-rfi-addendum/` per `../../01-seed/procurement-quoting-guide.md §5.3`.

#### 6.4 — Evaluation stage

Produce `05-procurement/05-evaluation/evaluation-matrix-v<NN>.md` via `../atomic/markdown-draft-for-review.md` (contractual — the matrix defends the recommendation).

Required columns per `../../01-seed/procurement-quoting-guide.md §5.4`:

- Tenderer;
- Lump sum (ex GST and inc GST shown separately);
- Departures and qualifications (verbatim from Schedule of Departures);
- Scope normalisation adjustments (Judgement-labelled);
- Normalised lump sum (apples-to-apples);
- Proposed programme;
- Proposed methodology;
- References (called and rated);
- Financial standing (ASIC search + financial returns where supplied);
- Capacity (current pipeline, key personnel committed);
- Builder licence + class + currency (NSW Fair Trading record);
- HOW / HBCF eligibility + capacity remaining (builder declaration + iCare confirmation);
- Contract works + PL + workers comp Certificate of Currency;
- BASIX / energy compliance method declared;
- Weighted score per criterion;
- Total weighted score;
- Commentary (architect-PM / evaluator narrative);
- Risk flags (explicit);
- Fact / Assumption / Judgement label per row (per `../../00-doctrine/doctrine.md §evidence-discipline`).

**Weights are project-specific and declared up front in the matrix.** Default residential weighting per `../../01-seed/procurement-quoting-guide.md §7`: price 50–60%, programme and methodology 15–20%, capability 15–20%, departures 5–10%, schedule of rates 5%. Confirm with the project lead before scoring; do not retrofit.

Where probity discipline is being applied (per `../../01-seed/procurement-quoting-guide.md §9`), produce the matrix as **two parallel drafts**: `05-procurement/05-evaluation/price_evaluation_v<NN>.md` and `05-procurement/05-evaluation/non_price_evaluation_v<NN>.md`. The non-price draft is settled first (qualitative scoring blind to price), then the price draft is overlaid. This mirrors the commercial parent's discipline (`../../../Harness/02-skills/systems/tender-evaluation-system.md`).

#### 6.5 — Recommendation stage

Produce two parallel drafts:

- `05-procurement/06-recommendation/recommendation-to-owner-v<NN>.md` — **stakeholder** voice per `../atomic/markdown-draft-for-review.md`'s voice / folder table. The owner-facing summary. Follows `../../00-doctrine/doctrine.md §owner-communication`:
  1. What this means for you (recommended tenderer + headline reasoning);
  2. What we need from you (owner's decision and sign-off with due date);
  3. What's happened (procurement process, tenderers, evaluation outcome);
  4. What's next (steps from owner sign-off to contract execution);
  5. Background detail (evaluation matrix, departures normalised, residual risks, conditions of award).

- `05-procurement/06-recommendation/tender_recommendation_v<NN>.md` — **contractual** voice per `../atomic/markdown-draft-for-review.md`'s table. The formal advice record for the architect-PM's file. Contains the structured recommendation: tender process followed, submissions received, price evaluation outcome, non-price evaluation outcome, clarifications and qualifications, recommended tenderer, conditions to satisfy before award, residual risks for owner approval.

Both drafts must:

- name **one** recommended tenderer (not three options — per `../../00-doctrine/doctrine.md §owner-communication` and `../../01-seed/procurement-quoting-guide.md §8`);
- state the conditions of award explicitly;
- surface residual risks the owner is being asked to accept;
- list next steps (owner sign-off, contract execution, mobilisation).

Iterate at each stage; do not progress to the next stage without owner / architect-PM approval. Per `../../01-seed/procurement-quoting-guide.md §5.5`.

### Step 7 — Surface gaps and escalations

Surface explicitly to the user (per `../../00-doctrine/doctrine.md §escalation-triggers` and `../../01-seed/procurement-quoting-guide.md §10`):

- every gap from the Step 3 sweep (e.g. BASIX certificate not yet issued; specification not finalised; contract form not decided);
- every scope gap in a Branch A comparison matrix;
- every probity concern in a Branch B evaluation (e.g. architect-PM's undisclosed prior relationship with a tenderer);
- every procurement-specific escalation trigger:
  - missing builder licence or insurance evidence (tenderer or shortlisted EOI respondent);
  - low-bid quality risk (lowest tender materially below the next with no plausible scope explanation);
  - HOW / HBCF capacity exhausted (per-project capacity already committed elsewhere);
  - BASIX method of compliance not declared in tender;
  - contract form mismatch (AS 4000 proposed where HIA Lump Sum appropriate);
  - owner change request mid-tender (cannot informally accept without notifying tenderers);
  - tender clarification overdue (probity risk);
  - subbie scope gap material to award (Branch A).

Escalation routing follows the role overlay loaded at Step 2:

- **Owner-builder** — self-flag log in `08-meetings-reporting/`.
- **Architect-PM** — owner-facing summary in `08-meetings-reporting/owner-update*` using `§owner-communication` format.
- **Builder** — owner per contract; high-value or contractual triggers via `07-construction/08-rfi-notices/` for the written record. Subbie procurement issues are internal — recorded in the subcontractor register.
- **D&C** — as builder, plus design-side procurement issues route to the owner where PPR, cost, or programme choices are live; to the certifier where compliance is affected; and to the responsible consultant or PI pathway where scope or design liability is live.

Route each escalation through `escalation-note-system.md` and report the trigger, route and recommended action in the return summary.

The skill **does not suppress** any escalation trigger. Per `../../00-doctrine/doctrine.md §escalation-triggers`.

### Step 8 — Return summary

Return a short summary to the user:

- branch taken (A / B);
- stage reached (Branch B only — EOI / RFT / evaluation / recommendation);
- mode used (advice-only / markdown-only / markdown-then-issue);
- seeds loaded (and the `seed_consulted:` list recorded in deliverable frontmatter);
- artefacts found by the sweep (relevance-ranked);
- drafts produced (paths);
- gaps remaining (actions opened);
- escalations surfaced;
- next action and date (e.g. "RFT pack ready for owner review then issue to shortlist by 2026-06-10").

The user reviews the deliverables, fills any gaps (or directs the agent to do so), and either signs off the procurement step as `status: reviewed` or returns for iteration.

## Rule

This skill is the **canonical entry point** for residential procurement evaluation in SiteWise. Other paths (manual tender pack drafting, ad-hoc subbie comparison) are valid but lose the discipline this skill enforces: §2 gate at the boundary, §seed-consultation-discipline via `seed-targeted-read` (including refusal-to-substitute for Branch B's role overlay), §evidence-discipline via `evidence-sweep` and the Fact / Assumption / Judgement / Recommendation labels, §register-discipline via `register-row-draft` for register touches, §5 output discipline via `markdown-draft-for-review`, §6 voice / folder discipline via the same.

This skill is **single-skill-with-role-branch by design.** Per `../../../SiteWise-PRD.md §"Decisions deferred — not blockers"`: the initial design is one skill with a role branch; refactor into two skills only if the role branch becomes a load-bearing if-statement in practice. If during use the branch logic balloons, flag for a later refactor issue — do not split this skill informally.

This skill **does not issue tender packs, send recommendations to owners, or notify awarded subbies**. Those are contractual acts performed by the project lead. The skill produces drafts; the project lead acts.

This skill **does not execute contracts**. Contract execution is handled by `contract-setup-system` after the procurement recommendation has been accepted.

This skill **does not pay claims, sign variations, or issue contractual notices**. Those are human contractual acts.

This skill is **idempotent** — re-running on a project with existing procurement drafts does not duplicate. It produces `<file>-v<NN+1>.md`, marks the prior superseded, and refreshes the comparison or recommendation against the latest evidence.

This skill **respects the `../../AGENTS.md §11` active-project boundary** — operates only within the active project folder.

## Skill skeleton inheritance

This skill inherits the slice-06+ skeleton documented in `contract-setup-system.md §"Skill skeleton — for slices 06+ to inherit"` and applied in `cost-plan-system.md`:

1. **Pre-flight: §2 declaration gate** (Step 0 above).
2. **Step 1: branch detection on `user_role:`** — this skill's role-branch precondition extension to the skeleton.
3. **Step 2: `seed-targeted-read`** with task subject.
4. **Step 3: `evidence-sweep`** with task subject.
5. **Step 4: mode confirmation.**
6. **Steps 5–6: branch-specific content drafting** — Branch A subbie comparison, or Branch B stage-aware drafting (EOI / RFT / Evaluation / Recommendation).
7. **Step 7: surface gaps and escalations** explicitly.
8. **Step 8: return summary** — branch, stage, drafts, gaps, escalations, headline next-action.

The role-branch step (Step 1) is the new element this skill adds to the skeleton. It is a precondition to seed-targeted-read because the skill's seed needs (and its refusal posture for missing role overlays) depend on which branch is selected. Slices 07, 08, 09 will author the missing role overlays this skill currently refuses Branch B for.

Slice 06's `progress-claim-assessment-system` and `variation-management-system`, and slice 13's `handover-pc-system`, inherit the slice-06+ skeleton from `contract-setup-system` and `cost-plan-system`. They do not (currently) need a role-branch step — they operate on a single role's contract administration. If a future skill needs the role-branch precondition, this skill is the pattern to mirror.

## See also

- `../../AGENTS.md §1` (authority stack), `§2` (declaration gate), `§3` (seed loading rules), `§5` (output discipline), `§6` (voice register — `05-procurement/` is contractual by default with stakeholder exceptions for owner-facing recommendations), `§8` (state callouts), `§9` (skill invocation), `§11` (active-project boundary)
- `../../00-doctrine/doctrine.md §seed-consultation-discipline`, `§evidence-discipline`, `§register-discipline`, `§decision-discipline`, `§escalation-triggers`, `§voice-and-style`, `§owner-communication` (the stakeholder-voice format for owner-facing recommendations)
- `../../01-seed/procurement-quoting-guide.md` — the topic seed this skill orchestrates around (informal subbie quoting reality, formal EOI → RFT → evaluation → recommendation pathway, evaluation criteria with weighting discipline, probity discipline scaled to context)
- `../../01-seed/contract-administration-guide.md` — contract form selection and Special Conditions for the contract executed after recommendation
- `../../01-seed/setup-and-commission-guide.md` — commissioning workflow procurement feeds into at contract execution
- `../../01-seed/cost-management-principles.md` — PC sums, owner-supplied items, contingency, variation pricing inform the comparison matrix and the recommendation
- `../../01-seed/new-dwelling-guide.md` (or other Tier 2 archetype seed per `archetype:`) — archetype-shaped procurement context
- `../../01-seed/role-builder.md` (or other Tier 3 role overlay per `user_role:`) — role-divergent procurement responsibilities and escalation routing
- (Slice 07) `../../01-seed/role-owner-builder.md` — required for Branch B with `user_role: owner-builder`; absent until slice 07 lands
- (Slice 08) `../../01-seed/role-architect-pm.md` — required for Branch B with `user_role: architect-pm`; absent until slice 08 lands
- `../../01-seed/role-d-and-c.md` — role overlay for D&C; required for D&C subcontractor and design-side consultant procurement
- `../atomic/seed-targeted-read.md` — loaded at Step 2 (also enforces the §2 gate redundantly)
- `../atomic/evidence-sweep.md` — loaded at Step 3
- `../atomic/markdown-draft-for-review.md` — used for every draft this skill produces; the voice / folder table maps `05-procurement/` paths to the correct register
- `../atomic/register-row-draft.md` — used for subcontractor register, EOI shortlist register, RFI register, decision register entries
- `contract-setup-system.md` — first system skill in SiteWise; the skeleton this skill inherits; handles contract execution after recommendation acceptance
- `cost-plan-system.md` — second system skill in SiteWise; the skeleton this skill inherits; cost-plan baseline informs procurement budget
- (Slice 06) `progress-claim-assessment-system.md`, `variation-management-system.md` — consume the subcontractor and head-contract baselines this skill establishes
- (Slice 13) `handover-pc-system.md` — references the procurement contracting record at handover
- `../../../Harness/01-seed/procurement-tendering-guide.md` — commercial parent of `procurement-quoting-guide.md`; the EOI / RFT / probity machinery originates there
- `../../../Harness/02-skills/systems/tender-evaluation-system.md` — commercial parent of this skill; the parallel price / non-price evaluation discipline originates there
