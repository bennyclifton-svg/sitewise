# SiteWise Test Prompt Corpus

Systematic coverage of every building class and subclass in `data/taxonomy/building-classes.json`, with work types and scale bands deliberately varied.

**How to use:** paste the prompt into a new project chat exactly as written. Do not clean it up — the roughness is the test. Run, then critique the output against the shared rubric plus the per-prompt checkpoints. Feed the critique to the coding agent as a categorised defect list, not prose.

**Coverage:** 47 subclasses, 5 work types, 4 scale bands. Prompts 1–12 are the currently under-tested small/services/refurb end.

---

## Shared critique rubric

Score every run against these. The per-prompt checkpoints are additions, not replacements.

| # | Category | Question |
|---|---|---|
| C1 | Classification | Did class, subclass and work type resolve correctly? |
| C2 | Input retention | Was every fact in my prompt used, or was some silently dropped? |
| C3 | Section applicability | Are any sections present that this project type does not need? |
| C4 | Section absence | Are any sections missing that this project type demands? |
| C5 | Consultant correctness | Is the named design lead the right discipline for this work? |
| C6 | Scale proportionality | Does the document's length and ceremony match the project's size? |
| C7 | Doctrine routing | Did the right seed knowledge load, and is it visible in the output? |
| C8 | Invention | Any fact asserted that I did not provide and no document supports? |
| C9 | Register | Would I send this to a client under my own name? |

**Scale bands:** XS (<$250k) · S ($250k–$2m) · M ($2m–$20m) · L ($20m+)

---

## Section 1 — Small works, services and trade packages

The identified blind spot. These should produce short, sharp documents. If any of them runs longer than two pages or names an Architect, that is a defect.

**1. Mechanical plant replacement** — commercial / office / refurb · XS

> Two Pioneer AC systems servicing the service centre and western office are 30+ years old, beyond economical repair, still on R22. Staff report the area is too cold in winter and too hot in summer. Rest of the site's units inspected and fine. Recommending full replacement of both with Actron 30kW split ducted units, including everything needed for a complete working install. Budget around $180k. Need a PMP and cost plan.

Check: R22 phase-out obligations under the Ozone Protection and Synthetic Greenhouse Gas Management Act. Licensed refrigerant handling. Occupied-building staging and shutdown windows. Out-of-hours work. Commissioning and balancing. Electrical capacity check for new units. Possible asbestos in 30-year-old plant. **No FFE schedule. No Architect. Mechanical engineer leads.**

**2. Fire services upgrade** — industrial / warehouse / refurb · S

> Fire upgrade across three warehouses at our Wetherill Park site. Replacing the sprinkler pumps and upgrading the sprinkler system to current standard. Warehouses stay operational throughout. Budget roughly $850k. PMP and cost plan please.

Check: AS 2118 / AS 2941. Fire engineer and hydraulic consultant, not Architect. Impairment management and fire watch during isolation. Essential safety measures and AFSS impact. Tenant coordination. Staged handover per building.

**3. Switchboard and electrical upgrade** — institution / education_primary_secondary / refurb · XS

> Main switchboard at the primary school is at capacity and non-compliant. Need to upgrade the MSB and associated submains. Work has to happen in the summer holidays. About $220k. Need a PMP.

Check: Working with children / site access during term. Hard programme constraint driving everything. Supply authority coordination and lead time. Electrical engineer leads. Shutdown planning. Should be brief.

**4. Lift replacement** — residential / apartments / refurb · S

> Strata building in Bondi, 8 levels, two lifts both original from 1988. Replacing both. Owners corporation has approved $1.4m. Residents stay in occupation. Need a PMP.

Check: Sequential replacement so one lift stays live. Strata approval and by-law process. Disability access compliance on upgrade. Vertical transportation consultant. Resident communication. Building code upgrade triggers.

**5. Roof replacement and waterproofing** — commercial / retail_standalone / refurb · XS

> Metal roof on a standalone retail building is leaking badly. Replacing the roof sheeting and re-doing the box gutters. Tenant trading throughout. Around $160k.

Check: Weather contingency and temporary weatherproofing. Trading-hours restrictions. Working at heights. Asbestos check on older roof. Building surveyor only if structural. Very short document.

**6. Remedial concrete and facade** — residential / apartments / remediation · S

> Concrete cancer in the basement carpark and spalling on the eastern facade. Building is 1970s, 6 levels, residential strata. Engineer's report says remediation needed. Budget not fixed yet, maybe $1.2m.

Check: Structural engineer leads. Investigation before scope lock. Provisional sums for unknown extent. Resident access and parking loss. Strata levies and funding. Heavy risk weighting.

**7. Asbestos removal and make-good** — industrial / manufacturing / remediation · S

> Old factory, need to remove asbestos cladding and roofing from Building 3 before we refit it. Site keeps running. Licensed removal, air monitoring, clearance certificates. Rough budget $600k.

Check: Class A licensed removalist. Occupational hygienist and clearance certification. SafeWork notification. Exclusion zones next to a live plant. Waste tracking. Compliance and risk sections dominate.

**8. Cosmetic tenancy refresh** — commercial / office / refurb · XS

> Refreshing our 400sqm tenancy. New carpet, repaint, replace ceiling tiles, new kitchenette joinery. Landlord's approval needed. About $95k, want it done over four weekends.

Check: **This one SHOULD have an FFE schedule** — contrast with prompt 1. Landlord consent and make-good. After-hours only. Minimal compliance. Interior designer, not Architect. Should be one page.

**9. Car park resurfacing and line marking** — commercial / retail_shopping_centre / refurb · XS

> Resurfacing the upper deck car park at the centre. Asphalt overlay, new line marking, replacing failed expansion joints. Centre trades throughout. $340k.

Check: Staged by zone to keep trading. Civil engineer. Traffic management. Weather. Accessible bay compliance. Waterproof membrane condition.

**10. Advisory — condition assessment** — institution / healthcare_medical_centre / advisory · XS

> Client wants us to assess the condition of their medical centre and give them a 10-year capital works plan with indicative costs. No construction yet.

Check: Advisory work type must suppress procurement, delivery and construction programme. Deliverables-based, not milestone-based. No contractor. Cost plan should be lifecycle forecast, not a build estimate.

**11. Due diligence advisory** — industrial / logistics_ecommerce / advisory · S

> Client is buying a distribution centre and wants technical due diligence before settlement in six weeks. Building condition, compliance, capex forecast, any deal-breakers.

Check: Hard deadline drives programme. Deliverables not milestones. No procurement or tender sections. Risk section should be about the transaction.

**12. Multi-trade minor works package** — institution / government_civic / refurb · S

> Council depot. Bundle of small jobs: new amenities block fitout, three roller doors replaced, LED lighting upgrade throughout, repaint the workshop. Council wants one contract. $480k total, needs to be done by end of financial year.

Check: Multiple unrelated trades under one head contract. Council procurement rules and thresholds. EOFY deadline. Depot stays operational. Package-based rather than sequential programme.

---

## Section 2 — Residential

**13. House, knock-down rebuild** — residential / house / new · M

> Knock down rebuild at 123 Warrigal Street, Wollongong. Two storey, 4 bed 3 bath, double garage, pool. Clients are M & S Petrakis. Budget $1.6m, want to start on site early next year.

Check: Demolition and enabling works. DA pathway. FFE schedule populated. Pool as a separate scope with fencing compliance. BASIX.

**14. House, extension and addition** — residential / house / extend · S

> Second storey addition and rear extension to a semi in Newtown. Heritage conservation area. Adding 2 beds and a bathroom up, opening the rear to a new kitchen and living. Clients living elsewhere during works. Around $750k.

Check: Heritage referral and conservation area controls. Structural adequacy of existing. Party wall / adjoining owner. Existing-to-new interface. Excavation near neighbours.

**15. Apartments** — residential / apartments / new · L

> New residential flat building, 6 storeys, 42 apartments over two basement parking levels. Site in Parramatta. Client is a mid-tier developer. Budget circa $28m.

Check: SEPP 65 and design review panel. Apartment Design Guide. Registered certifier and Design and Building Practitioners Act declarations. Basement excavation and dewatering. Strata subdivision.

**16. Townhouses** — residential / townhouses / new · M

> 11 townhouses, 3 bed each, on a subdivided site in Kellyville. Torrens title. Budget about $8m.

Check: Subdivision and torrens titling. Repetition and staged handover. Shared services and easements. Party wall construction.

**17. Build to rent** — residential / btr / new · L

> BTR tower, 180 apartments, ground floor amenity, gym, co-working lounge, rooftop terrace. CBD fringe site. Institutional client, long-term hold. Around $95m.

Check: Long-hold durability and lifecycle cost. Amenity fitout as distinct scope. Operator involvement. No strata. Different FFE standard.

**18. Student housing** — residential / student_housing / new · L

> PBSA development, 340 beds, mix of studios and 6-bed clusters, near the university. Ground floor study and social space. Budget $62m.

Check: Bed count as primary scale metric. Academic-year handover deadline is absolute. Repetitive modular rooms. Operator brief. High-durability finishes.

**19. Retirement living** — residential / retirement_living / new · L

> 64 independent living units plus a community centre, retirement village in Port Macquarie. Single storey, accessible throughout. $34m.

Check: Retirement Villages Act. Accessibility beyond minimum. Staged occupation with residents moving in progressively. Community facility as separate scope.

**20. Residential aged care** — residential / residential_aged_care / new · L

> New 120-bed residential aged care facility, Class 9c. Dementia wing, commercial kitchen, clinical areas. Regional NSW. $48m.

Check: Class 9c fire and egress requirements. Aged Care Quality Standards. Clinical and nurse call services. Commercial kitchen. Accreditation before occupancy.

**21. Social and affordable housing** — residential / social_affordable_housing / new · M

> 24 social housing dwellings for a community housing provider. Mix of 1 and 2 bed. Government funding with reporting requirements. $11m.

Check: Funding agreement milestones and acquittal. Livable Housing Design silver/gold. NatHERS. Provider handover and tenancy. Cost certainty over flexibility.

**22. Residential other — boarding house conversion** — residential / other / refurb · M

> Converting a disused motel into a boarding house, 28 rooms. Needs full services upgrade, fire upgrade, new amenities. $4.2m.

Check: Change of use and BCA classification change. Fire upgrade to current standard. Existing building survey. Unknowns and provisional sums.

---

## Section 3 — Commercial

**23. Office, new** — commercial / office / new · L

> New A-grade office building, 12 storeys, 18,000sqm NLA, target 5 star Green Star and 5.5 NABERS. CBD site. $140m.

Check: Green Star and NABERS as programme-critical, with commissioning and tuning. Base build vs tenant fitout boundary. Facade engineering. Developer/tenant decision split.

**24. Office refurbishment, occupied** — commercial / office / refurb · M

> Refurbishing levels 3 to 8 of an existing office tower while the building stays occupied. New end-of-trip, lobby upgrade, replacing the chillers. $9m.

Check: Occupied-building staging is the dominant constraint. After-hours and noise. Chiller replacement with seasonal windows. Tenant communication. Decanting.

**25. Shopping centre expansion** — commercial / retail_shopping_centre / extend · L

> Expanding a regional shopping centre. New 6,000sqm mall extension with 22 specialty tenancies and a relocated supermarket. Centre trades throughout. $75m.

Check: Trading continuity as the governing constraint. Tenancy delivery and handover to fitout. Supermarket relocation sequencing. Car parking during works. Landlord/tenant works split.

**26. Standalone retail** — commercial / retail_standalone / new · M

> New standalone bulky goods retail building, 3,200sqm, on a highway site. Single tenant pre-committed. $7m.

Check: Tenant agreement for lease driving specification. Highway access and RMS. Simple structure, fast programme. Shell vs fitout boundary.

**27. Hotel** — commercial / hotel / new · L

> 180 key 4.5 star hotel, restaurant, bar, conference facilities, gym. City fringe. Operator is an international brand with their own standards. $85m.

Check: Operator brand standards as a governing document. Key count as scale metric. FF&E and OS&E procurement separate from build. Back-of-house. Pre-opening programme.

**28. Food and beverage fitout** — commercial / food_beverage / refurb · S

> Restaurant fitout in a shell tenancy, 220sqm, 90 seats. Full commercial kitchen, bar, cool room. Client wants to open in 14 weeks. $980k.

Check: Kitchen exhaust and make-up air, grease arrestor, food authority approval. Extremely tight programme. Liquor licensing. Landlord services capacity. Heavy FFE.

**29. Coworking fitout** — commercial / serviced_office_coworking / refurb · M

> Fitting out 2,400sqm across two floors as a coworking space. Meeting rooms, phone booths, event space, kitchen. Operator client. $3.8m.

Check: Acoustic separation. Dense AV and IT. Operator brand fitout standard. Base building services capacity. Churn-ready design.

**30. Commercial other — service station** — commercial / other / new · M

> New service station and convenience store on a highway site. Fuel tanks, canopy, 200sqm store, drive-through coffee. $5.5m.

Check: Underground fuel storage and EPA. Dangerous goods licensing. Civil and pavement. Canopy structure. Contamination baseline.

---

## Section 4 — Industrial

**31. Warehouse** — industrial / warehouse / new · M

> New 12,000sqm warehouse with 800sqm office, 12m clear height, 8 recessed docks. Estate site in Eastern Creek. $18m.

Check: Clear height, dock count and floor flatness (FM2) as scale drivers. Portal frame. Slab specification. Estate design guidelines. Fire — early suppression.

**32. Logistics and e-commerce** — industrial / logistics_ecommerce / new · L

> Automated distribution centre, 45,000sqm, 24 dock doors, ASRS system with 30m high bay. Client is a national retailer. $120m.

Check: Automation interface as a separate contract with its own programme. High-bay fire (ESFR) and structure. Floor tolerance for robotics. Power and data. MHE vendor coordination.

**33. Manufacturing** — industrial / manufacturing / new · L

> New manufacturing facility, 9,000sqm production hall plus admin. Client is installing their own process equipment. Compressed air, 3-phase power, process water. $32m.

Check: Process equipment interface and free-issue coordination. Services capacity. Vibration and slab loading. EPA licence for emissions. Commissioning split.

**34. Cold storage** — industrial / cold_storage / new · L

> Cold store, 8,000sqm, mix of chilled and frozen, minus 25 in the freezer chambers. Ammonia refrigeration. $45m.

Check: Ammonia safety, bunding and leak detection. Insulated panel fire risk. Vapour barrier and underfloor heating. Refrigeration as a specialist package. Pull-down commissioning.

**35. Data centre** — industrial / data_centre / new · L

> 15MW data centre, Tier III, on a greenfield site. Client wants N+1 across power and cooling. $180m.

Check: Uptime Institute Tier certification. Power supply and substation lead time. Redundancy across every system. Level 1–5 commissioning. Security. Critical-path power authority approvals.

**36. Dangerous goods** — industrial / dangerous_goods / new · M

> Chemical storage and blending facility. Bunded storage for Class 3 and 8, blending room, drum store. $14m.

Check: Dangerous goods licensing and quantities. Bunding and spill containment. Separation distances. Fire and emergency plan. HAZOP. EPA.

**37. Heavy manufacturing** — industrial / heavy_manufacturing / new · L

> Steel fabrication plant. 40 tonne overhead cranes, heavy slab, rail siding. 15,000sqm. $58m.

Check: Crane loads driving structure. Heavy-duty pavement and slab. Rail siding and authority interface. Noise and vibration to neighbours. Power capacity.

**38. Food processing** — industrial / food_processing / new · L

> New food processing plant, ready meals. Hygienic production areas, chillers, packing hall, despatch. HACCP compliance. $40m.

Check: Hygienic design and washdown. HACCP and food safety accreditation. Wastewater and trade waste. Segregation of raw and cooked. Validation before production.

**39. Pharmaceutical GMP** — industrial / pharmaceutical_gmp / new · L

> Sterile manufacturing facility, GMP compliant. Grade B and C cleanrooms, filling suite, QC lab, warehouse. TGA licensed. $95m.

Check: GAMP 5 / URS-FS-DQ-IQ-OQ-PQ validation cascade. TGA licensing. Cleanroom classification and pressure cascade. Validation programme is not the construction programme. Change control.

**40. Cleanroom** — industrial / cleanroom / refurb · M

> Converting existing lab space into an ISO 7 cleanroom, 600sqm. Semiconductor client. Building stays operational around it. $8m.

Check: ISO 14644 classification and validation. Existing services capacity. Vibration criteria. Airlocks and pressure cascade. Certification before handover.

**41. Battery manufacturing** — industrial / battery_manufacturing / new · L

> Battery assembly plant, 20,000sqm. Dry rooms, thermal runaway containment, chemical storage. $150m.

Check: Dry room humidity control. Thermal runaway and fire strategy — beyond standard code. Dangerous goods. High power. Emerging-technology risk and precedent scarcity.

**42. Waste to energy** — industrial / waste_to_energy / new · L

> Waste to energy facility processing 300,000 tonnes a year. Boiler, turbine, flue gas treatment, tipping hall. $400m.

Check: EPA licensing and emissions. Community consultation and social licence. Process contractor interface. Grid connection. Multi-year programme with process commissioning.

**43. Industrial other — solar and battery on existing site** — industrial / other / extend · M

> Installing 2MW rooftop solar plus a 1MWh battery on an existing distribution centre. Site operational. $4m.

Check: Roof structural capacity. Grid connection and network approval. DC isolation and fire. Working over live operations. Metering and tariff.

---

## Section 5 — Institution

**44. Early childhood centre** — institution / education_early_childhood / new · S

> New 90 place childcare centre, single storey, outdoor play areas. $4.5m.

Check: Education and Care Services National Regulations — space per child, indoor and outdoor. Fencing and supervision sightlines. Approval before operation. Ligature and safety detailing.

**45. School upgrade** — institution / education_primary_secondary / extend · M

> New 8 classroom block plus refurbishing the existing library at a public high school. School operational throughout, works staged around terms. $12m.

Check: Term and holiday programme constraints. Child protection and site separation. Department of Education standards. Staged occupation. Existing building interface.

**46. University building** — institution / education_tertiary / new · L

> New teaching and research building at the university. 9,000sqm, lecture theatres, wet labs, offices. $110m.

Check: Wet lab services and fume cupboards. Academic-calendar handover. Research equipment interface. University design standards. Stakeholder complexity — faculties, facilities, students.

**47. Hospital redevelopment** — institution / healthcare_hospital / refurb · L

> Redeveloping the emergency department and adding two operating theatres at a regional hospital. Hospital fully operational, ED cannot close. $85m.

Check: Australasian Health Facility Guidelines. Infection control risk assessment during construction. ED must stay live — staging is the entire problem. Medical gases. Clinical stakeholder governance. Commissioning with clinical staff.

**48. Medical centre** — institution / healthcare_medical_centre / refurb · S

> Fitting out a new medical centre in a shell tenancy. 12 consult rooms, treatment room, reception, small pathology. $1.8m.

Check: Consult room compliance and accessibility. Medical gas if needed. Infection control finishes. Accreditation. Practitioner fitout expectations.

**49. Allied health clinic** — institution / healthcare_clinic_allied / refurb · XS

> Small physio and allied health clinic fitout, 180sqm. Four treatment rooms, gym area, reception. $290k.

Check: Should be short. Accessibility. Acoustic privacy. Simple services. Minimal compliance. No Architect necessarily — interior designer.

**50. Civic building** — institution / government_civic / new · L

> New council library and community hub. 4,500sqm, library, meeting rooms, cafe, council customer service. $42m.

Check: Public procurement and probity. Community consultation. Councillor and public stakeholder governance. Accessibility and inclusion beyond minimum. Long-life civic durability.

**51. Religious building** — institution / religious / new · M

> New church building, 400 seat worship space, hall, meeting rooms, commercial kitchen. Congregation is funding it progressively. $9m.

Check: Staged construction tied to fundraising. Acoustic design for worship. Assembly occupancy egress. Volunteer labour interface. Cash flow as programme driver.

**52. Institution other — correctional** — institution / other / extend · L

> New 120 bed accommodation wing at an existing correctional facility. Site remains fully operational and secure. $70m.

Check: Security clearance for all workers and materials. Anti-ligature and secure detailing. Operational security during works. Restricted access and escorted movement. Corrections authority standards.

---

## Section 6 — Mixed use

**53. Residential over retail** — mixed / residential_retail / new · L

> 8 storey mixed use — ground floor retail, 5 shops, with 54 apartments above. Site in Marrickville. $46m.

Check: Two building classifications in one structure. Fire separation between uses. Separate entries and services. Retail delivered as shell. Strata subdivision across uses.

**54. Residential over commercial** — mixed / residential_commercial / new · L

> Mixed use tower — 3 levels of commercial office over ground retail, then 90 apartments above. $105m.

Check: Three-way vertical stratification. Structural transfer at the interface. Separate services and cores. Staged handover by use. Complex strata.

**55. Hotel and residential** — mixed / hotel_residential / new · L

> Tower with a 140 key hotel in the podium and 70 apartments above, shared basement carpark. Hotel operator involved. $130m.

Check: Operator standards vs residential standards clashing. Shared vs separate services and back-of-house. Different handover dates. Acoustic separation. Strata across two uses.

**56. Retail and office** — mixed / retail_office / refurb · M

> Refurbishing a mixed retail and office building. Ground retail stays trading, offices above being repositioned. New lobby, services upgrade, end of trip. $16m.

Check: Retail trading continuity against office works above. Repositioning brief. Services upgrade through occupied space. Lobby as shared interface.

**57. BTR and retail** — mixed / btr_retail / new · L

> BTR building, 210 apartments, with 1,200sqm of ground floor retail and F&B. Institutional owner holding both. $115m.

Check: Single owner across both uses simplifies strata but complicates fitout. Retail tenancy delivery. BTR amenity. F&B services provision — exhaust risers.

**58. Vertical village** — mixed / vertical_village / new · L

> Vertical village — childcare, medical, gym, retail, offices and 120 apartments in one development. $160m.

Check: Multiple use classifications with different regulations. Childcare within a mixed development. Separation and access management. Extreme stakeholder complexity. Phased approvals.

**59. Mixed other — adaptive reuse** — mixed / other / refurb · L

> Converting a heritage warehouse into mixed use — ground floor F&B and retail, creative office above, some residential lofts. Heritage listed. $38m.

Check: Heritage constraints against new use requirements. Structural adequacy of existing. Fire upgrade in heritage fabric. Unknowns and provisional sums. Change of use classification.

---

## Section 7 — Infrastructure

**60. Road upgrade** — infrastructure / roads_highways / extend · L

> Upgrading 4km of arterial road from two to four lanes, including two signalised intersections and a bridge widening. $95m.

Check: Traffic management is a major cost and programme item. Utility relocations. Land acquisition. Environmental approvals. Linear staging and night works.

**61. Rail station** — infrastructure / rail_metro / refurb · L

> Station upgrade — new lifts, footbridge, accessible platforms and canopies. Rail line stays operational, work in possessions. $120m.

Check: Track possessions govern everything. Rail safety accreditation and worker competency. Electrical isolation near live overhead. DSAPT accessibility compliance. Interface with the rail authority.

**62. Water treatment plant** — infrastructure / water_utilities / new · L

> New water treatment plant, 40ML per day. Inlet works, filtration, chlorination, clear water storage, pumping. $180m.

Check: Process design and treatment performance. Drinking water quality regulator. Process commissioning and proving. Utility asset standards. Long-term operability and maintenance access.

**63. Solar farm** — infrastructure / energy_renewables / new · L

> 120MW solar farm with grid connection substation. Regional site, 300 hectares. $200m.

Check: Grid connection agreement and network approvals as critical path. Land access and landholder agreements. Environmental and biodiversity offsets. Module supply chain. Generator performance standards.

**64. Wharf upgrade** — infrastructure / marine_ports / refurb · L

> Wharf refurbishment — replacing fender systems, remediating concrete piles, upgrading mooring bollards. Port stays operational. $55m.

Check: Marine works and tidal windows. Vessel movements and berth availability. Underwater inspection and diving. Marine environmental protection. Corrosion and durability.

**65. Airport terminal expansion** — infrastructure / airports / extend · L

> Expanding the domestic terminal — 4 new gates, expanded baggage handling, security screening upgrade. Airport fully operational. $240m.

Check: Airside security and access. Aviation authority approvals. Baggage system as specialist package. Passenger flow during works. Night-only airside work windows.

**66. Telecommunications** — infrastructure / telecommunications / new · M

> Building 14 new mobile tower sites across regional NSW, including access tracks and power. $22m.

Check: Multi-site repeated delivery rather than one project. Land access and native title. Environmental and visual amenity approvals. Remote logistics. Power connection per site.

**67. Infrastructure other — pipeline** — infrastructure / other / new · L

> 18km of new trunk water main through mixed urban and rural land, including a creek crossing and two pump stations. $70m.

Check: Linear works and easement acquisition. Trenchless crossing methods. Traffic management through urban sections. Utility conflicts. Environmental approvals for the creek.

---

## Follow-up prompt sets

Run these as second and third messages on selected projects to test iterative behaviour.

**On prompt 1 (AC replacement):**
1. "The client wants to keep one system running at all times so the service centre isn't without cooling. Can you update the programme?"
2. "Add a provisional sum of $25k for asbestos in case we find it in the old plant rooms."
3. "Actually the budget is now $210k and they want it done before December."

**On prompt 15 (apartments):**
1. "The DA came back with a condition requiring a traffic management plan and an acoustic report. Add those."
2. "Add heated towel rails and a filtered water tap to the FFE schedule."
3. "Now create an RFP for the structural engineer."

**On prompt 24 (occupied office refurb):**
1. "The chillers have a 26 week lead time. Update the programme and flag it as a critical risk."
2. "Add $180k for temporary cooling during the changeover."

**On prompt 47 (hospital ED):**
1. "Infection control have said we need negative pressure hoarding and daily monitoring. Add it."
2. "Create a cost plan."

**On prompt 10 (advisory):**
1. "Client now wants us to also tender the first year of works. Update the plan."
   *Tests whether the document correctly shifts from advisory to delivery.*

---

## Suggested run order

Do not run 1 through 67. Run in waves and fix between waves.

**Wave 1 — the blind spot.** Prompts 1, 2, 3, 8, 10, 49. Six small projects. If the generic-framework problem is real, it will be obvious and consistent here, and these are the cheapest to critique.

**Wave 2 — work type coverage.** Prompts 6, 11, 14, **40**, 43, 61. One of each work type against varied classes. Tests whether work type actually changes anything. Do not skip 40: it is the industrial / ISO 14644 / validation-before-handover checkpoint and was omitted in the original Wave 2 run.

**Wave 3 — scale proportionality.** Prompts 5, 26, 31, 35 in ascending scale within a similar domain. The documents should visibly differ in length and ceremony.

**Wave 4 — class breadth.** One per class: 13, 23, 34, 47, 53, 62.

**Wave 5 — the long tail.** Everything remaining, once the structural fixes have landed.

---

## Recording template

One row per run, so the critique aggregates instead of scattering.

| Field | |
|---|---|
| Prompt # | |
| Expected class / subclass / work type | |
| Actual | |
| C1–C9 scores (0–2) | |
| Sections present that shouldn't be | |
| Sections missing that should be | |
| Facts from prompt that were dropped | |
| Invented facts | |
| Defect category | |
| Repo area implicated | |
| Build SHA | |

**Defect categories to use consistently** — these are what you hand the coding agent:

- `CLASSIFY` — wrong class, subclass or work type
- `SECTION-SET` — wrong sections included or omitted
- `DISCIPLINE` — wrong consultant or design lead
- `SCALE` — document weight wrong for project size
- `DOCTRINE` — right section, wrong or missing seed knowledge
- `INPUT-LOSS` — supplied fact not used
- `INVENT` — unsupported assertion
- `REGISTER` — tone or format not client-ready
- `WORKFLOW-LAUNCH` — the artefact never launched, queued, or completed
- `TAXONOMY-GAP` — the vocabulary has no value for a fact the prompt supplied
- `HARNESS` — the test environment, not the product, invalidated the measurement
- `COST` — cost plan missing figures, budget, GST discipline, or named plant
