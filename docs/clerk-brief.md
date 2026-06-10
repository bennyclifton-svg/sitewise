# SiteWise Doctrine — Residential Project Management

This is the practice's concise AI-readable doctrine for **residential** project management work. It is the **judgement layer** — what to think and do. Workspace mechanics (where files live, when to load what, how to write outputs) live in `../AGENTS.md`, not here.

SiteWise serves four user roles across one shared lifecycle: owner-builder, architect-PM (client-side advisory), builder (head contractor), and D&C contractor. The doctrine spine is abstract — **"the project lead"** — and covers the ~80% of obligations common across all four roles. The ~20% of role-divergent content (who takes out HOW, who pays LSL, who issues vs assesses progress claims, etc.) lives in the four role overlay seeds in `../01-seed/`, loaded based on the `user_role:` declaration.

## Authority stack

1. Project evidence in the **active** project folder only — never another project's
2. This doctrine
3. Seed knowledge in `../01-seed/`
4. Reusable skills in `../02-skills/`
5. General LLM knowledge

If project evidence conflicts with doctrine, project evidence wins. If evidence is missing, state the assumption (per `§evidence-discipline`). See `../AGENTS.md §1`.

## The project lead role

The **project lead** is the user of the harness — the abstraction across owner-builder, architect-PM, builder, and D&C. The project lead carries the time, cost, scope, quality, risk, and compliance position of the project. Specific obligations vary by role (see role overlay seeds), but the abstract responsibilities hold across all four.

The project lead must:
- understand the brief, the commercial drivers, and the role they occupy in the contract chain;
- establish governance, decision pathways, and reporting cadence appropriate to the project scale;
- coordinate consultants, contractors, authorities, and the owner (where the project lead is not the owner);
- maintain current registers for cost, programme, risk, actions, decisions, change, defects;
- give early warning on cost, programme, authority, scope, quality, and safety risk;
- keep records that allow decisions and claims to be reconstructed later — including for HOW and statutory warranty exposure;
- meet the statutory obligations that attach to their role (builder's licence, HOW, LSL, BASIX, owner-builder permit, PI insurance — see role overlay).

The project lead must not:
- act outside the scope or competence of their role;
- blur formal roles (e.g. a builder acting as Certifier; an architect-PM acting as Superintendent without express appointment);
- allow informal directions to replace documented approvals;
- present assumptions as project fact;
- silently substitute general knowledge for the role/archetype/state seed that the harness would have loaded if declarations were complete.

## Core principle

The project lead protects the project's time, cost, scope, quality, risk, and compliance position appropriate to their role. The agent supports that role by keeping the brief clear, evidence current, decisions recorded, risks visible, procurement disciplined, delivery controlled, and handover complete — with role-, archetype-, and state-appropriate guidance loaded deliberately, never substituted by general LLM knowledge.

---

# Folder-aligned doctrine

## 00-brief-pmp

Purpose: define what is being built, on what basis, under what role configuration, with what statutory instruments and authority pathway. This folder establishes the project at mobilisation.

The project lead must do:
- declare `archetype`, `user_role`, and `state` in the project `README.md` (the three-overlay declaration is gating per `../AGENTS.md §2`);
- record the brief in a form proportionate to the role: an owner-builder records their self-defined brief and owner-builder permit; an architect-PM records fee proposal, scope of services, PMP, and declaration of any formal role; a builder records tender response, executed contract, builder's licence, HOW evidence, LSL receipt, contract works insurance; a D&C contractor adds design fee, design programme, design responsibility matrix;
- confirm statutory instruments required for the role × state × archetype combination are in place before construction starts;
- identify the planning pathway (CDC, DA, exempt) and authority touch-points;
- define the high-level project stage regime in the PMP programme / staging section where a PMP is used. If project evidence does not define a more specific stage regime, use the baseline: Stage 1 - concept and schematic design to DA submission; Stage 2 - design development; Stage 3 - construction documentation and delivery. If project evidence requires more granularity, map it back to these baseline stages and state why. For multi-dwelling, apartment, staged OC or D&C-signalled projects, ratchet the PMP up to a detailed staged regime covering design/approvals, procurement, enabling, structure, envelope/services/finishes, commissioning, OC, handover and DLP.

The project lead must not:
- proceed past mobilisation with `archetype`, `user_role`, or `state` undeclared, blank, or `TBC`;
- silently assume a planning pathway where the brief or site has not been tested against the controls;
- begin work without the statutory instruments the role requires (e.g. a builder beginning without HOW lodged on a contract ≥ the state's threshold).

Standard deliverables:
- declared project `README.md` with frontmatter complete;
- brief / scope of works (form depends on role);
- PMP programme / staging section stage regime, where a PMP is part of the role setup;
- role-specific setup pack (per role overlay seed):
  - owner-builder: owner-builder permit, self-defined brief, self-flag decision log opened;
  - architect-PM: fee proposal, scope of services, PMP, governance map, role declaration;
  - builder: executed contract, builder's licence, HOW certificate, LSL receipt, contract works insurance;
  - D&C: builder pack **plus** design fee, design programme, design responsibility matrix, PI insurance.

Common failure modes:
- starting work without declared overlays;
- role drift (e.g. architect-PM agreeing to act as Superintendent informally);
- missing statutory instrument discovered mid-construction (typically HOW or LSL);
- planning pathway assumed rather than confirmed.

Agent use cases:
- run the setup checklist for the declared role;
- generate role-appropriate brief / scope template;
- flag missing statutory instruments against role × state requirements;
- draft governance and communications protocol proportionate to project scale.

## 01-cost

Purpose: protect the project's cost position — appropriate to role, scale, and contract type.

The project lead must do:
- maintain a current cost view distinguishing approved budget, forecast, committed, paid, pending variations, and contingency;
- prepare a residential elemental cost plan (HIA Schedule of Allowances format where appropriate, with PC sums for kitchen/bath, owner-supplied allowances, contingency of 5–10%);
- assess progress claims against contract evidence and physical completion — for HIA stage-payment contracts, against the slab / frame / lockup / fixing / completion schedule;
- escalate cost risk early — especially before it becomes unavoidable;
- defer to a QS for material variations or formal cost plans where the project scale warrants.

The project lead must not:
- certify or recommend payment without supporting evidence;
- treat contingency as available scope money;
- hide budget pressure until the next formal milestone;
- mix consultant invoices, contractor claims, and internal forecasts without status clarity.

Standard deliverables:
- elemental cost plan (residential format);
- budget summary and cost report;
- invoice / claim tracker;
- variation register (HIA Schedule of Variations or equivalent);
- contingency register;
- progress claim assessment notes.

Common failure modes:
- PC sums treated as fixed budget rather than allowance;
- owner-supplied items not tracked against budget;
- variations issued verbally and not priced before work begins;
- progress claims paid against stage-payment schedule without verifying physical completion.

Agent use cases:
- draft elemental cost plan in HIA format;
- assess progress claim against stage-payment schedule and physical-completion evidence;
- draft variation register entry with cost + time + scope impact;
- flag budget vs forecast variance.

## 02-consultant

Purpose: ensure the consultant team (where applicable) is complete, scoped, coordinated, and accountable. For owner-builders and small builders, this folder may be lightly populated; for architect-PMs and D&C contractors, it is central.

The project lead must do:
- identify the consultants required for the archetype × planning pathway × NCC class (architect, structural, hydraulic, BASIX assessor, certifier, surveyor, geotechnical, landscape, traffic where required);
- confirm each consultant's scope, deliverables, and fee basis;
- maintain a consultant appointment / status tracker that records each required discipline, evidence source, appointment status, scope stage, fee basis, programme dependency and next action;
- create consultant RFP / procurement artefacts as single-discipline documents unless the task is explicitly an appointment-status preflight review; a saved RFP must name one target discipline and be written for that consultant package; save under `02-consultant/consultant_procurement_<discipline>_vNN.draft.md` so parallel RFPs (for example architect, structural engineer and civil engineer) remain distinguishable;
- map consultant RFP stages, proposal stages and fee milestones to the PMP programme / staging regime where a PMP exists, rather than letting each consultant create a disconnected staging language;
- maintain a consultant advice register where consultant input is material;
- keep design responsibility and certification responsibility clear (especially for D&C — see role overlay).

The project lead must not:
- assume the architect or lead consultant covers specialist scope by default;
- allow client-side or owner stakeholders to direct consultants informally where the role is intermediary;
- let consultant deliverables drift without documented impact on cost, programme, or approvals.

Standard deliverables:
- consultant appointment / status tracker;
- consultant responsibility matrix (especially for D&C);
- deliverables schedule;
- consultant advice register;
- design RFI register.

Common failure modes:
- BASIX assessor or certifier omitted from consultant list at mobilisation;
- structural or hydraulic scope gap discovered during construction;
- verbal consultant advice not captured;
- D&C design responsibility matrix not maintained, leaving certifier submissions disputed.

Agent use cases:
- generate a consultant requirements list from `archetype` + `planning_pathway` + `ncc_class`;
- draft consultant responsibility matrix;
- extract design RFIs from minutes or email.

## 03-design

Purpose: control scope, design decisions, technical coordination, and design risk before procurement and construction. For D&C, this folder carries the design responsibility weight.

Preferred filing structure: file design evidence discipline-first so the folder does not become a loose drawing dump. Use `03-design/<discipline>/` for architect, structural, hydraulic, surveyor, bushfire consultant, geotechnical, arborist, energy assessor and other project disciplines. Where maturity staging matters, place it beneath the discipline folder, e.g. `03-design/architect/02-scheme/` or `03-design/structural/04-ifc/`.

The project lead must do:
- maintain a current view of design status and open decisions;
- ensure design decisions link to brief, budget, planning controls, and NCC compliance (BASIX, BCA Volume Two for Class 1, etc.);
- require options analysis where cost, authority, programme, or BASIX risk is material;
- coordinate design reviews before tender issue and phase gates.

The project lead must not:
- treat drawings as self-explanatory where constraints should be stated in tender documents or the brief;
- allow design to proceed without BASIX modelling feedback;
- let stakeholder or owner preferences become scope changes without approval and cost impact;
- (D&C only) submit construction design to certifier without the design responsibility matrix updated to reflect the latest submission.

Standard deliverables:
- design status summary;
- design decision register;
- design risk register;
- drawing / document register;
- design RFI register;
- BASIX compliance summary at scheme and at IFC.

Common failure modes:
- design advanced beyond approved brief or budget before BASIX modelling;
- planning pathway feasibility assumed without consent testing;
- structural / hydraulic / BASIX scope gaps discovered after design lock;
- D&C design submission lapses between revisions, leaving certifier with stale information.

Agent use cases:
- summarise design changes between revisions;
- extract open design decisions from minutes;
- draft design phase-gate checklist;
- check IFC set against design RFI responses.

## 04-planning-and-authorities

Purpose: manage planning, statutory approvals, utilities, consent conditions, and authority risks. For residential, this folder holds BASIX, CC, BPA, Sydney Water (or state equivalent), LSL receipt, OSD certification, and any DA conditions.

The project lead must do:
- identify required approvals and referral agencies at the planning-pathway stage;
- maintain an authority approvals tracker;
- record consent conditions and trace them into tender, delivery, and handover obligations;
- coordinate utility approvals (water, sewer, electricity, gas, NBN) into the programme;
- confirm BASIX commitments are evidenced at the appropriate stage (CC issue and final certificate).

The project lead must not:
- rely on best-case approval durations without contingency;
- tender or award on unclear authority assumptions without flagging risk allocation;
- leave consent conditions buried where the delivery team will miss them;
- assume utility connection lead times will fit a tight programme without sequencing.

Standard deliverables:
- planning pathway summary;
- authority approvals tracker (CDC / DA / CC / BPA / OC / BASIX / Sydney Water / LSL);
- consent conditions register;
- utility approvals tracker;
- BASIX compliance evidence pack.

Common failure modes:
- BASIX commitments locked in CC but not flowed into construction (window U-values, insulation R-values, HW system);
- consent conditions buried in DA approval and missed at PC;
- utility connection lead time becomes critical path late;
- LSL not paid before CC (a common NSW failure that blocks construction).

Agent use cases:
- extract conditions from approval documents into a register;
- draft consent-conditions-into-delivery cross-reference;
- compare BASIX certificate commitments against IFC specification;
- flag missing utility approvals against programme.

## 05-procurement

Purpose: select and run the procurement route that protects the project's objectives — appropriate to scale and role.

Preferred filing structure (per package, where formal):
- `05-procurement/<Package Name>/01-eoi/`
- `05-procurement/<Package Name>/02-tender-pack/`
- `05-procurement/<Package Name>/03-rfi-addendum/`
- `05-procurement/<Package Name>/04-submissions/`
- `05-procurement/<Package Name>/05-evaluation/`
- `05-procurement/<Package Name>/06-recommendation/`

Residential procurement is rarely fully formal. The procurement reality varies sharply by role:

| Role | Procurement reality |
|---|---|
| Owner-builder | Informal quoting of subcontractors (frame, brick, plumbing, electrical, etc.); evaluation is price + reputation + availability. |
| Architect-PM | Formal builder selection on behalf of the owner — typically 2–3 invited builders, structured evaluation, contract recommendation. |
| Builder | Informal subcontractor quoting on most trades, formal where the trade is high-value or specialist (e.g. structural steel, specialist joinery). |
| D&C | Builder selection of subcontractors + consultant procurement on the design side. |

The project lead must do:
- match procurement formality to the trade's value and risk;
- maintain a fair and auditable RFI / addenda process where the procurement is formal;
- document clarifications, qualifications, and recommendation rationale;
- (architect-PM / D&C) keep non-price evaluation separate from price until the right stage.

The project lead must not:
- default to a formal procurement process when the trade does not warrant it;
- accept verbal scope clarifications that bypass the written record;
- transfer risk the market cannot price (e.g. unknown latent conditions).

Standard deliverables:
- procurement strategy note (where formal);
- shortlist rationale;
- tender pack or quote request;
- RFI / addenda register;
- price and non-price evaluation;
- recommendation note.

Common failure modes:
- subbie verbal qualifications not captured before contract;
- scope gaps between trades (cleanup, set-out, hoisting, scaffold sharing);
- recommendation made without evaluation criteria stated;
- contract awarded before latent-condition risk allocation is clear.

Agent use cases:
- draft procurement strategy options based on role + archetype;
- draft tender evaluation matrix;
- summarise quote comparisons for owner-builder / builder informal selection.

## 06-programme

Purpose: protect the project's time position by keeping the programme, milestones, staging, and critical path visible.

The project lead must do:
- establish a baseline programme appropriate to project scale (residential master programmes are typically 50–200 lines);
- adopt the high-level stage regime from the latest current PMP programme / staging section where a PMP exists; if the PMP is missing, vague or contradicted by later evidence, use the baseline stage regime as an explicit Assumption and recommend a PMP update;
- track milestones for design lock, planning approval, CC, LSL payment, construction start, slab pour, frame complete, lockup, fixing, PC, OC, DLP start, DLP end;
- track residential cycle-time benchmarks (slab cure to frame start, frame to lockup, lockup to fixing, fixing to PC) — see `program-scheduling-guide.md`;
- record delay causes, responsibility assumptions, and mitigation options;
- link programme movement to cost, procurement, authority, and delivery impacts.

The project lead must not:
- rely on optimistic dates without evidence (especially for authority and utility approvals);
- treat programme slippage as a reporting issue only;
- present delay responsibility as fact without supporting records;
- (for HIA stage-payment contracts) ignore the link between programme stage and claim entitlement.

Standard deliverables:
- master programme;
- milestone tracker;
- lookahead programme (typically 4–6 weeks for residential);
- delay register;
- programme risk commentary.

Common failure modes:
- BASIX-driven specification change not reflected in programme;
- weather delay not contemporaneously recorded for HIA EOT claim;
- subcontractor sequencing assumed rather than confirmed;
- DLP start date not tracked accurately, exposing the project to defects claim drift.

Agent use cases:
- draft master programme outline for the archetype;
- summarise programme variance against baseline;
- flag milestone risk for the next 8 weeks;
- compare PMP, programme and consultant procurement staging and recommend an alignment update where they drift.

## 07-construction

Purpose: administer construction so time, cost, scope, quality, safety, and risk remain visible and controlled.

Preferred filing structure (residential):
- `07-construction/01-loi/` — letter of intent / pre-contract correspondence;
- `07-construction/02-fioa-contract/` — fully-executed contract and amendments;
- `07-construction/03-insurance-bgs/` — contract works insurance, public liability, bank guarantees / security;
- `07-construction/04-management-plans/` — construction management plan, waste management, traffic management;
- `07-construction/05-progress-claims/` — progress claims and assessments;
- `07-construction/06-variations/` — variations issued and assessed;
- `07-construction/07-programme-eot/` — programme updates and EOT claims;
- `07-construction/08-rfi-notices/` — site RFIs and formal contractual notices;
- `07-construction/09-cc-pc-oc/` — CC / PC / OC certificates and inspections;
- `07-construction/10-commissioning/` — appliance, HW, mechanical, PV commissioning records;
- `07-construction/11-defects/` — defects identified during construction and at PC;
- `07-construction/12-reports/` — site reports, inspection reports (structural, BASIX inspections);
- `07-construction/13-photos/` — dated site photos.

The project lead must do:
- maintain contemporaneous site records — especially for HIA / MBA stage payments and HOW / DLP exposure;
- assess variations against the contract's variation mechanism before work begins (written direction, cost + time impact, owner sign-off);
- assess EOT claims against the contract clause and the contemporaneous programme;
- track quality, defects, and inspection evidence (slab inspection, frame inspection, BASIX final inspection);
- escalate delivery risk with recommended action, not just observation.

The project lead must not:
- direct works outside contractual authority;
- let verbal site agreements become unmanaged scope change;
- certify progress without inspection or trade evidence;
- ignore early signs of critical-path slippage;
- allow variations to proceed without written direction and cost+time agreement.

Standard deliverables:
- progress claim assessment (per HIA stage schedule or AS contract claim);
- variation register and assessment notes;
- EOT register and assessment;
- site inspection records;
- RFI register;
- defects register (rolled forward into 09-handover-dlp);
- monthly delivery report.

Common failure modes:
- HIA stage payment claimed before stage physically achieved;
- variation worked before written direction;
- EOT claimed without contemporaneous programme;
- BASIX final certificate held up by missed appliance commissioning evidence at PC;
- defects discovered at PC walk that should have been picked up at trade-level inspection.

Agent use cases:
- assess progress claim against stage-payment schedule and trade evidence;
- draft variation assessment (cost + time + scope);
- draft EOT assessment against contract clause and programme;
- summarise site inspection findings.

## 08-meetings-reporting

Purpose: create a reliable decision record and keep stakeholders aligned — appropriate to role.

The project lead must do:
- set meeting cadence and purpose for each forum (site meetings, owner updates, consultant coordination);
- record decisions, actions, owners, due dates, and status;
- separate discussion from approved decisions (per `§decision-discipline`);
- escalate issues to the correct governance level (per `§escalation-triggers` and role overlay);
- produce monthly reporting that integrates time, cost, scope, quality, and risk — using stakeholder voice for the owner and contractual voice for formal notices.

The project lead must not:
- let meetings become the only control mechanism;
- record vague actions without owner or due date;
- mix owner-facing language with contractor-facing language in the same document where the audience differs.

Standard deliverables:
- meeting agendas and minutes;
- action register;
- decision register;
- monthly owner update (stakeholder register);
- monthly internal / contractor report (contractual register);
- dashboard.

Common failure modes:
- minutes record conversation but not decisions;
- stale action registers;
- owner overwhelmed by contractor-language report;
- decisions made in the wrong forum.

Agent use cases:
- draft minutes from notes or transcript;
- draft owner monthly update in stakeholder voice;
- update action and decision registers;
- identify overdue actions.

## 09-handover-dlp

Purpose: ensure the dwelling is complete, compliant, commissioned, documented, and defects close out cleanly. For residential, this is where HOW certificate handover to owner, BASIX final certificate, OC, manuals/warranties, and DLP obligations live.

The project lead must do:
- plan handover early — not at PC;
- run a PC walk producing a defects schedule with owner sign-off;
- assemble compliance evidence pack (BASIX final, OC, structural certifications, BPA sign-offs, HOW certificate copy to owner);
- track defects through DLP with owner-confirmed close-out;
- (role-specific) meet the role's DLP obligations: builder under HOW and statutory warranty; owner-builder under warranty obligations to future buyers if sold within seven years; architect-PM as advisor through DLP only.

The project lead must not:
- treat handover as a contractor-only event;
- accept incomplete O&M, warranty, or commissioning evidence without status clearly marked;
- let defects drift without prioritisation;
- close the project without HOW certificate handed to the owner.

Standard deliverables:
- handover plan;
- PC checklist (residential — defects walk, BASIX final, OC, HOW handover, manuals, warranties, keys, final claim);
- defects register (carries forward from `07-construction/11-defects/`);
- O&M / warranty pack;
- DLP close-out report.

Common failure modes:
- PC declared without BASIX final or OC in hand;
- HOW certificate never handed to owner;
- defects register dies in the first month of DLP;
- final claim released before defects close-out evidence.

Agent use cases:
- generate PC checklist for the archetype + state;
- summarise outstanding defects by trade / priority;
- flag DLP obligations approaching expiry;
- assemble compliance evidence pack against requirements list.

---

# Cross-cutting rules

## §voice-and-style

Default register: formal Australian English. Plain, direct, structured. Active voice. Short sentences.

SiteWise uses a **two-register split**, chosen from folder and document type rather than prompt:

- **Contractual register** — used for contract notices, variations, EOT, RFIs, formal letters, authority correspondence, progress claim assessments. Formal Australian English. Cite clause numbers verbatim. Use ISO short-form dates (2026-05-27) in registers; long form (27 May 2026) in correspondence. Currency in AUD with $ symbol (e.g. $850,000). Never paraphrase a Principal or owner direction without quoting the source.
- **Stakeholder register** — used for owner-facing summaries, non-contractual coordination, monthly owner updates. Plain English. Lead with "what this means for you" and "what we need from you" (see `§owner-communication`). Avoid jargon; explain technical terms inline once.

Per `../AGENTS.md §6`, register selection is folder-driven. Where the role overlay specifies otherwise (e.g. an owner-builder writing to themselves), the overlay wins.

Numbers: figures for amounts and dates; words for counts under ten.

## §evidence-discipline

Internal language when drafting. Every claim in a project lead output must be classifiable as one of:

- **Fact** — supported by source document or direct observation;
- **Assumption** — reasonable but not yet evidenced; must be labelled and recorded for later confirmation;
- **Judgement** — project lead interpretation based on evidence and doctrine;
- **Recommendation** — proposed action for the decision-maker (owner, Principal, or self in the owner-builder case).

The agent must label assumptions explicitly when source evidence is absent. The agent must never present an assumption as fact. Where Fact, Assumption, and Judgement coexist in one paragraph, label them.

Completeness is part of evidence discipline. When the task is to create a cost plan, claim assessment, programme, procurement recommendation, or other phase-gate deliverable, the agent must synthesise the active project evidence into the most complete useful working view the evidence supports. It must not collapse available structured detail into a single summary line merely because the formal register, workbook, or schedule was not prepared in advance.

For cost planning specifically, a progress claim, payment claim, schedule of values, trade package schedule, contract annexure, or variation roll-up can be the best available construction cost breakdown. If that evidence exists, it is project evidence. The agent must preserve its useful granularity, reconcile it to the latest contract sum and variations as far as the evidence allows, and label unresolved conflicts instead of replacing the detail with one "construction contract" allowance.

## §document-quality-discipline

Generated documents must be scored against `../99-docs/eval/document-quality-rubric.md` when a workflow is being evaluated or uplifted. The rubric is subordinate to this doctrine, but it is the working measurement layer for clarity, concision, accuracy, evidence discipline, PM usefulness, and auditability.

For PMP outputs, the PM-facing document and hidden/internal audit layer are quality-controlled separately. The PM-facing layer must stay concise and project-specific; the hidden/internal layer carries evidence traceability, context used, assumptions, and warnings.

For Cost Plan outputs, quality includes breadth, granularity, workbook reliability, and correct invoice/variation mapping. A cost plan must identify likely consultants, trades, fees, authority costs, owner-side costs, and contingency where they are evidenced or reasonably required, while labelling benchmark estimates and assumptions.

## §seed-consultation-discipline

Seed knowledge ranks above general LLM knowledge in the authority stack. The agent must consult it **deliberately, not opportunistically**.

**Three-overlay declaration is gating** (per `../AGENTS.md §2`). Before any phase-gate deliverable — cost plan, programme, procurement strategy, contract setup, progress claim assessment, variation management, handover, or any system skill invocation — the agent must:

1. Confirm `archetype`, `user_role`, and `state` are declared in the project `README.md` frontmatter. **If any is missing, blank, or `TBC`, the agent stops and asks.** It does not guess from project name, address, budget, site, or any other proxy.
2. Load the Tier 2 archetype seed (`new-dwelling-guide.md` | `renovation-guide.md` | `multi-dwelling-guide.md` | `ancillary-guide.md` | `small-commercial-guide.md`).
3. Load the Tier 3 role overlay seed (`role-owner-builder.md` | `role-architect-pm.md` | `role-builder.md` | `role-d-and-c.md`).
4. Use `seed-targeted-read` to identify any cross-cutting topic seeds the task needs.
5. List in the deliverable's frontmatter the seed files actually consulted (`seed_consulted:` field). This creates an audit trail the project lead can check at review.

**Cross-archetype tasks** — where a task on a project of one archetype touches another (e.g. a renovation with a granny flat addition), the agent loads the additional archetype seed task-loaded and records both in `seed_consulted:`.

**Failure mode this prevents:** drafting BASIX commitments without reading `sustainability-energy-guide.md`; drafting an HOW workflow for an owner-builder (who is exempt) by silently substituting LLM general knowledge; drafting a progress claim assessment without loading `progress-claim-assessment-system`. Each of these is a §authority-stack breach.

The agent must not suppress this gate to make the user's life easier. If declarations are incomplete, stopping and asking is the correct behaviour, even if the user is mid-flow.

## §register-discipline

A register is useful only if every row carries:

- unique **ID**
- **description**
- **owner**
- **status**
- **due date** or review date
- **source / evidence reference**
- **next action**

Registers are queryable structured data. They live in Excel (for residential project scale, the working source of truth for cost, programme, and risk registers) or — where the project warrants — in `project.db` (SQLite). Narrative belongs in linked markdown drafts, not in register cells.

Use the `register-row-draft` atomic skill to draft register entries that pass discipline at the point of creation.

## §decision-discipline

A decision record states:

- decision made
- decision-maker / forum (for owner-builder: self; for architect-PM: the owner, with the architect-PM as advisor; for builder: typically owner with builder recommendation; for D&C: owner, with D&C carrying design and construction recommendation)
- date
- basis of decision
- alternatives considered where material
- consequences for cost, time, scope, quality, or risk
- follow-up actions

Decisions are **append-only**. Superseded decisions are marked superseded; the superseding decision links back to the original. Decision history must survive — this is the audit trail for HOW claim, statutory warranty defence, and dispute resolution.

## §escalation-triggers

Escalate when:

- budget or contingency is likely to move;
- critical path is threatened (especially BASIX / OC / utility connection risk);
- scope is unclear or changing;
- approval timing or conditions are uncertain;
- consultant or contractor deliverables are late;
- a decision is required from the owner / Principal / self;
- the project lead's authority or role is unclear;
- project evidence conflicts;
- a safety or compliance risk is visible.

**Escalation routes are role-shaped** — the role overlay specifies the path:

- **Owner-builder** — escalation is to a self-flag log (the "park-for-decision" queue) inside `08-meetings-reporting/`. The agent must not let a flag silently disappear.
- **Architect-PM** — escalation defaults to a formatted owner-facing summary (using `§owner-communication`) with recommendation, so the owner can decide quickly without re-explanation.
- **Builder** — escalation routes per HIA / MBA / AS contract: to the owner for owner decisions; to the consultant or engineer-of-record for technical decisions; to formal contractual notice (via `07-construction/08-rfi-notices/`) where the contract requires.
- **D&C** — as builder, plus design-side escalations: to the certifier where design submission affects compliance; to PI insurer where design risk is material.

**The agent must refuse to suppress an escalation trigger.** If the agent sees a trigger, the project lead sees it.

## §owner-communication

A new anchor specific to SiteWise. Used for any communication directed at a non-technical residential owner — most often by an architect-PM, but also by an owner-builder writing for their own future reference, and by a builder writing to their owner-client.

The format:

1. **What this means for you** — the practical consequence in one or two sentences. Plain language.
2. **What we need from you** — the explicit decision, sign-off, or supply requirement, with a clear due date. One bullet per ask.
3. **What's happened** — the brief factual chronology, in stakeholder voice (not contractual).
4. **What's next** — the project lead's planned action and timing.
5. **Background detail** — anything the owner needs the option to read but not required to read. Below a fold.

Do not lead with technical detail. Do not lead with risk language. Do not bury the ask. Do not use clause references in items 1 and 2 (save them for item 5 if necessary). Do not present three options without a recommendation — a residential owner is not paid to decide between three options; the project lead is paid to recommend.

Use the stakeholder register (per `§voice-and-style`) for items 1 and 2; contractual register is acceptable for items 3 and 5 where the underlying source is a contract notice.

## §state-handling

`state:` is required (per `../AGENTS.md §2`). NSW is the deep default in every seed. Non-NSW states receive inline graceful-degradation callouts (e.g. "in VIC, the equivalent is NatHERS 6-star instead of BASIX; HOW is DBI under HBA; LSL is CoINVEST").

Where a non-NSW state has no callout for the task at hand, the agent **flags the gap** and asks the project lead to supplement, rather than silently extending NSW guidance to a state where it does not apply.

State overlay seed files (`state-VIC.md`, `state-QLD.md`, etc.) do not exist in v1. The mechanism is reserved for future deepening.

---

# Sub-roles, authority, and the four-role chain

The four user roles occupy different positions in the residential contract chain. The doctrine spine is abstract, but a few cross-cutting points hold across all of them:

- **Owner-builder** is principal and contractor simultaneously. HOW does not apply (the owner-builder cannot insure themselves), but statutory warranty to future buyers applies if the property sells within seven years. The owner-builder permit is in the role of "builder's licence equivalent" for the project.
- **Architect-PM** acts client-side, advisory. Does not take out HOW (the builder does), does not pay LSL (the builder does), but must verify both before signing the construction contract on behalf of the owner. Holds PI insurance for the advisory scope. Does not hold a Superintendent or Certifier role unless expressly appointed and competent.
- **Builder** holds the head contract with the owner. Takes out HOW, pays LSL, holds builder's licence, holds contract works insurance and public liability. Issues progress claims; assesses subcontractor claims.
- **D&C contractor** is a builder who also carries design responsibility. All builder obligations apply, plus consultant procurement, PI insurance for design liability, design submission to certifier, design responsibility matrix maintained through the project.

Role-specific deep coverage lives in the role overlay seeds (`role-owner-builder.md`, `role-architect-pm.md`, `role-builder.md`, `role-d-and-c.md`). The agent loads the overlay matching the `user_role:` declaration; it does not load the other three for the active project.
