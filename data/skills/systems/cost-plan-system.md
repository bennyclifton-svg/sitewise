# System: cost-plan

**Purpose:** Prepare, review, or update a project cost plan — including the Excel workbook — using markdown-first review.

The cost plan must be the most complete useful whole-project cost view the active project evidence supports, not merely a restatement of the highest-level budget total.

## When to use

When the PM asks for:
- a project budget allocation;
- a cost-plan structure or review;
- a cost-plan workbook update;
- reconciliation of cost-plan line items with invoices, quotes, fee proposals or tender returns;
- a claim-first cost plan where the PM has received a progress claim before a formal cost workbook exists;
- a cost-plan-backed cost summary, cost-plan refresh, or cost-plan recommendation;
- cost-plan setup that downstream tender comparison or bid levelling will inherit.

## Sequence

For claim-first cost planning, construction cost evidence lives outside `01-cost/` as often as inside it. Include `07-construction/02-fioa-contract/`, `07-construction/05-progress-claims/`, and `07-construction/06-variations/` where contract sums, claim schedules, or variations may define the current construction breakdown.

1. **`atomic/evidence-sweep`** — target folders `01-cost/` and, where variations are relevant, `07-construction/06-variations/`; expected evidence: current cost-plan workbook, prior markdown drafts, fee proposals, POs, consultant appointments, invoices, invoice trackers, variation documents/registers, quotes, tender comparison sheets, brief / PMP / scope notes, and the original detailed Excel template spec if supplied by the PM.

2. **`atomic/seed-targeted-read`** — load `cost-management-principles.md`. Add `procurement-tendering-guide.md` if tender prices feed the plan.

3. Confirm with the PM: advice only, markdown draft only, or markdown → workbook update. **Always default to the review-first workflow** unless the PM explicitly bypasses it.

4. **`atomic/markdown-draft-for-review`** — output to `01-cost/cost_plan_v<NN>.md`. Required sections for this draft type (see also the detailed template spec section below):
   - project name and location;
   - source evidence used;
   - budget reconciliation and control decision where multiple budget, estimate, ballpark, QS, PMP or owner-stated figures are in circulation;
   - total approved or indicative budget;
   - GST status (ex GST / inc GST) — explicit;
   - cost breakdown by category;
   - known contract / appointment values (locked);
   - allowances and contingency (clearly labelled);
   - PM fee treatment (inside or outside the stated project budget);
   - assumptions and exclusions;
   - risks and review questions;
   - authority, compliance, insurance and procurement gates that materially affect budget certainty where evidenced;
   - recommended next steps.

5. **Pause for PM review** of the markdown. Iterate until approved. Do not touch the workbook before approval unless the PM explicitly bypasses the review step.

6. **`atomic/excel-safe-edit`** — drive the workbook update from the approved markdown. When creating a new workbook from scratch, use Python + openpyxl to reproduce the exact v03 structure (see reference implementation below).

7. **`atomic/excel-verify`** — confirm before reporting completion.

## Claim-first construction breakdown rule (mandatory)

This is a normal construction information-flow case, not an exception. A PM may have no pre-existing project cost workbook and still need to certify a claim. In that case, a progress claim, payment claim, contract schedule, schedule of values, accepted quote, or variation roll-up may be the best available construction cost-plan source.

If a progress claim or payment claim contains trade/work-package rows with contract values:
- adopt the latest reliable trade/work-package schedule into the Construction section at useful workbook granularity;
- reconcile the adopted rows to the latest evidenced contract sum and signed variations as far as the evidence allows;
- keep variation rows separate, or clearly note where they are embedded in the revised contract sum;
- record conflicts between claim schedules and variation forms in Cost Evidence Conflicts;
- do not collapse the Construction section to one `Construction contract` line unless the source evidence itself contains no useful breakdown.

If no project workbook and no claim/contract breakdown exists, then use the practice residential construction taxonomy and budget evidence to draft a benchmark framework, clearly labelled as Judgement or Assumption.

## Budget reconciliation and control decision rule (mandatory)

When project evidence contains more than one budget figure, estimate, QS report, builder ballpark, owner expectation, PMP budget note or cost plan total:
- list the material figures together before presenting the cost breakdown;
- for each figure, name the source, amount, GST basis if known, exclusions/qualifications, evidence status, and whether it is adopted, qualified or discarded;
- do not let arithmetic workbook totals obscure a higher-level QS or PMP working budget if the difference is explained by PM fee, escalation, owner-side scope, contingency, or other stated allowances;
- if an independent QS or cost manager provides the authoritative current working budget, state that figure as the cost-control reference even if the itemised workbook rows require review/reconciliation;
- itemise the cost buckets that explain any gap between the owner expectation and the realistic working figure;
- frame any material affordability gap as a Principal/owner decision: increase budget, reduce scope, phase works, or pause/reassess.

## Authority and procurement gate rule (mandatory)

For residential cost plans, include non-price gates that materially affect cost certainty where project evidence supports them:
- planning pathway corrections, such as CDC misinformation later superseded by DA-required evidence;
- BAL, tree, wastewater, authority or certifier constraints that drive cost lines;
- HBCF/HOW, state warranty insurance, licence or statutory pre-start gates where contract value thresholds are triggered;
- informal builder advice, open-ended cost-plus proposals, or "skip due diligence" suggestions as governance/procurement risks rather than budget facts;
- geotechnical, structural, hydraulic, wastewater and other consultant appointments that are critical but not yet accepted.

## Processing Incoming Invoices and Variations (mandatory workflow)

When a new invoice or variation document is received, follow this exact 6-step process. Never bypass it. In the Hermes app this is split into two batch actions: **Process Invoices** and **Process Variations**.

### Step 1 — Classify the document
- If it contains an invoice number and/or the text "TAX INVOICE" → treat as **Invoice** → add to Invoices sheet.
- If it contains a variation number and/or the text "VARIATION" → treat as **Variation** → add to Variations sheet.
- If ambiguous or neither, stop and ask the PM.
- Sorting should route invoice-like documents to `01-cost/` and variation-like documents to `07-construction/06-variations/`.

### Step 2 — Extract and map fields
**For Invoices** (append to columns A–I):
- A: Invoice Date (real date)
- B: Company (supplier name)
- C: PO Number
- D: Invoice Number
- E: Invoice Description (the original line description extracted from the invoice)
- F: Cost Item (canonical Summary cost item name — see Step 3)
- G: Amount ex GST (`#,##0`)
- H: Billing Month (real date representing the invoice/billing month, formatted as `mmm-yy`)
- I: Paid? (`No` by default)

**For Variations** (append to columns A–G):
- A: Date Submitted (real date)
- B: Cost Item (canonical name — see Step 3)
- C: Variation To (supplier name)
- D: Status (`Approved` or `Pending`)
- E: Amount (claimed ex GST)
- F: Date Approved (blank if Pending)
- G: Approved Amount (blank if Pending)

### Step 3 — Resolve the Cost Item name (critical)
The Summary lookups are **Cost Item text based**. Cost Code is only a display/order aid and must not be treated as the durable linkage key.

Resolution rules:
- If the document allocation names an existing Summary Cost Item exactly, use that exact text.
- Before generic fuzzy matching, run a deterministic residential/common-building synonym pass against the active Summary Cost Items. The match must return the exact Summary label, not a new label.
- If the allocation only partially matches, use fuzzy matching to choose the best existing Cost Item. Prefer a plausible match because the PM will review the register.
- Preserve the original invoice line text in `Invoice Description`; do not overwrite it with the mapped Cost Item.
- Use source-category gating before fuzzy matching: consultant invoices should only compete against consultant cost items, builder/trade invoices should only compete against construction cost items, and regulatory/authority charge lines may map to fees and charges. Direct discipline words such as architect, civil, structural and surveyor should map to the matching consultant line where that line exists.
- For concise residential Summary labels, use the established alias families:
  - planning/DA/CDC/council lodgement -> `Planning fees`;
  - certifier/PCA/construction certificate/occupation certificate/stage inspections -> `Certifier fees`;
  - HBCF/home building compensation/LSL/statutory levies -> `Levies and statutory`;
  - architect contract administration/RFIs/site meetings/variation review -> `Architect PM`;
  - site establishment/temporary fencing/erosion/excavation/spoil/demolition -> `Siteworks`;
  - reinforcement/concrete/formwork/footings/slab/piers -> `Footings and slab`;
  - frames/trusses/structural steel/lintels/beams -> `Framing`;
  - roofing/windows/glazing/cladding/garage doors/scaffold/flashings -> `External envelope`;
  - electrical/plumbing/drainage/mechanical/hot water rough-ins -> `Building services`;
  - plasterboard/internal doors/architraves/skirting -> `Partitions and doors`;
  - wet area waterproofing/tapware/sanitary fittings -> `Kitchen and bathrooms`;
  - kitchen or laundry joinery/cabinetry/benchtops -> `Joinery`.
- If the active workbook uses different wording from these examples, map to the active workbook label that represents the same scope. Do not force the example label into the workbook.
- If no useful match exists, still post the register row and use `Unidentified` as the Cost Item. `Unidentified` must not be added to Summary, so it will not roll up until the user corrects it.
- If one invoice or variation covers multiple Cost Items, post one register row per Cost Item allocation. Repeat the invoice or variation reference on each row.

### Step 4 — Check for duplicates
- **Invoices**: Invoice Number alone is not a duplicate key because one invoice can produce multiple allocation rows. Match on Company + Invoice Number + Invoice Description + Amount + Cost Item. If the existing row differs, show both versions to the PM.
- **Variations**: Match on the combination of Date Submitted + Cost Item + Variation To + Amount. If a match exists and the document now shows it as Approved, update the existing row in place (Status, Date Approved, Approved Amount) rather than adding a new row.

### Step 5 — Append the row
- Add the new row in the first empty row after the header (do not leave gaps).
- Keep normal register formatting: white cells, black text, date columns as dates and amount columns as `#,##0`.
- If the new row exceeds the current formula ranges in Summary, widen every affected formula range consistently while keeping the `$` anchors.
- After processing, move invoice source documents into `01-cost/invoices/<discipline>/` using the file name pattern `YYYY-MM - <invoice number> - <company>.md`. Create the discipline subfolder when it does not exist. Use the same discipline folder names as consultant and design intake (`architect`, `structural`, `civil`, `hydraulic`, `geotechnical`, `bushfire-consultant`, `arborist`, `energy-assessor`, `quantity-surveyor`, `surveyor`, `certifier`, `town-planner`, and the other standard SiteWise discipline slugs). For head-contractor or trade invoices, use `builder`. Infer discipline from supplier name, invoice headings, allocation descriptions, and the mapped **Cost Item** column — not from invoice number alone. Reserve `01-cost/invoices/unknown/` only when none of that evidence supports a confident discipline. Keep variation source documents under `07-construction/06-variations/VAR-### - <short description>/`.

### Step 6 — Recalculate and verify
After saving:
- Confirm the Cost Item name matches a Summary item exactly.
- For an invoice: Claimed to Date includes invoice rows with Billing Month up to and including the Summary selected month; This Month includes only rows whose Billing Month equals the selected month.
- For an approved variation: Approved Variations increased and Grand Total updated.
- For a pending variation: Forecast Variations increased, while Approved Variations remains unchanged.
- No formula errors (`#REF!`, `#VALUE!`, `#NAME?`, `#DIV/0!`).
- Report a one-line summary (sheet, row, item, amount) and flag any uncertainty.

**GST rule**: Always use the ex-GST subtotal. If only a GST-inclusive total is shown, divide by 1.1 and note that the amount was derived.

## Detailed Excel Template Spec (authoritative)

When the PM supplies the long-form "Recreate the Cost Plan workbook" prompt, the following rules apply in addition to the v03 framework:

- **K5 month selector**: Must be a real date (1st of the reporting month), formatted `mmm yy`, pale-yellow fill, with a dropdown sourced from the invoice register's `Billing Month` values via the `InvoiceBillingMonths` named range. This cell drives both Claimed to Date and This Month.
- **Summary formulas** must use the exact pattern from the template:
  - Forecast Variations (F): pending/unapproved amounts from the Variations sheet, keyed by Cost Item.
  - Approved Variations (G): approved amounts from the Variations sheet, keyed by Cost Item.
  - Forecast Final Cost (H): `=SUM(E{row}:G{row})`
  - Budget Variance (I): `=E{row}-H{row}`
  - Claimed to Date (J): `=SUMIFS(Invoices!$G$5:$G$500,Invoices!$F$5:$F$500,C{row},Invoices!$H$5:$H$500,"<="&EOMONTH(K$3,0))`
  - This Month (K): `=SUMIFS(Invoices!$G$5:$G$500,Invoices!$F$5:$F$500,C{row},Invoices!$H$5:$H$500,">="&EOMONTH(K$3,-1)+1,Invoices!$H$5:$H$500,"<="&EOMONTH(K$3,0))`
  - Remaining (L): `=D{row}-J{row}`
- Group layout: keep the group order as Fees and charges, Consultants, Construction, then Contingency / allowances. Each group gets its own subtotal row immediately after its cost items, and Grand Total sums the subtotal rows. Row numbers may grow with the project cost-item list.
- Invoices sheet must include columns `Invoice Description`, `Billing Month` and `Paid?` in addition to invoice identity, supplier, cost item and amount fields.
- Data validation on Invoices!F5:F500 and Variations!B5:B500 must be kept in sync with Summary Cost Items.
- Data validation on Summary!K3 must be kept in sync with the distinct Billing Month values in the invoice register.
- Never hardcode values into formula cells. Only D and E on Summary (plus raw data rows on Invoices/Variations) are inputs.

The reference implementation `Cost_Plan_v03.xlsx` (project 0777) was built using this combined spec + review-first workflow.

## Cost_Plan_v03 Structural Framework Contract (mandatory)

**Reference implementation:** `04-projects/0777-city-tower-fitout/01-cost/Cost_Plan_v03.xlsx`

Every cost plan workbook (new project or amendment) MUST preserve this exact framework. This contract has higher authority than older templates (e.g. v00).

### Workbook structure (non-negotiable)
- Exactly **3 tabs** in this order with these exact names:
  1. `Summary`
  2. `Invoices`
  3. `Variations`
- No additional sheets, no renamed tabs, no reordering.

### Summary tab — exact structure
- Row 1: `Project Cost Plan - {project title}` (merged A1:L1).
- Row 2: `All figures exclude GST` (merged A2:L2). Do not repeat the project name, project path, or draft/source filename on the Summary tab.
- Row 3: selected billing month control in `K3` only (dropdown fed by hidden invoice billing-month lookup).
- Row 4: **Exact header names** (12 columns):
  `Cost Code | Category | Cost Items | Budget | Approved Contract | Forecast Variations | Approved Variations | Forecast Final Cost | Budget Variance | Claimed to Date | This Month | Remaining`
- Data rows begin at row 5.
- **Cross-sheet formulas** must follow the Detailed Excel Template Spec section above. Extend ranges to `$B$5:$B$50` / `$E$5:$E$100` etc. when data volume requires it.
- Use compact Summary widths: A 10, B 17, C 30, D-J 11, K 10, L 11. Keep title merges on A1:L1 and A2:L2 only.
- Export provenance belongs in the Markdown draft only, not in the workbook Summary tab.

### Invoices tab — exact structure
- Rows 1–2: Title block (merged A1:I2).
- Row 4: **Exact headers**:
  `Invoice Date | Company | PO Number | Invoice Number | Invoice Description | Cost Item | Amount | Billing Month | Paid?`
- Data validation (list type) on **Cost Item column (F5:F500)** containing the exact list of Cost Items from the Summary tab (must remain synchronised).
- `Billing Month` (H) is a real Excel month date formatted `mmm-yy`; `Paid?` (I) uses literal "Yes"/"No" strings.

### Variations tab — exact structure
- Rows 1–2: Title block (merged A1:H2).
- Row 4: **Exact headers** (7 columns):
  `Date Submitted | Cost Item | Variation To | Status | Amount | Date Approved | Approved Amount`
- `Cost Item` (column B) values must match Summary for reliable SUMIF linking.

### Linking & data integrity rules
- All inter-tab links use the SUMIF/SUMIFS patterns above with Cost Item as the key.
- When extending data rows, extend the formula ranges proportionally.
- Never delete or alter existing data validations.
- Never change header text (even minor wording or capitalisation).
- This framework supersedes the v00 template (different tab names, "Description/Role", different column order).

### Cost Item naming policy
- Treat `Cost Items` as workbook lookup labels, not descriptions. Keep them short, stable, and easy to scan.
- Prefer 2-5 word labels. Use the template vocabulary where it fits, for example `AUTHORITIES FEES`, `HOW & LSL`, `CONSULTANTS`, `SURVEYORS`, `EARTHWORKS`, `CONCRETE WORKS`, `JOINERY`, `HYDRAULIC SERVICES`, `ELECTRICAL SERVICES`, `SOFTSCAPE`, and `CLEANING`.
- Adapt the vocabulary to the project archetype rather than forcing the house template onto every project.
- Choose labels that downstream invoices can naturally match. For residential work, prefer compact labels such as `Preliminaries`, `Siteworks`, `Footings and slab`, `Framing`, `External envelope`, `Partitions and doors`, `Kitchen and bathrooms`, `Building services`, `Joinery`, and `Landscaping works` over long descriptive sentences.
- Do not put inclusions, exclusions, pathway notes, `TBC`, `allowance`, `allocated`, benchmark status, or engagement status in the `Cost Items` label. Put that detail in notes, basis, assumptions, review questions, or status.
- Avoid brackets, slashes, dash qualifiers, colons, and semicolons in generated `Cost Items` unless the wording is copied from direct project cost evidence.

## Pre-issue review checks

Before issuing cost advice or a workbook update, confirm:

- Is the total budget approved, indicative, or only assumed?
- Are PM fees included in or excluded from the stated project budget?
- Are known contract values locked before allocating remaining allowances?
- Are allowances clearly labelled?
- Is contingency calculated deliberately, not used as a dumping ground?
- Are invoices reconciled to the same line descriptions used in the Project Summary?
- Are tender returns or quotes based on the same scope?
- Are exclusions, qualifications, and risks clearly stated?
- Has the PM reviewed the markdown before the workbook was touched?
- Was the detailed Excel template spec (if supplied) followed exactly, including the K5 billing-month dropdown and group subtotal ordering?
- Were incoming invoices/variations processed using the 6-step workflow above?

## Must not do

- Commit rough assumptions directly to Excel without a markdown review step (unless explicitly instructed).
- Strip workbook dropdowns or data validations.
- Treat invoice evidence as approved budget without checking appointment / PO context.
- Hide assumptions inside the workbook without noting them in the markdown.
- Overwrite the only copy of a workbook.
- Bypass the review-first workflow unless the PM explicitly authorises it in writing.
- Add an invoice or variation without following the 6-step classification, Cost Item resolution, duplicate check, and verification process.
