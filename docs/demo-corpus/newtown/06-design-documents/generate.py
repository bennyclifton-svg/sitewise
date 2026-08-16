"""Generate the Newtown demo drawing and report corpus.

Each drawing is a title block only — enough for the document register to build a
credible row (number, title, revision, discipline, issue purpose) without pretending
to carry real design content. Reports carry a cover page and a short contents stub for
the same reason.

Re-runnable: deletes and rewrites drawings/ and reports/ on every run.

    python docs/demo-corpus/newtown/06-design-documents/generate.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT = "41 Georgina Street, Newtown NSW 2042"
PROJECT_SHORT = "41 Georgina St, Newtown"
CLIENT = "D. and A. Marchetti"
SCOPE = "Rear extension and first-floor addition"

# --------------------------------------------------------------------------- firms

FIRMS = {
    "architectural": {
        "name": "Bower Lane Architecture",
        "abn": "62 471 903 118",
        "address": "Studio 4, 118 Erskineville Road, Erskineville NSW 2043",
        "job": "BLA-2603",
        "drawn": "T. Okafor",
        "checked": "J. Bowerman",
        "prefix": "A",
        "nominated": "J. Bowerman — NSW ARB 8841",
    },
    "structural": {
        "name": "Ardent Structural",
        "abn": "51 208 664 372",
        "address": "Level 2, 27 Cooper Street, Surry Hills NSW 2010",
        "job": "AS-26118",
        "drawn": "M. Delacroix",
        "checked": "P. Ardent",
        "prefix": "S",
        "nominated": "P. Ardent — CPEng 4471209",
    },
    "civil": {
        "name": "Catchment Civil & Hydraulic",
        "abn": "88 315 720 946",
        "address": "Unit 11, 3 Wetherill Street, Leichhardt NSW 2040",
        "job": "CCH-2604",
        "drawn": "R. Nithsdale",
        "checked": "S. Basu",
        "prefix": "C",
        "nominated": "S. Basu — CPEng 3980114",
    },
    "hydraulic": {
        "name": "Catchment Civil & Hydraulic",
        "abn": "88 315 720 946",
        "address": "Unit 11, 3 Wetherill Street, Leichhardt NSW 2040",
        "job": "CCH-2604-H",
        "drawn": "R. Nithsdale",
        "checked": "S. Basu",
        "prefix": "H",
        "nominated": "S. Basu — CPEng 3980114",
    },
    "electrical": {
        "name": "Verge Electrical Contracting",
        "abn": "19 604 288 573",
        "address": "6 Bridge Road, Stanmore NSW 2048",
        "job": "VE-2609",
        "drawn": "A. Pahlavi",
        "checked": "D. Verge",
        "prefix": "E",
        "nominated": "D. Verge — NSW EC 224871C",
    },
    "mechanical": {
        "name": "Astra Air Mechanical Services",
        "abn": "44 190 736 025",
        "address": "Unit 7, 22 Chalder Street, Marrickville NSW 2204",
        "job": "AAM-2612",
        "drawn": "L. Fenner",
        "checked": "G. Marek",
        "prefix": "M",
        "nominated": "G. Marek — ARCtick AU39114",
    },
}

DISCIPLINE_LABEL = {
    "architectural": "Architectural",
    "structural": "Structural",
    "civil": "Civil / Stormwater",
    "hydraulic": "Hydraulic Services",
    "electrical": "Electrical Services",
    "mechanical": "Mechanical Services",
}

# ------------------------------------------------------------------------ drawings
# (number, title, revision, scale, date, purpose)

DRAWINGS: dict[str, list[tuple[str, str, str, str, str, str]]] = {
    "architectural": [
        ("A-000", "Cover Sheet and Drawing Register", "C", "NTS", "2025-06-19", "For Development Application"),
        ("A-001", "Site Plan and Site Analysis", "C", "1:200 @ A1", "2025-06-19", "For Development Application"),
        ("A-002", "Demolition Plan", "C", "1:100 @ A1", "2025-06-19", "For Development Application"),
        ("A-010", "Existing Ground Floor Plan", "B", "1:100 @ A1", "2025-05-22", "For Development Application"),
        ("A-011", "Existing Elevations and Site Photographs", "B", "1:100 @ A1", "2025-05-22", "For Development Application"),
        ("A-100", "Proposed Ground Floor Plan", "C", "1:100 @ A1", "2025-06-19", "For Development Application"),
        ("A-101", "Proposed First Floor Plan", "C", "1:100 @ A1", "2025-06-19", "For Development Application"),
        ("A-102", "Proposed Roof Plan", "B", "1:100 @ A1", "2025-06-19", "For Development Application"),
        ("A-200", "Proposed Elevations — North and East", "C", "1:100 @ A1", "2025-06-19", "For Development Application"),
        ("A-201", "Proposed Elevations — South and West", "C", "1:100 @ A1", "2025-06-19", "For Development Application"),
        ("A-300", "Sections A-A and B-B", "B", "1:100 @ A1", "2025-06-19", "For Development Application"),
        ("A-301", "Section C-C and Stair Section", "A", "1:50 @ A1", "2025-06-19", "For Development Application"),
        ("A-400", "External Finishes and Materials Schedule", "B", "NTS", "2025-06-19", "For Development Application"),
        ("A-401", "Window and Door Schedule", "A", "1:50 @ A1", "2025-06-19", "For Development Application"),
        ("A-500", "Shadow Diagrams — 21 June, 9am 12pm 3pm", "B", "1:200 @ A1", "2025-06-19", "For Development Application"),
        ("A-501", "Streetscape Elevation and Heritage Context", "B", "1:200 @ A1", "2025-06-19", "For Development Application"),
        ("A-600", "Waste Management Plan", "A", "1:200 @ A1", "2025-06-19", "For Development Application"),
        ("A-700", "Notification Plan", "A", "1:200 @ A3", "2025-06-19", "For Development Application"),
        ("A-900", "Details — Eaves, Parapet and Party Wall Junction", "A", "1:10 @ A1", "2025-11-21", "For Construction"),
        ("A-901", "Details — Stair, Balustrade and Wet Areas", "A", "1:10 @ A1", "2025-11-21", "For Construction"),
    ],
    "structural": [
        ("S-001", "General Notes, Legend and Design Criteria", "B", "NTS", "2025-06-12", "For Development Application"),
        ("S-100", "Footing and Ground Floor Framing Plan", "B", "1:100 @ A1", "2025-06-12", "For Development Application"),
        ("S-101", "First Floor Framing Plan", "B", "1:100 @ A1", "2025-06-12", "For Development Application"),
        ("S-102", "Roof Framing Plan", "A", "1:100 @ A1", "2025-06-12", "For Development Application"),
        ("S-200", "Sections and Details — Sheet 1", "B", "1:20 @ A1", "2025-06-12", "For Development Application"),
        ("S-201", "Sections and Details — Sheet 2", "A", "1:20 @ A1", "2025-06-12", "For Development Application"),
        ("S-300", "Underpinning and Party Wall Details", "A", "1:20 @ A1", "2025-11-21", "For Construction"),
    ],
    "civil": [
        ("C-001", "Civil Notes, Legend and Abbreviations", "A", "NTS", "2025-06-05", "For Development Application"),
        ("C-100", "Stormwater Concept Plan", "B", "1:100 @ A1", "2025-06-05", "For Development Application"),
        ("C-101", "Stormwater Detailed Design and OSD Layout", "B", "1:100 @ A1", "2025-06-05", "For Development Application"),
        ("C-200", "OSD Tank Details, Sections and Discharge Control", "A", "1:20 @ A1", "2025-06-05", "For Development Application"),
        ("C-300", "Erosion and Sediment Control Plan", "A", "1:100 @ A1", "2025-06-05", "For Development Application"),
    ],
    "hydraulic": [
        ("H-001", "Hydraulic Notes, Legend and Fixture Schedule", "A", "NTS", "2025-11-14", "For Construction"),
        ("H-100", "Ground Floor Hydraulic Services Plan", "B", "1:100 @ A1", "2025-11-14", "For Construction"),
        ("H-101", "First Floor Hydraulic Services Plan", "B", "1:100 @ A1", "2025-11-14", "For Construction"),
        ("H-200", "Sanitary Drainage Plan and Invert Levels", "A", "1:100 @ A1", "2025-11-14", "For Construction"),
        ("H-300", "Hot and Cold Water Schematic", "A", "NTS", "2025-11-14", "For Construction"),
    ],
    "electrical": [
        ("E-001", "Electrical Notes, Legend and Symbols", "A", "NTS", "2025-11-21", "For Construction"),
        ("E-100", "Ground Floor Power and Lighting Plan", "B", "1:100 @ A1", "2025-11-21", "For Construction"),
        ("E-101", "First Floor Power and Lighting Plan", "B", "1:100 @ A1", "2025-11-21", "For Construction"),
        ("E-200", "Switchboard Schedule and Single Line Diagram", "A", "NTS", "2025-11-21", "For Construction"),
        ("E-300", "External Lighting and Pool Equipment Plan", "A", "1:100 @ A1", "2025-11-21", "For Construction"),
    ],
    "mechanical": [
        ("M-001", "Mechanical Notes, Legend and Equipment Schedule", "A", "NTS", "2025-11-28", "For Construction"),
        ("M-100", "Ground Floor Mechanical Services Plan", "B", "1:100 @ A1", "2025-11-28", "For Construction"),
        ("M-101", "First Floor Mechanical Services Plan", "B", "1:100 @ A1", "2025-11-28", "For Construction"),
        ("M-200", "Ductwork Layout and Zoning Diagram", "A", "1:100 @ A1", "2025-11-28", "For Construction"),
        ("M-300", "Condenser Location Plan and Acoustic Treatment", "A", "1:50 @ A1", "2025-11-28", "For Construction"),
    ],
}

REVISION_HISTORY = {
    "A": [("A", "2025-05-08", "Issued for coordination and client comment")],
    "B": [
        ("A", "2025-05-08", "Issued for coordination and client comment"),
        ("B", "2025-05-22", "Client comments incorporated. Issued for DA coordination"),
    ],
    "C": [
        ("A", "2025-05-08", "Issued for coordination and client comment"),
        ("B", "2025-05-22", "Client comments incorporated. Issued for DA coordination"),
        ("C", "2025-06-19", "Heritage setback revised to 1.8m. Issued for Development Application"),
    ],
}

# ------------------------------------------------------------------------- reports
# (number, title, revision, date, firm, abn, author, pages, purpose, contents)

REPORTS: list[dict] = [
    {
        "number": "SEE-001", "title": "Statement of Environmental Effects", "rev": "B",
        "date": "2025-06-24", "firm": "Verity Urban Planning", "abn": "73 402 951 668",
        "author": "K. Verity MPIA", "pages": 42, "purpose": "For Development Application",
        "contents": [
            "Introduction and site description",
            "The proposal",
            "Statutory planning framework — EP&A Act 1979, IWLEP 2022",
            "Compliance with development standards",
            "Inner West DCP 2023 assessment",
            "Heritage conservation area assessment",
            "Environmental impacts — overshadowing, privacy, views, streetscape",
            "Suitability of the site",
            "Public interest",
            "Conclusion",
        ],
    },
    {
        "number": "HIS-001", "title": "Heritage Impact Statement", "rev": "B",
        "date": "2025-06-24", "firm": "Verity Urban Planning", "abn": "73 402 951 668",
        "author": "K. Verity MPIA / N. Aldridge (Heritage)", "pages": 28,
        "purpose": "For Development Application",
        "contents": [
            "Historical context — Newtown/Enmore Heritage Conservation Area",
            "Physical description and significance of No. 41",
            "Statement of significance",
            "Description of the proposed works",
            "Assessment against the Inner West DCP heritage controls",
            "Impact on the significance of the conservation area",
            "Streetscape and first-floor setback analysis",
            "Comparative analysis — precedent additions in Georgina Street",
            "Recommendations and conclusion",
        ],
    },
    {
        "number": "BCA-001", "title": "BCA / NCC Compliance Statement", "rev": "A",
        "date": "2025-11-07", "firm": "Meridian Building Certifiers", "abn": "26 883 419 507",
        "author": "H. Meridian — Registered Certifier BDC2871", "pages": 18,
        "purpose": "For Development Application",
        "contents": [
            "Building classification — Class 1a",
            "NCC 2025 Volume Two — applicable provisions",
            "Part H1 Structure",
            "Part H2 Damp and weatherproofing",
            "Part H3 Fire safety — separating wall to No. 43",
            "Part H4 Health and amenity",
            "Part H5 Safe movement and access — stairs and balustrades",
            "Part H6 Energy efficiency",
            "Part H7 Ancillary provisions — swimming pool barriers",
            "Deemed-to-Satisfy assessment and matters for resolution at CC",
        ],
    },
    {
        "number": "ACC-001", "title": "Access Statement", "rev": "A",
        "date": "2025-11-07", "firm": "Meridian Building Certifiers", "abn": "26 883 419 507",
        "author": "H. Meridian — Registered Certifier BDC2871", "pages": 8,
        "purpose": "For Development Application",
        "contents": [
            "Scope and applicable standards",
            "Building classification and applicability of AS 1428.1",
            "Class 1a — statutory access provisions not triggered",
            "Livable Housing Design Guidelines — voluntary silver-level assessment",
            "Ground floor entry, circulation and sanitary facility",
            "Recommendations",
        ],
    },
    {
        "number": "BSX-001", "title": "BASIX Certificate — No. 2026/418877S", "rev": "A",
        "date": "2025-06-16", "firm": "Solaris Sustainability", "abn": "35 771 204 839",
        "author": "E. Solaris — BASIX Assessor ABSA 41190", "pages": 6,
        "purpose": "For Development Application",
        "contents": [
            "Certificate details and commitments",
            "Water — target 40, achieved 42",
            "Thermal comfort — target pass, achieved pass",
            "Energy — target 50, achieved 54",
            "Schedule of commitments to be shown on DA and CC plans",
        ],
    },
    {
        "number": "ESD-001", "title": "ESD and Thermal Performance Report", "rev": "A",
        "date": "2025-06-16", "firm": "Solaris Sustainability", "abn": "35 771 204 839",
        "author": "E. Solaris — BASIX Assessor ABSA 41190", "pages": 22,
        "purpose": "For Development Application",
        "contents": [
            "Environmentally sustainable design strategy",
            "Passive design — orientation, cross ventilation, northern glazing",
            "NatHERS simulation results and star rating",
            "Building fabric — insulation, glazing and thermal bridging",
            "All-electric strategy — gas disconnection and induction cooking",
            "Reverse-cycle system efficiency and zoning",
            "Rainwater reuse and water-efficient fixtures",
            "Materials, embodied carbon and construction waste",
            "Commitments carried to BASIX certificate 2026/418877S",
        ],
    },
    {
        "number": "SUR-001", "title": "Detail and Level Survey", "rev": "A",
        "date": "2025-03-30", "firm": "Larkin & Vale Surveyors", "abn": "47 116 682 390",
        "author": "M. Vale — Registered Surveyor NSW 3117", "pages": 2,
        "purpose": "For Information",
        "contents": [
            "Survey plan — boundaries, levels, existing structures",
            "Adjoining building footprints — No. 39 and No. 43",
            "Services located — sewer, water, stormwater, electricity",
            "Datum and control notes",
        ],
    },
    {
        "number": "GEO-001", "title": "Geotechnical Investigation Report", "rev": "A",
        "date": "2025-04-28", "firm": "Stratum Geotechnical", "abn": "68 550 271 194",
        "author": "F. Okonkwo — CPEng 4118826", "pages": 24,
        "purpose": "For Information",
        "contents": [
            "Scope of investigation and methodology",
            "Site geology — Ashfield Shale, Wianamatta Group",
            "Borehole logs BH1 and BH2",
            "Existing footing exposure — pier and beam, sandstone rubble",
            "Site classification to AS 2870 — Class M",
            "Foundation recommendations for the first-floor addition",
            "Underpinning requirements at the party wall",
            "Excavation, shoring and groundwater",
        ],
    },
    {
        "number": "ARB-001", "title": "Arboricultural Impact Assessment", "rev": "A",
        "date": "2025-05-15", "firm": "Canopy Arboriculture", "abn": "92 338 715 460",
        "author": "R. Sandoval — AQF Level 5 Arborist", "pages": 14,
        "purpose": "For Development Application",
        "contents": [
            "Scope and methodology to AS 4970",
            "Tree schedule — 3 trees assessed",
            "T1 Jacaranda mimosifolia, No. 43 rear, retained",
            "T2 Callistemon viminalis, subject site, to be removed",
            "T3 Backhousia citriodora, subject site, retained",
            "Tree protection zones and structural root zones",
            "Impact assessment and tree protection measures",
            "Replacement planting recommendations",
        ],
    },
    {
        "number": "SWM-001", "title": "Stormwater Management Report", "rev": "B",
        "date": "2025-06-05", "firm": "Catchment Civil & Hydraulic", "abn": "88 315 720 946",
        "author": "S. Basu — CPEng 3980114", "pages": 16,
        "purpose": "For Development Application",
        "contents": [
            "Existing drainage regime and site constraints",
            "Inner West Council stormwater policy compliance",
            "Impervious area calculation — existing and proposed",
            "On-site detention sizing — 4.2 m³ required",
            "Rainwater tank and reuse strategy",
            "Discharge control pit and connection to kerb",
            "Erosion and sediment control during construction",
        ],
    },
    {
        "number": "WMP-001", "title": "Waste Management Plan", "rev": "A",
        "date": "2025-06-19", "firm": "Bower Lane Architecture", "abn": "62 471 903 118",
        "author": "T. Okafor", "pages": 6,
        "purpose": "For Development Application",
        "contents": [
            "Demolition waste — estimated volumes and destinations",
            "Construction waste — segregation and recycling targets",
            "Salvage and reuse — bricks, roof sheeting, joinery",
            "Ongoing operational waste and bin storage",
            "Site waste management responsibilities",
        ],
    },
    {
        "number": "QS-001", "title": "Cost Summary Report for Development Application", "rev": "A",
        "date": "2025-06-22", "firm": "Redwood Cost Consulting", "abn": "13 927 604 815",
        "author": "G. Redwood — AIQS MAIQS 22841", "pages": 4,
        "purpose": "For Development Application",
        "contents": [
            "Development cost summary — Inner West Council format",
            "Estimated development cost $750,000 excluding GST",
            "Basis of estimate and exclusions",
            "Quantity Surveyor's certification",
        ],
    },
]


def title_block(discipline: str, number: str, title: str, rev: str,
                scale: str, date: str, purpose: str) -> str:
    firm = FIRMS[discipline]
    history = REVISION_HISTORY[rev]
    rows = "\n".join(
        f"| {r} | {d} | {note} |" for r, d, note in history
    )
    return f"""# {number} — {title}

**{DISCIPLINE_LABEL[discipline]} drawing · {firm['name']}**

---

## Title block

| | |
| --- | --- |
| **Project** | {PROJECT} |
| **Scope** | {SCOPE} |
| **Client** | {CLIENT} |
| **Drawing title** | {title} |
| **Drawing number** | **{number}** |
| **Revision** | **{rev}** |
| **Discipline** | {DISCIPLINE_LABEL[discipline]} |
| **Scale** | {scale} |
| **Sheet size** | A1 |
| **Date** | {date} |
| **Issue purpose** | {purpose} |
| **Job number** | {firm['job']} |
| **Drawn** | {firm['drawn']} |
| **Checked** | {firm['checked']} |
| **Nominated** | {firm['nominated']} |

## Consultant

**{firm['name']}**
ABN {firm['abn']}
{firm['address']}

## Revision history

| Rev | Date | Description |
| --- | --- | --- |
{rows}

---

*Drawing sheet content is not reproduced. This document exists to carry the title block
into the project document register. Do not read design information from it.*

*Do not scale from this drawing. Figured dimensions take precedence. All dimensions to be
verified on site prior to fabrication or construction.*

© {firm['name']} — issued for the named project only.
"""


def report_doc(spec: dict) -> str:
    contents = "\n".join(f"{i}. {item}" for i, item in enumerate(spec["contents"], 1))
    return f"""# {spec['number']} — {spec['title']}

**{spec['firm']}**

---

## Document control

| | |
| --- | --- |
| **Project** | {PROJECT} |
| **Scope** | {SCOPE} |
| **Client** | {CLIENT} |
| **Document title** | {spec['title']} |
| **Document number** | **{spec['number']}** |
| **Revision** | **{spec['rev']}** |
| **Date** | {spec['date']} |
| **Issue purpose** | {spec['purpose']} |
| **Prepared by** | {spec['author']} |
| **Pages** | {spec['pages']} |

## Author

**{spec['firm']}**
ABN {spec['abn']}

## Contents

{contents}

---

*Report body is not reproduced. This document exists to carry document-control information
into the project document register. Do not read technical findings from it.*

© {spec['firm']} — issued for the named project only.
"""


def register() -> str:
    """The master document register — the artefact the repository should reproduce."""
    parts = [
        "# Document Register",
        "",
        f"**Project** {PROJECT}",
        f"**Scope** {SCOPE}",
        f"**Client** {CLIENT}",
        "**Register date** 2026-08-07 — construction underway, month 7",
        "",
        "Generated by `generate.py`. Do not hand-edit — change the source lists and re-run.",
        "",
        "This is the answer key. After the drawings and reports are uploaded, the project's",
        "document repository should reproduce these rows: number, title, revision, discipline,",
        "issue purpose and author. Anything the repository gets wrong here is a real defect.",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Discipline | Sheets | Consultant |",
        "| --- | ---: | --- |",
    ]
    for discipline, sheets in DRAWINGS.items():
        parts.append(
            f"| {DISCIPLINE_LABEL[discipline]} | {len(sheets)} | {FIRMS[discipline]['name']} |"
        )
    parts.append(f"| Reports and statements | {len(REPORTS)} | various |")
    total = sum(len(v) for v in DRAWINGS.values()) + len(REPORTS)
    parts.append(f"| **Total** | **{total}** | |")
    parts.extend(["", "---", "", "## Drawings", ""])

    for discipline, sheets in DRAWINGS.items():
        firm = FIRMS[discipline]
        parts.extend([
            f"### {DISCIPLINE_LABEL[discipline]} — {firm['name']}",
            "",
            f"Job number `{firm['job']}` · ABN {firm['abn']}",
            "",
            "| Number | Title | Rev | Scale | Date | Issue purpose |",
            "| --- | --- | :---: | --- | --- | --- |",
        ])
        for number, title, rev, scale, date, purpose in sheets:
            parts.append(
                f"| `{number}` | {title} | **{rev}** | {scale} | {date} | {purpose} |"
            )
        parts.append("")

    parts.extend(["---", "", "## Reports and statements", "",
                  "| Number | Title | Rev | Date | Author | Issue purpose |",
                  "| --- | --- | :---: | --- | --- | --- |"])
    for spec in REPORTS:
        parts.append(
            f"| `{spec['number']}` | {spec['title']} | **{spec['rev']}** | "
            f"{spec['date']} | {spec['firm']} | {spec['purpose']} |"
        )

    parts.extend([
        "",
        "---",
        "",
        "## DA submission pack — 26 June 2025",
        "",
        "What actually went to Inner West Council. Everything at `For Development Application`",
        "at revision current on the lodgement date.",
        "",
        "| Item | Documents |",
        "| --- | --- |",
        "| Architectural drawings | `A-000` to `A-700` — 18 sheets |",
        "| Structural drawings | `S-001` to `S-201` — 6 sheets |",
        "| Civil / stormwater drawings | `C-001` to `C-300` — 5 sheets |",
        "| Statement of Environmental Effects | `SEE-001` Rev B |",
        "| Heritage Impact Statement | `HIS-001` Rev B |",
        "| BASIX Certificate | `BSX-001` — certificate 2026/418877S |",
        "| ESD and Thermal Performance Report | `ESD-001` Rev A |",
        "| Stormwater Management Report | `SWM-001` Rev B |",
        "| Arboricultural Impact Assessment | `ARB-001` Rev A |",
        "| Waste Management Plan | `WMP-001` Rev A |",
        "| Cost Summary Report | `QS-001` Rev A |",
        "| Survey | `SUR-001` Rev A |",
        "",
        "**Not in the DA pack** — issued later or for information only:",
        "",
        "- `A-900`, `A-901`, `S-300` — construction details, issued 21 November 2025",
        "- All hydraulic (`H-`), electrical (`E-`) and mechanical (`M-`) drawings — trade",
        "  design, issued for construction in November 2025 with the CC",
        "- `BCA-001`, `ACC-001` — certifier documents, issued 7 November 2025",
        "- `GEO-001` — informed the structural design, not a council requirement here",
        "",
        "---",
        "",
        "## Revision status at register date",
        "",
        "| Rev | Meaning | Sheets |",
        "| :---: | --- | ---: |",
    ])
    rev_counts: dict[str, int] = {}
    for sheets in DRAWINGS.values():
        for _, _, rev, _, _, _ in sheets:
            rev_counts[rev] = rev_counts.get(rev, 0) + 1
    meanings = {
        "A": "First issue — coordination and client comment",
        "B": "Second issue — client comments incorporated, DA coordination",
        "C": "Third issue — heritage setback revised, lodged with Council",
    }
    for rev in sorted(rev_counts):
        parts.append(f"| **{rev}** | {meanings[rev]} | {rev_counts[rev]} |")

    parts.extend([
        "",
        "---",
        "",
        "## Notes on this corpus",
        "",
        "- **Title blocks only.** No sheet carries real design content. The register is the",
        "  deliverable; the drawings exist to populate it.",
        "- **Hydraulic, electrical and mechanical are trade-designed.** On a job this size that",
        "  is normal — the trades design and certify their own work under the head contract.",
        "  It is also why there are no fee proposals or invoices for those three disciplines.",
        "- **Five DA-support consultants have documents but no fee proposals in this corpus** —",
        "  Larkin & Vale, Stratum, Canopy, Solaris and Redwood. That gap is deliberate and",
        "  realistic: their reports are on file, their engagements are not evidenced. The PMP",
        "  should say so rather than assume appointment.",
        "- **`A-000` is a register sheet inside a register.** That is correct practice and a",
        "  good test of whether ingest handles it without double-counting.",
        "",
        "All firms, people, ABNs, registration numbers and certificate numbers are fabricated.",
    ])
    return "\n".join(parts) + "\n"


def slug(text: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in text]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def main() -> None:
    drawings_dir = ROOT / "drawings"
    reports_dir = ROOT / "reports"
    for directory in (drawings_dir, reports_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    count = 0
    for discipline, sheets in DRAWINGS.items():
        sub = drawings_dir / discipline
        sub.mkdir()
        for number, title, rev, scale, date, purpose in sheets:
            path = sub / f"{number}-{slug(title)}.md"
            path.write_text(
                title_block(discipline, number, title, rev, scale, date, purpose),
                encoding="utf-8",
            )
            count += 1

    for spec in REPORTS:
        path = reports_dir / f"{spec['number']}-{slug(spec['title'])}.md"
        path.write_text(report_doc(spec), encoding="utf-8")
        count += 1

    (ROOT / "document-register.md").write_text(register(), encoding="utf-8")

    print(f"wrote {count} documents + document-register.md")
    print(f"  drawings: {sum(len(v) for v in DRAWINGS.values())}")
    print(f"  reports:  {len(REPORTS)}")


if __name__ == "__main__":
    main()
