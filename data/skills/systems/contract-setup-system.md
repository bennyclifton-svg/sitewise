# System skill: contract-setup-system

**Job:** End-to-end commissioning workflow for a SiteWise project. Orchestrates the seed-loading, evidence sweep, contract execution, statutory instrument capture, register opening, and ready-to-start checklist into one workflow. Produces drafts under `00-brief-pmp/`, `04-planning-and-authorities/`, `07-construction/03-insurance-bgs/`, `07-construction/04-management-plans/`, and `08-meetings-reporting/` — the user reviews each before commissioning is signed off.

This is the **first system skill in SiteWise** and the template that slice 06 (`progress-claim-assessment-system`, `variation-management-system`) and slice 13 (`handover-pc-system`) will inherit. The skill skeleton — `seed-targeted-read` first, then `evidence-sweep`, then content-specific atomics, then `markdown-draft-for-review` and `register-row-draft` — is load-bearing for the harness.

This skill is the first to invoke the §2 three-overlay declaration gate. If declarations are incomplete, the skill stops at step 0 and asks. It does not guess.

## When called

Called by:
- the agent at project mobilisation, when the user asks to set up a new SiteWise project for delivery;
- the agent at any time the user asks "are we ready to start" or "what's our commissioning status";
- as a re-run when significant commissioning evidence changes (e.g. HBCF certificate re-issued for a contract sum increase).

The skill is **idempotent** — re-running on a project where some commissioning is already done will not duplicate registers or overwrite executed evidence. Re-runs identify what is new and surface gaps and changes.

## Caller passes

- **Active project folder path** — required.
- **Mode** — `initial` (first commissioning at mobilisation) or `re-run` (subsequent invocation). Optional; defaults to `initial` if the project README's status is `active` and no `ready-to-start.md` exists, otherwise `re-run`.

The skill reads everything else it needs from the project folder.

## Pre-flight — Step 0: §2 declaration gate

Before any work:

1. Read the project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC` (per AGENTS.md §2 and `../../00-doctrine/doctrine.md §seed-consultation-discipline`).
3. **If any is missing, blank, or `TBC`:** **stop**. Return:
   > Cannot commission this project: the README is missing one or more required overlay declarations. Please declare `archetype`, `user_role`, and `state` in the frontmatter before commissioning. Per `../../AGENTS.md §2` and `../../00-doctrine/doctrine.md §seed-consultation-discipline`, the agent does not guess these from project name, address, budget, site, or any other proxy.
4. **Do not load any seed, do not run evidence-sweep, do not draft.** The gate is binary.

This is the §2 gate enforced at the system-skill level. The atomic `seed-targeted-read` also enforces it; the redundancy is intentional — system skills are the canonical entry point for phase-gate work (per AGENTS.md §9) and the gate is checked at the system-skill boundary as well as at the seed-loading boundary.

If the user is mid-flow and wants the gate bypassed, the gate is **not** bypassed. The agent surfaces the gate and offers to help complete the declaration, but does not proceed with commissioning until declarations are complete.

## Steps

### Step 1 — seed-targeted-read

Invoke `../atomic/seed-targeted-read.md` with task subject `commissioning and contract setup`. The skill loads:

- Tier 2 archetype seed (`new-dwelling-guide.md` for `archetype: new-dwelling`, etc.).
- Tier 3 role overlay (`role-builder.md` for `user_role: builder`, etc.).
- Cross-cutting seeds matched to the task subject:
  - `setup-and-commission-guide.md` — required;
  - `contract-administration-guide.md` — required.
- For non-NSW states, the agent flags state-coverage gaps where the seeds reference NSW-specific instruments without callouts (per AGENTS.md §8).

The loaded seed list is held for use in `seed_consulted:` frontmatter on every deliverable this skill produces.

### Step 2 — evidence-sweep

Invoke `../atomic/evidence-sweep.md` with task subject `commissioning and contract setup`. The sweep returns:

- existing artefacts found in the project folder (sorted by relevance to commissioning);
- gap report identifying expected-but-missing artefacts for the declared role × archetype × state;
- §2 declaration check result (already passed at step 0; this is a redundant confirmation).

For a `user_role: builder` project at initial commissioning, the gap report typically lists: HBCF certificate, LSL receipt, executed head contract, CWI Certificate of Currency, PL Certificate of Currency, workers comp Certificate of Currency, builder's licence reference, Qualified Supervisor reference. Some may have been pre-loaded by the user — the sweep finds them — and others may be genuinely outstanding.

For a `user_role: d-and-c` project, the gap report includes the same builder pack plus the design pack: Principal's Project Requirements / design brief, design fee basis, design programme, design responsibility matrix, consultant appointment / novation evidence, consultant PI, D&C PI, design deliverables register, design RFI register, and certifier submission protocol. For `archetype: multi-dwelling`, it also checks classification, party-wall strategy, separate metering, infrastructure contributions, and staging / OC pathway.

### Step 2A - Architect-PM PMP facet

When `user_role: architect-pm` is declared, `commission-pmp` includes a named **Architect-PM PMP facet**. This is the canonical SiteWise contract for the Clerk **Create PMP** and **Update PMP** workflows.

This facet drafts or refreshes `00-brief-pmp/pmp_vNN.draft.md` through `../atomic/markdown-draft-for-review.md`. It is a review-only governance plan for the owner-side architect-PM role. It is not an issued instruction, statutory submission, tender document, contract certificate, Superintendent direction, or construction management plan.

The facet is idempotent:

- if no PMP exists, draft `pmp_v01.draft.md`;
- if one or more PMP drafts exist, use the latest draft as evidence, preserve it, and draft the next version;
- never overwrite a reviewed or draft PMP in place;
- keep previous PMP drafts as project evidence, not as a source of truth that can beat current active-project evidence;
- do not mark a draft `reviewed` or `approved`.

For this facet, Step 1 must include:

- `role-architect-pm.md`;
- the declared archetype seed;
- `setup-and-commission-guide.md`;
- `contract-administration-guide.md` where contract / award / notice posture is discussed;
- `cost-management-principles.md`, `program-scheduling-guide.md`, and `procurement-quoting-guide.md` where the PMP includes cost, programme or procurement sections. In Clerk Create PMP context these topic seeds are included when present and warning-reported if missing.

The PM-facing PMP must cover, in concise project-specific form:

| Section | Required content |
| --- | --- |
| Evidence basis and document control | Status `draft`, source project, seed and evidence basis, review-only / not-issued boundary, source hierarchy. |
| Project overview | Project description, phase, owner context, declared archetype / role / state, planning context. |
| Architect-PM role and appointment | Scope of services, engagement instrument, role declaration, authority matrix, Superintendent / Certifier / contract-administrator status, PI / registration evidence where relevant. |
| Two-brief discipline | Separate the architect-PM engagement brief from the owner's project brief. Do not merge fee scope with building scope. |
| Governance and decisions | Who decides, who recommends, who is consulted, who is informed, decision gates and decision-record links. |
| Communications protocol | Owner reporting cadence, meeting rhythm, builder / consultant / certifier / authority routes, emergency route, escalation-note route. |
| Fee, services and programme relationship | Fee basis, deliverables, reimbursables, service exclusions, programme assumptions, extension / additional-service trigger, and how owner or authority delay affects service scope. |
| Scope and change control | Current building scope, exclusions, scope sensitivities, owner selections, service-scope variations and project-scope changes kept distinct. |
| Approvals and compliance | DA / CDC / CC / BASIX / certifier path, authority assumptions, consent-condition controls and state callouts. |
| Programme and staging regime | The PMP programme / staging section must define the high-level project stage regime, regardless of the section number used in the final PMP. If project evidence does not define a better regime, use: Stage 1 - concept and schematic design to DA submission; Stage 2 - design development; Stage 3 - construction documentation and delivery. For multi-dwelling, apartment, staged OC or D&C-signalled projects, ratchet this up to a detailed Stage/Phase 1 to 6 or greater regime covering design/approvals, procurement, enabling, structure, envelope/services/finishes, commissioning/OC/handover/DLP. State whether any project evidence ratchets this up and map detailed stages back to the baseline. |
| Cost, programme and procurement posture | Budget control basis, missing cost / programme / procurement artefacts, builder procurement pathway, award conditions and HBCF / LSL / licence / insurance evidence verification. |
| Consultant coordination | Consultant appointments, scope boundaries, responsibility matrix, advice register, deliverables and design RFI controls. |
| Risks, decisions and next actions | Top current risks, open owner decisions, missing evidence, register rows to draft or refresh, and immediate next actions. |

The hidden / internal layer must include:

- Facts, Assumptions, Judgements and Recommendations separated under `../../00-doctrine/doctrine.md §evidence-discipline`;
- missing information and evidence gaps with consequence;
- early flags for cost, programme, procurement, approvals and compliance;
- staging conflicts between the PMP, programme, consultant procurement / RFPs, consultant fee stages and project evidence, with a recommendation to align the affected artefacts rather than allowing drift;
- seeds consulted;
- evidence references;
- workflow warnings, including unsorted `_inbox/` files and missing programme / procurement material;
- context used by Clerk or the agent runtime where applicable.

Guardrails for the architect-PM PMP facet:

- do not accept a vague commission boundary;
- do not imply the architect-PM is the builder, Certifier, Superintendent or contract administrator unless the appointment evidence says so;
- do not treat builder HBCF / HOW, LSL, licence or contract works insurance as architect-PM instruments. They are builder evidence the architect-PM verifies;
- do not absorb specialist consultant, certifier, procurement, contract-administration or additional-service work silently into the base fee;
- do not leave the PMP programme / staging section as a loose programme commentary where the project stage regime is undefined;
- do not let programme, consultant RFP or consultant fee staging diverge from the PMP programme / staging regime without recommending a coordinated update;
- do not give the owner options without a recommendation where the evidence supports a professional view;
- do not bury owner asks, budget resets, programme reality checks or authority blockers in appendices;
- do not issue a PMP that conflicts with the engagement letter, owner project brief, consultant appointments, head contract or approval pathway.

Quality check: where the PMP facet is being evaluated or uplifted, score the draft against `../../99-docs/eval/document-quality-rubric.md`. Score the PM-facing layer and hidden/internal layer separately. A hard-fail gate in that rubric blocks treating the PMP as release-quality even if the numeric score is acceptable.

### Step 3 — Draft contract summary

If the project has an executed head contract (found in `07-construction/02-fioa-contract/` by the sweep), draft a contract summary at `00-brief-pmp/contract-summary.md` using `../atomic/markdown-draft-for-review.md`.

Content:
- contract family and edition (e.g. HIA Lump Sum NSW New Homes, edition dated YYYY-MM-DD);
- contract sum (AUD);
- deposit amount and statutory cap check;
- stage payment schedule (table of stages, percentages, dollar amounts);
- variation form reference and mechanism summary;
- EOT clause reference, notification window, qualifying events list;
- latent conditions clause reference (where applicable);
- PC mechanism summary;
- DLP duration;
- special conditions summary (each special condition with the standard-form clause it modifies and the effect of the modification — this is the most important section).

Voice register: contractual. Folder: `00-brief-pmp/`. The summary is a §evidence-discipline-labelled aid for retrieval — it does **not** substitute for the executed contract (which remains the source of truth per `../../03-project-template/README.md` §"Source-of-truth rule").

If no executed contract exists yet, this step produces a stub at `00-brief-pmp/contract-summary.md` with `status: draft` and content "Contract not yet executed — see register entry CC-001 for execution status", and the contract-execution row is added to the decision register at step 6.

### Step 4 — Draft statutory instrument inventory

For each statutory instrument required by the role × archetype × state, draft a row in the **authority approvals tracker** at `04-planning-and-authorities/authority-approvals-tracker.md` (or `.xlsx` — markdown for slice 02; Excel becomes possible in slice 03 with `excel-safe-edit`).

After commissioning, `authority-approvals-system.md` is the canonical workflow for refreshing these rows, extracting consent conditions, reviewing authority / utility lead times, and carrying approval obligations into tender, programme, delivery and handover controls.

For `user_role: builder` in NSW, the rows are:

| ID | Instrument | Owner | Source | Status |
|---|---|---|---|---|
| AA-001 | Builder's Contractor Licence (NSW Fair Trading) | Builder | NSW Fair Trading record | Held / Verify currency |
| AA-002 | Qualified Supervisor certificate | Builder | NSW Fair Trading record | Held / Verify currency |
| AA-003 | HBCF eligibility | Builder | iCare HBCF record | Held |
| AA-004 | HBCF per-project certificate | Builder | iCare HBCF, this project | Issued / Outstanding |
| AA-005 | LSL Receipt | Builder | NSW Long Service Corporation | Paid / Outstanding (CC-blocking) |
| AA-006 | CC (Construction Certificate) | Certifier | Certifier | Issued / Pending |
| AA-007 | BASIX Certificate | BASIX assessor | BASIX assessor | Issued / Pending |
| AA-008 | Sydney Water approval (Build Over Sewer if applicable) | Builder | Sydney Water | Issued / Not applicable / Pending |
| AA-009 | BPA (Building Practice Approval) where required | Authority | Authority | Issued / Not applicable / Pending |
| AA-010 | DA + conditions of consent (DA pathway) or CDC (CDC pathway) | Council / Certifier | Council / Certifier | Issued |

Each row drafted via `../atomic/register-row-draft.md`, with source / evidence reference pointing to the file path returned by `evidence-sweep` (or marked Assumption / Outstanding where the sweep found nothing).

For `user_role: owner-builder`, the builder HBCF rows are not carried forward as gaps. The owner-builder statutory rows are:

| ID | Instrument | Owner | Source | Status |
|---|---|---|---|---|
| AA-001 | Owner-builder permit | Owner-builder | Building Commission NSW / Service NSW record | Issued / Required / Not applicable with basis |
| AA-002 | Owner-builder course / competency and white card evidence | Owner-builder | Training / permit evidence | Held / Outstanding / Not applicable |
| AA-003 | DA / CDC / CC / approval path | Owner-builder / Certifier | Council / certifier / Planning Portal | Issued / Pending |
| AA-004 | Principal certifier appointment and inspection schedule | Owner-builder / Certifier | Certifier | Appointed / Pending |
| AA-005 | BASIX certificate for alteration/addition where triggered | Owner-builder / BASIX assessor | Planning Portal / BASIX assessor | Issued / Not applicable / Pending |
| AA-006 | Contractor HBCF certificate for any direct contractor package over the threshold | Trade contractor | Contractor / SIRA HBC check | Issued / Not applicable / Outstanding |
| AA-007 | Warranty / future-buyer disclosure reminder | Owner-builder | Owner-builder permit date / decision record | Open through handover / DLP |
| AA-008 | Renovation due diligence pack | Owner-builder | Survey / dilapidation / services / structural / heritage / hazardous material evidence | Complete / Gap-report |

For the owner-builder's own work, HOW / HBCF is recorded as **not applicable**, not as an outstanding lodgement. Contractor HBCF can still be required where a directly engaged licensed contractor package triggers it. For `user_role: architect-pm`, the rows track the **architect-PM's** instruments (registration, PI) and the **builder's** instruments are tracked separately as conditions for the architect-PM's recommendation to sign the construction contract.

For `user_role: d-and-c`, the statutory inventory carries all builder rows plus design-control rows:

| ID | Instrument / evidence | Owner | Source | Status |
|---|---|---|---|---|
| AA-011 | Principal's Project Requirements / design brief | D&C | Owner / principal / contract pack | Filed / Outstanding |
| AA-012 | Design responsibility matrix | D&C | D&C design pack | Current / Missing / Stale |
| AA-013 | Design programme | D&C | D&C programme / consultant deliverables schedule | Baselined / Missing |
| AA-014 | Design fee basis | D&C | Contract particulars / fee schedule | Recorded / Missing |
| AA-015 | Consultant appointment / novation evidence | D&C / consultant | Consultant agreements / novation deeds | Complete / Gap-report |
| AA-016 | Certifier design-submission protocol | D&C / certifier | Certifier correspondence / CC path | Agreed / Pending |
| AA-017 | Multi-dwelling classification basis | D&C / certifier | Drawings / NCC advice / certifier advice | Class 1a / Class 2 / Unresolved |
| AA-018 | Party-wall / fire-separation strategy | D&C / designer | Design drawings / NCC report | Evidenced / Gap-report |
| AA-019 | Separate metering / services strategy | D&C / services designer | Utility applications / services drawings | Evidenced / Gap-report |
| AA-020 | Infrastructure contribution / authority charge allowance | D&C / project lead | Consent / authority correspondence / cost plan | Recorded / Unknown |
| AA-021 | Staging / OC / subdivision or strata pathway | D&C / certifier | Programme / authority / survey evidence | Evidenced / Gap-report |

### Step 5 — Draft insurance inventory

For each required insurance, draft a row in the insurance register at `07-construction/03-insurance-bgs/insurance-register.md`. The register is a register-row table, the underlying Certificates of Currency live as PDFs in the same folder.

For `user_role: builder` in NSW:

| ID | Policy | Insured | Insurer | Sum insured | Period | Status |
|---|---|---|---|---|---|---|
| Ins-001 | Contract Works | Builder + Owner (joint) | (insurer) | Contract sum + owner-supplied + debris removal + professional fees | Site possession → PC (with DLP run-off) | Bound / Pending |
| Ins-002 | Public Liability (≥ $10M) | Builder | (insurer) | $10M minimum | Pre-mobilisation → ongoing | Bound / Pending |
| Ins-003 | Workers Compensation | Builder | icare workers insurance | per legislation | Ongoing | Bound / Pending |

Each row drafted via `register-row-draft`. For `user_role: owner-builder`, the policies differ:

| ID | Policy / evidence | Insured / holder | Status logic |
|---|---|---|---|
| Ins-001 | Public liability | Owner-builder | Bound / Pending / Not adequate |
| Ins-002 | Home / construction-period works cover | Owner-builder / insurer | Bound / Excluded / Pending |
| Ins-003 | Personal accident / income protection posture | Owner-builder | Held / Declined with decision record / Pending |
| Ins-004 | Contractor public liability evidence | Trade contractor | Verified per trade / Outstanding |
| Ins-005 | Contractor workers compensation evidence where applicable | Trade contractor | Verified per trade / Not applicable / Outstanding |
| Ins-006 | Contractor contract works insurance where applicable | Trade contractor | Verified per trade / Not applicable / Outstanding |

The owner-builder branch must not describe conventional builder CWI as though it automatically covers the owner-builder's work. It records the actual insurer position and raises an escalation where owner-builder or renovation work is excluded.

For `user_role: d-and-c`, the insurance inventory distinguishes builder-side and design-side insurance:

| ID | Policy / evidence | Insured / holder | Status logic |
|---|---|---|---|
| Ins-001 | Contract works insurance | D&C + owner / principal as required by contract | Bound / Pending / Sum-insured gap |
| Ins-002 | Public liability | D&C | Bound / Pending |
| Ins-003 | Workers compensation | D&C | Bound / Not applicable / Pending |
| Ins-004 | D&C professional indemnity | D&C | Bound / Exclusion gap / Pending |
| Ins-005 | Consultant professional indemnity | Consultant | Verified per consultant / Outstanding |
| Ins-006 | Design-and-construct endorsement / exclusion check | D&C / broker | Confirmed / Gap-report |

CWI and public liability do not evidence design liability. If PI is missing or excluded for the design responsibility assumed under the contract, the skill surfaces an escalation before treating the project as ready to start.

### Step 6 — Open standard registers

Open the standard set of registers per `setup-and-commission-guide.md` §"Cross-cutting registers opened at commissioning":

| Register | File path | Initial row |
|---|---|---|
| Decision register | `08-meetings-reporting/decision-register.md` | D-001: Project commissioned under SiteWise. Overlay declarations recorded. Contract form selected. |
| Action register | `08-meetings-reporting/action-register.md` | A-001 onwards: every gap from steps 2–5 becomes an action row with owner and due date |
| Risk register | `00-brief-pmp/risk-register.md` | R-001 onwards: mobilisation risk scan (procurement risk, programme risk, BASIX risk, latent-conditions risk for renovations, etc.) |
| Cost register | `01-cost/cost-register.md` | C-001: Contract sum baselined |
| Variation register | `07-construction/06-variations/variation-register.md` | Header row only; first variation creates V-001 |
| EOT register | `07-construction/07-programme-eot/eot-register.md` | Header row only; first EOT creates E-001 |
| Defects register | `07-construction/11-defects/defects-register.md` | Header row only; first defect at PC creates Df-001 |
| Inspection register | `07-construction/12-reports/inspection-register.md` | I-001 onwards: inspections scheduled by the certifier (pre-pour, slab, frame, wet area, structural completion, BASIX final, OC) |
| Subcontractor register | `05-procurement/subcontractor-register.md` (builder/D&C) | Header row only; first subcontractor engagement creates S-001 |
| Owner-supplied items register | `00-brief-pmp/owner-supplied-items.md` | Items from contract Particulars (where Particulars list owner-supplied items) |
| Park-for-decision queue | `08-meetings-reporting/park-for-decision-queue.md` (owner-builder) | Header row plus first deferred setup decisions; first decision creates PFD-001 |
| Design responsibility register | `02-consultant/design-responsibility-register.md` or `03-design/design-responsibility-register.md` (D&C) | Header row plus first design elements; first element creates DRM-001 |
| Design deliverables register | `03-design/design-deliverables-register.md` (D&C) | Header row plus first design packages; first deliverable creates DD-001 |
| Design RFI register | `03-design/design-rfi-register.md` or `07-construction/08-rfi-notices/design-rfi-register.md` (D&C) | Header row plus open design questions; first question creates DRFI-001 |

Each row drafted via `register-row-draft`. Each register opened via `markdown-draft-for-review` (with `status: draft`) so the human can review the initial rows before they become the live record.

After commissioning, `consultant-coordination-system.md` is the canonical workflow for refreshing consultant appointments, responsibility matrix rows, deliverables, advice and design-question controls.

### Step 7 — Draft management plans

For `user_role: builder` (or `user_role: d-and-c`), draft skeleton Construction Management Plan, Waste Management Plan, and Traffic Management Plan at `07-construction/04-management-plans/`:

- `cmp-skeleton.md` — site setup, access, hours, deliveries, noise, dust, neighbour-property dilapidation reference, WHS framework.
- `wmp-skeleton.md` — waste streams, separation, removal contractor, disposal destinations, target recycling rates per state requirements.
- `tmp-skeleton.md` — only where required by council or site conditions; vehicle movements, pedestrian management, traffic control measures.

These are skeletons — the builder fills in project-specific detail. The skeleton's purpose is to surface the requirement at commissioning rather than at first delivery / first wet-weather event / first neighbour complaint.

### Step 8 — Draft ready-to-start checklist

The final commissioning deliverable. At `00-brief-pmp/ready-to-start.md`, via `markdown-draft-for-review`:

```markdown
# Ready-to-start checklist — <project slug>

For role: <user_role> | Archetype: <archetype> | State: <state>

## Overlays declared (§2 gate)

- [x] archetype declared and not TBC
- [x] user_role declared and not TBC
- [x] state declared and not TBC
- [x] ncc_class declared (may be TBC at mobilisation; must firm by CC)
- [x] planning_pathway declared (may be TBC; must firm by concept)

## Statutory instruments (role-specific — example shown for builder)

- [ ] Builder's licence verified (AA-001)
- [ ] Qualified Supervisor verified (AA-002)
- [ ] HBCF eligibility confirmed (AA-003)
- [ ] HBCF per-project certificate issued (AA-004); copy delivered to owner
- [ ] LSL paid (AA-005); receipt filed; CC not blocked
- [ ] BASIX certificate received (AA-007); commitments flowed to procurement
- [ ] CC issued (AA-006); upstream prerequisites confirmed
- [ ] DA conditions extracted to consent conditions register (if DA pathway)
- [ ] Sydney Water BOS issued (AA-008) if applicable
- [ ] BPA scheduled if applicable

## Contract (role-specific)

- [ ] Head contract executed; pack filed under 07-construction/02-fioa-contract/
- [ ] Special conditions reviewed; effects recorded in contract-summary.md
- [ ] Deposit invoiced (within statutory cap) and received

## Insurances

- [ ] Contract Works bound; owner named as joint insured (Ins-001)
- [ ] Public Liability ≥ $10M bound (Ins-002)
- [ ] Workers Compensation bound where applicable (Ins-003)

## Pre-site

- [ ] Construction Management Plan drafted and filed
- [ ] Waste Management Plan drafted and filed
- [ ] Traffic Management Plan drafted and filed (where required)
- [ ] Baselined programme filed under 06-programme/
- [ ] Site possession date confirmed with owner
- [ ] Subcontractor pre-engagement: head trades approached, insurance and licence requested
- [ ] Utility approvals lodged (water, sewer, electricity, gas, NBN); lead times tracked

## Registers

- [ ] Decision register opened (D-001)
- [ ] Action register opened with mobilisation actions
- [ ] Risk register opened with mobilisation risk scan
- [ ] Cost register baselined (contract sum recorded)
- [ ] Variation, EOT, defects, inspection registers opened (header rows)
- [ ] Authority approvals tracker populated
- [ ] Subcontractor register opened
- [ ] Owner-supplied items register populated from contract Particulars

## Owner briefing

- [ ] Owner briefed on payment mechanism (stage payments / cost plus)
- [ ] Owner briefed on variation mechanism (written direction before work)
- [ ] Owner briefed on communication cadence and channels
- [ ] Owner briefed on escalation pathway

## Commissioning sign-off

When every item above is checked, commissioning is complete. The agent does **not** flip this draft to `status: reviewed` — the project lead does, after walking the list against evidence.

Outstanding items at site possession are tracked in the action register with deadlines and impact-if-late assessment.
```

For `user_role: owner-builder`, the checklist content uses the slice-07 owner-builder variant. It replaces builder licence / HBCF / head-contract / CWI rows with:

- [ ] Owner-builder permit filed, or documented no-permit basis recorded (AA-001)
- [ ] Course / competency / white card evidence filed where required (AA-002)
- [ ] DA / CDC / CC / principal certifier path recorded (AA-003 / AA-004)
- [ ] BASIX alteration/addition trigger checked and certificate filed where required (AA-005)
- [ ] Contractor HBCF evidence checked for direct contractor packages where triggered (AA-006)
- [ ] Warranty / future-buyer disclosure reminder opened through handover / DLP (AA-007)
- [ ] Renovation due diligence pack filed or gap-reported where `archetype: renovation` (AA-008)
- [ ] Public liability and construction-period insurance position recorded (Ins-001 / Ins-002)
- [ ] Trade register opened with licence, insurance, scope, HBCF, and payment checks
- [ ] Park-for-decision queue opened and overdue items surfaced

The owner-builder checklist deliberately omits owner-builder HOW / HBCF lodgement. For `user_role: architect-pm`, the checklist uses the slice-08 architect-PM variant in `setup-and-commission-guide.md` and `role-architect-pm.md`.

For `user_role: d-and-c`, the checklist content uses the slice-09 D&C variant. It includes the builder pack plus:

- [ ] Accepted D&C tender response filed.
- [ ] Principal's Project Requirements / design brief filed.
- [ ] Design fee basis recorded.
- [ ] Design programme baselined under `06-programme/`.
- [ ] Design responsibility matrix opened and current (DRM-001 or equivalent).
- [ ] Consultant appointments / novations filed.
- [ ] Consultant PI evidence checked.
- [ ] D&C PI evidence checked, including design-and-construct exclusions.
- [ ] Design deliverables register opened.
- [ ] Design RFI register opened.
- [ ] Certifier design-submission protocol agreed and filed.
- [ ] Design release / revision-control path recorded before construction packages are issued.

For `archetype: multi-dwelling`, the D&C checklist also includes:

- [ ] Class 1a attached dwelling vs Class 2 classification tested and evidenced.
- [ ] Party-wall / fire-separation strategy evidenced.
- [ ] Separate metering / services strategy evidenced.
- [ ] Infrastructure contribution / authority charge assumptions recorded in cost / authority trackers.
- [ ] Staging, subdivision / strata, OC, and handover pathway recorded.

### Step 9 — Surface gaps and escalations

Surface explicitly to the user:

- every gap from step 2's gap report;
- every Outstanding row from steps 4 and 5;
- every §escalation-triggers signal raised during commissioning (e.g. CC pending with LSL not paid; HBCF outstanding with contract proposed for signing; CWI sum insured set to contract sum only with owner-supplied items present).
- for `user_role: owner-builder`, every due or overdue `Park-for-decision queue` row, with the owner-builder as the decision owner and the consequence if deferred stated plainly.
- for `user_role: d-and-c`, every missing or stale design responsibility row, missing PI evidence, unappointed consultant, design package not ready for certifier, unresolved Class 1a / Class 2 classification, unresolved party-wall strategy, unresolved metering strategy, infrastructure contribution gap, or staging / OC path gap.

Escalation routing follows the role overlay's escalation table (see `role-builder.md §"Escalation routing — builder"` for the builder routing pattern; analogous tables sit in the other role overlays). Route each escalation through `escalation-note-system.md` and report the trigger, route and recommended action in the return summary.

### Step 10 — Return summary

Return a short summary to the user:

- which seeds were loaded (and `seed_consulted:` list for downstream deliverables);
- which artefacts the sweep found, with relevance ranking;
- which deliverables were drafted (paths);
- which gaps remain (actions opened);
- which escalations surfaced;
- the headline commissioning status (e.g. "12 of 28 ready-to-start items satisfied; 16 outstanding — 4 critical-path before site possession").

The user reviews the drafts, fills the gaps (or directs the agent to do so where the gap is gathering evidence rather than waiting for action), and signs the ready-to-start checklist.

## Rule

This skill is **the canonical commissioning entry point** for any SiteWise project. Other paths to commissioning (manual file creation, ad-hoc register opening) are valid but lose the discipline this skill enforces: §2 gate at the boundary, §evidence-discipline via `evidence-sweep`, §register-discipline via `register-row-draft`, §5 output discipline via `markdown-draft-for-review`, §6 voice / folder discipline via the same.

This skill **does not execute the contract**. Executing a head contract is a human act — owner and builder sign. The skill prepares the project's commissioning posture; the act of signing happens outside the skill.

This skill **does not bind insurance, lodge LSL, lodge HBCF**, or do any other statutory act on behalf of the project lead. Those are external transactions. The skill captures the evidence of those acts once done, and surfaces the gap until they are.

This skill is **idempotent** — re-running on a project where commissioning is partially complete identifies what is new (e.g. CWI Certificate of Currency now filed since the last run), surfaces what is still outstanding, and updates the ready-to-start checklist. It does not duplicate registers, does not overwrite reviewed drafts, does not re-create rows that already exist.

This skill **respects the AGENTS.md §11 active-project boundary** — operates only within the active project folder.

## Skill skeleton — for slices 06+ to inherit

The template for future system skills is:

1. **Pre-flight: §2 declaration gate** (re-checked at system-skill boundary even though `seed-targeted-read` also checks it).
2. **Step 1: `seed-targeted-read`** with the task subject — loads the right Tier 2 / Tier 3 / cross-cutting seed set.
3. **Step 2: `evidence-sweep`** with the task subject — returns the artefact inventory and gap report.
4. **Steps 3 to N: content-specific atomics and drafting** — using `register-row-draft` for register entries and `markdown-draft-for-review` for narrative deliverables, in the sequence appropriate to the workflow.
5. **Step N+1: surface gaps and escalations** — explicitly, per `../../00-doctrine/doctrine.md §escalation-triggers`.
6. **Step N+2: return summary** — drafts produced, gaps open, escalations surfaced, headline status.

Slice 06's `progress-claim-assessment-system` and `variation-management-system`, and slice 13's `handover-pc-system`, inherit this skeleton. The skeleton is not boilerplate; it is the §evidence-discipline / §register-discipline / §seed-consultation-discipline enforcement made consistent across all system skills.

## See also

- `../../AGENTS.md §1` (authority stack), `§2` (declaration gate), `§3` (seed loading rules), `§5` (output discipline), `§6` (voice register), `§9` (skill invocation), `§11` (active-project boundary)
- `../../00-doctrine/doctrine.md §seed-consultation-discipline`, `§evidence-discipline`, `§register-discipline`, `§decision-discipline`, `§escalation-triggers`, `§voice-and-style`
- `../../01-seed/setup-and-commission-guide.md` — the cross-cutting workflow this skill orchestrates
- `../../01-seed/contract-administration-guide.md` — contract clause coverage referenced by the contract summary
- `../../01-seed/new-dwelling-guide.md` — Tier 2 archetype seed loaded at step 1 for `archetype: new-dwelling`
- `../../01-seed/role-builder.md` — Tier 3 role overlay loaded at step 1 for `user_role: builder`
- `../../01-seed/multi-dwelling-guide.md` — Tier 2 archetype seed loaded at step 1 for `archetype: multi-dwelling`
- `../../01-seed/role-d-and-c.md` — Tier 3 role overlay loaded at step 1 for `user_role: d-and-c`
- `authority-approvals-system.md` — ongoing authority tracker, consent-condition register and approval handoff workflow
- `consultant-coordination-system.md` — ongoing consultant appointment, responsibility, deliverable and advice workflow
- `../atomic/seed-targeted-read.md` — loaded at step 1
- `../atomic/evidence-sweep.md` — loaded at step 2
- `../atomic/register-row-draft.md` — used at steps 4, 5, 6
- `../atomic/markdown-draft-for-review.md` — used at steps 3, 6, 7, 8
- (Slice 06) `progress-claim-assessment-system.md`, `variation-management-system.md` — inherit this skill's skeleton
- (Slice 13) `handover-pc-system.md` — inherits this skill's skeleton
