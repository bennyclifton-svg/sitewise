---
seed_tier: cross-cutting
seed_type: compliance
loaded_by: task subject (NCC, BCA, building code, Class 1, Class 10, DTS, performance solution, deemed-to-satisfy, building classification)
applies_to_roles: [owner-builder, architect-pm, builder, d-and-c]
applies_to_archetypes: [new-dwelling, renovation, multi-dwelling, ancillary, small-commercial]
state_default: NSW
doctrine_anchors: [§evidence-discipline, §seed-consultation-discipline, §escalation-triggers]
agents_anchors: [§1, §2, §8]
---

# NCC reference guide — Class 1 and Class 10

This seed gives SiteWise its NCC posture for residential practice. Load it when the task signal is NCC classification, building code compliance, deemed-to-satisfy pathway, performance solution, Class 1a, Class 1b, Class 10a, or Class 10b.

Authority stack reminder (per `../AGENTS.md §1`): the project's CC, BPA reports, DA consent conditions, and certifier correspondence are the source of truth. Where evidence is missing, label the point as Assumption per `../00-doctrine/doctrine.md §evidence-discipline`. The NCC is a complex document; this seed provides posture and orientation, not a substitute for the certifier's advice.

## 1. What the NCC is

The **National Construction Code (NCC)** is Australia's primary performance-based building regulation. It is published by the Australian Building Codes Board (ABCB) and adopted by each state and territory via its own legislation. In NSW, adoption is through the *Environmental Planning and Assessment Regulation 2021*. The version current in NSW practice as of mid-2025 is **NCC 2022**.

The NCC comprises:
- **Volume One** — Class 2–9 buildings (apartments, commercial, industrial).
- **Volume Two** — Class 1 and Class 10 buildings (**Housing Provisions**) — the relevant volume for SiteWise's residential scope.
- **Volume Three** — Plumbing and Drainage (adopted separately in NSW through the *Plumbing and Drainage Act 2011*).

SiteWise's scope is **NCC Volume Two**. Volume One (Class 2–9) applies to multi-unit apartment buildings and commercial work; if a project involves a Class 2–9 building as the primary scope, it falls outside the SiteWise residential harness — flag this and refer to the commercial harness.

## 2. Building classification — Class 1 and Class 10

### Class 1a — Detached dwelling

A **Class 1a** building is a single dwelling — detached house, townhouse (if separated from adjacent dwellings by a wall to the top of the roof), or terrace — occupied by one household. This is the dominant NCC class for SiteWise's `new-dwelling` and `renovation` archetypes.

Key Class 1a points:
- Three storeys maximum in most applications of NCC Volume Two DTS provisions.
- Kitchen serves the household (distinguishes from Class 3 residential accommodation).
- Structural design governed by AS 2870 (footings/slabs), AS 1684 (timber framing), AS 4055 (wind), AS 3959 (bushfire). Load `as-standards-reference.md` for detail.
- Energy efficiency: in NSW, **BASIX** applies — not NCC Section J. Load `sustainability-energy-guide.md` for BASIX detail.
- Plumbing: AS 3500 series under NCC Volume Three / Plumbing and Drainage Act.

### Class 1b — Guest house or bed and breakfast

A **Class 1b** building is a boarding house, guest house, or bed-and-breakfast with:
- not more than 12 residents (if not Class 3), or
- up to 300 m² floor area with not more than 12 guests.

Class 1b triggers additional fire safety and exit requirements not applicable to Class 1a. In SiteWise's residential scope, a homeowner converting part of a Class 1a to a B&B may trigger Class 1b reclassification — surface this if the project evidence shows short-term commercial accommodation.

### Class 10a — Non-habitable structure

**Class 10a** covers non-habitable structures associated with a Class 1 dwelling:
- private garages, carports, and sheds;
- decks, verandahs, and pergolas attached or detached;
- retaining walls (where subject to a construction certificate).

NCC Volume Two contains DTS provisions for Class 10a structures. However, many Class 10a structures are exempt development under the *State Environmental Planning Policy (Exempt and Complying Development Codes) 2008* — check the SEPP before assuming a CC is required. The exemption envelope has floor area, height, and setback limits; structures outside those limits need a CC (and must comply with NCC Volume Two).

Key Class 10a NCC points:
- Structural adequacy: Volume Two Part 3.0 applies.
- Bushfire construction (AS 3959): applies if the site is bushfire-prone and the structure is within the applicable proximity — even if the main dwelling is exempt.
- Plumbing: Class 10a structures are typically unserviced; any sanitary facilities trigger plumbing compliance.

### Class 10b — Swimming pool, fence, mast, antenna, retaining wall

**Class 10b** covers private swimming pools, fencing, masts, antennas, and retaining walls. In residential practice:
- Swimming pools: require a CC in NSW (and a complying pool barrier per *Swimming Pools Act 1992*). The pool barrier/fence is a separate obligation layered on top of NCC compliance.
- Fencing: largely governed by the *Dividing Fences Act 1991* in NSW; NCC compliance is limited. Fences used as pool barriers must meet AS 1926.1.
- Retaining walls: may be classified Class 10b or Class 10a depending on use; structural adequacy under Volume Two applies.

### Class 2–9 — Out of scope for SiteWise residential

Class 2–9 buildings (apartments, commercial, industrial, etc.) are governed by **NCC Volume One** — a substantially different compliance framework involving:
- Fire rating of elements, sprinkler systems, egress travel distances, passive fire compartmentalisation.
- Energy efficiency under NCC Section J (not BASIX).
- Structural design to different loadings and standards.
- Different BCA assessment pathways.

If a project's primary scope is a Class 2 building (apartment block) or any Class 3–9 use, **flag this immediately** — the SiteWise residential harness and its seeds are not calibrated for those classes. Route to the commercial harness or engage a specialist.

**Multi-residential note:** Two-storey townhouses or terraces on separate titles (or Torrens-titled strata) are typically Class 1a each. A purpose-built apartment block (single folio, multiple units) is Class 2. The distinction matters for NCC volume, fire compliance, and energy pathway. When evidence is ambiguous, flag the classification question to the certifier before proceeding.

## 3. Compliance pathways — DTS and Performance Solution

NCC Volume Two provides two pathways to compliance:

### Deemed-to-Satisfy (DTS)

The DTS pathway follows the prescriptive provisions in Volume Two exactly. If the building meets every DTS provision for its class, it complies. This is the dominant pathway for standard residential construction:
- Concrete and masonry per AS 3700 and Volume Two Part 3.3.
- Timber framing per AS 1684 (DTS provisions reference span tables).
- Glazing area and type per Volume Two Part 3.6 (and BASIX for energy).
- Waterproofing to Volume Two Part 3.8 (AS 3740 referenced for wet areas).

The certifier verifies DTS compliance at each inspection stage (slab, frame, waterproofing, completion). The project lead must ensure documentation matches the DTS specification — substitutions require re-verification.

### Performance Solution (PS)

A Performance Solution demonstrates compliance by showing the building meets the NCC's Performance Requirements through an alternative means. It is used when:
- the proposed design departs from DTS provisions (e.g. non-standard glazing, open-plan fire-egress arrangement, unusual structural system);
- the designer/owner wants to achieve an outcome the DTS provisions would otherwise prohibit;
- a bushfire BAL-FZ site requires demonstrating that AS 3959 BAL-FZ requirements are met through tested and assessed systems (a common fire engineering PS pathway).

A Performance Solution for a residential building typically requires:
- a Verification Method (e.g. structural engineering calculation, fire engineering report, energy modelling);
- a registered practitioner certifying the solution;
- the certifier's acceptance and notation on the CC.

**Agent posture:** surface the possibility of a Performance Solution pathway when the project evidence shows non-standard design, BAL-FZ, or unusual site constraints. Do not attempt to draft the PS — route to the relevant specialist.

## 4. Key NCC Volume Two provisions — Class 1a overview

| Part | Topic | Residential significance |
|---|---|---|
| Part 2.1 | Structural reliability | Structural adequacy — engineer of record triggers |
| Part 2.2 | Fire safety | Non-combustible construction, Class 1a limited requirements vs Class 1b/2 |
| Part 2.3 | Damp and weatherproofing | Subfloor ventilation, wall weatherproofing, roof drainage |
| Part 2.4 | Safe movement and access | Stairs, handrails, balustrades — riser/going ratios, height requirements |
| Part 2.6 | Energy efficiency | Redirects to BASIX in NSW; NatHERS/Section J in other states |
| Part 3.1 | Site preparation | Termite management, fill, drainage |
| Part 3.2 | Footings and slabs | AS 2870 slab classifications referenced |
| Part 3.3 | Masonry | AS 3700, AS 4773 |
| Part 3.4 | Framing | AS 1684 (timber), AS 4100 (steel), AS 3600 (concrete) |
| Part 3.5 | Roof cladding and gutters | Sarking, metal roofing fixings, gutters and downpipes |
| Part 3.6 | Glazing | AS 1288 safety glass, impact areas |
| Part 3.8 | Wet areas | AS 3740 waterproofing referenced |
| Part 3.9 | Insulation | R-values by climate zone — subject to BASIX override in NSW |
| Part 3.12 | Energy efficiency | For Class 1 in non-BASIX states |

*Note:* Part 2.6 and Part 3.12 are the NCC energy efficiency provisions. In NSW, BASIX is the energy compliance instrument for Class 1 and Class 10. BASIX effectively replaces Parts 2.6 and 3.12 for those classes in NSW. Load `sustainability-energy-guide.md` for BASIX/NatHERS detail.

## 5. Class 10a overview — selected DTS provisions

- **Structural adequacy:** Volume Two Part 3.1 and AS 1684 (timber) apply. Engineer sign-off triggers at spans or loads beyond the DTS tables.
- **Wind resistance:** AS 4055 wind classification applies — a carport or pergola in a N3 wind zone needs fixing details matched to that classification.
- **Bushfire:** If the lot is bushfire-prone, AS 3959 applies to Class 10a structures within the applicable zone — even where the main dwelling is exempt development. BAL assessment carries across all structures on the lot.
- **Roof drainage:** Gutters and downpipes must comply with Volume Two Part 3.5 where fitted.
- **Energy efficiency:** No BASIX requirement for Class 10a. (Class 10a is non-habitable.)

## 6. NCC 2022 in NSW — adoption context

**NCC 2022** is the current edition in NSW. Key adoption points:
- Adopted via the *Environmental Planning and Assessment Regulation 2021*, effective 1 May 2023 (with a transition period ending 1 October 2023 for most applications).
- NCC 2022 introduced updated energy efficiency provisions (6-star NatHERS requirement nationally for Class 1); in NSW, BASIX satisfies the NCC energy provisions and the BASIX tool was updated to align.
- Subsequent NCC editions (NCC 2025 and beyond) will be adopted by amendment; confirm the current adopted edition for any project where compliance dates are in question.

**State callout — other states:** Other states may be on NCC 2019, NCC 2022, or a transitional version. If the project's `state:` declaration is non-NSW, flag: "Confirm the adopted NCC edition with the certifier — do not assume NCC 2022 applies."

## 7. The certifier's role

In NSW, building certifiers (or private certifiers appointed under the *Design and Building Practitioners Act 2020*) assess NCC compliance at key stages. The project lead's obligation is to:
- ensure documentation submitted for a CC is consistent with NCC Volume Two DTS provisions (or includes a Performance Solution where required);
- ensure no substitution of NCC-critical materials or systems without the certifier's confirmation that compliance is maintained;
- flag any post-CC change that may affect NCC compliance to the certifier before the work proceeds.

The agent must not opine on NCC compliance — that is the certifier's professional judgment. The agent's role is to surface potential compliance questions and route them to the certifier.

## Coverage depth

| Topic | Depth |
|---|---|
| Class 1a posture and scope | Deep |
| Class 10a/10b scope and triggers | Moderate |
| DTS pathway overview | Moderate |
| Performance Solution pathway | Shallow (posture only) |
| NCC Volume Two part-by-part detail | Shallow (signpost) |
| Class 2–9 | Minimal (signpost out of scope) |
| NCC 2022 adoption in NSW | Moderate |

## Low-confidence flags

- **NCC amendment currency:** NCC editions and state adoption dates change. Verify the current adopted edition and any building regulation amendments for any project where compliance timing is relevant.
- **Class 1b triggers:** The Class 1b threshold (12 residents, 300 m²) is a paraphrase; verify the exact current NCC wording before advising on reclassification.
- **BASIX–NCC interaction:** The BASIX/NCC energy provision interaction is stated based on the NSW position as at NCC 2022. Confirm with the certifier for any project where the energy compliance pathway is in doubt.
- **Performance Solution detail:** PS procedures, reporting requirements, and certifier acceptance criteria are not covered here — engage a fire engineer, structural engineer, or energy assessor as appropriate.
- **Class 10a bushfire:** AS 3959 applicability to Class 10a structures depends on the BAL rating and proximity rules. Confirm with the BAL assessor and certifier.

## See also

- `as-standards-reference.md` — AS 2870, AS 1684, AS 4055, AS 3959, AS 3500 detail (task-loaded)
- `sustainability-energy-guide.md` — BASIX/NatHERS, energy compliance pathways (task-loaded)
- `new-dwelling-guide.md` — new-dwelling lifecycle, CC/inspection stages
- `renovation-guide.md` — renovation NCC triggers, existing building compliance
- `../00-doctrine/doctrine.md §evidence-discipline` — labelling assumptions vs confirmed facts
- `../00-doctrine/doctrine.md §escalation-triggers` — when to route NCC questions to the certifier
- `../AGENTS.md §1` — authority stack; project evidence beats seed guidance
