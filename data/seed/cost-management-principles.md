# Cost Management Principles — Residential

This is the residential cost-management seed for SiteWise. It is the cross-cutting topic seed loaded by `seed-targeted-read` when the task signal is cost, budget, contingency, claim, or variation pricing (see `../02-skills/atomic/seed-targeted-read.md §"Step 2 — Match task subject to cross-cutting topic seeds"`).

Residential cost management is **not** commercial cost management in miniature. The conventions differ in shape, not just scale:

- the **HIA Schedule of Allowances** is the format owners and builders both expect — not the AIQS elemental breakdown;
- **PC (prime cost) sums** for owner-selected items (kitchen, bath, tiles, appliances, taps, sanitary, lighting, joinery, flooring) are how the contract handles the not-yet-chosen specification cost;
- **owner-supplied items** are a discrete category, contractually distinct from PC items;
- **contingency** sits in the project lead's accounting in the 5–10% band (not the 3–5% commercial construction band), with the residential reality of owner change appetite priced in;
- **GST** is typically inclusive in residential cost plans (the owner is usually an owner-occupier who cannot recover GST), the reverse of commercial convention;
- the **HIA stage-payment schedule** (deposit / base / frame / lockup / fixing / completion) is the typical claim mechanism — not monthly measured progress claims;
- **variation discipline** is enforced by the HIA Schedule of Variations form rather than by a Superintendent's direction.

The principles below are the abstract project-lead view; role-specific obligations (who issues a claim, who assesses it, who pays) live in the role overlay seeds (`role-builder.md`, `role-architect-pm.md`, `role-owner-builder.md`, `role-d-and-c.md`) and are loaded alongside this seed.

Authority stack reminder (per `../AGENTS.md §1`): project evidence in the active project folder beats this seed. If the project has a cost plan or contract that uses a different schema, the project evidence wins. State the assumption explicitly where evidence is silent, per `../00-doctrine/doctrine.md §evidence-discipline`.

## 1. The residential cost plan in HIA Schedule of Allowances format

The HIA Schedule of Allowances is the residential industry's accepted format for the cost-plan equivalent in an HIA lump-sum or HIA cost-plus contract. It is the basis on which an owner and a builder agree the budget shape, and it carries through into the contract's PC and variation mechanisms. A cost plan that does not map cleanly to the Schedule of Allowances is hard for the owner to read against the contract and hard for the builder to claim against.

The Schedule of Allowances structure (typical):

1. **Preliminaries** — site set-up, hoarding, site amenities, scaffold, temporary services, site supervision, project insurances charged to the builder, builder's licence fee allocation, HBCF premium (NSW) or DBI premium (VIC) allocation, LSL or CoINVEST allocation.
2. **Excavation and earthworks** — site cut and fill, footing excavation, spoil removal, rock allowance (provisional sum where soil report flags risk).
3. **Foundations and slab** — concrete, reinforcement, formwork, vapour barrier, termite management; slab classification per AS 2870 (M / H1 / H2 / E / P) drives volume and reinforcement.
4. **Frame** — timber framing per AS 1684 or steel framing where specified; wind classification per AS 4055 drives bracing.
5. **External cladding** — brick veneer, render, weatherboard, FC sheet, EPS panel, etc.
6. **Roof** — trusses, sarking, battens, roof cladding (tile / Colorbond / membrane), gutters and downpipes.
7. **Windows and external doors** — frame material, glazing performance per BASIX (U-value, SHGC), security screens.
8. **Internal linings and partitions** — plasterboard, insulation per BASIX commitments (R-values), cornices.
9. **Floor coverings** — tile, timber, carpet, vinyl, polished concrete. Usually a PC line per coverage type.
10. **Wet areas** — waterproofing, tile, taps and sanitary (PC items), shower screens, mirrors, accessories.
11. **Kitchen** — joinery (PC item), benchtop (PC item), appliances (PC items, often owner-supplied), splashback, sink and tapware (PC items).
12. **Joinery (non-kitchen)** — robes, vanities, laundry joinery, study or built-in furniture. Typically PC items.
13. **Electrical** — switchboard, sub-circuits, lighting (PC item for fittings), data, security, PV per BASIX.
14. **Plumbing and gas** — sanitary fixtures (PC item), HW system (BASIX commitment), gas service, rainwater tank if BASIX requires.
15. **HVAC and mechanical ventilation** — split / ducted system, range-hood discharge, bathroom and laundry mechanical exhaust per NCC.
16. **External works and landscaping** — driveway and crossover, paths, fencing, retaining, landscape. Often a defined PC or excluded with owner-supplied scope.
17. **Painting and final finishes** — internal and external paint, stains and clear finishes.
18. **PC sums schedule** — itemised allowances for owner-selected components (see §3).
19. **Owner-supplied allowances** — items the owner is supplying outside the builder's scope (see §4).
20. **Contingency** — 5–10% line, declared with a basis (see §5).
21. **Builder's margin** — where the contract is HIA Cost Plus, the margin is a separate line; for HIA Lump Sum it is embedded in the trade lines and not a discrete row.
22. **Variation totals to date** — running variation total as the project progresses (cross-reference variation register, see §7).

The line list above is typical, not canonical — the HIA stationery and the executed contract's particulars together define the exact structure for a project. **The project's contract is the source of truth.** This seed lists the typical pattern so the agent can draft a recognisable cost plan when no project-specific schedule exists yet.

**Claim-first cost planning:** A project lead may be asked to certify or assess a claim before a formal cost plan workbook exists. In that case, do not treat the missing workbook as a reason to produce a thin cost plan. Use the best structured active-project evidence available: executed contract schedule, schedule of allowances, progress claim schedule, payment claim schedule of values, tender return, accepted quote, or variation roll-up.

Where a progress claim contains trade/work-package rows with contract values, those rows are construction cost evidence. Use the latest reliable claim schedule as the working construction breakdown, reconcile it to the revised contract sum, and carry variation rows separately or clearly identify them as embedded in the revised sum. If the claim schedule and variation forms conflict, keep the trade breakdown visible and record the conflict; do not collapse the construction section to one contract total merely to avoid the reconciliation problem.

For commercial projects with a quantity surveyor, an AIQS elemental cost plan (substructure / superstructure / external envelope / internal finishes / fittings / services / external works / preliminaries) may be a contractual requirement. SiteWise's `small-commercial-guide.md` archetype seed addresses this graceful degradation. For all four residential archetypes (new-dwelling, renovation, multi-dwelling, ancillary), the HIA Schedule of Allowances is the default.

**Reference:** HIA Lump Sum NSW New Homes contract (current edition); HIA Renovations; HIA Cost Plus.
**Applies to:** archetypes new-dwelling, renovation, multi-dwelling (where each dwelling is HIA-procured), ancillary.

**Common pitfalls:**
- Using an AIQS elemental breakdown on an HIA lump-sum contract — the owner cannot read the cost plan against the contract claim schedule, and PC reconciliation becomes opaque.
- Folding PC sums and owner-supplied items into trade lines rather than itemising them — the contract's PC adjustment mechanism then has nowhere to attach.
- Omitting contingency as a line — leaves the owner with no buffer and the builder no way to flag latent risk without a variation.

## 2. Total project cost vs construction cost

The cost plan must distinguish total project cost from construction cost. Owners frequently treat the construction-cost figure as the total commitment and are surprised at handover by the additional spend.

**Construction cost** — the contracted amount payable to the builder under the HIA / MBA / AS construction contract. Includes preliminaries, trades, PC sums (as allowances), owner-supplied allowances (where contracted that way), contingency held within the contract, and the builder's margin (embedded or separate).

**Total project cost** — construction cost plus:
- consultant fees (architect, structural engineer, hydraulic, BASIX assessor, certifier, surveyor, geotechnical, landscape — where engaged);
- authority charges (DA fees, CC fees, BASIX certificate fee, Sydney Water charges or state equivalent, OSD certification, BPA where applicable, long service levy);
- statutory insurance and warranty premiums (HBCF / DBI premium where the builder passes through; CWI premium where the principal places the cover; PI premium where applicable);
- utility connection charges (electricity, water, sewer, gas, NBN, telecommunications);
- owner-supplied items procured outside the contract;
- finance costs during construction (where the owner has a construction loan);
- contingency held outside the contract by the owner (typical when owner change appetite is high);
- legal fees, conveyancing where applicable, land or pre-purchase costs (project-level);
- FF&E (furniture, fittings, equipment), moving costs, and post-PC fitout.

For an architect-PM (`user_role: architect-pm`), making the total project cost visible to the owner is part of the duty of care. For a builder (`user_role: builder`), the construction-cost number is what the builder is responsible for, but the builder should be aware which owner-side commitments depend on the construction programme. For an owner-builder (`user_role: owner-builder`), there is no distinction in practice — the owner-builder is responsible for everything.

Per `../00-doctrine/doctrine.md §evidence-discipline`, every cost figure in a cost plan must be labelled **Fact** (supported by a quote, invoice, or signed contract), **Assumption** (no source yet — must be confirmed), **Judgement** (the project lead's estimate based on evidence and benchmark), or **Recommendation** (the suggested allowance for owner decision). Owners frequently misread Assumption / Judgement figures as Fact when not labelled.

## 3. PC sums (prime cost items)

A PC sum is a contractual allowance for an item the owner has not yet selected at the time of contract signing. The most common PC items in residential are:

- kitchen appliances (cooktop, oven, dishwasher, rangehood, fridge cavity — note appliances are often owner-supplied rather than PC; see §4);
- sanitary ware (toilets, basins, baths);
- tapware (kitchen tapware, basin and bath taps, shower mixers);
- tiles (floor, wall, splashback — typically priced by area + supply rate);
- floor coverings (timber, carpet, vinyl);
- lighting (fittings only, not the wiring — wiring is in the electrical trade);
- joinery (kitchen joinery, robes, vanities, custom built-ins);
- ironmongery / door furniture;
- letterbox, house number, mailbox where specified;
- door and window furniture upgrades.

**The mechanism under HIA contracts:**

1. The contract Particulars or annexure lists each PC item with an **allowance** (a $ figure the builder has priced into the contract sum, typically supply-only, sometimes supply-and-install).
2. The owner selects the actual item. The owner has a contractual obligation to select within a programme window — failure to select can be a variation reason for time.
3. When the actual cost is known (typically by quote from the builder's nominated supplier or by an owner-procured invoice), the PC is **reconciled**: actual cost vs allowance.
4. The difference is a contractual adjustment: actual > allowance flows up as additional cost to the owner (with the builder's margin applied per the contract — typically the contract specifies whether margin applies to the increment or to the actual cost in full); actual < allowance flows down as a credit (margin treatment varies — read the contract).
5. The reconciliation is recorded in a **PC reconciliation register** (typically the variation register's adjacent columns or a discrete PC schedule). The reconciliation closes at PC.

**Common pitfalls:**
- The owner treats the PC allowance as the budget for the item rather than a placeholder. When the owner then chooses an $8,000 cooktop against a $1,500 PC, the additional $6,500 + margin lands as a contractual obligation, not a surprise — but it is invariably presented as a surprise.
- The builder does not reconcile PC items as selections are made — the budget shifts under the cost plan without a corresponding variation register entry, and the cost plan version goes stale.
- "Supply only" vs "supply and install" is not clearly stated in the PC line. The installation cost ambiguity becomes a dispute at fixing stage.
- PC items selected from an owner-supplied source (the owner brings their own tapware): this should usually be reclassified as **owner-supplied** (see §4), not retained as a PC. The two mechanisms are different — running a PC against an owner-supplied actual confuses everyone.

**Labelling discipline:** every PC line in the cost plan carries a status: `allowance` (not yet selected), `selection-pending-quote`, `selected-priced` (the actual is known and reconciliation is calculable), `reconciled` (the variation register entry is open), or `closed` (the contract adjustment has been signed).

**Reference:** HIA Lump Sum / HIA Cost Plus / HIA Renovations contract PC clauses; the contract's executed Schedule of Allowances or PC schedule is the source of truth for a given project.

## 4. Owner-supplied items and allowances

Owner-supplied items are distinct from PC sums. An **owner-supplied** item is one the owner procures and supplies directly — the builder does not include it in the contract sum and may charge a separate handling or installation fee where the contract permits. PC items by contrast are included in the contract sum (as allowances) and are procured by the builder (or by the owner with the builder's involvement, depending on the contract).

The two mechanisms must not be conflated:

| Aspect | PC sum | Owner-supplied |
|---|---|---|
| In contract sum? | Yes (as an allowance) | No (excluded) |
| Procurement | Builder (often) or owner via builder | Owner directly |
| Reconciliation | Actual vs allowance, with margin treatment per contract | Not applicable — no contract sum impact, but installation cost may be a separate item |
| Risk of cost overrun | Owner bears the increment over allowance (plus margin) | Owner bears entire cost outside contract |
| Programme risk | Builder selects within programme; delay on selection is owner's risk | Owner must deliver on programme; late delivery is owner's risk |
| Warranty | Builder warrants installation; supplier warrants the item | Owner warrants the item; builder warrants installation only |
| Insurance | Covered under CWI (builder-procured) | Owner must confirm CWI extension or arrange own cover |
| Defects | Builder's responsibility for installation; supplier's for product | Owner's responsibility for product defects |

**Common owner-supplied scope in residential:**
- whitegoods (fridge, freezer, washing machine, dryer) — usually owner-supplied;
- light fittings (where the owner has bought from a specialist supplier);
- joinery hardware (handles, pulls);
- furniture being built in (e.g. a vintage cabinet inserted into a niche);
- decorative tiles, splashback materials sourced overseas;
- pizza ovens, fireplaces, BBQs — items at the edge of "building" vs "furniture".

**Owner-supplied allowances** appear as a separate schedule in the cost plan, **below** the contract sum total. The schedule lists each item with:
- item description;
- supplier (where committed) or status `to-source`;
- expected delivery date (programme-critical for fixing stage);
- expected cost (for the owner's total-project-cost view);
- installation cost (in contract if builder is installing; separate if owner is sourcing the trade).

The agent should propose an **owner-supplied items register** (per `register-row-draft.md` standard register `Owner-supplied items register`, ID convention `OS-<seq>`) at commissioning. The register tracks status: `committed`, `ordered`, `delivered`, `installed`, `late`. Late delivery is one of the most common programme risks in residential — flag it under `../00-doctrine/doctrine.md §escalation-triggers` when delivery dates threaten the fixing-stage programme.

**Common pitfalls:**
- The owner agrees to supply an item, then expects the builder to chase it through procurement. The role boundary is unclear and the item is late.
- Insurance gap: the owner-supplied item is stored on site before installation; CWI does not extend to owner-supplied goods unless explicitly endorsed. Theft or damage falls on the owner without notice.
- Owner-supplied items not in the register at all — they live in email threads and surface as scope arguments at PC.

## 5. Contingency — the 5–10% band

Residential contingency sits in a different band from commercial construction contingency. Where commercial new-build construction contingency is typically 3–5% of contract sum at construction phase, residential contingency at the same stage is typically 5–10%.

The reasons residential contingency is higher:

- **owner change appetite** is intrinsic to residential — the owner is making personal-taste decisions throughout construction, and selections shift in ways that are not material in commercial fit-out;
- **PC reconciliation** drift — the gap between PC allowances and actual selections almost always lands above allowance (owners select up, not down);
- **owner-supplied items** late delivery cascades into builder standing time charges;
- **scope creep** through informal site-meeting agreement is harder to discipline in residential than in commercial — the architect (if present) is usually not the Superintendent, and the owner is on site weekly;
- **latent conditions** in renovations — the wall opens up and reveals something not in the dilapidation report;
- **BASIX commitment chase** — late discovery that a glazing or HW system upgrade is required to meet certificate commitments.

**Band guidance (cross-reference issue-03 brief's acceptance criterion of 5–10%):**

| Project profile | Contingency | Basis |
|---|---|---|
| Well-documented new build, owner-low-change-appetite, no latent risk (e.g. a project home on a benign site) | 5% | Tight specification, repeatable build pattern, low owner-side variation pressure. |
| Custom new build, NSW Class 1a, well-documented, M-class site | 5–7% | Custom always carries more PC reconciliation risk than project. |
| Custom new build with H1 / H2 / E / P slab class, or BAL ≥ 19, or significant cut/fill | 7–10% | Site risk priced in. |
| Renovation with full dilapidation report and structural intervention scope | 8–10% | Latent conditions live here. |
| Renovation, urban infill, neighbour-property dilapidation risk, tight site access | 10% | Tight-site and neighbour management overhead is material. |
| Multi-dwelling residential (Class 2 or repeated Class 1a) | 6–9% | Repeat efficiency offsets some risk, party-wall and metering coordination adds back. |
| Ancillary (granny flat, CDC pathway) on existing residential lot | 5–7% | Constrained scope, well-trodden pathway. |
| Heritage or character residential intervention | 10%+ | Latent conditions and authority-condition rework dominate. Treat as a renovation+ band. |

The contingency line must be declared with its band and basis in the cost plan. Reciting "10%" without basis is a §evidence-discipline failure: contingency is a **Judgement**, and the basis must be stated.

For `archetype: multi-dwelling`, the cost plan must make the shared-vs-per-dwelling split visible. At minimum, test whether classification, party-wall / fire and acoustic treatment, separate metering and service upgrades, authority / infrastructure contributions, shared civil works, staged preliminaries, and OC / subdivision / strata pathway costs have a line, allowance, or explicit exclusion. Repeated dwellings create trade efficiency, but they also multiply design and services coordination errors.

**Drawdown discipline:**

- Contingency is **not available scope money**. Owner-initiated scope changes are variations, not contingency uses. Variations have their own register entry, owner sign-off, and pricing path (see §6).
- Contingency is for genuinely unforeseen costs: latent conditions, BASIX commitment recovery, neighbour-property remedy where the dilapidation report did not foresee it, PC reconciliation drift the cost plan held against contingency, and similar.
- Track **drawdown rate against percent complete**. If contingency is 40% consumed at 25% complete, that is a flag — escalate per `../00-doctrine/doctrine.md §escalation-triggers`.
- Release unused contingency in the cost report at PC, not before. Releasing contingency mid-project — even when the project looks clean — gives the owner false comfort and removes the reserve for the most common claim period (fixing stage and PC walk).

**Reference:** HIA cost-management practice; AIQS Cost Management Practice Guide (residential application).

**Common pitfalls:**
- Treating contingency as a slush fund for owner-initiated scope. The owner sees it consumed and assumes the build is going badly.
- Setting contingency at the lower band on a renovation with latent risk — the cost report goes red at first wall-opening.
- Not tracking drawdown rate — contingency falls off a cliff at fixing stage with no early warning.

## 6. Variations under HIA Schedule of Variations

In residential construction, variations are administered through the HIA Schedule of Variations form (or the equivalent stationery in MBA / NSW Fair Trading prescribed / AS 4000-4902 contracts). The discipline is the same across contract families:

1. **No work without written direction.** The variation form is issued and signed *before* the work begins. Verbal directions on site are not variations.
2. **Cost + time + scope** assessed in the variation form. Cost is the dollar adjustment (plus builder's margin per the contract). Time is the EOT impact in calendar days. Scope is what is included and what is not, and which trades are affected.
3. **Owner sign-off** is contractual. The owner signs the variation form. For owner-builder projects, the owner-builder signs against themselves (the discipline is for the project record, not external sign-off).
4. **Variation register entry** opens at proposal (`V-<seq>`, status `proposed`), moves through `priced` and `owner-signed`, lands at `completed`. Per `register-row-draft.md` standard register convention.
5. **Cost-plan update.** The cost plan's variation total runs alongside the contract sum baseline. A cost plan that does not reconcile to the variation register's running total has lost its audit trail.

The **mechanism difference** vs AS 4000/4902 commercial:
- No Superintendent in most residential contracts; the role is split (owner makes the call, builder issues the form, architect-PM where present advises). Get this right at commissioning.
- HIA Schedule of Variations is the contract's named form; the standard form has the price breakdown and time impact fields built in.
- Time impact is regularly underestimated in residential variations because the variation often touches trades that are already scheduled — the cascade through following trades is the time cost, not the variation work itself. The variation form must include this cascade in the time impact, not just the direct duration.

The **assessment** of variations against the contract sits in slice 06 (`variation-management-system`). This seed covers the **principles**: discipline at proposal, register entry, cost-plan reconciliation, time impact realism, owner sign-off pathway per role.

**Common pitfalls:**
- Site agreements not formalised: the builder does the work because the owner asked verbally on a Saturday site visit, then has no contractual basis to charge.
- Time impact captured only as direct duration: the variation register shows "2 days" when the trade cascade gives "10 days" of programme slip.
- Variation register and cost plan kept by different people in different files — they diverge, and at PC neither matches the actual.
- "It's just a small variation" — sub-$500 variations not formalised. Cumulatively these become a significant unpriced amount and a dispute trigger.

## 7. Progress claim assessment against HIA stage-payment schedule

The HIA Lump Sum stage-payment schedule for a new home is typically (subject to the executed contract's particulars):

- **Deposit** — up to the statutory cap (5% NSW; varies by state; check NSW Home Building Act for the current cap). Released at contract signing.
- **Base stage** — typically the slab pour for slab-on-ground construction (or the bearer/joist completion for footings-and-suspended-floor construction). Typical 10–15% of contract sum.
- **Frame stage** — frame complete and bracing fixed, internal door frames in (or framing trade complete on slab-on-ground). Typical 15–20%.
- **Lockup stage** — external cladding, windows, external doors fitted and lockable, roof on. Typical 20–25%.
- **Fixing stage** — internal linings, internal doors, skirtings and architraves, kitchen and bathroom carcasses, cabinetry, tiling. Typical 25–30%.
- **Completion stage** — final fixings, painting, commissioning, PC walk readiness. Typical 10–15%.

Specific percentages vary — the executed contract is the source of truth for a given project.

**Assessment discipline (cross-reference slice 06's `progress-claim-assessment-system`):**

1. **Physical stage achieved?** The claim is for stage completion. The stage definition in the contract is the test, not a percentage estimate. Walk the site and verify against the contract definition. Photos to file (per `07-construction/13-photos/`).
2. **Trade evidence in place?** For slab: concrete conformance test (CFT), reinforcement inspection record, slab inspection by certifier. For frame: structural inspection. For lockup: window installation, roofing, external cladding. For fixing: trade sign-offs. For completion: PC walk and BASIX final.
3. **Prior claims and variations.** Cumulative claimed amount + this claim ≤ contract sum + signed variations. Variations not yet signed do not count.
4. **Statutory timing.** The contract specifies the claim payment window (typically 5–10 business days for HIA residential). NSW Security of Payment Act applies where the contract triggers SOP.
5. **Retention.** Residential HIA contracts often do **not** carry retention — the stage-payment structure substitutes. Check the executed contract.
6. **Defects withholding.** Defects identified at PC stage are typically withheld against the completion-stage claim. Quantum is the rectification cost estimate, not punitive.

If the claim is not a simple HIA stage claim and instead includes a trade/work-package table or schedule of values, that table is also cost-plan evidence. A claim assessment should be able to read across from the cost plan to the claim schedule. If no cost plan exists yet, draft the cost plan from the claim schedule, contract sum, signed variations, and project budget evidence before assessing whether the claim is reasonable.

The **principles** sit in this seed. The **system** is slice 06. The role overlay says **who** does the assessment:

- `user_role: builder` issues the claim;
- `user_role: architect-pm` typically assesses on behalf of the owner;
- `user_role: owner-builder` issues claims to subcontractors and assesses them as the head — does not issue head-contractor claims to themselves;
- `user_role: d-and-c` issues head claims and assesses subcontractor claims.

**Common pitfalls:**
- Claim issued before stage physically achieved — particularly the frame and lockup stages. Builder claims at "frame complete bar one window" — that is not lockup.
- Owner pays the claim because the percentage looks right against the schedule, without checking physical completion. The contract permits withholding; the discipline is to use it where evidence is incomplete.
- Variations rolled into stage claims without separate identification — the contract sum and the variation total are not separately visible.
- BASIX final certificate or OC missing at completion-stage claim — the completion stage cannot be claimed until these are in hand if the contract conditions claim on them.

## 8. GST in residential cost reporting

The GST convention in residential is different from commercial. Default residential cost plans are presented **GST-inclusive**.

The reason: most residential owners are owner-occupiers, not GST-registered entities. The owner cannot recover GST on construction costs through a BAS. GST is a real cost of $0.10 on every dollar. Presenting the cost plan GST-exclusive misleads the owner about their actual financial commitment by exactly the GST amount.

**Exceptions where GST-exclusive is appropriate:**
- The owner is a GST-registered entity (e.g. an investor running the property as a rental, or a developer building to sell), and GST is recoverable. In this case the cost plan should still **show both** the GST-exclusive figure and the GST amount to make the cashflow timing visible (the owner pays GST upfront and recovers it on BAS — there is a cash gap).
- An architect-PM working for an investor / developer owner — present GST-exclusive with GST shown separately.
- A multi-dwelling project where the dwellings are being sold (margin scheme may apply to the land component — get advice).

**The cost plan must state its GST basis explicitly in the frontmatter or in the cost-plan summary section.** Mixing GST-inclusive and GST-exclusive figures in the same cost plan is a §evidence-discipline failure that misleads readers by 10% — flag and rebase.

**Cashflow note:** even where the owner can recover GST, the cashflow timing matters. The owner pays GST on each progress claim and recovers it on the next quarterly BAS (or monthly for large taxpayers). For a residential investor, this is typically a 1–3 month float. Surface it.

**Reference:** A New Tax System (Goods and Services Tax) Act 1999; ATO residential construction guidance.

## 9. Role-divergent cost responsibilities

Cost-management responsibilities split across the four user roles. The seed below is the abstract project-lead view; the role overlay seeds are the source of truth for who does what.

| Role | Issues claims | Assesses claims | Pays claims | Owns cost plan | Owns variation register | Holds contingency |
|---|---|---|---|---|---|---|
| `owner-builder` | To subcontractors only | Own assessment of subcontractors | Pays subcontractors directly | Self | Self | Self |
| `architect-pm` | Does not issue | Assesses builder's claims on owner's behalf | Advises owner; owner pays | Architect-PM drafts; owner approves | Architect-PM maintains | Owner; architect-PM advises drawdown |
| `builder` | Issues head claims to owner; assesses subcontractor claims | Builder's internal | Owner pays to builder; builder pays subcontractors | Builder drafts; owner reviews | Builder maintains; owner signs each entry | Builder's contract contingency; owner may hold separate |
| `d-and-c` | As builder, plus design-fee claims if separate | As builder | Owner pays | D&C drafts | D&C maintains | D&C; owner may hold separate |

The role overlay seed loaded for the active project (per `../02-skills/atomic/seed-targeted-read.md`'s mandatory Tier 3 load) is the operational truth for these splits. This seed names the dimensions; the role overlay names the obligations.

For `user_role: d-and-c`, keep the builder construction sum, design fee, consultant fees, PI / consultant PI allowance, certifier submission allowance, authority / infrastructure contributions, party-wall / fire / acoustic allowances, separate metering / service upgrade costs, staging preliminaries, and per-dwelling vs shared infrastructure split visible. A design-fee claim is assessed against the design deliverables register, design programme, and certifier submission status where relevant; construction progress alone does not prove design-fee entitlement.

**Escalation routing** (per `../00-doctrine/doctrine.md §escalation-triggers`):
- **Owner-builder** — cost escalations go to the self-flag log in `08-meetings-reporting/`.
- **Architect-PM** — cost escalations route to the owner via a `§owner-communication`-shaped summary in `08-meetings-reporting/owner-update*`.
- **Builder** — cost escalations route to the owner per contract; high-value or contractual triggers route via `07-construction/08-rfi-notices/` for the written record.
- **D&C** — as builder, plus design-side cost issues route to the owner where PPR, cost, or programme choices are required; to the certifier where compliance is affected; and to the responsible consultant where scope or design advice is live.

## 10. State callouts (graceful degradation per AGENTS.md §8)

NSW is the deep default in this seed. Non-NSW callouts:

**VIC** — *Slice 14 will deepen this.* HIA contracts are used widely; the prescribed state contract is different. Domestic Building Insurance (DBI) replaces NSW HBCF. CoINVEST replaces NSW Long Service Corporation. The Security of Payment regime is BCISP Act 2002 (VIC). BASIX is not the energy instrument — NatHERS 6-star (or 7-star post-2022 amendment depending on adoption date) applies via the Victorian Building Authority. Building Act 1993 (VIC) carries different defect liability and statutory warranty provisions. **Treat as Assumption** in any cost plan for a VIC project — confirm against current VIC instruments before relying on residential conventions that differ from NSW.

**QLD** — *Callout only; deep coverage deferred.* QBCC replaces NSW Fair Trading and HBCF (Home Warranty Insurance is mandatory under QBCC). The Security of Payment regime is the Building Industry Fairness (Security of Payment) Act 2017 (QLD), which has materially different payment claim mechanics and statutory cooling-off. BASIX does not apply — QDC Part MP 4.1 / NCC Section J. Treat as Assumption.

**SA, WA, TAS, NT, ACT** — *Callout only; deep coverage deferred.* Each state has its own statutory warranty regime (e.g. WA BSA, TAS Building Act, NT Building Practitioners Board). Energy compliance varies by state adoption of NCC. Treat as Assumption and flag for project lead supplementation.

Where a non-NSW state has no callout for the task at hand, the skill (calling this seed) **flags the gap** rather than silently extending NSW guidance — per `../AGENTS.md §8` and `../00-doctrine/doctrine.md §state-handling`.

## 11. Cost reporting cadence and structure

Residential cost reports are typically monthly during construction, aligned to the HIA stage claim cycle. The report's job is to keep the owner's cost picture current and to surface drift early.

A residential cost report carries:

- **header**: project, period, author, status (draft until reviewed);
- **baseline**: contract sum, signed variations to date, current contract value (sum + variations);
- **claimed-to-date**: cumulative across stage claims (with each claim's date, amount, assessment status, payment status);
- **paid-to-date**: cumulative against claimed (gap is unpaid or disputed);
- **forecast to complete**: forecast cost remaining + any anticipated variations;
- **contingency drawdown**: opening contingency, used this period, used to date, remaining, drawdown rate vs % complete;
- **PC reconciliation**: PC line items with allowance vs actual where known, running net reconciliation total;
- **owner-supplied items**: status of each item (committed / ordered / delivered / installed / late);
- **RAG status**: green / amber / red against approved budget (see thresholds below);
- **narrative**: why anything moved; what is expected next period;
- **decisions required from owner**: per `§owner-communication` if the report is owner-facing.

**RAG thresholds (residential default):**
- **Green** — forecast total ≤ contract sum + signed variations + 30% of remaining contingency.
- **Amber** — forecast total within 5% above contract sum + signed variations, or contingency drawdown rate is materially ahead of % complete.
- **Red** — forecast total > 5% above contract sum + signed variations, or contingency is consumed and remaining work carries identified risk.

**Voice register** (per `../00-doctrine/doctrine.md §voice-and-style`): cost reports drafted into `01-cost/` are contractual register (formal Australian English, clause-cited where contractual mechanism is referenced, ISO short-form dates, AUD with $ symbol). Owner-facing monthly cost summaries drafted into `08-meetings-reporting/owner-update*` are stakeholder register (plain English, leads with "what this means for you" / "what we need from you" per `../00-doctrine/doctrine.md §owner-communication`).

The two are different documents. The contractual cost report sits in `01-cost/`. The owner-facing summary derived from it sits in `08-meetings-reporting/`. Do not collapse them — the owner needs the plain-language version and the project record needs the contractual version.

## 12. Cashflow and the residential S-curve

Residential cashflow follows the stage-payment schedule's curve, not the S-curve of commercial monthly measured progress. For a typical NSW Class 1a HIA Lump Sum project:

- **Month 0** (deposit + base): ~10–15% of contract sum;
- **Months 1–3** (frame + lockup): ~35–45% cumulative;
- **Months 3–6** (fixing): ~70–75% cumulative;
- **Months 6–9** (completion): ~100% cumulative.

Actual timing depends heavily on the executed programme. The cashflow forecast must mirror the executed contract's claim schedule, not a generalised S-curve.

**Cashflow risk surfacing:**
- Owner construction-loan drawdown windows often require certifier or QS sign-off at each draw. The cashflow forecast must align to draw timing.
- GST timing for investor owners (see §8) introduces a 1–3 month cash gap between payment and BAS recovery.
- Retention (if applicable — see §7) timing affects the back-end cashflow.
- Final claim release timing is contingent on PC walk close-out — model both an optimistic and pessimistic close-out date.

## 13. What this seed is and is not

This seed is **principles**. It is loaded by `seed-targeted-read` when the task signal is cost / budget / contingency / claim / variation pricing. It is not a set of skill steps and it does not draft.

For the **workflow** (seeding → sweeping → drafting → workbook update → verification), call `../02-skills/systems/cost-plan-system.md` — the residential cost-plan system skill. The system skill loads this seed plus the archetype seed plus the role overlay, and orchestrates the atomic skills.

For **register row format** for cost / variation / PC reconciliation / owner-supplied rows, call `../02-skills/atomic/register-row-draft.md`.

For **markdown draft wrapping** of any cost-plan narrative output, call `../02-skills/atomic/markdown-draft-for-review.md`. The voice register for `01-cost/cost-plan*`, `01-cost/cost-report*`, `01-cost/*claim-assessment*`, `01-cost/*variation-pricing*` is contractual.

For **workbook edits** to the project's cost workbook (e.g. a Master Project Finance.xlsx), call `../02-skills/atomic/excel-safe-edit.md` driven by an approved markdown source, followed by `../02-skills/atomic/excel-verify.md`. The atomics' hard rules (backup first, preserve named ranges and data validations, never `#REF!`, never overwrite the only copy, never commit assumptions directly) are non-negotiable.

This seed does not cover:
- **detailed elemental cost rates** (e.g. $/m² rates for slabs, framing, roofing) — those belong in a future trade-cost reference (not in scope for slice 03);
- **specific contract clause references** for HIA / MBA / NSW Fair Trading / AS — that is `contract-administration-guide.md`'s job;
- **progress claim assessment workflow** — that is slice 06's `progress-claim-assessment-system`;
- **variation pricing workflow** — that is slice 06's `variation-management-system`;
- **handover and final account** — that is slice 13's `handover-pc-system`.

## See also

- `../AGENTS.md §1` — authority stack (project evidence beats this seed)
- `../AGENTS.md §3` — seed loading rules (this seed is a Tier-cross-cutting topic seed)
- `../AGENTS.md §5` — output discipline (frontmatter on every cost-plan deliverable)
- `../AGENTS.md §6` — voice register (`01-cost/` is contractual per the table in `markdown-draft-for-review.md`)
- `../AGENTS.md §8` — state handling (non-NSW callouts above are graceful-degradation placeholders)
- `../00-doctrine/doctrine.md §evidence-discipline` — Fact / Assumption / Judgement / Recommendation labelling required on every cost figure
- `../00-doctrine/doctrine.md §seed-consultation-discipline` — why this seed must be loaded by `seed-targeted-read`, not assumed
- `../00-doctrine/doctrine.md §register-discipline` — cost / variation / PC reconciliation register schema
- `../00-doctrine/doctrine.md §voice-and-style` — two-register split (contractual for `01-cost/` content; stakeholder for owner-facing derivatives)
- `../00-doctrine/doctrine.md §owner-communication` — format for the owner-facing cost summary derived from the cost report
- `../00-doctrine/doctrine.md §escalation-triggers` — cost-related triggers (budget movement, contingency drawdown, BASIX cost recovery, PC reconciliation drift)
- `role-builder.md`, `role-architect-pm.md`, `role-owner-builder.md`, `role-d-and-c.md` — role-divergent obligations referenced in §9
- `contract-administration-guide.md` — clause-citation discipline and contract-family mechanics
- `setup-and-commission-guide.md` — opens the cost register and the owner-supplied items register at commissioning
- `../02-skills/systems/cost-plan-system.md` — primary caller; the workflow that loads this seed
- `../02-skills/atomic/seed-targeted-read.md` — loads this seed
- `../02-skills/atomic/evidence-sweep.md` — finds project cost evidence before drafting
- `../02-skills/atomic/markdown-draft-for-review.md` — wraps cost-plan narrative drafts
- `../02-skills/atomic/register-row-draft.md` — drafts cost / variation / PC / owner-supplied register rows
- `../02-skills/atomic/excel-safe-edit.md`, `../02-skills/atomic/excel-verify.md` — workbook update path
