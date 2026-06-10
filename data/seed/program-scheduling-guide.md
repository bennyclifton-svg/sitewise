---
seed_tier: cross-cutting
seed_type: programme-reference
loaded_by: task subject (programme, schedule, critical path, lead time, residential cycle time, risk register)
applies_to_roles: [owner-builder, architect-pm, builder, d-and-c]
applies_to_archetypes: [new-dwelling, renovation, multi-dwelling, ancillary, small-commercial]
state_default: NSW
doctrine_anchors: [§seed-consultation-discipline, §evidence-discipline, §register-discipline, §voice-and-style, §escalation-triggers]
agents_anchors: [§1, §2, §3, §5, §6, §8, §9, §11]
---

# Programme scheduling guide - residential

This seed gives SiteWise its residential programme and cycle-time posture. It is loaded by `seed-targeted-read` when the task signal is programme, scheduling, lead time, critical path, lookahead, EOT support, or risk register.

The filename uses `program` for compatibility with the existing seed catalogue. The content uses Australian construction language: **programme**.

Authority stack reminder (per `../AGENTS.md §1`): project evidence in the active project folder beats this seed. The executed contract, current programme, approval conditions, certifier inspection requirements, supplier commitments, and site records are the source of truth. Where evidence is missing, the agent labels the point as Assumption per `../00-doctrine/doctrine.md §evidence-discipline`.

## 1. Purpose and scope

Residential programming is not just a bar chart. It is the time-control system that connects approvals, procurement, trade sequencing, inspections, stage-payment entitlement, EOT evidence, owner decisions, and handover.

This seed covers:
- master programmes for residential projects;
- milestone trackers;
- four to six week lookahead programmes;
- delay registers and EOT-supporting programme updates;
- programme risk commentary for reports and owner updates;
- residential cycle-time benchmarks for slab, frame, lockup, fixing, completion, and handover.

This seed does not create a standalone programme-drafting system skill. System skills that need programme coverage load this seed and then use `markdown-draft-for-review`, `register-row-draft`, and, where approved, the Excel atomics.

## 2. Residential programme outputs

The usual residential programme outputs are:

| Output | Folder | Voice | Purpose |
|---|---|---|---|
| Master programme | `06-programme/` | contractual | Baseline sequence from mobilisation to PC, OC, and DLP |
| Milestone tracker | `06-programme/` | contractual | Key dates and movement against baseline |
| Lookahead programme | `06-programme/` | contractual | Rolling four to six week coordination tool |
| Delay register | `06-programme/` or `07-construction/07-programme-eot/` | contractual | Contemporaneous delay events, cause, impact, owner, next action |
| EOT-supporting update | `07-construction/07-programme-eot/` | contractual | Contractual evidence for time claims or assessments |
| Owner programme summary | `08-meetings-reporting/owner-programme*` | stakeholder | Plain-English date movement and decisions needed from the owner |
| Programme risk commentary | `08-meetings-reporting/` or `00-brief-pmp/` | contractual or stakeholder by audience | Integrated time-risk view for governance |

Every programme output should include:
- baseline date and revision date;
- source evidence consulted;
- cycle-time assumptions;
- working calendar assumptions, including public holidays, industry shutdown, and weather allowance;
- critical path or near-critical path summary;
- float assumptions;
- lead-time assumptions for approvals, utilities, inspections, and long-lead items;
- owner, builder, consultant, certifier, supplier, or authority decisions required;
- next review date.

## 3. Master programme shape

A residential master programme is typically 50 to 200 lines. A small owner-builder or ancillary project may sit at the lower end. A multi-dwelling or high-end D&C project may need more detail, but the same discipline applies.

PMP stage anchor:

Where a PMP exists, use its programme / staging section as the high-level stage source before drafting the detailed milestone spine. If the PMP does not define staging clearly, use this baseline as an explicit Assumption and recommend updating the PMP:

| Stage | Baseline meaning |
|---|---|
| Stage 1 | Concept and schematic design to DA submission |
| Stage 2 | Design development |
| Stage 3 | Construction documentation and delivery |

Detailed programme activities may be more granular than these stages, but they must map back to them. If authority, consultant, funding, contract or construction evidence requires a different stage regime, flag the conflict and recommend aligning the PMP, programme and affected procurement / consultant artefacts.

For multi-dwelling, apartment, staged OC or D&C-signalled projects, establish a more detailed PMP stage regime before the programme is drafted. A typical detailed regime is:

| Stage | Detailed meaning |
|---|---|
| Stage 1 | Design status, DA / consent status, certifier pathway and responsibility confirmation |
| Stage 2 | Procurement and D&C / head contract pathway confirmation |
| Stage 3 | Enabling works, demolition, excavation, shoring, services authority setup and site establishment |
| Stage 4 | Basement, structure and superstructure |
| Stage 5 | Envelope, services rough-in, fire/access/acoustic compliance, waterproofing, finishes and repeated dwelling / apartment cycles |
| Stage 6 | Commissioning, OC, staged handover, defects close-out and DLP commencement |

Minimum residential milestone spine:

| Milestone | Why it matters |
|---|---|
| Design lock | Starts the chain for approvals, BASIX/NatHERS modelling, structural design, and procurement |
| Planning approval / CDC / DA | Confirms the planning pathway and conditions |
| CC or building permit issued | Enables lawful construction start |
| LSL / state equivalent cleared | Blocks CC in NSW if missing |
| Site possession | Starts site risk and usually programme accountability |
| Slab / footing inspection and pour | First major site stage and common claim milestone |
| Frame complete | Structural inspection gate and claim milestone |
| Roof / lockup | Envelope control, window/door lead-time proof point, claim milestone |
| Rough-in complete | Services ready for lining and wet-area sequencing |
| Fixing complete | Joinery, linings, wet areas, and services progressing toward completion |
| PC inspection | Defects list and contract completion posture |
| OC / occupancy approval | Authority close-out and handover gate |
| Handover | Keys, manuals, warranties, HOW/HBCF handover where applicable |
| DLP start and end | Defect time window pinned to PC/handover mechanics |

The programme must not treat stage-payment names as proof of completion. HIA stages are useful programme milestones, but each stage still needs physical evidence and contract-specific meaning.

## 4. Residential cycle-time examples

The ranges below are planning benchmarks only. They are not a substitute for project evidence. The agent should label them as Assumption when project-specific durations are not evidenced.

| Cycle | Typical range | Main variables | Evidence to confirm |
|---|---|---|---|
| Site possession to slab pour | 2-6 weeks | demolition, tree removal, cut/fill, rock, services disconnections, piering, weather, certifier availability | survey, geotech, structural drawings, demolition plan, certifier inspection booking |
| Slab pour to frame start | 3-10 working days | curing requirement, supplier mobilisation, frame delivery, set-out check, wet weather | concrete docket, engineer/certifier sign-off, frame supplier delivery date |
| Frame start to frame complete | 2-6 weeks single storey; 4-10 weeks two storey | complexity, steel beams, truss timing, weather, crew size, stair/install sequencing | framer quote, truss order, structural drawings, inspection booking |
| Frame complete to roof-on | 1-3 weeks | truss/roof sheet lead time, scaffolding, weather, roof complexity, gutters | truss certificate, roof supply commitment, scaffold plan |
| Roof-on to lockup | 2-6 weeks | windows/doors lead time, brick/cladding sequence, weather, BAL detailing | window order, BASIX/NatHERS glazing commitments, cladding procurement |
| Lockup to rough-in complete | 2-5 weeks | electrical, plumbing, HVAC, gas, NBN, inspection availability | trade scopes, services drawings, inspection hold points |
| Rough-in to lining complete | 1-3 weeks | insulation inspection, plasterboard crew, moisture in framing, design changes | insulation spec, frame moisture check, lining schedule |
| Lining to fixing complete | 4-10 weeks | joinery, tiling, waterproofing, floor finishes, PC selections, owner decisions | joinery shop drawings, PC item schedule, tile/appliance orders |
| Fixing to PC | 3-6 weeks | painting, flooring, final services, commissioning, defect pickup, BASIX final evidence | commissioning records, inspection schedule, defect list |
| PC to OC / handover | 2-6 weeks | OC evidence, BASIX final, defects, final claim, owner manuals, keys | certifier requirements, BASIX assessor confirmation, handover checklist |

For multi-dwelling, these cycles repeat by dwelling, block, or stage. The agent should identify whether the programme is sequential, overlapping, or staged for settlement/handover.

For `user_role: d-and-c`, the master programme needs linked design and construction tracks. Design deliverables, design review, certifier submissions, authority responses, and construction-release milestones must be visible before the affected site activity. Do not let a site activity rely on unreleased design; surface it as a programme gap, RFI, or design deliverable action.

For `archetype: multi-dwelling`, show the classification / approval gate, first-of-type party-wall inspection, metering and utility application lead times, infrastructure / OSD / stormwater authority gates, and staged OC / subdivision / strata / handover assumptions where they affect sequence or cashflow.

## 5. Trade duration guidance

Residential trade durations vary sharply by project size, access, design maturity, and labour availability. Use the ranges below as a first-pass planning check.

| Trade / activity | Typical duration signal | Programme note |
|---|---|---|
| Demolition / clearing | 1-10 working days for simple demolition; longer if asbestos or neighbour protection applies | Separate disconnection, hazmat, and waste certificates from physical demolition |
| Excavation and cut/fill | 2 days to 3 weeks | Rock, tight access, spoil disposal, and wet weather drive variance |
| Formwork / reo / vapour barrier | 2-8 working days | Inspection booking must be a separate hold point |
| Concrete pour | 1 day plus cure/strip time | Weather and concrete supply can move dates by days at a time |
| Termite treatment | 1 day, but gate-sensitive | Must precede pour or relevant enclosure point depending on system |
| Framing | 2-10 weeks | Two-storey, steel beams, complex roof forms, and stair openings add time |
| Roof trusses and roof cover | 1-3 weeks after frame ready | Truss lead time often starts well before site readiness |
| Windows and external doors | 1-3 weeks install after manufacture | Lead time can dominate lockup; BASIX/NatHERS commitments constrain substitution |
| Brickwork / cladding | 2-8 weeks | Weather and scaffold access matter; brick choice may have 6-12 week lead time |
| Plumbing rough-in | 3-10 working days | Wet areas, gas, HW system, rainwater tank, and sewer constraints change duration |
| Electrical rough-in | 3-10 working days | Lighting changes and owner selections can destabilise fixing dates |
| HVAC / ventilation rough-in | 2-8 working days | Ducted systems and mechanical ventilation require ceiling coordination |
| Insulation | 1-4 working days | BASIX/NatHERS commitments and inspection timing matter |
| Plasterboard / linings | 1-4 weeks | Moisture in frame and incomplete services are common blockers |
| Waterproofing | 1-2 weeks including cure and inspection | Do not compress cure/test periods to recover programme |
| Tiling | 1-4 weeks | Large-format tiles and substrate prep slow production |
| Joinery | 1-3 weeks install, but 6-16 weeks lead time | Shop drawings and site measure drive reliability |
| Painting | 1-4 weeks | Exclusive possession improves productivity; rework follows late trades |
| Floor finishes | 1-3 weeks | Moisture tests and protection need explicit activities |
| Services final fix | 1-3 weeks | Appliances, HW, PV, NBN, commissioning records feed completion |
| Defect close-out | 1-3 weeks pre-PC plus DLP later | Separate pre-PC defects from DLP defects |

## 6. Lead-time guidance

The master programme must show long-lead decisions early enough that the project lead can act before they become critical path.

| Item | Typical residential lead-time signal | Trigger point |
|---|---|---|
| DA determination | 8-24 weeks in NSW where DA pathway applies | Before design promises site-start date |
| CDC | 2-6 weeks where design fits complying pathway | After compliance test, before assuming faster start |
| CC / building permit | 4-12 weeks depending on documentation and prerequisites | Before site possession |
| LSL / state equivalent | Days to weeks depending on payment and processing | Before CC in NSW |
| HBCF / HOW or state equivalent | Days to weeks, longer if eligibility/sum changes | Before contract requirements and deposit/commencement posture |
| Certifier / BPA inspections | 3 days to 3 weeks depending on market | Before each hold point |
| Utility connections | Water/sewer 4-12 weeks; electricity 6-16 weeks; NBN variable | Lodge at or before CC where possible |
| Trusses | 4-8 weeks | Order after final frame/roof design |
| Windows / glazing | 8-14 weeks | Order after BASIX/NatHERS and final openings confirmed |
| Bricks / cladding | 6-12 weeks for non-standard selections | Order before frame/roof sequence makes facade critical |
| Joinery | 6-16 weeks; imported longer | Site measure and shop drawing approval are separate activities |
| Tiles / floor finishes | 4-12 weeks for selected/imported items | Owner selection must precede fixing start |
| Appliances | 4-12 weeks, volatile by brand | Confirm before joinery and services final fix |
| HW system | 4-10 weeks for heat pump/specialist systems | BASIX/NatHERS commitment must be checked before substitution |
| PV system | 4-10 weeks plus grid/installer availability | Program commissioning before OC/handover |

If a lead time is not evidenced by supplier quote, purchase order, approval notice, or written commitment, treat it as Assumption and record the next action.

## 7. Cycle-time annotation discipline

Every master programme, lookahead, or programme summary produced through SiteWise should annotate residential cycle times. The annotation can be a table, note field, or appendix. It must state:

| Field | Requirement |
|---|---|
| Activity / milestone | The programme line being annotated |
| Cycle-time basis | Fact, Assumption, Judgement, or Recommendation per §evidence-discipline |
| Duration | Working days or calendar days; state which calendar is used |
| Source / evidence | Quote, contract, prior programme, supplier commitment, approval, inspection requirement, or seed assumption |
| Float / criticality | Critical, near-critical, or has float, with basis |
| Lead-time trigger | Date by which procurement, approval, or decision must occur |
| Owner | Who must act next |
| Review date | ISO date for the next check |

Example:

| Activity | Duration | Basis | Source | Float | Owner | Review |
|---|---|---|---|---|---|---|
| Window manufacture | 10 weeks | Assumption | BASIX-linked glazing package; supplier quote not yet received | Near-critical to lockup | Builder | 2026-06-15 |

## 8. Programme risk triggers

The following risk triggers should feed `risk-register-system` when relevant:

| Trigger | Programme consequence | Register signal |
|---|---|---|
| BAL/bushfire rating not confirmed | Window, cladding, decking, and ember-sealing lead times can change | Risk row for BAL/bushfire |
| Latent moisture / wet substrate | Lining, flooring, joinery, and painting can be blocked | Risk row for latent moisture |
| Neighbour dilapidation not captured | Access, excavation, vibration, and damage claims become harder to manage | Risk row for neighbour dilapidation |
| Tight-block access | Deliveries, craneage, spoil removal, scaffold, and trade overlap slow down | Risk row for tight-block site access |
| Owner change requests | Design, procurement, PC sums, variations, and trade resequencing move | Risk row for owner change requests |
| Weather | Excavation, slab, roof, cladding, painting, and external works slip | Risk row for weather |
| Materials lead time | Lockup/fixing/completion dates move if long-lead items are late | Risk row for materials lead time |
| Subcontractor no-show | Lookahead fails; downstream trades lose workface | Risk row for subcontractor no-show |
| Certifier / BPA availability | Hold-point inspections strand the programme | Risk row for inspection availability |
| Utility connection delay | OC/handover can be blocked late | Risk row for utility connection |
| BASIX / NatHERS substitution | Re-certification and procurement changes delay completion | Risk row for energy-commitment substitution |
| OSD / stormwater hold point | OC or external works completion can be blocked | Risk row for stormwater/OSD |

Risks are useful only where they create a next action. A risk with no owner, no source, no review date, or no next action fails §register-discipline.

## 9. Programme reporting and voice

Voice is folder-driven per `../AGENTS.md §6` and `../02-skills/atomic/markdown-draft-for-review.md`.

Use **contractual register** for:
- master programme submissions in `06-programme/`;
- lookahead programmes issued to builders, subcontractors, consultants, certifiers, or authorities;
- EOT-supporting programme updates in `07-construction/07-programme-eot/`;
- delay registers;
- programme-risk commentary used for contract administration.

Use **stakeholder register** for:
- owner-facing programme summaries;
- monthly owner updates that explain date movement in plain English;
- owner decision requests where the purpose is to explain consequences rather than issue a formal notice.

The same programme movement can require two outputs: a contractual update for the project record and a stakeholder summary for the owner. Do not blend the voices inside one document unless the audience truly needs both.

## 10. State callouts

NSW is the deep default in SiteWise v1. Non-NSW states use inline graceful-degradation callouts per `../AGENTS.md §8`.

Common programme equivalents:
- **VIC:** building permit replaces NSW CC posture; domestic building insurance and VMIA / insurer processes can affect setup timing; NatHERS rather than BASIX shapes energy evidence.
- **QLD:** QBCC Home Warranty and inspection practices can affect setup and claims; NCC energy pathway rather than BASIX.
- **SA / WA / TAS / NT / ACT:** use the state building approval, warranty/insurance, and energy evidence pathways applicable to the project. Where this seed lacks detail, flag the gap rather than silently extending NSW guidance.

For non-NSW projects, the agent should state: "State-specific timing is an Assumption until the project lead confirms the applicable approval, warranty/insurance, and energy compliance pathway."

## 11. Agent behaviour

When a task touches programme or cycle time:

1. Confirm the §2 declaration gate has passed before any phase-gate draft.
2. Load the Tier 2 archetype seed, Tier 3 role overlay, and this guide via `seed-targeted-read`.
3. Run `evidence-sweep` before drafting so project evidence beats seed benchmarks.
4. Label unsupported durations and lead times as Assumption.
5. Include the cycle-time annotation discipline above in master programmes and lookaheads.
6. Feed programme risk triggers into `risk-register-system` when a risk needs an owner and next action.
7. Use `markdown-draft-for-review` for narrative programme outputs.
8. Use `register-row-draft` for delay, action, decision, risk, EOT, or owner-supplied rows that flow from programme work.

## 12. See also

- `../AGENTS.md §1` - authority stack
- `../AGENTS.md §2` - three-overlay declaration gate
- `../AGENTS.md §3` - seed loading rules
- `../AGENTS.md §5` - output discipline
- `../AGENTS.md §6` - voice register
- `../AGENTS.md §8` - state handling
- `../AGENTS.md §9` - skill invocation
- `../AGENTS.md §11` - active-project boundary
- `../00-doctrine/doctrine.md §seed-consultation-discipline`
- `../00-doctrine/doctrine.md §evidence-discipline`
- `../00-doctrine/doctrine.md §register-discipline`
- `../00-doctrine/doctrine.md §voice-and-style`
- `../00-doctrine/doctrine.md §escalation-triggers`
- `new-dwelling-guide.md` - lifecycle, inspection gates, sequencing risks
- `setup-and-commission-guide.md` - baseline programme and commissioning registers
- `contract-administration-guide.md` - EOT, variation, claim, and notice posture
- `cost-management-principles.md` - cashflow and cost-plan relationship to programme
- `../02-skills/atomic/seed-targeted-read.md` - loads this seed by task subject
- `../02-skills/atomic/evidence-sweep.md` - identifies programme evidence
- `../02-skills/atomic/register-row-draft.md` - drafts risk, delay, action, and EOT rows
- `../02-skills/atomic/markdown-draft-for-review.md` - wraps programme drafts with frontmatter and voice checks
- `../02-skills/systems/risk-register-system.md` - consumes the risk triggers above
