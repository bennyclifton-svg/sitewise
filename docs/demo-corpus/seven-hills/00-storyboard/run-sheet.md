# Capture run sheet — Wianamatta Avenue landing proof

**Purpose.** Establish the synthetic Wianamatta Avenue project in SiteWise,
exercise the current product end to end, and capture the minimum frames needed
for the landing page described in [`README.md`](README.md).

This is a product-proof run, not a screen-design exercise. Do not composite a
result that the live application cannot produce.

---

## 1. Non-negotiable capture rules

1. Use **14–18 Wianamatta Avenue, Seven Hills NSW 2147** everywhere. It is
   fictional.
2. Ridgeline Project Management Pty Ltd is the **client-side project manager and Superintendent**.
3. The head contract is **AS 4000 construct-only**. Keep the consultant
   engagements client-side throughout.
4. Pi is the sole agent runtime.
5. All Cost Plan arithmetic comes from software. The $68,500 input comes from
   the QS advice; Pi does not calculate it.
6. All programme dates come from programme operations. The ten-day input comes
   from the consultant coordination note; do not claim critical-path analysis.
7. Any evidence-derived mutation is proposed or explicitly authorised by the
   user. Intake alone does not change the PMP, Cost Plan or programme.
8. Every outbound email remains a draft until the user presses Send.
9. Treat Builder Invoice 04 as an invoice review. Do not show a certified
   progress claim or payment schedule.
10. Capture real interface states with synthetic project data only. Remove
    personal account details, real email addresses and OS watermarks.

---

## 2. Preconditions

Do not begin the public capture until all boxes are true.

- [ ] The complete synthetic corpus is generated and passes its internal date,
      arithmetic and document-register checks.
- [ ] Townhouse support is accepted through both the workflow capability matrix
      and Tender Comparison context adapter.
- [ ] Transmittal-aware Pulse merges S-202 Rev C into the existing structural
      drawing revision item and retains its source thread.
- [ ] Pi can answer a project-evidence question through authorised SiteWise tools.
- [ ] The Cost Plan, programme, consultant appointment, Tender Comparison,
      invoice and email/Pulse paths are green in the capture environment.
- [ ] The email provider is configured for the intended proof. If a seeded/fake
      provider is used, public copy does not imply a live personal mailbox.
- [ ] The fictional Blacktown planning references, version dates and clauses have
      been professionally checked.
- [ ] All three tender groups complete extraction, reconciliation and QA.
- [ ] The OSD finding uses an explicit exclusion or the controlled
      `Not explicitly itemised — confirm with builder` phrase.
- [ ] The QS advice states **$68,500 excluding GST**.
- [ ] The programme note states **10 calendar days** and names programme nodes PRG-210 and PRG-220.
- [ ] Builder Invoice 04 states **VO-007** and the variation is not approved.

---

## 3. Required corpus state

### Project identity

| Field | Required value |
|---|---|
| Address | 14–18 Wianamatta Avenue, Seven Hills NSW 2147 |
| Building class | residential |
| Subclass | townhouses |
| Work type | new |
| State | NSW |
| Storeys | 2 |
| Dwellings | 11 |
| Construction budget | $9,800,000 excluding GST |
| Contract form | AS 4000 construct-only |
| Project manager / Superintendent | Ridgeline Project Management Pty Ltd |
| Tender Comparison region | metro |
| Tender Comparison specification level | mid |

### Register minimums

| Register | Minimum complete state |
|---|---|
| Consultant procurement | 5 disciplines × 3 fee proposals |
| Consultant appointments | 5 separate appointment letters |
| Consultant invoices | 5 invoices × 5 appointed disciplines = 25 |
| Architectural drawings | 20 |
| Civil / stormwater drawings | 5, including C-201 Rev C as the OSD design source |
| Structural drawings | 7, including staged S-202 Rev B and current Rev C |
| Other drawings | 5 each: hydraulic, electrical, mechanical and landscape |
| Builder tenders | 3 whole-of-works bidder groups |
| Builder invoices | Invoices 01–04; Invoice 04 includes unapproved VO-007 |
| Reports | 13 supporting planning, site, cost, design and tender facts |
| Correspondence | inbound/outbound threads for planning, consultant procurement, design transmittal and construction advice |

### The four change-pack attachments

The inbound coordination email used in the final beat must carry or link:

1. `S-202` Rev C — revised OSD base and wall reinforcement, superseding Rev B;
2. `DCN-007` — structural design-change notice describing the revision scope;
3. QS change advice — forecast effect **+$68,500 excluding GST**;
4. consultant programme note — **10 calendar days** for OSD redesign and
   coordination, with a named finish-to-start predecessor.

The documents must agree on the revision, date and scope.

---

## 4. Version choreography

The landing proof requires the construction advice to update **PMP v3 → v4**.
Create that state deliberately:

1. Appoint the first four consultants before the first PMP exists. Those
   appointments update Cost Plan state and shared consultant facts without
   revising a PMP.
2. Ingest the dated planning/approval set, review the 12→11 scheme change, then create
   **PMP v1** from the current project evidence and the four existing appointments.
3. Appoint civil/stormwater last. The appointment patches the Consultants
   register and creates **PMP v2**.
4. Make one legitimate user inline edit, supported by project evidence, to create
   **PMP v3**. Recommended edit: record the evidenced pre-award position—AS 4000–1997
   construct-only is proposed; Ridgeline Project Management is client PM and intended
   Superintendent—citing the client brief and consultant appointment letters.
5. Reserve the S-202 Rev C change pack for the Pi block update that creates **PMP v4**.

If the live system produces different version numbers, stop and resolve the
state. Do not alter a screenshot label.

---

## 5. Capture run order

Each step has one purpose. `Capture` names the frame to keep; routine loading and
intermediate navigation do not need footage.

### Phase A — establish the project

#### 1. Create the synthetic project

Create Wianamatta Avenue and enter the stable identity fields from §3. Keep dwellings at the
12-dwelling acquisition target until the later planning evidence is reviewed.

**Capture `A01-project-profile`**

- fictional address visible;
- `residential · townhouses · new · NSW` visible;
- 12 dwellings labelled as a feasibility target and two storeys visible;
- no real user or client identity in frame.

#### 2. Load the initial planning and briefing evidence

Upload the client brief, pre-DA record and feasibility advice. Import or seed the acquisition
handover email through the configured project-email path so the deposited-plan summary,
title summary, preliminary planning advice and desktop geotechnical advice use canonical
attachment intake. Do not separately upload those four attachments again.

Wait for extraction, classification and filing to finish.

**Capture `A02-intake-register`**

- coherent source filenames and their document dates;
- real SiteWise class/subject labels and filing destinations;
- one low-confidence or user-corrected row if the corpus intentionally contains it;
- no invented confidence percentage.

#### 3. Attach the official planning references

Attach the checked planning instruments through the official-reference path.
Confirm they are labelled official guidance/reference, not project evidence.

**Capture `A03-evidence-planes`**

- the planning advice as project evidence;
- the planning instrument as official reference;
- source labels readable in one frame.

#### 4. Ask Pi to establish the current position

Use:

> Set this project up from the evidence. Show me what is known, conflicted and
> still missing. Do not fill an unsupported field.

Review any profile proposals and accept only those supported by the named
sources. Record the proposed delivery basis and leave execution/authority confirmation open.

**Capture `A04-known-conflicted-missing`**

- one grounded fact;
- one explicit gap or `Not evidenced` field;
- citations/tool trace visible;
- no unsupported planning conclusion.

#### 5. Create the Cost Plan and programme base

Create the Cost Plan from the confirmed project state. Ensure the programme and
its Planning, Procurement and Delivery stages exist. Keep the initial programme
simple; no critical-path or baseline language.

**Capture `A05-controls-base`**

- Cost Plan version and basis column;
- contingency/forecast fields computed by the application;
- three-stage programme with finish-to-start sequencing.

### Phase B — consultant procurement and control

#### 6. Draft the five consultant RFPs

Draft RFPs for architecture, town planning, structural engineering,
civil/stormwater engineering and building services engineering. The civil RFP must cite
the project OSD evidence and require the appropriate design/authority
deliverables.

**Capture `B01-civil-rfp`**

- civil/stormwater scope open at the OSD requirement;
- evidence/source marks visible;
- document shown as a draft.

#### 7. Issue the RFPs through reviewed email

Create the cover emails, review recipients/attachments, and have the user issue
them. Do not imply Pi sent them unattended.

No landing capture is required unless the final email proof needs a matching
outbound visual.

#### 8. Load all 15 fee proposals

Ingest three proposals for each of the five disciplines. Verify their commercial
classification and discipline metadata before appointment.

**Capture `B02-proposal-register`**

- five discipline groups;
- three returns in each group;
- only the civil/stormwater group expanded.

#### 9. Stage and appoint four consultants before creating the PMP

After the user has selected the firms, ingest the separate executed appointment letters for
architecture, town planning, structural engineering and building services engineering.
Appoint from each letter, not from the proposal alone. Confirm each appointment updates
shared consultant facts and the Cost Plan committed fee.

Do not create the PMP yet.

#### 10. Establish the approved planning position and create PMP v1

Ingest all seven files in `05-planning-and-approvals/` in date order. Review the move from
the 12-dwelling DA Rev C position to the approved 11-dwelling Rev D position, including the
120 m³ OSD requirement. Then create the PMP after the four appointments. Confirm its
Consultants register, OSD control, evidence coverage and gaps are grounded in current state.

**Capture `B03-pmp-v1`**

- scaffolded document shape;
- four appointed consultant rows;
- 11 dwellings and 120 m³ OSD supported by the later planning evidence;
- civil/stormwater unresolved or not appointed;
- one OSD source citation.

#### 11. Stage and appoint civil/stormwater last

After the user selects Catchment Works, ingest its separate executed appointment letter.
Appoint from that letter, not from the proposal alone. Verify the single
appointment updates:

- the Cost Plan committed consultant fee;
- the shared civil/stormwater consultant fact;
- the PMP Consultants register, producing PMP v2.

**Capture `B04-one-appointment-three-controls`**

- selected proposal reference;
- firm and excluding-GST fee;
- Cost Plan version;
- `PMP updated · v2` or the equivalent real result.

#### 12. Create PMP v3 with a manual inline edit

Open the PMP and edit the delivery/authority statement inline using the client brief and
consultant appointment letters as evidence. State that AS 4000–1997 construct-only is
proposed and Ridgeline is the client PM and intended Superintendent; do not call it executed
before WD-LOA-001 arrives. Save through the normal block-edit path.

**Capture `B05-inline-edit-v3`**

- the edited block in context;
- the v2 → v3 change/delta if exposed;
- evidence or basis visible;
- no whole-document replacement.

#### 13. Load and process the 25 consultant invoices

Ingest five invoices for each appointed discipline. Process and allocate them
against the relevant consultant Cost Plan items. The invoice series and fee
proposal totals must reconcile according to the corpus answer key.

**Capture `B06-consultant-invoices`**

- `25 invoices` or the exact complete count;
- five discipline/consultant groupings;
- one civil invoice open with source, extracted values and allocation;
- review state kept separate from payment status.

### Phase C — design register and tender

#### 14. Load the baseline drawing and report corpus

Follow Run 1 in the design register: ingest all 13 reports and every current drawing except
S-202 Rev C, then ingest the staged S-202 Rev B baseline sheet in its place. The baseline
therefore has 52 current sheets without leaking the later revision. Wait for drawing
metadata extraction, sheet-title recognition, classification, filing and indexing.

**Capture `C01-drawing-register`**

- discipline counts: at least 20 architectural, 7 structural and 5
  civil/stormwater;
- C-201 Rev C visible;
- S-202 Rev B visible as current at the baseline;
- one representative row open, not a long scroll.

#### 15. Issue the pre-tender drawing transmittal

Select the issued drawing set and draft its transmittal. Review it before issue.

**Capture `C02-transmittal`**

- selected revisions and discipline labels;
- draft state;
- recipient/issue confirmation still required.

#### 16. Load the three whole-builder tenders

Ingest only the three builder tender groups and Redgum clarification at this stage. Include
each bidder's quote and any schedule, exclusions, addendum or clarification needed to interpret that quote.
Do not treat three different trade packages as comparable bidders.

Do **not** ingest the Ironbark letter of acceptance yet; it is outcome evidence.

Save the ordered quote selection and verify the project is ready for Tender
Comparison. Prepare its context with `region=metro` and `spec_level=mid`; do not
leave those required fields implicit.

#### 17. Run Tender Comparison

Use:

> Compare the selected builder tenders.

Let Pi prepare/start the comparison through the authorised Tender Comparison
tools. Complete human QA for every `needs_review` item. Confirm each quote
reconciles or is explicitly flagged.

**Capture `C03-tender-hero`**

- three builder columns;
- OSD row selected;
- the explicit exclusion page or controlled not-itemised phrase;
- no benchmark-derived OSD adjustment.

**Capture `C04-tender-source`**

- source-page highlight;
- quote ledger stated/computed totals;
- provenance visible.

#### 18. Build and approve the Tender Comparison report

Build the report, review the controlled language and approve only after QA is
complete. If the selected tender is handed to the Cost Plan, apply it as the
reviewed proposal the current workflow requires. After the user decision, ingest
WD-LOA-001 as the separate evidence of Ironbark's appointment; arithmetic alone is not
appointment evidence. Then ingest
`08-project-controls/00-IBG-PROG-B01-reviewed-construction-programme.md` and explicitly update the programme to site
possession on 5 May 2026, the accepted 58-week duration and practical completion on
15 June 2027. Confirm PRG-210 and PRG-220 exist before the change beat.

**Capture `C05-tender-report`**

- versioned report draft/approved state;
- comparison matrix and methodology/limits available;
- no builder ranking or motive language.
- reviewed contract programme state with PRG-210 and PRG-220.

### Phase D — construction change proof loop

#### 19. Load Builder Invoices 01–03

Process and allocate the first three builder invoices so the Cost Plan and
invoice register have a credible month-3 baseline. Keep their review/payment
states internally consistent.

No landing capture is required.

#### 20. Deliver the S-202 Rev C coordination email

Import the inbound project email carrying S-202 Rev C, the QS change advice and
the ten-day programme note. Wait for canonical attachment intake and revision
detection.

**Capture `D01-pulse-revision-email`**

- `S-202 Rev C supersedes Rev B`;
- the inbound transmittal/thread merged into the Pulse item;
- `View evidence` and `View thread` actions;
- no automatic PMP, Cost Plan or programme change yet.

#### 21. Inspect the four evidence files

Open the Pulse evidence and verify:

- S-202 is Rev C and supersedes Rev B;
- DCN-007 describes the OSD reinforcement revision;
- QS advice states +$68,500 excluding GST;
- programme note states ten calendar days and the predecessor.
- programme note re-sequences existing successor PRG-220.

**Capture `D02-change-evidence`**

- the four evidence references in one product context;
- no free-typed replacement amount or duration.

#### 22. Authorise the reviewed updates through Pi

Use an explicit mutation request equivalent to:

> From the S-202 Rev C coordination email and its attachments: update the PMP OSD
> control from the cited advice; apply the QS change advice of $68,500 excluding
> GST to the OSD Cost Plan item as a forecast variation; add the evidenced
> 10-calendar-day OSD redesign and coordination activity after civil design; and
> draft a reply confirming the review actions. Do not send it.

Verify each tool result before moving on.

Only after these reviewed updates exist, compare the application-created change record with
`00-answer-keys/reviewed-change-record-chg-007.md`. Do not ingest that control file.

**Capture `D03-pmp-v3-v4`**

- only the relevant addressable block/row changes;
- PMP v3 → v4 visible;
- source citation retained;
- no regenerated whole document.

**Capture `D04-cost-plan-forecast`**

- OSD line selected;
- forecast variation +$68,500 excluding GST;
- approved variation remains zero/unapproved;
- new Cost Plan version and recalculated totals.

**Capture `D05-programme-ten-days`**

- `OSD redesign and coordination` activity;
- duration 10 calendar days;
- PRG-210 predecessor and PRG-220 successor;
- deterministic forecast-completion movement to 25 June 2027;
- contractual practical completion remains 15 June 2027;
- no critical-path label.

**Capture `D06-draft-reply`**

- reply attached to the inbound thread;
- evidence-based summary of the reviewed actions;
- status `Draft`;
- no sent timestamp.

#### 23. User reviews and sends the reply

The user checks recipients, attachments and wording, then presses Send through
the authorised UI path.

**Capture `D07-user-sent-reply`**

- sent status/timestamp;
- actor-visible user action;
- same project thread;
- no implication of unattended sending.

If the capture environment uses a fake provider, keep this frame for internal
proof only unless the landing labels it as a staged demonstration.

#### 24. Deliver Builder Invoice 04 with VO-007

First ingest the dated VO-007 builder request and confirm its status is unapproved. Then
deliver the Progress Claim 04 email and canonical attachment. The claim includes the $68,500
OSD line against VO-007 while VO-007 remains unapproved. Process the invoice and wait for
validation/Pulse.

**Capture `D08-pulse-unapproved-vo`**

- invoice number and builder;
- `VO-007` or unapproved-variation basis;
- $68,500 amount;
- action opens invoice review rather than approving it.

#### 25. Open the invoice review and hold it

Open the three-pane invoice review. Confirm the original invoice, extracted
values, issue and Cost Plan allocation are visible. Choose Hold unless the demo
brief explicitly requires another human decision.

**Capture `D09-invoice-review`**

- original / extraction / allocation context;
- unapproved-variation validation issue;
- Hold / Reject / Approve controls;
- payment status shown separately;
- no payment schedule or Superintendent assessment claim.

### Phase E — closing proof

#### 26. Capture provenance and versions

Open the final PMP and show the OSD citation, evidence coverage or used-by marks.
Make the current version labels legible for PMP, Cost Plan and programme.

**Capture `E01-source-stays-attached`**

- source citation resolves to the project document;
- PMP v4;
- current Cost Plan version;
- current programme version;
- activity/workflow trace available.

This is the closing proof. Do not create a fake seven-surface trace composite.

---

## 6. Landing frame selection

The final page needs only these frames:

| Landing section | Primary capture | Optional supporting crop |
|---|---|---|
| Hero | `C03-tender-hero` | `C04-tender-source` |
| The pile becomes a project | `A02-intake-register` | `A04-known-conflicted-missing` |
| One appointment, three controls | `B04-one-appointment-three-controls` | `B06-consultant-invoices` or `C01-drawing-register` |
| Three tenders, one basis | `C03-tender-hero` | `C05-tender-report` |
| One email, four reviewed updates | `D01-pulse-revision-email` | a compact sequence from `D03`–`D06` |
| Close | `E01-source-stays-attached` | none |

Do not add another landing section merely because a capture is good. Unused
captures become sales-demo or later-film material.

---

## 7. Capture QA

Run one bounded review after all captures are taken.

### Factual consistency

- [ ] Address is Wianamatta Avenue everywhere.
- [ ] Ridgeline is consistently client-side PM/Superintendent.
- [ ] AS 4000 appears consistently.
- [ ] Exactly five competitive consultant disciplines are represented.
- [ ] The tender has exactly three whole-builder groups.
- [ ] OSD sources agree on drawing number, revision and dates.
- [ ] $68,500 is excluding GST everywhere it appears.
- [ ] Ten days is described as calendar days everywhere.
- [ ] VO-007 is forecast/unapproved when Invoice 04 arrives.

### Product truth

- [ ] The S-202 Rev C email does not silently mutate canonical state.
- [ ] PMP changes through an addressable block operation.
- [ ] Cost Plan and programme calculations are application-owned.
- [ ] Reply remains draft until the user sends it.
- [ ] Invoice review does not masquerade as claim certification.
- [ ] Tender wording follows the controlled report language.
- [ ] No cross-project Pulse or unified fact-graph view is shown.

### Presentation

- [ ] One representative row is expanded per register.
- [ ] Counts establish scale without long scrolling.
- [ ] The OSD label remains visually consistent across frames.
- [ ] No personal data, real third-party identity or OS watermark is visible.
- [ ] Text is legible at desktop and narrow landing crops.
- [ ] Reduced-motion presentation retains every factual step.

If a box fails, fix the corpus or product state and recapture. Do not repair the
story in image editing.
