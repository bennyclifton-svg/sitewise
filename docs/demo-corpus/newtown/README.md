# Newtown Demo Corpus — run sheet

**Purpose.** A synthetic but internally consistent document set for one residential project,
built so the project can be established end-to-end in SiteWise and screenshotted for the
cockpit animation.

**Everything here is fabricated.** Firms, people, ABNs, licence and registration numbers,
SKUs and prices are invented. Brand names are deliberately fictional so no real product's
specification is misrepresented. The street exists; the property, the owners and every
document do not. Nothing here should be presented as a real customer, quotation or product.

---

## The project

| | |
|---|---|
| **Address** | 41 Georgina Street, Newtown NSW 2042 |
| **Owners** | Daniel and Anthea Marchetti |
| **Property** | Semi-detached single-storey cottage, c. 1908, attached to No. 43 on the eastern boundary |
| **Site area** | 232 m² · 6.4 m frontage × 36.2 m depth |
| **Existing GFA** | 88 m² · 2 bed, 1 bath |
| **Proposed GFA** | 175 m² · net addition 87 m² |
| **Scheduled area** | 261 m² — includes 86 m² of external space |
| **Work** | Ground-floor rear extension + first-floor addition |
| **Class / subclass / work type** | residential / house (Class 1a) / **extend** |
| **Scale band** | S · $250k–$2m |
| **Construction budget** | $750,000 excl GST · owner ceiling $950,000 all-in |
| **Contract sum** | $748,900 excl GST — Halden Building Co |
| **Planning pathway** | **DA** — Inner West Council · DA/2025/0418, approved 30 Sept 2025 |
| **Controls** | Newtown/Enmore Heritage Conservation Area · IWLEP 2022 · IWDCP 2023 |
| **Status at register date** | Construction month 7 of 12 |

**Why DA, not CDC.** The site is inside the Newtown/Enmore Heritage Conservation Area, and
land in an HCA is excluded from complying development under the Codes SEPP. A second-storey
addition here is a DA, with a Heritage Impact Statement. This matters because the audience
for the finished animation is Australian planners, architects and PMs — the one group
guaranteed to notice if it were wrong.

**Why this project type.** It is the most common serious residential job in inner Sydney and
it legitimately triggers five appointed consultants, six drawing disciplines, a heritage
overlay, a party wall, a structural investigation of unknown footings and on-site detention.
Small enough to read on one screen; complex enough to earn a real PMP.

**Why construction is underway.** Consultant fees are only fully drawn once the
construction phase has been invoiced. Setting "now" at month 7 of the build gives a cost
plan with real committed *and* actual figures, and gives the invoice-reconciliation beat
somewhere to land.

---

## Timeline

Every document in the corpus is dated against this. Keep it when entering the project.

| Date | Event |
|---|---|
| 2025-03-02 | Project started from a one-line prompt |
| 2025-03-03 | Profile corrected by owner; PMP v1 |
| 2025-03-05 | RFP issued — architectural services |
| 2025-03-18 | **Owner's Project Brief** issued → accommodation schedule expands, PMP v2 |
| 2025-03-20 | Three architectural fee proposals received |
| 2025-03-27 | Bower Lane Architecture appointed |
| 2025-04-02 | RFPs issued — planning, structural, civil/stormwater, certification |
| 2025-04-17 | Three fee proposals received per discipline |
| 2025-04-24 | Four consultants appointed |
| 2025-05-02 | Footing exposure — sandstone rubble at 410 mm, underpinning confirmed |
| 2025-05-21 | Pre-DA meeting, Inner West Council |
| 2025-06-19 | DA drawing set issued at Rev C — heritage setback revised to 1.8 m |
| 2025-06-26 | **DA/2025/0418 lodged** |
| 2025-09-30 | DA approved, 34 conditions |
| 2025-10-15 → 17 | Three builder quotations received |
| 2025-11-14 | **Halden Building Co appointed** — $748,900 |
| 2025-11-21 → 28 | Construction documentation and trade drawings issued |
| 2025-12-05 | CC/2025/1188 issued |
| 2026-01-19 | Construction commences |
| 2026-08-15 | **Now** — month 7 |

---

## Folder map

```
00-prompts/            six chat prompts, in order — start here
01-brief/              Owner's Project Brief — the document that expands the schedule
02-fee-proposals/      15 proposals, 3 per discipline          [generated]
03-invoices/           16 invoices drawing the full fee        [generated]
04-builder-quotes/     3 quotations + comparison answer key
05-product-data/       3 product documents for FFE extraction
06-design-documents/   47 drawings + 12 reports + register     [generated]

generate-commercial.py    rebuilds 02- and 03-
06-design-documents/generate.py    rebuilds drawings, reports and the register
```

Both generators assert their own arithmetic and are safe to re-run.

---

## Run order

Each step is a screenshot opportunity. **Capture** notes what the animation needs from it.

| # | Action | Input | Capture |
|---|---|---|---|
| 1 | New project. Paste the kick-off prompt. | [`01-kickoff`](00-prompts/01-kickoff.md) | Empty cockpit → profile resolving field by field, GFA staying empty |
| 2 | Correct the profile by hand. Add the plunge pool. | [`02-profile-corrections`](00-prompts/02-profile-corrections.md) | Taxonomy picker, user override, scheduled area = 12 m² |
| 3 | Run **Create PMP**. | — | Scaffold-first build; `Assumption` / `Not evidenced` rows |
| 4 | Run consultant RFP — Architect. | — | Draft landing in `02-consultant/` |
| 5 | Upload the Owner's Project Brief. | [`owners-project-brief`](01-brief/owners-project-brief.md) | Ingest strip; routing to `00-brief-pmp/` |
| 6 | Lodge the accommodation schedule. | [`03-brief-uploaded`](00-prompts/03-brief-uploaded.md) | **5 rows → 26. Scheduled area 12 m² → 261 m².** The centrepiece |
| 7 | Run **Update PMP**. | — | `Assumption` upgrading; consultant rows correctly *not* upgrading |
| 8 | Run consultant RFPs — planning, structural, civil, certification. | — | Four drafts stacking |
| 9 | Upload all 15 fee proposals. | [`02-fee-proposals/`](02-fee-proposals/) | Bulk ingest → `05-procurement/quotes/` |
| 10 | Compare fees per discipline. | [`04-fee-comparison`](00-prompts/04-fee-comparison.md) | The heritage statement nobody priced |
| 11 | Upload all 59 design documents. | [`06-design-documents/`](06-design-documents/) | **Largest ingest — the repository under load** |
| 12 | Build the document register. | [`06-design-documents`](00-prompts/06-design-documents.md) | 59 rows, six disciplines, three revisions |
| 13 | Upload the three builder quotations. | [`04-builder-quotes/`](04-builder-quotes/) | Tender comparison; the gaps in the thin quote |
| 14 | Upload all 16 invoices. | [`03-invoices/`](03-invoices/) | Invoice register filling; allocations mapping |
| 15 | Run **Create Cost Plan**. | — | Real numbers, real basis column |
| 16 | Upload the three product documents. | [`05-product-data/`](05-product-data/) | Ingest |
| 17 | Extract FFE items from each. | [`05-ffe-extraction`](00-prompts/05-ffe-extraction.md) | FFE schedule filling with SKUs and models |

---

## The two schedule states

Step 6 is the centrepiece. The accommodation schedule goes from what one sentence can
support to what a real brief supports.

**After step 2 — five rows**

| Space | Level | Area | Characteristics | Status |
|---|---|---|---|---|
| Master Bedroom | First | TBC | TBC | New |
| Parents' Retreat | First | TBC | TBC | New |
| Kitchen | Ground | TBC | TBC | New |
| Living / Dining | Ground | TBC | open plan | New |
| Plunge Pool | External | 12 m² | rear courtyard | New |
| **Scheduled area** | | **12 m²** | | |

**After step 6 — 26 rows**

| | Before | After |
|---|---|---|
| Rows | 5 | 26 |
| Rows with a parseable area | 1 | 26 |
| Demolished spaces captured | 0 | 5 |
| External spaces captured | 1 | 4 |
| **Scheduled area** | 12 m² | **261 m²** |

Composition of the 261 m²: 43 m² retained + 60 m² new ground + 72 m² first floor + 86 m²
external. The 45 m² of `Demolished` space is recorded but excluded. GFA is 175 m² — the
schedule is not a floor area calculation and should not be reconciled against the profile's
`gfa_sqm`.

That contrast is the most valuable frame in the exercise, and it needs no narration: a
column of five sparse `TBC` rows becomes a full schedule with a real total. A sketch
becoming a brief.

---

## How the money reconciles

### Consultants — appointed

| Discipline | Firm | Fee excl GST | Invoices |
|---|---|---:|---:|
| Architectural | Bower Lane Architecture | $82,000 | 4 |
| Town Planning | Verity Urban Planning | $9,900 | 3 |
| Structural | Ardent Structural | $11,500 | 3 |
| Civil / Stormwater | Catchment Civil & Hydraulic | $5,800 | 3 |
| Certification | Meridian Building Certifiers | $4,600 | 3 |
| **Total** | | **$113,800** | **16** |

The 16 invoices draw each fee down to **exactly** its proposal total — `generate-commercial.py`
asserts it. If the cost plan does not land on $113,800 excl GST / $125,180 incl GST, ingest
lost something, and it is worth knowing before the capture session.

### Construction

| | excl GST |
|---|---:|
| Owner's construction budget | $750,000 |
| Southbrook Projects — submitted | $712,000 |
| Halden Building Co — submitted, **appointed** | $748,900 |
| Kingsford Bay Constructions — submitted | $792,400 |

**The tender story.** Southbrook is cheapest and has silently omitted the plunge pool, the
OSD tank, scaffolding, all PC sums and the heritage-matched brickwork — $197,700 of scope,
carried by a general exclusion clause rather than stated. Corrected, Southbrook is
$909,700 and the dearest of the three by $117,300. Full workings in
[`tender-comparison-answer-key.md`](04-builder-quotes/tender-comparison-answer-key.md) —
**do not upload it**, the comparison has to find the gaps itself.

---

## Deliberate gaps

Three things are missing on purpose. Each is realistic, and each gives the PMP something
true and slightly uncomfortable to say.

1. **Five consultants have documents but no engagement evidence.** Larkin & Vale (survey),
   Stratum (geotechnical), Canopy (arborist), Solaris (BASIX and ESD) and Redwood (QS).
   Their reports are on file; no fee proposal or invoice exists for any of them. A report
   arriving does not prove anyone was engaged, and the consultant table should hold the
   line on that.

2. **Hydraulic, electrical and mechanical have drawings but no consultant fees.** They are
   trade-designed under the head contract, which is normal at this scale. The drawings are
   authored by the trade contractors, not by an appointed consultant.

3. **Halden's two stated exclusions are unfunded.** Appliances (~$18,000) and soft
   landscaping (~$13,000) sit outside the contract sum and need to appear in the cost plan
   as separately funded owner items. The Milette collection totals $12,950 against the
   $18,000 allowance — the first genuinely good news in the cost plan.

---

## Answer keys — do not upload

- [`04-builder-quotes/tender-comparison-answer-key.md`](04-builder-quotes/tender-comparison-answer-key.md)
- [`06-design-documents/document-register.md`](06-design-documents/document-register.md)
- Everything in [`00-prompts/`](00-prompts/) — these are run instructions with expected
  results, not project evidence

Upload only `01-brief/`, `02-fee-proposals/`, `03-invoices/`, the three quotations in
`04-builder-quotes/`, `05-product-data/`, and `06-design-documents/drawings/` and
`reports/`. That is **97 documents**:

| Source | Documents |
|---|---:|
| Owner's Project Brief | 1 |
| Fee proposals | 15 |
| Invoices | 16 |
| Builder quotations | 3 |
| Product data | 3 |
| Drawings | 47 |
| Reports and statements | 12 |
| **Total** | **97** |
