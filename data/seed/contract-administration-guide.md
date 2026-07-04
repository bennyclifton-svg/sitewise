---
tier: topic
seed_type: contract-reference
loaded_by: task subject (contract setup, variation, EOT, claim, notice, clause interpretation)
applies_to_roles: [owner-builder, architect-pm, builder, d-and-c]
applies_to_archetypes: [new-dwelling, renovation, multi-dwelling, ancillary, small-commercial]
state_default: NSW
topics: [contract-admin, variations, eot, claims, notices]
summary: "The NSW residential head-contract landscape across the HIA, MBA, Fair Trading prescribed, AS and ABIC families — payment, variation, EOT, latent conditions, notices, completion and DLP mechanisms. Clause-aware but not clause-exhaustive: the executed contract always wins."
required_by: {create-pmp: 2}
doctrine_anchors: [§seed-consultation-discipline, §evidence-discipline, §voice-and-style, §register-discipline]
agents_anchors: [§1, §6, §9]
---

# Contract administration guide — NSW residential

This seed gives the **NSW residential head-contract landscape** as it applies across the four SiteWise user roles. It covers contract families (HIA, MBA, NSW Fair Trading prescribed, AS, ABIC), the residential-relevant mechanisms (payment, variation, EOT, latent conditions, notices, suspension, completion, DLP), and the discipline of clause citation.

This seed is **clause-aware but not clause-exhaustive**. Where a specific clause interpretation is needed, the project's actual executed contract (with any special conditions) is the source of truth under the §1 authority stack. This seed gives the **shape** of each contract family and the **administration discipline** that applies across them; it does not substitute for reading the executed contract.

NSW is the deep default. Non-NSW callouts appear inline where contract family use or threshold differs materially.

## Contract families in NSW residential — at a glance

| Family | Form references | Typical use | Issued by |
|---|---|---|---|
| **HIA Lump Sum** (NSW New Homes) | "HIA Building Contract — NSW New Homes" | New Class 1a, defined scope | Housing Industry Association |
| **HIA Cost Plus** | "HIA Cost Plus Contract" | Uncertain scope, high-end residential, owner-builder hybrid | HIA |
| **HIA Renovation** | "HIA Renovations Contract" | Renovations, additions, alterations to existing dwelling | HIA |
| **HIA Trade Contract** | "HIA Sub-contract" | Subcontract between builder and subcontractor | HIA |
| **MBA NSW equivalents** | MBA NSW residential building contracts | Alternative to HIA for new homes, renovations, cost-plus | Master Builders Association NSW |
| **NSW Fair Trading prescribed contract** | "Small Jobs Contract" (the official Fair Trading template) | Residential work between $5,000 and $20,000 (mandatory written contract is triggered above $5,000) | NSW Fair Trading |
| **AS 4000-1997** | General conditions of contract | High-end residential where Superintendent is appointed; rare for standard residential | Standards Australia |
| **AS 4902-2000** | General conditions of contract for design and construct | D&C residential (sits on `role-d-and-c.md`) | Standards Australia |
| **ABIC** | ABIC SW (Simple Works), ABIC MW (Major Works) suites | Rare in NSW residential; sometimes architect-administered residential | Australian Building Industry Contracts (joint Master Builders Australia and the Australian Institute of Architects) |

The **HIA Lump Sum (NSW New Homes)** is the dominant new-dwelling contract in NSW. Most residential builders use it as default; most owners encounter it as the contract their builder presents. The HIA Renovation form is the dominant renovation contract. Cost Plus is for narrower situations.

For each contract family below, citation discipline applies: when referring to a clause in a project deliverable, **cite the clause number verbatim** and quote the relevant text. Do not paraphrase a clause into a project document — paraphrase loses precision and risks creating a contradicting record.

## HIA Lump Sum (NSW New Homes) — mechanism shape

The HIA Lump Sum contract is structured as standard conditions + schedules (special conditions, particulars, drawings, specifications) + appendices (prescribed forms).

Key mechanisms (clause numbers and exact text vary by edition — current edition is referenced; the executed contract is authoritative):

### Deposit

- Statutory cap on deposit: **10% in NSW** for residential building work under the Home Building Act 1989 — but commonly limited to **5% by the contract form**. Special conditions sometimes increase to 10%; never exceed the statutory cap.
- Deposit is taken **after HBCF certificate issued**, not before.

### Stage payment schedule

- Typical default stages and percentages (the contract editable):
  - Deposit: 5%
  - Base / Slab: 10%
  - Frame: 15%
  - Lockup: 35%
  - Fixing: 20%
  - Completion: 15%
- Percentages add to 100% of contract sum.
- Each stage is defined in the contract's Definitions or Particulars — read these carefully because "lockup" in particular varies.
- Builder issues a progress claim **only after** the stage is physically achieved.

### Owner-payment timing

- Owner must pay within the contract's stated period (often 5 to 7 working days from claim).
- Late payment triggers interest and, after sustained delay, suspension rights for the builder.

### Variation mechanism

- **HIA Schedule of Variations** — prescribed form within the contract.
- Variation **must** be written, priced, and signed by both parties **before work begins**.
- The variation clause is explicit: unwritten variations are recoverable only by argument and are unlikely to succeed in dispute.
- The variation form records: variation number, description, cost (or method of pricing if cost not yet known), time impact (or none), date signed by each party.

### EOT mechanism

- Notice given within the contract's notification window (commonly within 10 working days of the cause becoming apparent, but read the executed contract — special conditions can shorten this).
- Qualifying delay events typically: inclement weather above a stated threshold (e.g. more than a stated number of wet days per month), owner-caused delay, authority delay outside builder's control, latent conditions, force majeure.
- Time bar engaged for late notice.

### Latent conditions

- HIA Lump Sum has limited latent conditions provisions (more developed in HIA Renovation). For a new Class 1a on a previously cleared site, latent conditions are rare; for knockdown-rebuild they are common (existing footings, services not on diagrams, unrecorded fill).
- Where applicable, builder gives notice and stops work in the area of the latent condition; owner directs how to proceed; the direction is treated as a variation.

### Practical completion (PC)

- PC is reached when the works are complete except for minor defects and minor omissions that do not prevent the dwelling from being used for its intended purpose.
- Builder issues a notice of PC; owner inspects with builder; defects schedule is agreed.
- PC starts the DLP.

### Defects liability period (DLP)

- HIA Lump Sum default DLP: **13 weeks** (sometimes called the "warranty period" in the contract).
- Often varied by special conditions to 26 weeks.
- During DLP, builder rectifies defects identified at PC and notified during DLP.
- **Statutory warranty** runs independently and longer: in NSW, **6 years** for major defects and **2 years** for minor, under the Home Building Act 1989. The statutory warranty is not the DLP and is not coterminous.

### Insurance, HBCF, security

- The contract requires HBCF (referenced as "home building compensation cover" or by the older "HOW" name in older forms).
- Contract works and public liability insurance are contract obligations.
- Security (bank guarantee or retention) is uncommon in HIA Lump Sum but can be added by special conditions.

### Special conditions discipline

Special conditions modify the standard form and almost always shift risk. The project lead must:
- read every special condition;
- record the effect on payment, variation, EOT, latent conditions, defects, DLP, dispute resolution;
- not assume the standard form mechanism applies where a special condition has modified it.

A frequent special-condition trap: a clause reducing the EOT notification window from the standard form's default to (say) 5 working days. The shorter window catches builders out.

## HIA Cost Plus — mechanism shape

Cost Plus pays the builder for actual cost incurred plus a margin (typically 10–20%).

Key mechanism differences from Lump Sum:

- **No stage payments.** Builder invoices periodically (typically monthly or fortnightly) for actual cost incurred in that period, plus the margin.
- **Cost substantiation.** Every cost claimed must be substantiated by invoice or wage record. Owner is entitled to inspect records.
- **No variation form** in the same sense — Cost Plus is "everything is a variation" relative to the work directed. Owner direction in writing is still required; pricing is open by definition.
- **No fixed contract sum.** Contract may state a target cost with a defined sharing arrangement above target, or simply leave the total open.
- **EOT mechanism still applies** but with reduced commercial significance because the builder is paid time costs.
- **PC, DLP** as for Lump Sum.

Cost Plus is appropriate where scope is genuinely uncertain (high-end residential with bespoke detail, complex renovation, owner-builder hybrid where some packages are taken by builder and others by owner-builder). It is **inappropriate** for a defined-scope new Class 1a — Lump Sum is the right form there.

## HIA Renovation — mechanism shape

HIA Renovation is structurally a Lump Sum variant with **explicit latent conditions provisions** and stage definitions adapted for renovations (often: deposit / preparation / structural / lockup / fixing / completion, instead of slab as the structural milestone).

Renovation-specific mechanism notes:

- **Latent conditions clause is more developed** — builder gives notice, stops work in the affected area, owner directs (treated as variation).
- **Dilapidation report becomes a contract document** — the dilapidation establishes the baseline against which neighbour damage claims are judged.
- **Existing-services investigation** — discoveries of unrecorded services often become latent conditions.
- **Owner-occupied during renovation** — special conditions often cover access, working hours, dust and noise mitigation, security of the existing dwelling.

Slice 07 (Owner-builder + renovation cell) deepens renovation-specific contract content beyond this stub.

## HIA Trade Contract — subcontract mechanism

Used between builder and subcontractor. Mirrors the head Lump Sum form in shape:

- defined scope and price;
- progress claims against milestones or measured work;
- variations in writing, before work;
- subcontractor's insurances (PL, workers comp) named in the subcontract.

Builder must hold a Trade Contract (or equivalent written subcontract) with every subcontractor before site possession. Verbal subcontracts are common in residential and a recurring dispute source.

## MBA NSW equivalents

The Master Builders Association NSW publishes contracts that mirror the HIA forms — Lump Sum, Cost Plus, Renovation, Trade. Mechanism is functionally similar; clause numbering and specific drafting differ.

**Citation discipline:** if the project uses MBA forms, cite MBA clause numbers in project deliverables. Do not substitute HIA clause numbers — they are not equivalent and the contract is the MBA form.

## NSW Fair Trading prescribed contract — small jobs

The NSW Office of Fair Trading publishes a small-jobs contract template for residential building work between $5,000 and $20,000. Above $5,000, a written contract is mandatory under the Home Building Act; the prescribed form satisfies the requirement.

Mechanically thin compared to HIA / MBA:

- shorter form;
- simpler payment mechanism (often a small deposit and a single completion payment, or two payments);
- limited variation, EOT, and dispute provisions;
- DLP is the statutory minimum.

Appropriate for short-duration small-value work (a fence, a deck rebuild, a small bathroom renovation). **Not appropriate** for a new build or a renovation of any complexity — the thin mechanism cannot administer a long-running project.

## AS 4000-1997 — general conditions of contract

AS 4000 is the standard for general construction contracting in Australia. Use in residential is uncommon and limited to:

- high-end residential where the owner appoints a Superintendent (often the architect-PM);
- residential projects of unusual scale or complexity (multi-dwelling subdivisions, custom homes at the top of the market);
- owners with prior commercial experience who prefer AS contract structure.

Mechanism differences from HIA Lump Sum:

- **Superintendent** is named; the Superintendent issues directions, assesses claims, certifies practical completion. The Superintendent is the owner's appointed representative — the builder takes instructions through the Superintendent.
- **Time bars are explicit and strictly enforced** — late notices for EOT or variation under AS 4000 are generally unrecoverable.
- **Security** — bank guarantee or retention is standard.
- **Contemporaneous claims discipline** — claims are assessed as at the time of the event, not retrospectively.

For new Class 1a, the AS 4000 mechanism is heavy. Where used, the role overlay for whoever is administering the contract (typically architect-PM as Superintendent's representative, or builder) drives the daily administration discipline.

## AS 4902-2000 — D&C variant

AS 4902 is the D&C variant. Loaded for `user_role: d-and-c` per `role-d-and-c.md`. Mechanism differences from AS 4000:

- Contractor carries design responsibility under the contract;
- Principal's Project Requirements (PPR) form the contractual scope basis;
- Design submission protocol with the Principal.

`role-d-and-c.md` covers the D&C role posture in depth, including design responsibility matrix, design programme, PI evidence, consultant procurement, and certifier submission control.

## ABIC — Australian Building Industry Contracts

ABIC suite (SW for Simple Works, MW for Major Works, EW for Early Works, BW for Basic Works) is used occasionally in NSW residential, more often where the architect is the contract administrator and there is preference for ABIC's clarity around architect-administered residential.

Mechanism in ABIC is broadly comparable to HIA but with the architect as the explicit administrator (similar to AS 4000's Superintendent). Architect issues instructions, assesses claims, certifies completion.

For a project using ABIC, cite ABIC clause numbers; do not paraphrase or substitute.

## Cross-family administration discipline

Across all contract families, the following discipline applies to the project lead's contract administration:

### Clause citation

When writing a project deliverable that references the contract:

- cite the clause number;
- quote the clause text verbatim (or the relevant portion);
- name the contract edition and date if not obvious from the project header;
- file the deliverable in a folder whose voice register is contractual (per AGENTS.md §6 — typically `07-construction/05-progress-claims/`, `06-variations/`, `07-programme-eot/`, `08-rfi-notices/`).

Example phrasing (contractual register):
> Under Clause 17.1 of the executed HIA Lump Sum Contract dated 14 March 2026, "the Builder may submit a progress claim within seven days after the end of each stage". This claim is submitted in accordance with that clause.

Counter-example (loose paraphrase, do not do):
> The contract lets the builder claim after each stage.

### Notice mechanics

A contractual notice has form requirements: addressed to the right party at the contract address, in the form the contract requires (often written, sometimes delivered or sent in a specific way), within the contract's time window. The form requirements are clause-specific.

- record the date of issue;
- record the method of delivery (email to contract email, hand delivery with signed receipt, registered post);
- save a copy in `07-construction/08-rfi-notices/`;
- log a register row with reference, date, recipient, subject, response-due-date.

### Time bars

Many contractual rights are barred by late notice:

- EOT typically time-barred under HIA Lump Sum (the precise window is in the clause; commonly 10 working days from the cause becoming apparent — but read the contract);
- Variation claims by builder for unwritten changes are not formally time-barred but are evidentially weak;
- Dispute notices are time-barred under HIA and most forms;
- Final claim under AS 4000 is time-barred at a fixed point relative to PC.

A late notice is the most common way builders lose otherwise valid claims. The §escalation-triggers anchor catches the trigger event; the contract administration discipline turns it into a timely notice.

### Variation discipline (cross-family)

Every contract family requires written variations before work begins. The mechanism varies (HIA uses Schedule of Variations form; AS 4000 uses Superintendent's directions; MBA uses MBA variation form), but the discipline is universal:

1. Owner / Superintendent / Principal issues written direction (or builder identifies a needed change and requests direction).
2. Builder prices the variation (cost + time impact).
3. Owner / Superintendent / Principal accepts in writing.
4. Work begins.
5. Builder records the variation in the variation register (§register-discipline) and the cost register.

Skipping any step is a §variation-management failure. The most common skip is step 4 starting before step 3 finishes — the work proceeds while pricing is "still being finalised", and by the time pricing surfaces, the bargaining position is gone.

### Progress claim discipline (cross-family)

For Lump Sum / Renovation contracts (HIA / MBA), the claim is against the stage payment schedule and requires:
- the stage to be physically achieved;
- trade evidence (inspections, certificates) supporting achievement;
- the claim form per the contract;
- the cover letter citing the relevant clause;
- supporting documentation list as the contract requires.

For Cost Plus, the claim is for actual costs incurred and requires invoice / wage record substantiation.

For AS 4000, the claim is contemporaneous with the period being claimed, assessed by the Superintendent.

For NSW Fair Trading prescribed and small jobs, the mechanism is simpler — typically one or two staged payments per the prescribed form.

The **assessor side** (whoever receives the claim and decides what to pay) is the subject of the `progress-claim-assessment-system` skill in slice 06. This guide gives the **issuer side** discipline and the cross-family shape.

### EOT discipline (cross-family)

1. Cause event occurs (weather, owner delay, latent condition, authority delay).
2. Builder identifies it as a qualifying delay event under the contract.
3. Builder gives notice within the contract's window.
4. Builder maintains contemporaneous evidence (programme, photos, correspondence, weather records).
5. Builder pricing time impact through the contemporaneous programme.
6. Owner / Superintendent / Principal assesses and grants (or part-grants) the EOT.
7. Builder updates programme and EOT register.

Step 3 is the failure point. Late notice = time bar = lost claim.

### Practical completion discipline (cross-family)

PC is reached when works are complete except for minor defects and minor omissions. Disputes about PC commonly arise around what is "minor". A minor defect:
- does not prevent the dwelling from being used for its intended purpose;
- is reasonably capable of rectification;
- is identified on the PC defects list.

A non-minor incomplete item (e.g. balustrade missing, kitchen joinery not installed) is not eligible to be on the PC list — it stops PC from being achieved. Builder must complete it before claiming PC.

PC starts the DLP. PC starts the statutory warranty period. PC is a non-trivial gate; do not let pressure to "call PC" rush past genuine completion.

### Defects liability — discipline

During DLP:
- defects notified by the owner are recorded in the defects register;
- builder rectifies within reasonable time;
- builder's rectification is inspected and closed in the register;
- final claim (retention release, final payment) is released after DLP expires and all defects closed.

The §register-discipline applies — every defect row has ID, description, owner (typically the trade responsible), status, due date, source / evidence reference, next action.

## Contract-family-by-role suitability

| Family | Owner-builder | Architect-PM | Builder | D&C |
|---|---|---|---|---|
| HIA Lump Sum | N/A (owner-builder has no head contract; subcontracts may use HIA Trade) | Recommends and administers on owner's behalf | Issues to owner | Possible head form |
| HIA Cost Plus | Hybrid — owner-builder may use Cost Plus for specific packages (e.g. brickwork) | Sometimes recommended for high-end / uncertain scope | Issues to owner | Possible |
| HIA Renovation | N/A | Recommends for additions to existing | Issues to owner | Possible |
| MBA equivalents | As HIA | As HIA | As HIA | As HIA |
| NSW Fair Trading prescribed | Owner-builder may use for small package subcontracts | Recommends only for genuinely small work | Issues to owner only for small jobs ($5,000–$20,000) | Rare |
| AS 4000 | N/A | Acts as Superintendent's representative if appointed | Subject to head contract if owner has selected AS form | Rare |
| AS 4902 | N/A | Possible | Possible D&C variant | **Primary form for D&C** |
| ABIC | N/A | Sometimes architect-administered residential | Subject to head contract | Possible |

## Non-NSW callouts

- **VIC:** HIA Victorian Conditions are different from NSW; *Domestic Building Contracts Act 1995* (Vic) applies (set of statutory implied terms). Builder licence is "Domestic Builder" registration with the Victorian Building Authority (VBA) — not NSW Fair Trading. **DBI (Domestic Building Insurance)** administered by the VMIA or approved insurers is the VIC equivalent of NSW HBCF / HOW; threshold is $16,000 and must be obtained before any deposit is taken. Contract forms: HIA Vic Lump Sum or Master Builders Victoria equivalents — confirm which edition is executed before citing clauses.
- **QLD:** QBCC governs residential contracts. Standard QBCC Level 1 and Level 2 contracts published. QBCC Home Warranty Insurance threshold $3,300 — much lower trigger than NSW.
- **SA:** Consumer and Business Services (CBS) governs Building Work Contractors. HIA SA forms differ.
- **WA / TAS / NT / ACT:** state-specific frameworks. Where a non-NSW project is administered, the agent flags the gap and asks the project lead to supplement.

Where `state:` is not NSW and the project uses a HIA-branded form, **the form will have state-specific variants** — confirm which edition is executed before citing clauses.

## Common contract-administration failures

- **Special conditions not read.** Builder signs the standard form without noticing that special conditions have, for example, shortened the EOT window to 3 days.
- **Variations worked before pricing.** "We'll sort it out at the end" — by the end, the bargaining position is gone.
- **Late EOT notices.** Time bar engaged.
- **PC declared while non-minor items incomplete.** DLP starts in dispute.
- **Statutory warranty conflated with DLP.** Owner expects DLP to cover what is actually a statutory warranty claim, or vice versa.
- **HIA clause numbers cited where the contract is MBA** (or vice versa). The cited clause does not exist or means something else.
- **Paraphrased clause text in project deliverables.** Paraphrase loses precision; if a dispute arises, the project record contradicts the contract.

## Agent behaviour under this seed

When this seed is loaded:

1. Confirm the project's executed contract is known. If not, flag and ask before drafting any contract-referring content.
2. Cite the actual executed contract's clause numbers and form name (e.g. "Clause 17.1 of the HIA Lump Sum NSW New Homes Contract, edition dated [X]"), not a generic reference.
3. Quote clause text verbatim where the deliverable depends on the wording.
4. Apply §evidence-discipline labelling — a clause interpretation that is the project lead's reading is Judgement; the clause text itself is Fact (from the executed contract); a position taken on the basis of the clause is Recommendation.
5. Default to contractual register per §voice-and-style for any deliverable that references the contract.

## See also

- `../00-doctrine/doctrine.md §voice-and-style`, `§evidence-discipline`, `§register-discipline`, `§escalation-triggers`
- `../AGENTS.md §1` (authority stack — the executed contract beats this seed), `§6` (voice register), `§9` (skill invocation)
- `role-builder.md` — builder-side issuance discipline for claims, variations, EOT
- `role-owner-builder.md` — owner-builder hybrid contract use (slice 07 deepens)
- `role-architect-pm.md` — architect-PM as Superintendent's representative (slice 08 deepens)
- `role-d-and-c.md` — AS 4902 and D&C contract administration
- `setup-and-commission-guide.md` — contract execution as part of mobilisation
- `new-dwelling-guide.md` — Class 1a project context for contract selection
- `../02-skills/atomic/seed-targeted-read.md` — the gate that loads this seed
- `../02-skills/systems/contract-setup-system.md` — orchestrates contract setup using this seed
- (Slice 06 future) `progress-claim-assessment-system`, `variation-management-system` — assessment side of the issuance discipline this seed establishes
