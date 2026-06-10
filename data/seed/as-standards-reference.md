---
seed_tier: cross-cutting
seed_type: compliance
loaded_by: task subject (AS 2870, AS 1684, AS 4055, AS 3959, AS 3500, AS 1170, footing classification, slab, framing, wind class, bushfire BAL, plumbing standard)
applies_to_roles: [owner-builder, architect-pm, builder, d-and-c]
applies_to_archetypes: [new-dwelling, renovation, multi-dwelling, ancillary, small-commercial]
state_default: NSW
doctrine_anchors: [§evidence-discipline, §seed-consultation-discipline, §escalation-triggers]
agents_anchors: [§1, §2, §8]
---

# Australian Standards reference — residential

This seed gives SiteWise its posture on the key Australian Standards that govern residential structural, plumbing, and building fabric design. Load it when the task signal is slab classification, footing design, timber framing, wind loading, bushfire construction, plumbing, or load cases for a residential project.

Authority stack reminder (per `../AGENTS.md §1`): the structural engineer's report, soil report, BAL assessment, hydraulic engineer's certification, and CC documentation in the project evidence folder beat this seed. Where evidence is missing, label the point as Assumption per `../00-doctrine/doctrine.md §evidence-discipline`. Australian Standards are licensed documents; this seed provides orientation and project-lead posture, not a reproduction of standard text.

The agent's role with standards is to: surface the right question, identify which professional is responsible for the answer, and flag when the project evidence is silent on a matter that ought to be resolved. The agent must not attempt to substitute for an engineer's, certifier's, or licensed tradesperson's professional judgment.

## 1. AS 2870 — Residential slabs and footings

**Scope:** Design of slabs and footings for Class 1 and Class 10 buildings on reactive and non-reactive sites. The dominant structural standard for residential ground-supported construction in Australia.

### Site classification

AS 2870 classifies sites by soil reactivity — the degree to which the subsoil expands and contracts with moisture change. Classification drives slab and footing design; it is determined by a geotechnical engineer based on soil investigation.

| Class | Reactivity description | Typical design implication |
|---|---|---|
| A | Non-reactive (sandy, gravelly soils) | Standard slab design; low risk of movement |
| S | Slightly reactive | Minor surface movement possible; some additional reinforcement |
| M | Moderately reactive | Surface movement 20–40 mm; footing design intensifies |
| H1 | Highly reactive (shallow) | Surface movement 40–60 mm; engineer-specified footing |
| H2 | Highly reactive (deep) | Surface movement 40–60 mm, deeper influence depth; engineer-specified |
| E | Extremely reactive | Surface movement > 60 mm; site-specific engineering required |
| P | Problem site | Filled ground, soft soil, aggressive soil chemistry, or unstable conditions; site-specific engineering required |

**Project-lead implications:**
- A soil report and AS 2870 classification are project evidence gates — they must exist before slab design is finalised.
- H2, E, or P classification substantially increases footing cost. Flag immediately to the cost plan if the soil report returns one of these classifications.
- A P-class or E-class site may require a structural engineer of record for the slab/footing design (not just reference to the DTS tables).
- Sydney basin soils frequently return M, H1, or H2. An A or S classification in Sydney should be confirmed — it is not the default assumption.

**Common failure mode:** soil report ordered late (post-scheme or post-tender). H2 or E classification discovered after the budget was fixed; slab redesign moves the cost plan materially.

### Geotechnical report requirement

AS 2870 contemplates that a soil investigation is performed and results are provided to the designer. The standard includes a default presumptive classification procedure for simple sites, but a project lead should treat a proper geotechnical report as mandatory for any project where:
- the site has been filled, disturbed, or remediated;
- neighbouring buildings show cracking or movement;
- the planning authority or certifier requires it as a consent condition;
- the site is near a watercourse, has drainage issues, or shows evidence of expansive clay.

## 2. AS 1684 — Timber framing

**Scope:** Design and construction of timber-framed Class 1 and Class 10 buildings. The standard provides span tables, species and stress-grade requirements, fastener schedules, and notching/drilling rules.

### Key concepts for project leads

**Species and stress grade (MGP/F-grade):**
- Softwood framing is typically specified to MGP grades (MGP10, MGP12, MGP15). The higher the MGP number, the stiffer and stronger the timber.
- Hardwood framing uses F-grades (F7, F8, F14, F17, F27).
- The engineer or frame designer specifies the required grade; the project lead confirms the supplied timber matches the specification at delivery.

**Span tables:**
- AS 1684 includes prescriptive span tables for floor joists, bearers, rafters, ceiling joists, lintels, and studs. A standard residential frame can be sized from the tables by the designer without bespoke structural calculations — provided the loading and span conditions fall within the table limits.
- Beyond the table limits (long spans, heavy loads, irregular geometry), an engineer of record is required.

**Notching and drilling rules:**
- AS 1684 sets out strict limits on notching and drilling of structural timber members for services penetrations. Violations are a common inspection failure — notches and holes in the wrong zone or exceeding the permitted size weaken the member.
- The agent should flag notching/drilling issues as a frame inspection risk when the project has complex services routing through the frame.

**Inspection gate — frame inspection:**
- The certifier (or BPA) must inspect the completed frame before any lining or insulation is installed. This is a mandatory hold point.
- The frame inspection checks: straightness, connections, bracing, lintel bearing, notching/drilling, and that the frame matches the approved drawings.

**Cyclonic regions:**
- In cyclonic areas (C1–C4 per AS 4055), AS 1684 requires upgraded connections and fixings. This applies in Far North Queensland, parts of Northern Australia, and coastal WA. Flag as a graceful-degradation callout for NSW (non-cyclonic).

## 3. AS 4055 — Wind loads for housing

**Scope:** Determination of the design wind speed and wind classification for Class 1 and Class 10 buildings. Used by the certifier and building designer to assign a wind class that then drives structural fixing requirements.

### Wind classification system

AS 4055 produces a wind classification from **N1** (lowest, sheltered suburban) to **N6** (very high, exposed non-cyclonic) for non-cyclonic regions, and **C1** to **C4** for cyclonic regions.

| Classification | Non-cyclonic / Cyclonic | Typical location |
|---|---|---|
| N1 | Non-cyclonic | Sheltered suburban locations, low terrain |
| N2 | Non-cyclonic | Most suburban locations, moderate exposure |
| N3 | Non-cyclonic | Coastal, elevated, or exposed suburban |
| N4 | Non-cyclonic | Very exposed: cliff tops, hilltops, open farmland |
| N5–N6 | Non-cyclonic | Extreme exposure; uncommon in metro NSW |
| C1–C4 | Cyclonic | Northern Australia — different design regime entirely |

### How the classification is determined

The wind classification depends on:
- **Wind speed region** (A, B, C, or D in AS/NZS 1170.2, or the simplified AS 4055 region map) — region broadly reflects geographic location.
- **Terrain category** — open country, suburban, or sheltered, based on surrounding development within a fetch distance.
- **Topographic factor (shield factor)** — whether the site is on a hill, ridge, escarpment, or is shielded by surrounding buildings.

The certifier or designer assigns the wind classification and records it on the CC documentation. The structural frame, tie-downs, and roof fixings must be designed to suit the classification.

**Project-lead implications:**
- Wind class drives fixing specification — N3 requires more robust tie-downs and bracing than N2.
- Elevated, coastal, or ridgeline sites in NSW commonly attract N3 or N4. This affects cost (more fixings, stronger connections) and must be confirmed before procurement.
- Substituting structural fixings (hurricane ties, straps, nogs) to cheaper equivalents without checking the wind classification is a defect risk and certifier-inspection failure.

**Cyclonic regions (C1–C4):**
- Cyclonic wind classes require substantially upgraded construction — special fixings, connections, glazing, and roof sheeting. This is not a common SiteWise scenario (NSW is non-cyclonic), but flag explicitly if a project is in a cyclonic region.

## 4. AS 3959 — Construction in bushfire-prone areas

**Scope:** Construction requirements for buildings in bushfire-prone areas. The standard prescribes construction details for each BAL (Bushfire Attack Level) rating.

### BAL ratings

| BAL | Fire exposure level | Typical construction requirement |
|---|---|---|
| BAL-LOW | Very low | No specific construction requirements |
| BAL-12.5 | Low | Ember protection: screens to subfloor vents, roof voids; some glazing requirements |
| BAL-29 | Medium | Ember + radiant heat: more robust glazing, external walls, decking restrictions |
| BAL-40 | High | Significant radiant heat: non-combustible external cladding, toughened glazing, enclosed eaves |
| BAL-FZ | Flame zone | Direct flame impingement: most stringent — fire-rated systems, tested assemblies, specialist design required |

A BAL-FZ site almost always requires a Performance Solution or fire engineering report. The agent must flag BAL-FZ as a specialist-engagement trigger immediately.

### How BAL is assessed

BAL is determined by a BAL assessment (or bushfire assessment report) performed by a suitably qualified person (accredited bushfire consultant or certifier) based on:
- the site's proximity to classified bushfire-prone vegetation;
- the effective slope of the land;
- vegetation type and FDI (Fire Danger Index) for the planning authority's flame zone table.

**The BAL assessment is project evidence** — the project lead must obtain it at due diligence stage. Do not assume BAL-LOW for any site where bushfire-prone land is indicated on the planning certificates.

### AS 3959 and the new-dwelling lifecycle

BAL rating has cascading cost and procurement implications:
- Glazing type and framing — BAL-29+ requires specific glazing specification (U-value and impact resistance). BASIX window commits may need to be reconciled with BAL glazing requirements.
- Decking and subfloor cladding — BAL-29+ restricts or prohibits combustible timber decking.
- Roof cladding, eaves — BAL-40+ requires enclosed eaves and specific roof cladding.
- Reveal and external joinery — BAL-40+ requires non-combustible reveals.

For full detail on BAL construction requirements, load `new-dwelling-guide.md` (BAL section). AS 3959 construction requirements are noted there in the context of the new-dwelling lifecycle.

## 5. AS 3500 — Plumbing and drainage

**Scope:** The AS/NZS 3500 series covers all aspects of plumbing and drainage for residential buildings. It is referenced by NCC Volume Three and adopted by state plumbing legislation.

The AS 3500 series is divided into parts:

| Part | Coverage |
|---|---|
| AS/NZS 3500.1 | Cold water services |
| AS/NZS 3500.2 | Sanitary plumbing and drainage |
| AS/NZS 3500.3 | Stormwater drainage |
| AS/NZS 3500.4 | Hot water, heated water, and warm water services |
| AS/NZS 3500.5 | Domestic installations |

### Residential plumbing posture for project leads

- All plumbing work in NSW must be carried out by a **licensed plumber** (licensed under the *Home Building Act 1989*).
- Plumbing work is subject to council/authority inspection gates (rough-in inspection before lining; final inspection before CC sign-off and OC).
- The certifier is not the plumbing authority — plumbing inspections are carried out by the relevant council or the licensed plumber's supervisor under TAFE/WaterNSW/council arrangements. In NSW, the plumber provides a compliance certificate to council.

**Hot water (AS/NZS 3500.4):**
- Hot water system type, capacity, and energy source must align with BASIX commitments. A substitution at procurement (e.g. replacing a heat pump with an electric storage unit) without re-checking the BASIX certificate is a compliance failure mode. Load `sustainability-energy-guide.md` for BASIX HW detail.
- Tempering valve (mixing valve) to limit outlet temperature to 50°C is mandatory for domestic installations in NSW under AS/NZS 3500.4 and the *Plumbing Code of Australia*.

**Stormwater (AS/NZS 3500.3):**
- Stormwater must not be discharged to the sanitary sewer — a cross-connection is both a regulatory breach and a common defect. Load `civil-residential.md` for OSD and stormwater connection context.

**Inspection gates:**
- Rough-in plumbing inspection: all rough-in (drain, vent, water supply) to be inspected by council or a registered certifying authority before lining.
- Final plumbing: plumber issues a compliance certificate; this feeds into the CC sign-off.

## 6. AS 1170 — Structural loads for residential

**Scope:** The AS/NZS 1170 series establishes the design actions (loads) for structures. For residential Class 1 buildings, the relevant parts are:

| Part | Coverage |
|---|---|
| AS/NZS 1170.1 | Permanent and imposed actions (dead and live loads) |
| AS/NZS 1170.2 | Wind actions (the full wind standard; AS 4055 is a simplified residential derivative) |
| AS/NZS 1170.3 | Snow and ice actions |
| AS/NZS 1170.4 | Earthquake actions |

### Typical residential load cases

**Dead loads (Permanent actions):** Self-weight of structure — concrete slab, framing, roof, finishes. For a standard timber-framed house with lightweight roof cladding (metal or concrete tile), typical dead loads are well within AS 1684 DTS table assumptions.

**Live loads (Imposed actions):**
- Residential floor: 1.5 kPa (general), 3.0 kPa (balconies), per AS 1170.1.
- These are standard DTS assumptions in AS 1684 span tables. Engineer involvement is triggered when loads depart from standard domestic use (e.g. large stone benchtops, swimming pool above podium, green roof).

**Wind loads:** Use AS 4055 for the simplified residential wind classification. AS 1170.2 is the full wind action standard used for structures where AS 4055 is insufficient (unusual geometry, tall structures, engineer-designed systems).

**Snow loads (AS 1170.3):** Relevant to alpine and sub-alpine areas (Snowy Mountains, ACT alpine). Flag as a graceful-degradation callout for Sydney metro (snow loads not applicable to typical NSW metro residential). For alpine projects, a structural engineer is required.

**Earthquake (AS 1170.4):** Residential Class 1 buildings generally fall within the simplified Earthquake Design Category (EDC) assessment under AS 1170.4. Most of NSW metro is in a low-seismicity zone; typical Class 1a timber-framed construction with adequate bracing satisfies seismic requirements without bespoke design. Engineer sign-off is advisable for:
- Class 1 buildings on P-class sites with soft soil amplification;
- masonry-heavy construction (unreinforced masonry) in any region;
- heritage buildings or unusual structural systems.

## Coverage depth

| Topic | Depth |
|---|---|
| AS 2870 site classifications (M/H1/H2/E/P) | Deep |
| AS 1684 framing concepts and inspection gates | Moderate |
| AS 4055 wind classification | Moderate |
| AS 3959 BAL ratings and construction triggers | Moderate |
| AS 3500 residential plumbing posture | Moderate |
| AS 1170 residential load cases | Shallow (posture only) |
| Engineering calculation procedures | Minimal (out of scope) |

## Low-confidence flags

- **Standards currency:** Australian Standards are revised periodically. Confirm the current edition for any standard before using it as a compliance basis — especially AS 1684 (series being revised), AS 3959 (BAL thresholds may update), and AS 3500 (state plumbing codes may differ).
- **P-class sites:** P-class site design is highly site-specific. This seed provides orientation only; P-class always requires a geotechnical and structural engineer engaged for that site.
- **BAL-FZ construction:** BAL-FZ requirements go beyond this seed's coverage — engage a bushfire consultant and fire engineer.
- **Cyclonic regions:** All cyclonic wind class (C1–C4) guidance here is shallow. Northern Australia cyclonic construction has its own detailed requirements beyond this seed.
- **AS 1170.4 seismic:** Seismic design details are not covered here. For any project with unusual geometry, soft soil (P-class), or masonry-heavy construction, engage a structural engineer.

## See also

- `ncc-reference-guide.md` — NCC Volume Two compliance framework, Class 1/10 (task-loaded)
- `sustainability-energy-guide.md` — BASIX/NatHERS, energy compliance, HW and glazing commitments (task-loaded)
- `structural-residential.md` — deeper residential structural guidance (task-loaded)
- `civil-residential.md` — stormwater, OSD, sewer connection (task-loaded)
- `mep-residential.md` — HW, gas, electrical, plumbing services in residential context (task-loaded)
- `new-dwelling-guide.md` — BAL/bushfire section, slab inspection gate, frame inspection gate
- `../00-doctrine/doctrine.md §evidence-discipline` — labelling assumptions vs confirmed facts
- `../00-doctrine/doctrine.md §escalation-triggers` — when to route to engineer, certifier, or specialist
- `../AGENTS.md §1` — authority stack; project evidence beats seed guidance
