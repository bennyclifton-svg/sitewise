"""Generate the Newtown demo fee proposals and consultant invoices.

Fifteen proposals — three per discipline — and sixteen invoices that draw the five
appointed fees down to exactly their proposal totals. The reconciliation is the point:
if the cost plan built from these does not land on $113,800 of consultant fees, ingest
lost something.

Re-runnable: deletes and rewrites 02-fee-proposals/ and 03-invoices/ on every run.

    python docs/demo-corpus/newtown/generate-commercial.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT = "41 Georgina Street, Newtown NSW 2042"
SCOPE = "Rear extension and first-floor addition"
CLIENT = "Daniel and Anthea Marchetti"
CLIENT_SHORT = "D. and A. Marchetti"

GST_RATE = 0.10


def money(amount: float) -> str:
    return f"${amount:,.2f}"


# ------------------------------------------------------------------- fee proposals
# Each proposal: firm, abn, address, contact, ref, date, fee, stages, includes,
# excludes, programme, terms, outcome.

PROPOSALS: dict[str, dict] = {
    "Architectural Services": {
        "rfp_issued": "2025-03-05",
        "due": "2025-03-20",
        "proposals": [
            {
                "firm": "Kestrel Studio Architects",
                "abn": "29 663 108 442",
                "address": "Level 1, 88 Abercrombie Street, Chippendale NSW 2008",
                "contact": "N. Kestrel — Director",
                "ref": "KSA-P2519",
                "date": "2025-03-17",
                "fee": 68500,
                "stages": [
                    ("Concept and Schematic Design", 25, 17125),
                    ("DA Documentation and Lodgement", 25, 17125),
                    ("Detailed Design and Construction Documentation", 35, 23975),
                    ("Construction Attendance — 4 site visits", 15, 10275),
                ],
                "includes": [
                    "Measured survey of the existing dwelling",
                    "Concept and schematic design to client sign-off",
                    "DA drawing set — plans, elevations, sections, shadow diagrams",
                    "Coordination of structural and civil consultants",
                    "Construction documentation for Construction Certificate",
                    "Four construction-stage site visits",
                ],
                "excludes": [
                    "Heritage Impact Statement — assumed covered by the town planner",
                    "Interior design and FFE documentation",
                    "Landscape design",
                    "Site visits beyond four; additional visits at $420 each",
                    "3D visualisation",
                    "Attendance at Council meetings",
                ],
                "programme": "Concept 4 weeks · DA set 5 weeks · CC documentation 7 weeks",
                "terms": "Monthly progress claims. 14 days. 1.5% per month on overdue.",
                "note": "Project delivery by an associate under director review. Director "
                        "attendance at concept presentation and one design review only.",
                "outcome": "Not appointed — reduced construction-stage service and heritage "
                           "exclusion left a coordination gap the owners were not comfortable with.",
            },
            {
                "firm": "Bower Lane Architecture",
                "abn": "62 471 903 118",
                "address": "Studio 4, 118 Erskineville Road, Erskineville NSW 2043",
                "contact": "J. Bowerman — Director, NSW ARB 8841",
                "ref": "BLA-P2603",
                "date": "2025-03-19",
                "fee": 82000,
                "stages": [
                    ("Concept and Schematic Design", 25, 20500),
                    ("DA Documentation and Lodgement", 25, 20500),
                    ("Detailed Design and Construction Documentation", 30, 24600),
                    ("Construction Attendance — 12 site visits", 20, 16400),
                ],
                "includes": [
                    "Measured survey and dilapidation photography of the existing dwelling",
                    "Concept and schematic design, two options developed to client sign-off",
                    "Full DA drawing set including shadow diagrams, streetscape elevation "
                    "and heritage context sheet",
                    "External finishes and materials schedule",
                    "Coordination of structural, civil, planning and certification consultants",
                    "Construction documentation for Construction Certificate",
                    "Interior documentation — joinery, wet areas, FFE schedule",
                    "Window and door schedule",
                    "Twelve construction-stage site visits and progress claim recommendations",
                    "Pre-DA meeting attendance with Inner West Council",
                ],
                "excludes": [
                    "Landscape design beyond hard-surface layout",
                    "Pool design and engineering — by pool contractor",
                    "Structural, civil, hydraulic, electrical and mechanical design",
                    "Council fees, BASIX and long service levy",
                    "Physical models and VR",
                ],
                "programme": "Concept 4 weeks · DA set 6 weeks · CC documentation 8 weeks · "
                             "construction attendance for the duration of the works",
                "terms": "Monthly progress claims against stage completion. 14 days.",
                "note": "Three completed first-floor additions within the Newtown/Enmore "
                        "Heritage Conservation Area, two on Georgina Street. Director-led "
                        "throughout. References provided on request.",
                "outcome": "**APPOINTED 27 March 2025.** Local conservation-area experience, "
                           "full construction-stage attendance, and interiors included rather "
                           "than carved out.",
            },
            {
                "firm": "Harrow & Vine Architects",
                "abn": "77 214 985 630",
                "address": "Level 6, 210 Crown Street, Surry Hills NSW 2010",
                "contact": "P. Harrow — Principal, NSW ARB 6612",
                "ref": "HV-2503-41GS",
                "date": "2025-03-20",
                "fee": 96500,
                "stages": [
                    ("Concept, Schematic Design and Visualisation", 30, 28950),
                    ("DA Documentation and Lodgement", 22, 21230),
                    ("Detailed Design and Construction Documentation", 28, 27020),
                    ("Construction Attendance — fortnightly", 20, 19300),
                ],
                "includes": [
                    "Everything in a full architectural service, concept to completion",
                    "Interior design including finishes, joinery and FFE specification",
                    "Landscape design coordination with a nominated landscape architect",
                    "3D visualisation package and a VR walkthrough at concept stage",
                    "Physical sketch model at 1:50",
                    "Fortnightly site attendance for the duration of the works",
                    "Principal-led on every stage",
                ],
                "excludes": [
                    "Sub-consultant fees",
                    "Council and authority charges",
                    "Landscape architect's own fee",
                ],
                "programme": "Concept 6 weeks · DA set 6 weeks · CC documentation 8 weeks",
                "terms": "Monthly progress claims. 30 days.",
                "note": "Practice specialises in high-end inner-city residential. Portfolio "
                        "provided. Would recommend an increased finishes budget to suit the "
                        "level of documentation offered.",
                "outcome": "Not appointed — service level and fee both above what the project "
                           "needs. Visualisation package not valued by the owners.",
            },
        ],
    },
    "Town Planning": {
        "rfp_issued": "2025-04-02",
        "due": "2025-04-17",
        "proposals": [
            {
                "firm": "Loftus Planning & Development",
                "abn": "84 559 273 016",
                "address": "Suite 3, 41 Norton Street, Leichhardt NSW 2040",
                "contact": "B. Loftus MPIA",
                "ref": "LPD-2504-118",
                "date": "2025-04-11",
                "fee": 7800,
                "stages": [
                    ("Planning review and pre-lodgement advice", 30, 2340),
                    ("Statement of Environmental Effects and DA lodgement", 50, 3900),
                    ("Post-lodgement RFI response", 20, 1560),
                ],
                "includes": [
                    "Review of planning controls — IWLEP 2022 and IWDCP 2023",
                    "Statement of Environmental Effects",
                    "DA lodgement via the NSW Planning Portal",
                    "One round of response to Council requests for information",
                ],
                "excludes": [
                    "**Heritage Impact Statement — to be obtained separately by the client**",
                    "Pre-DA meeting attendance with Council",
                    "Community or neighbour consultation",
                    "Attendance at the Local Planning Panel",
                    "Land and Environment Court proceedings",
                ],
                "programme": "SEE 3 weeks from receipt of the DA drawing set",
                "terms": "50% on commencement, 50% on lodgement. 14 days.",
                "note": "Fee assumes a straightforward assessment. A Heritage Impact "
                        "Statement will be required for this site and is not included.",
                "outcome": "Not appointed — the heritage exclusion is the single most "
                           "important document in a conservation-area DA.",
            },
            {
                "firm": "Verity Urban Planning",
                "abn": "73 402 951 668",
                "address": "Level 3, 15 Enmore Road, Newtown NSW 2042",
                "contact": "K. Verity MPIA — Director",
                "ref": "VUP-2504-41GS",
                "date": "2025-04-14",
                "fee": 9900,
                "stages": [
                    ("Planning review, pre-DA meeting and strategy", 30, 2970),
                    ("Statement of Environmental Effects, Heritage Impact Statement "
                     "and DA lodgement", 50, 4950),
                    ("Post-lodgement RFI response and determination", 20, 1980),
                ],
                "includes": [
                    "Planning controls review — IWLEP 2022, IWDCP 2023, Codes SEPP screening",
                    "Pre-DA meeting with Inner West Council and written file note",
                    "Statement of Environmental Effects",
                    "**Heritage Impact Statement prepared in-house** by our heritage specialist",
                    "Comparative analysis of precedent first-floor additions in the immediate "
                    "streetscape",
                    "DA lodgement via the NSW Planning Portal",
                    "Response to Council requests for information through to determination",
                    "Advice on neighbour notification and objection management",
                ],
                "excludes": [
                    "Council application and assessment fees",
                    "Attendance at the Local Planning Panel if the DA is escalated",
                    "Land and Environment Court proceedings",
                    "Section 4.55 modification applications after determination",
                ],
                "programme": "Pre-DA 3 weeks · SEE and HIS 4 weeks from receipt of the DA set",
                "terms": "Progress claims at stage completion. 14 days.",
                "note": "Our office is on Enmore Road. We have prepared 40+ applications in "
                        "the Newtown/Enmore HCA and hold a current file of precedent "
                        "determinations on Georgina, Wilson and Lennox Streets.",
                "outcome": "**APPOINTED 24 April 2025.** Heritage Impact Statement in-house "
                           "removes a coordination interface, and the precedent file is "
                           "directly relevant to the first-floor setback argument.",
            },
            {
                "firm": "Callan Planning Group",
                "abn": "31 887 640 219",
                "address": "Level 12, 32 Martin Place, Sydney NSW 2000",
                "contact": "M. Callan FPIA — Associate Director",
                "ref": "CPG-25-0447",
                "date": "2025-04-16",
                "fee": 13500,
                "stages": [
                    ("Planning due diligence and pre-DA", 25, 3375),
                    ("SEE, HIS and DA lodgement", 45, 6075),
                    ("RFI, notification management and determination", 20, 2700),
                    ("Panel briefing retainer", 10, 1350),
                ],
                "includes": [
                    "Full planning due diligence and risk assessment",
                    "Pre-DA meeting and Council liaison",
                    "Statement of Environmental Effects",
                    "Heritage Impact Statement via sub-consultant",
                    "Structured neighbour consultation programme with door-knock and letters",
                    "Objection management and mediation",
                    "Local Planning Panel briefing pack if escalated",
                ],
                "excludes": [
                    "Council fees",
                    "Land and Environment Court appeal",
                ],
                "programme": "Pre-DA 4 weeks · SEE and HIS 5 weeks",
                "terms": "Monthly. 30 days.",
                "note": "Recommend the consultation programme given the conservation-area "
                        "context and the likelihood of submissions on overshadowing.",
                "outcome": "Not appointed — consultation programme and panel retainer are "
                           "sensible for a contested application but not proportionate here.",
            },
        ],
    },
    "Structural Engineering": {
        "rfp_issued": "2025-04-02",
        "due": "2025-04-17",
        "proposals": [
            {
                "firm": "Grimshaw Vale Consulting Engineers",
                "abn": "56 733 190 824",
                "address": "12 Parramatta Road, Annandale NSW 2038",
                "contact": "T. Grimshaw — CPEng 3771056",
                "ref": "GV-2504-882",
                "date": "2025-04-10",
                "fee": 8400,
                "stages": [
                    ("Concept structural advice", 25, 2100),
                    ("DA and CC documentation", 55, 4620),
                    ("Construction attendance and certification", 20, 1680),
                ],
                "includes": [
                    "Concept structural advice on the first-floor addition",
                    "Structural drawings and specification for DA and CC",
                    "Steel and timber design for the new floor and roof",
                    "Two construction-stage inspections",
                    "Structural certification at completion",
                ],
                "excludes": [
                    "**Footing exposure inspection and existing foundation assessment**",
                    "**Underpinning design**",
                    "Party wall assessment and dilapidation",
                    "Geotechnical investigation and liaison",
                    "Retaining wall design",
                    "Temporary works and propping design — by the builder",
                ],
                "programme": "Concept 2 weeks · documentation 4 weeks",
                "terms": "50/40/10. 14 days.",
                "note": "Fee assumes existing footings are adequate. If they are not, "
                        "underpinning design would be a variation.",
                "outcome": "Not appointed — the owners' brief flags unknown footings as a "
                           "specific concern. Excluding the investigation puts the largest "
                           "structural risk outside the fee.",
            },
            {
                "firm": "Ardent Structural",
                "abn": "51 208 664 372",
                "address": "Level 2, 27 Cooper Street, Surry Hills NSW 2010",
                "contact": "P. Ardent — CPEng 4471209, NER 1180446",
                "ref": "AS-P26118",
                "date": "2025-04-15",
                "fee": 11500,
                "stages": [
                    ("Concept design and footing investigation", 30, 3450),
                    ("Detailed design and CC documentation", 45, 5175),
                    ("Construction attendance and certification", 25, 2875),
                ],
                "includes": [
                    "**Footing exposure inspection and assessment of existing foundations**",
                    "Liaison with the geotechnical engineer and review of the site "
                    "classification to AS 2870",
                    "Concept structural scheme for the first-floor addition and rear extension",
                    "**Underpinning design where required at the party wall**",
                    "Party wall condition assessment and dilapidation report",
                    "Structural drawings and specification for DA and CC",
                    "Steel, timber and concrete design",
                    "Six construction-stage inspections at hold points",
                    "Structural certification for the Occupation Certificate",
                ],
                "excludes": [
                    "Geotechnical investigation and borehole cost — by others",
                    "Temporary works and propping design — by the builder",
                    "Pool structural design — by the pool contractor",
                    "Certification of work not designed by this office",
                ],
                "programme": "Footing investigation within 2 weeks of access · concept 3 weeks · "
                             "documentation 5 weeks",
                "terms": "Progress claims at stage completion. 14 days.",
                "note": "We would want the footing exposure done before the concept is locked. "
                        "On a c.1908 semi in this area the footings are usually sandstone "
                        "rubble on shallow bedding, and that changes the scheme.",
                "outcome": "**APPOINTED 24 April 2025.** The only proposal that puts the "
                           "footing investigation and underpinning design inside the fee "
                           "rather than treating them as a variation.",
            },
            {
                "firm": "Bellhaven Engineering",
                "abn": "23 908 447 561",
                "address": "Level 8, 100 Walker Street, North Sydney NSW 2060",
                "contact": "R. Bellhaven — CPEng 2884901",
                "ref": "BH-25-1194",
                "date": "2025-04-17",
                "fee": 15900,
                "stages": [
                    ("Concept, investigation and geotechnical liaison", 30, 4770),
                    ("Detailed design, FEM analysis and CC documentation", 45, 7155),
                    ("Construction attendance and independent certification", 25, 3975),
                ],
                "includes": [
                    "Everything in a full structural service for the works",
                    "Footing exposure and foundation assessment",
                    "Underpinning design",
                    "Finite element analysis of the party wall load transfer",
                    "Independent structural review by a second CPEng",
                    "Eight construction-stage inspections",
                    "Full dilapidation survey of both adjoining properties",
                ],
                "excludes": [
                    "Geotechnical investigation cost",
                    "Temporary works design",
                ],
                "programme": "Concept 4 weeks · documentation 6 weeks",
                "terms": "Monthly. 30 days.",
                "note": "FEM analysis is recommended where a new floor loads a shared "
                        "masonry wall of unknown construction.",
                "outcome": "Not appointed — the analysis offered exceeds what a two-storey "
                           "semi requires. Retained as a fallback if underpinning proves "
                           "more extensive than expected.",
            },
        ],
    },
    "Civil and Stormwater Engineering": {
        "rfp_issued": "2025-04-02",
        "due": "2025-04-17",
        "proposals": [
            {
                "firm": "Stormline Consulting",
                "abn": "67 220 813 495",
                "address": "9 Pyrmont Bridge Road, Camperdown NSW 2050",
                "contact": "J. Stormline",
                "ref": "SL-2504-63",
                "date": "2025-04-09",
                "fee": 4200,
                "stages": [
                    ("Stormwater concept plan", 45, 1890),
                    ("DA documentation", 35, 1470),
                    ("Construction certificate markup", 20, 840),
                ],
                "includes": [
                    "Stormwater concept plan for DA",
                    "Impervious area calculation",
                    "Preliminary OSD sizing",
                ],
                "excludes": [
                    "**Detailed OSD design and tank documentation**",
                    "**Erosion and sediment control plan**",
                    "Council liaison and drainage approval",
                    "Construction-stage attendance",
                    "Stormwater compliance certificate at completion",
                ],
                "programme": "Concept 2 weeks",
                "terms": "50/50. 14 days.",
                "note": "Detailed OSD design available as a separate engagement if Council "
                        "requires it.",
                "outcome": "Not appointed — Inner West will require detailed OSD design and "
                           "a compliance certificate. Excluding both means a second "
                           "engagement later at a worse price.",
            },
            {
                "firm": "Catchment Civil & Hydraulic",
                "abn": "88 315 720 946",
                "address": "Unit 11, 3 Wetherill Street, Leichhardt NSW 2040",
                "contact": "S. Basu — CPEng 3980114",
                "ref": "CCH-P2604",
                "date": "2025-04-14",
                "fee": 5800,
                "stages": [
                    ("Stormwater concept and site drainage strategy", 30, 1740),
                    ("OSD detailed design and CC documentation", 45, 2610),
                    ("Construction attendance and compliance certificate", 25, 1450),
                ],
                "includes": [
                    "Site drainage investigation including the rear ponding issue",
                    "Stormwater concept plan and management report for DA",
                    "**On-site detention sizing and detailed tank design**",
                    "Discharge control pit and kerb connection design",
                    "Rainwater tank and reuse strategy for BASIX",
                    "Erosion and sediment control plan",
                    "Council drainage liaison",
                    "Two construction-stage inspections",
                    "**Stormwater compliance certificate at completion**",
                ],
                "excludes": [
                    "Council drainage application fees",
                    "Survey — by others",
                    "Hydraulic services design for the dwelling, quoted separately",
                    "Flood study — not required at this site",
                ],
                "programme": "Concept 2 weeks · detailed design 3 weeks from DA determination",
                "terms": "Progress claims at stage completion. 14 days.",
                "note": "We also offer hydraulic services design for the dwelling. Happy to "
                        "quote separately if the builder does not carry it.",
                "outcome": "**APPOINTED 24 April 2025.** Complete scope through to the "
                           "compliance certificate, and the rear ponding is addressed rather "
                           "than assumed away.",
            },
            {
                "firm": "Ridgeway Civil Group",
                "abn": "40 176 559 288",
                "address": "Level 4, 55 Phillip Street, Parramatta NSW 2150",
                "contact": "A. Ridgeway — CPEng 4008317",
                "ref": "RCG-2504-221",
                "date": "2025-04-16",
                "fee": 7900,
                "stages": [
                    ("Concept, flood screening and WSUD strategy", 35, 2765),
                    ("Detailed OSD and civil documentation", 45, 3555),
                    ("Construction attendance and certification", 20, 1580),
                ],
                "includes": [
                    "Full civil and stormwater service",
                    "Flood risk screening assessment",
                    "Water sensitive urban design strategy",
                    "Detailed OSD design and documentation",
                    "Erosion and sediment control",
                    "Compliance certification",
                ],
                "excludes": [
                    "Council fees",
                    "Survey",
                ],
                "programme": "Concept 3 weeks · documentation 4 weeks",
                "terms": "Monthly. 30 days.",
                "note": "Flood screening included as a precaution given proximity to the "
                        "Johnstons Creek catchment.",
                "outcome": "Not appointed — flood screening and WSUD are not triggered at "
                           "this site. Sound proposal, wrong scope.",
            },
        ],
    },
    "Building Certification": {
        "rfp_issued": "2025-04-02",
        "due": "2025-04-17",
        "proposals": [
            {
                "firm": "Pinnacle Certification Group",
                "abn": "72 604 331 907",
                "address": "Suite 8, 210 George Street, Liverpool NSW 2170",
                "contact": "V. Pinnacle — Registered Certifier BDC1994",
                "ref": "PCG-25-3318",
                "date": "2025-04-08",
                "fee": 3400,
                "stages": [
                    ("Construction Certificate assessment and issue", 55, 1870),
                    ("Mandatory critical stage inspections — 4", 45, 1530),
                ],
                "includes": [
                    "Construction Certificate assessment and issue",
                    "Four mandatory critical stage inspections",
                    "PCA appointment",
                ],
                "excludes": [
                    "**Occupation Certificate — quoted separately at $890**",
                    "BCA compliance statement at DA stage",
                    "Access statement",
                    "Swimming pool barrier inspection and certification",
                    "Re-inspection where work is not ready — $310 each",
                ],
                "programme": "CC assessment 10 business days from complete submission",
                "terms": "Payable on lodgement. 7 days.",
                "note": "Fee excludes the Occupation Certificate. Pool barrier certification "
                        "is a separate engagement.",
                "outcome": "Not appointed — the excluded OC and pool certification bring the "
                           "real cost above Meridian once added back.",
            },
            {
                "firm": "Meridian Building Certifiers",
                "abn": "26 883 419 507",
                "address": "Level 1, 74 King Street, Newtown NSW 2042",
                "contact": "H. Meridian — Registered Certifier BDC2871",
                "ref": "MBC-P3308",
                "date": "2025-04-15",
                "fee": 4600,
                "stages": [
                    ("Construction Certificate assessment and issue", 40, 1840),
                    ("Mandatory critical stage inspections", 35, 1610),
                    ("Final inspections and Occupation Certificate", 25, 1150),
                ],
                "includes": [
                    "**BCA / NCC compliance statement at DA stage**",
                    "**Access statement**",
                    "Construction Certificate assessment and issue",
                    "PCA appointment",
                    "Six mandatory critical stage inspections — footings, slab, frame, "
                    "waterproofing, stormwater, final",
                    "**Swimming pool barrier inspection and certification**",
                    "**Occupation Certificate**",
                ],
                "excludes": [
                    "Long service levy and Council bonds",
                    "Re-inspection where work is not ready — $280 each",
                    "Fire safety certification — not applicable to Class 1a",
                ],
                "programme": "CC assessment 10 business days · inspections within 24 hours "
                             "of booking",
                "terms": "Progress claims at stage completion. 14 days.",
                "note": "Our office is on King Street, ten minutes from the site. We include "
                        "the DA-stage BCA statement because it is cheaper to find a "
                        "compliance problem before lodgement than after.",
                "outcome": "**APPOINTED 24 April 2025.** Only proposal covering DA-stage BCA "
                           "advice, pool barrier certification and the OC in one fee.",
            },
            {
                "firm": "Statewide Building Approvals",
                "abn": "58 442 007 163",
                "address": "Level 15, 227 Elizabeth Street, Sydney NSW 2000",
                "contact": "C. Nandakumar — Registered Certifier BDC0994",
                "ref": "SBA-2504-7712",
                "date": "2025-04-17",
                "fee": 6200,
                "stages": [
                    ("DA-stage compliance advice and statements", 25, 1550),
                    ("Construction Certificate assessment and issue", 35, 2170),
                    ("Inspections — 8", 25, 1550),
                    ("Occupation Certificate", 15, 930),
                ],
                "includes": [
                    "BCA compliance statement and access statement",
                    "Construction Certificate",
                    "Eight critical stage inspections",
                    "Pool barrier certification",
                    "Occupation Certificate",
                    "Dedicated client portal with inspection photographs",
                ],
                "excludes": [
                    "Levies and bonds",
                    "Re-inspections — $340 each",
                ],
                "programme": "CC assessment 15 business days",
                "terms": "Monthly. 30 days.",
                "note": "Portal access provides photographic records of every inspection.",
                "outcome": "Not appointed — two extra inspections and a portal do not justify "
                           "the difference on a single dwelling.",
            },
        ],
    },
}

# ----------------------------------------------------------------------- invoices
# (number, date, stage description, percent, amount, note)

INVOICES: list[dict] = [
    # Architect — Bower Lane Architecture — $82,000
    {"firm": "Bower Lane Architecture", "abn": "62 471 903 118",
     "address": "Studio 4, 118 Erskineville Road, Erskineville NSW 2043",
     "discipline": "Architectural Services", "ref": "BLA-2603", "fee": 82000,
     "bank": "BSB 062-118 · Account 1049 7732",
     "number": "INV-BLA-1042", "date": "2025-05-09", "due": "2025-05-23",
     "stage": "Stage 1 — Concept and Schematic Design", "percent": 25, "amount": 20500,
     "prior": 0,
     "note": "Two concept options developed and presented. Option B adopted 6 May 2025."},
    {"firm": "Bower Lane Architecture", "abn": "62 471 903 118",
     "address": "Studio 4, 118 Erskineville Road, Erskineville NSW 2043",
     "discipline": "Architectural Services", "ref": "BLA-2603", "fee": 82000,
     "bank": "BSB 062-118 · Account 1049 7732",
     "number": "INV-BLA-1188", "date": "2025-06-30", "due": "2025-07-14",
     "stage": "Stage 2 — DA Documentation and Lodgement", "percent": 25, "amount": 20500,
     "prior": 20500,
     "note": "DA drawing set A-000 to A-700 Rev C issued. DA lodged with Inner West "
             "Council 26 June 2025, application DA/2025/0418."},
    {"firm": "Bower Lane Architecture", "abn": "62 471 903 118",
     "address": "Studio 4, 118 Erskineville Road, Erskineville NSW 2043",
     "discipline": "Architectural Services", "ref": "BLA-2603", "fee": 82000,
     "bank": "BSB 062-118 · Account 1049 7732",
     "number": "INV-BLA-1401", "date": "2025-11-28", "due": "2025-12-12",
     "stage": "Stage 3 — Detailed Design and Construction Documentation",
     "percent": 30, "amount": 24600, "prior": 41000,
     "note": "Construction documentation issued for Construction Certificate. "
             "Details A-900 and A-901 issued 21 November 2025."},
    {"firm": "Bower Lane Architecture", "abn": "62 471 903 118",
     "address": "Studio 4, 118 Erskineville Road, Erskineville NSW 2043",
     "discipline": "Architectural Services", "ref": "BLA-2603", "fee": 82000,
     "bank": "BSB 062-118 · Account 1049 7732",
     "number": "INV-BLA-1622", "date": "2026-06-30", "due": "2026-07-14",
     "stage": "Stage 4 — Construction Attendance", "percent": 20, "amount": 16400,
     "prior": 65600,
     "note": "Twelve site visits completed to 30 June 2026. Progress claim "
             "recommendations 1 to 5 issued."},

    # Town Planner — Verity Urban Planning — $9,900
    {"firm": "Verity Urban Planning", "abn": "73 402 951 668",
     "address": "Level 3, 15 Enmore Road, Newtown NSW 2042",
     "discipline": "Town Planning", "ref": "VUP-2504-41GS", "fee": 9900,
     "bank": "BSB 082-356 · Account 4471 0928",
     "number": "INV-VUP-0884", "date": "2025-05-30", "due": "2025-06-13",
     "stage": "Stage 1 — Planning review, pre-DA meeting and strategy",
     "percent": 30, "amount": 2970, "prior": 0,
     "note": "Pre-DA meeting held with Inner West Council 21 May 2025. File note issued."},
    {"firm": "Verity Urban Planning", "abn": "73 402 951 668",
     "address": "Level 3, 15 Enmore Road, Newtown NSW 2042",
     "discipline": "Town Planning", "ref": "VUP-2504-41GS", "fee": 9900,
     "bank": "BSB 082-356 · Account 4471 0928",
     "number": "INV-VUP-0931", "date": "2025-06-30", "due": "2025-07-14",
     "stage": "Stage 2 — Statement of Environmental Effects, Heritage Impact "
              "Statement and DA lodgement",
     "percent": 50, "amount": 4950, "prior": 2970,
     "note": "SEE-001 Rev B and HIS-001 Rev B issued. DA/2025/0418 lodged 26 June 2025."},
    {"firm": "Verity Urban Planning", "abn": "73 402 951 668",
     "address": "Level 3, 15 Enmore Road, Newtown NSW 2042",
     "discipline": "Town Planning", "ref": "VUP-2504-41GS", "fee": 9900,
     "bank": "BSB 082-356 · Account 4471 0928",
     "number": "INV-VUP-1044", "date": "2025-10-03", "due": "2025-10-17",
     "stage": "Stage 3 — RFI response and determination", "percent": 20, "amount": 1980,
     "prior": 7920,
     "note": "Two Council requests for information answered. DA/2025/0418 approved "
             "30 September 2025 subject to 34 conditions."},

    # Structural — Ardent Structural — $11,500
    {"firm": "Ardent Structural", "abn": "51 208 664 372",
     "address": "Level 2, 27 Cooper Street, Surry Hills NSW 2010",
     "discipline": "Structural Engineering", "ref": "AS-26118", "fee": 11500,
     "bank": "BSB 032-002 · Account 7718 2260",
     "number": "INV-AS-2611", "date": "2025-05-16", "due": "2025-05-30",
     "stage": "Stage 1 — Concept design and footing investigation",
     "percent": 30, "amount": 3450, "prior": 0,
     "note": "Footing exposure carried out 2 May 2025. Sandstone rubble footings at "
             "410 mm found on the party wall line. Underpinning confirmed as required."},
    {"firm": "Ardent Structural", "abn": "51 208 664 372",
     "address": "Level 2, 27 Cooper Street, Surry Hills NSW 2010",
     "discipline": "Structural Engineering", "ref": "AS-26118", "fee": 11500,
     "bank": "BSB 032-002 · Account 7718 2260",
     "number": "INV-AS-2744", "date": "2025-11-28", "due": "2025-12-12",
     "stage": "Stage 2 — Detailed design and CC documentation",
     "percent": 45, "amount": 5175, "prior": 3450,
     "note": "S-001 to S-201 issued for CC. Underpinning and party wall details "
             "S-300 issued for construction 21 November 2025."},
    {"firm": "Ardent Structural", "abn": "51 208 664 372",
     "address": "Level 2, 27 Cooper Street, Surry Hills NSW 2010",
     "discipline": "Structural Engineering", "ref": "AS-26118", "fee": 11500,
     "bank": "BSB 032-002 · Account 7718 2260",
     "number": "INV-AS-2988", "date": "2026-07-31", "due": "2026-08-14",
     "stage": "Stage 3 — Construction attendance and certification",
     "percent": 25, "amount": 2875, "prior": 8625,
     "note": "Six hold-point inspections completed — underpinning, footings, ground "
             "floor frame, first floor frame, roof frame, tie-downs."},

    # Civil / Stormwater — Catchment Civil & Hydraulic — $5,800
    {"firm": "Catchment Civil & Hydraulic", "abn": "88 315 720 946",
     "address": "Unit 11, 3 Wetherill Street, Leichhardt NSW 2040",
     "discipline": "Civil and Stormwater Engineering", "ref": "CCH-2604", "fee": 5800,
     "bank": "BSB 012-244 · Account 3390 5518",
     "number": "INV-CCH-1177", "date": "2025-06-06", "due": "2025-06-20",
     "stage": "Stage 1 — Stormwater concept and site drainage strategy",
     "percent": 30, "amount": 1740, "prior": 0,
     "note": "C-100 Rev B and SWM-001 Rev B issued. Rear ponding traced to a blocked "
             "1980s surface drain; addressed in the OSD design."},
    {"firm": "Catchment Civil & Hydraulic", "abn": "88 315 720 946",
     "address": "Unit 11, 3 Wetherill Street, Leichhardt NSW 2040",
     "discipline": "Civil and Stormwater Engineering", "ref": "CCH-2604", "fee": 5800,
     "bank": "BSB 012-244 · Account 3390 5518",
     "number": "INV-CCH-1290", "date": "2025-11-28", "due": "2025-12-12",
     "stage": "Stage 2 — OSD detailed design and CC documentation",
     "percent": 45, "amount": 2610, "prior": 1740,
     "note": "C-101, C-200 and C-300 issued for CC. OSD tank sized at 4.2 m³."},
    {"firm": "Catchment Civil & Hydraulic", "abn": "88 315 720 946",
     "address": "Unit 11, 3 Wetherill Street, Leichhardt NSW 2040",
     "discipline": "Civil and Stormwater Engineering", "ref": "CCH-2604", "fee": 5800,
     "bank": "BSB 012-244 · Account 3390 5518",
     "number": "INV-CCH-1466", "date": "2026-07-31", "due": "2026-08-14",
     "stage": "Stage 3 — Construction attendance and compliance certificate",
     "percent": 25, "amount": 1450, "prior": 4350,
     "note": "OSD tank and discharge control pit inspected 17 July 2026. Stormwater "
             "compliance certificate to issue on completion of external works."},

    # Certifier — Meridian Building Certifiers — $4,600
    {"firm": "Meridian Building Certifiers", "abn": "26 883 419 507",
     "address": "Level 1, 74 King Street, Newtown NSW 2042",
     "discipline": "Building Certification", "ref": "MBC-3308", "fee": 4600,
     "bank": "BSB 062-000 · Account 8841 3307",
     "number": "INV-MBC-3308", "date": "2025-12-05", "due": "2025-12-19",
     "stage": "Stage 1 — Construction Certificate assessment and issue",
     "percent": 40, "amount": 1840, "prior": 0,
     "note": "CC/2025/1188 issued 5 December 2025. PCA appointment accepted."},
    {"firm": "Meridian Building Certifiers", "abn": "26 883 419 507",
     "address": "Level 1, 74 King Street, Newtown NSW 2042",
     "discipline": "Building Certification", "ref": "MBC-3308", "fee": 4600,
     "bank": "BSB 062-000 · Account 8841 3307",
     "number": "INV-MBC-3512", "date": "2026-04-24", "due": "2026-05-08",
     "stage": "Stage 2 — Mandatory critical stage inspections",
     "percent": 35, "amount": 1610, "prior": 1840,
     "note": "Inspections completed — underpinning, footings, slab, frame. All passed. "
             "No re-inspections charged."},
    {"firm": "Meridian Building Certifiers", "abn": "26 883 419 507",
     "address": "Level 1, 74 King Street, Newtown NSW 2042",
     "discipline": "Building Certification", "ref": "MBC-3308", "fee": 4600,
     "bank": "BSB 062-000 · Account 8841 3307",
     "number": "INV-MBC-3701", "date": "2026-08-07", "due": "2026-08-21",
     "stage": "Stage 3 — Final inspections and Occupation Certificate",
     "percent": 25, "amount": 1150, "prior": 3450,
     "note": "Waterproofing and stormwater inspections completed. Pool barrier "
             "inspection and Occupation Certificate to follow on practical completion."},
]


def proposal_doc(discipline: str, meta: dict, spec: dict) -> str:
    gst = spec["fee"] * GST_RATE
    total = spec["fee"] + gst
    stages = "\n".join(
        f"| {name} | {pct}% | {money(amt)} |" for name, pct, amt in spec["stages"]
    )
    includes = "\n".join(f"- {item}" for item in spec["includes"])
    excludes = "\n".join(f"- {item}" for item in spec["excludes"])
    return f"""# Fee Proposal — {discipline}

## {spec['firm']}

**ABN** {spec['abn']}
{spec['address']}

---

| | |
| --- | --- |
| **To** | {CLIENT} |
| **Project** | {PROJECT} |
| **Scope** | {SCOPE} |
| **Discipline** | {discipline} |
| **Our reference** | {spec['ref']} |
| **Date** | {spec['date']} |
| **In response to** | RFP issued {meta['rfp_issued']}, responses due {meta['due']} |
| **Contact** | {spec['contact']} |
| **Validity** | 60 days from the date above |

---

## Fee

| Stage | % | Fee excl GST |
| --- | ---: | ---: |
{stages}
| **Total** | **100%** | **{money(spec['fee'])}** |

| | |
| --- | ---: |
| Professional fees excl GST | {money(spec['fee'])} |
| GST | {money(gst)} |
| **Total incl GST** | **{money(total)}** |

Fees are fixed for the scope described and are not subject to rise and fall.

## Scope included

{includes}

## Excluded

{excludes}

## Programme

{spec['programme']}

## Terms

{spec['terms']}

## Notes

{spec['note']}

---

## Assessment outcome

{spec['outcome']}

---

*Synthetic document. Firm, people, ABN and registration numbers are fabricated.*
"""


def invoice_doc(spec: dict) -> str:
    gst = spec["amount"] * GST_RATE
    total = spec["amount"] + gst
    prior = spec["prior"]
    to_date = prior + spec["amount"]
    remaining = spec["fee"] - to_date
    return f"""# Tax Invoice {spec['number']}

## {spec['firm']}

**ABN** {spec['abn']}
{spec['address']}

---

| | |
| --- | --- |
| **Invoice number** | **{spec['number']}** |
| **Invoice date** | {spec['date']} |
| **Due date** | {spec['due']} |
| **Bill to** | {CLIENT_SHORT} |
| **Project** | {PROJECT} |
| **Discipline** | {spec['discipline']} |
| **Our reference** | {spec['ref']} |

---

## Services

| Description | Amount excl GST |
| --- | ---: |
| {spec['stage']} — {spec['percent']}% of agreed fee | {money(spec['amount'])} |

| | |
| --- | ---: |
| Subtotal excl GST | {money(spec['amount'])} |
| GST 10% | {money(gst)} |
| **Total due** | **{money(total)}** |

## Fee status

| | |
| --- | ---: |
| Agreed fee excl GST | {money(spec['fee'])} |
| Previously invoiced | {money(prior)} |
| This claim | {money(spec['amount'])} |
| **Invoiced to date** | **{money(to_date)}** |
| Remaining | {money(remaining)} |

## Notes

{spec['note']}

## Payment

{spec['bank']}
Reference: {spec['number']}

Terms 14 days from invoice date.

---

*Synthetic document. Firm, people, ABN and bank details are fabricated.*
"""


def slug(text: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in text)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def main() -> None:
    prop_dir = ROOT / "02-fee-proposals"
    inv_dir = ROOT / "03-invoices"
    for directory in (prop_dir, inv_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    n_prop = 0
    for discipline, meta in PROPOSALS.items():
        sub = prop_dir / slug(discipline)
        sub.mkdir()
        for spec in meta["proposals"]:
            total = sum(amt for _, _, amt in spec["stages"])
            assert total == spec["fee"], f"{spec['firm']}: stages {total} != fee {spec['fee']}"
            pct = sum(p for _, p, _ in spec["stages"])
            assert pct == 100, f"{spec['firm']}: stages sum to {pct}%"
            path = sub / f"{slug(spec['firm'])}-{spec['ref'].lower()}.md"
            path.write_text(proposal_doc(discipline, meta, spec), encoding="utf-8")
            n_prop += 1

    drawn: dict[str, float] = {}
    for spec in INVOICES:
        assert spec["prior"] == drawn.get(spec["firm"], 0), (
            f"{spec['number']}: prior {spec['prior']} != running {drawn.get(spec['firm'], 0)}"
        )
        drawn[spec["firm"]] = spec["prior"] + spec["amount"]
        path = inv_dir / f"{spec['number']}-{slug(spec['firm'])}.md"
        path.write_text(invoice_doc(spec), encoding="utf-8")

    # Every appointed fee must be fully drawn.
    appointed = {
        "Bower Lane Architecture": 82000,
        "Verity Urban Planning": 9900,
        "Ardent Structural": 11500,
        "Catchment Civil & Hydraulic": 5800,
        "Meridian Building Certifiers": 4600,
    }
    for firm, fee in appointed.items():
        assert drawn[firm] == fee, f"{firm}: drawn {drawn[firm]} != fee {fee}"

    grand = sum(appointed.values())
    print(f"wrote {n_prop} fee proposals and {len(INVOICES)} invoices")
    print(f"  consultant fees reconcile to {money(grand)} excl GST")
    print(f"  incl GST {money(grand * (1 + GST_RATE))}")


if __name__ == "__main__":
    main()
