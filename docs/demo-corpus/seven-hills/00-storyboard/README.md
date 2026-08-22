# Wianamatta Avenue — landing story and later-film brief

**Project:** 14–18 Wianamatta Avenue, Seven Hills NSW 2147

**Status:** landing-first specification; the film is a later derivative

**Audience:** project managers, architects, design managers, superintendents and
small-to-mid-sized contractors

**Primary surface:** `frontend/public/landing.html`

**Capture instructions:** [`run-sheet.md`](run-sheet.md)

> **Synthetic project.** Wianamatta Avenue, the site, the client, every person,
> practice, tenderer, identifier, fee, price and project document in this corpus
> are fictional. The planning setting is modelled on Western Sydney practice, but
> this corpus must never be presented as a real development or customer project.

---

## 1. The decision

Build the **landing proof first**. Do not make a two-minute film before the
project can be run end to end in the live SiteWise interface and every frame can
be captured from a reproducible state.

The landing page is not a feature tour. It follows one requirement — the on-site
detention tank — from the first planning note to consultant appointment, civil
design, builder tender, design revision and invoice review. The complete corpus
sits behind that thread and makes it credible; only one representative row is
expanded in each beat.

The governing proposition is:

> **SiteWise turns scattered project evidence into controlled, reviewable work —
> and when new evidence arrives, it shows what should change without taking the
> judgement away.**

The short form is:

> **One fact arrives. SiteWise assembles the updates. You decide what moves.**

The existing brand spine remains the close:

> **You do the judgement. SiteWise does the assembly.**

The previous thesis — *one document arrives, nine things move* — is retained only
as a later product ambition. The current product proof is stronger when it shows
explicit authority: one document arrives, SiteWise identifies the relevant work,
and the user reviews the PMP, Cost Plan, programme and email changes before any
of them becomes project state.

---

## 2. The project

| | |
|---|---|
| **Site** | 14–18 Wianamatta Avenue, Seven Hills NSW 2147 — three fictional lots amalgamated |
| **Client** | Wianamatta Developments Pty Ltd — fictional |
| **Client-side practice** | Ridgeline Project Management Pty Ltd — project manager and Superintendent |
| **Scheme** | 11 two-storey attached townhouses, basement-free, Torrens subdivision |
| **Zone / pathway** | R3 Medium Density · DA to Blacktown City Council · multi dwelling housing — corpus assumptions to be clause-checked before capture |
| **Class** | Class 1a dwellings with fire-resisting separating walls |
| **Construction budget** | $9.8 million excluding GST |
| **Head contract** | AS 4000 construct-only |
| **Procurement** | Three whole-of-works builder tenders on the same issued scope |
| **Now** | Construction month 4; the corpus spans establishment to the fourth builder invoice |

### Why AS 4000

Ridgeline Project Management remains on one side of the contract throughout the story. It procures
and manages the client-side consultants, runs the builder tender and later acts
as Superintendent. The five consultant invoice histories therefore remain
client-side project costs. The commercial register therefore does not change
owner halfway through the demo.

### The five competitive consultant disciplines

| Discipline | Why it earns a place in the story |
|---|---|
| Architecture | Primary design coordination, DA and issued drawing sets |
| Town planning | Pathway, Council RFI and determination advice |
| Structural engineering | Class 1a structure and construction-stage revisions |
| Civil / stormwater engineering | The OSD requirement, design and revision — the red thread |
| Building services engineering | Coordinated hydraulic, electrical and mechanical design |

Each discipline has three fictional fee proposals and one appointment. Each
appointed consultant has five invoices, giving a complete 25-invoice consultant
register.

Survey, geotechnical, traffic, waste, arboricultural, landscape, BASIX/ESD,
acoustic, BCA and QS material may appear as direct specialist reports or one-off
advice. They must not silently inflate the five competitive disciplines. The
building-services appointment covers the coordinated hydraulic, electrical and
mechanical drawing sets without implying three additional appointments.

---

## 3. The red thread: the OSD tank

The OSD requirement is useful because it legitimately appears in every major
part of the application without requiring an invented fact graph.

| Lifecycle point | OSD evidence or action | Product surface |
|---|---|---|
| Early planning | Planning advice and stormwater controls identify the need for OSD | Evidence intake, official sources, project profile, PMP |
| Consultant procurement | Civil/stormwater RFP requires design, authority coordination and certification deliverables | Procurement draft and email issue |
| Appointment | The selected civil proposal is adopted | Consultant facts, PMP Consultants register, Cost Plan committed fee |
| Design | Civil drawing C-201 defines the tank and drainage arrangement | Drawing register, retrieval, transmittal |
| Builder tender | One bidder explicitly excludes the OSD tank; the other two include it | Tender Comparison matrix and source reference |
| Construction revision | Structural drawing S-202 Rev C supersedes Rev B; QS advice prices the forecast effect at **$68,500 excluding GST** | Pulse, inline PMP edit, Cost Plan operation |
| Programme | The architect's evidenced coordination note requires a **10 calendar-day** activity | Programme operation and deterministic dates |
| Correspondence | SiteWise drafts the reply; the user sends it | Project email thread |
| Invoice | Builder Invoice 04 includes **VO-007** for the OSD work before the variation is approved | Invoice review and Pulse |

The $68,500 is not model arithmetic. It comes from a fictional QS change advice
in the project evidence. The ten-day duration is not inferred from a generic
programme. It comes from a dated consultant coordination note. SiteWise applies
those evidenced inputs and software recalculates the Cost Plan and programme.

The OSD tender finding must also be document-led. Do not use the low-confidence
house-scale OSD benchmark to manufacture a comparable price for this development.
If the comparison needs an adjustment, include a bidder clarification/addendum
with the bidder's stated price.

---

## 4. The exact landing spine

The page is **hero + four beats + close**. Its one job is to make a construction
professional want to open the product because the evidence stays connected to
real project work.

### Hero — the consequence first

**Eyebrow**

> ONE REQUIREMENT · THE WHOLE PROJECT

**Headline**

> **The cheapest tender did not price the OSD tank.**

**Body**

> SiteWise found the requirement in the planning evidence and civil design, then
> put the bidder's stated exclusion beside the comparison before you made the
> call.

**Primary action:** `Open SiteWise`

**Secondary action:** `Follow the evidence`

**UI proof:** a real Tender Comparison crop with three whole-builder columns,
the OSD row selected and the source page open. The bidder document must state the
exclusion explicitly so the interface may truthfully show:

> `Excluded (stated, p. N)`

If the corpus instead provides only silence, the copy and UI must use the
binding phrase:

> `Not explicitly itemised — confirm with builder`

Never say the builder *forgot*, *hid*, *underquoted* or intended anything.

### Beat 1 — the pile becomes a project

**Anchor:** `#project`

**Heading:** `The pile becomes a project.`

**Body**

> A client brief, deposited-plan extract, planning advice, a forwarded email and a
> desktop geotechnical note arrive as fragments with different assumptions. SiteWise
> reads them as project evidence, files them, and shows what is known, conflicted
> and still missing.

**UI proof:** canonical intake and classification flow into the project profile
and the first scaffolded PMP. Open the OSD control row and its citation. Keep one
real `Not evidenced` field visible; refusal to fill a gap is part of the product.

**Capabilities proved:**

- upload and email attachments use the same intake;
- text extraction, classification, filing and user override;
- project evidence, platform guidance and official reference remain distinct;
- profile changes are proposals or explicit user changes;
- capability gates unlock the valid workflows;
- PMP, Cost Plan and programme begin from the current project state;
- every asserted project fact remains source-linked.

### Beat 2 — one appointment, three controls

**Anchor:** `#controls`

**Heading:** `One appointment. Three controls.`

**Body**

> Five disciplines go to market. When the civil/stormwater appointment is
> accepted, the firm and fee become one controlled project fact: the Consultant
> register changes, the committed Cost Plan fee changes, and the proposal remains
> attached as the basis.

**UI proof:** show the proposal register grouped by five disciplines, then expand
only the selected civil proposal. The appointment result must visibly show the
Cost Plan version, shared consultant fact and PMP v1 → v2 register update.

The surrounding interface may show the scale counters — all proposal returns,
25 consultant invoices, and the drawing discipline counts — but must not scroll
through them.

**Capabilities proved:**

- consultant RFP generation;
- classified fee proposals and disciplined selection;
- the dedicated consultant appointment mutation;
- deterministic Cost Plan versioning;
- consultant facts reused by the PMP;
- invoice extraction and allocation against appointed fees;
- versioned, editable working documents rather than chat-only output.

### Beat 3 — three tenders, one basis

**Anchor:** `#compare`

**Heading:** `Three tenders. One basis.`

**Body**

> Three builders price the same job in three different document structures.
> SiteWise reconciles each quote to its own total, maps the scope to one matrix,
> and makes the missing or qualified work visible before price decides the job.

**UI proof:** three ordered bidder groups, the OSD row, one source-page highlight
and the report draft. Do not compare concrete, brickwork and framing returns with
one another: different packages are not three bids for the same scope.

**Capabilities proved:**

- two-to-five bidder document groups;
- census-verified structured number extraction;
- quote-ledger reconciliation;
- line-item taxonomy mapping and silence analysis;
- human QA for uncertain mappings/statuses;
- report language from the controlled vocabulary;
- a versioned, reviewable Tender Comparison report;
- approved tender handoff to the Cost Plan as a reviewed proposal.

### Beat 4 — one email, four reviewed updates

**Anchor:** `#change`

**Heading:** `One email. Four reviewed updates.`

**Body**

> S-202 Rev C arrives by email with a QS change advice and a ten-day coordination
> note. Pulse shows the revised structural drawing and its thread. You ask SiteWise to update
> the work: one PMP control changes inline, the Cost Plan carries the evidenced
> forecast, the programme gains the activity, and a reply is drafted. You still
> send it.

**UI sequence:**

1. Pulse merges the inbound transmittal with `S-202 Rev C supersedes Rev B`.
2. The evidence drawer shows the drawing, QS advice and programme note.
3. A user-authorised Pi turn updates the OSD control **inline**; PMP v3 becomes v4.
4. The Cost Plan applies **+$68,500 excluding GST as a forecast variation**, not an approved variation.
5. The programme adds **OSD redesign and coordination — 10 calendar days** with a finish-to-start predecessor.
6. Pi drafts the reply; the user reviews it and presses Send.
7. Builder Invoice 04 later arrives with unapproved **VO-007** and Pulse opens the invoice review surface.

**Capabilities proved:**

- inbound email matching and canonical attachment intake;
- drawing revision detection and transmittal-aware Pulse;
- evidence-linked Pi tool use through project-scoped authority;
- addressable block editing rather than whole-document replacement;
- shared operation vocabulary for manual and agent edits;
- Python-owned Cost Plan and programme calculations;
- invoice extraction, allocation and unapproved-variation validation;
- Hold / Reject / Approve remain user decisions;
- email drafting is not unattended sending.

### Close — the authority line

**Heading**

> **You've still got the last word.**

**Body**

> The source stays attached. The numbers show their workings. The decision stays
> yours.

**Action:** `Open SiteWise`

**Final UI proof:** citations, used-by marks, workflow trace, evidence coverage
and the version labels for PMP, Cost Plan and programme. Do not fabricate a
cross-application fact-graph view.

---

## 5. Visual and editorial compression

The corpus is exhaustive; the landing is selective.

1. Keep cumulative register counts visible, but expand one row only.
2. Use the same `OSD` evidence label in every beat so the eye follows the fact.
3. Reuse the same three-part composition where possible: **source → controlled
   project state → human action**.
4. Use amber only for the active OSD exclusion, unresolved issue or review item.
   Evidence and settled state remain neutral/blue in the current landing system.
5. Show real filenames, dates, revisions, page references and version numbers.
   They carry credibility more efficiently than explanatory copy.
6. Never animate all documents. One source travelling into one register is enough;
   the grouped count proves scale.
7. Do not add a section for every workflow. A feature appears only when it advances
   the OSD thread.

The minimum register proof behind the page is:

| Group | Corpus contract | What the landing shows |
|---|---:|---|
| Initial planning / briefing | Deposited-plan/title summaries, brief, handover email, desktop advice and pre-DA/cost records | One planning note and one cited OSD fact |
| Fee proposals | 3 proposals × 5 disciplines = 15 | Five discipline groups; one civil proposal open |
| Consultant invoices | 5 invoices × 5 appointed disciplines = 25 | Register count; one mapped invoice |
| Architectural drawings | Exactly 20 current sheets | Discipline count only |
| Structural drawings | Exactly 7 current sheets, plus staged S-202 Rev B | S-202 Rev B→C row |
| Civil / stormwater drawings | Exactly 5 current sheets | C-201 Rev C open |
| Hydraulic / electrical / mechanical | Exactly 5 each, coordinated by appointed Flux Services | Discipline counts only |
| Landscape | Exactly 5 current sheets by direct specialist Fieldwork Landscape | Discipline count only |
| Reports | Exactly 13, spanning survey, site, planning, design, compliance and cost evidence | One relevant source at a time |
| Builder tenders | 3 whole-of-works tender groups | Three comparison columns |
| Builder invoices | Exactly 4, including Progress Claim 04 / VO-007 | One review item |
| Correspondence | Planning, consultant transmittals, procurement issue/returns and construction advice | One Pulse thread and one drafted reply |

---

## 6. Product truth boundaries

### Safe to show as current product proof

- Pi is the sole reasoning runtime and acts only through authorised,
  project-scoped SiteWise tools.
- Upload and project email attachments converge on canonical document intake.
- Document classification, filing, retrieval, citations and user overrides.
- Project profile proposals, decisions and capability gates.
- Scaffolded, versioned PMP and Cost Plan workflows with evidence coverage.
- Deterministic Cost Plan arithmetic and downloadable workbook.
- An editable finish-to-start programme with deterministic date roll-up.
- Stable block-level PMP editing by the user or Pi.
- Consultant procurement and the dedicated consultant appointment operation.
- Drawing registers, revision detection and drafted transmittals.
- Three whole-builder Tender Comparison with human QA and controlled language.
- Approved tender handoff to the Cost Plan as a reviewed proposal.
- Invoice extraction, allocation, validation and Hold / Reject / Approve review.
- Per-project Pulse for drawing revisions, tender receipts, invoice issues,
  classifications, approvals and unanswered correspondence.
- Email drafts, explicit user send and project-thread history when a provider is
  configured.

### Must be shown as proposed or user-authorised

- an email-derived action or project decision;
- any profile change inferred from evidence;
- the PMP v3 → v4 inline update;
- the +$68,500 Cost Plan forecast variation;
- the ten-day programme activity;
- a tender-to-cost handoff;
- an invoice approval or rejection;
- an outbound email.

The user may authorise several bounded changes in one Pi turn. That does not
make them automatic consequences of document intake.

### Language constraints

- Say **drafted**, not sent, until the user presses Send.
- Say **forecast variation** for the $68,500 until VO-007 is approved.
- Say **invoice review**, not progress-claim certification or payment schedule.
- Say **finish-to-start programme effect**, not critical path impact.
- Say **forecast completion moves**, not contractual practical completion, unless a
  separately authorised EOT or contract adjustment changes the contract date.
- Say **not explicitly itemised** unless an exclusion is stated and page-cited.
- Findings describe documents, never the bidder's motives.
- Project guidance and official reference are labelled separately from project
  evidence.

### Deployment gates before capture

- Fix and verify townhouse support through both the workflow capability matrix
  and the Tender Comparison context adapter.
- Configure a real Graph/Gmail provider or the inbound project alias if the
  public copy says an email arrived from a live mailbox. If the demo uses the
  fake provider or seeded webhook, label the capture as a staged demo.
- Verify the fictional planning instruments, version dates, clauses and OSD
  requirement against the intended 2026 planning setting.
- Run the three tenders through the actual evaluation pipeline; do not rely on
  an answer key alone.
- Confirm every screenshot contains no personal account data, real mailbox
  address, OS watermark or non-synthetic third-party identity.

---

## 7. Later film / product-gap annex — not current landing claims

This annex preserves the ambition of the first storyboard. None of these scenes
may be presented as current product behaviour until its acceptance test passes
in the live application.

### A. Cross-project Monday Pulse

**Later scene:** three projects, hundreds of weekend arrivals, five items needing
judgement.

**Gap:** Pulse is project-scoped; there is no cross-project roll-up.

### B. One arrival, nine prepared updates

**Later scene:** a Council RFI produces obligations, consultant requests,
programme proposals, cost exposure and a drafted response.

**Gap:** email intelligence creates evidence-linked candidates, not a complete
obligation or impact-review workflow. There is no automatic nine-surface cascade.

The desirable product is a review queue of typed candidate impacts, not silent
mutation.

### C. Full revision blast radius

**Later scene:** Rev D changes yield and shows every affected package, recipient,
PMP section, cost item and programme activity.

**Gap:** revision detection exists; drawing-derived yield extraction, recipient
holdings and a complete blast-radius graph do not.

### D. Automatic feasibility and contribution reforecast

**Later scene:** 12 dwellings become 11; revenue, margin and s7.11 contributions
recalculate.

**Gap:** there is no current pro forma workflow or automatic revision-to-cost/
contribution propagation. Do not ask the model to perform this arithmetic.

### E. The contract-administration week

**Later scene:** EOT, variation, progress claim and site RFI arrive together;
every clock starts and assessments are drafted.

**Gap:** current SiteWise has invoice review and editable Cost Plan variation
columns, not complete EOT, variation, progress-claim, RFI, direction or time-bar
registers. The programme has no critical path, baseline, working calendar or
delay-analysis engine. There is no BOM weather-record integration.

### F. One fact, seven places

**Later scene:** the OSD requirement is highlighted simultaneously across every
artefact and register.

**Gap:** citations, used-by marks, evidence coverage, version history and activity
trace exist; the unified fact-graph view does not.

### Later-film thesis

Once the product gaps above are closed, the film may use:

> **One document arrives. Nine updates are ready for review. Nothing is sent
> until you decide.**

That is the future form of the original idea that remains consistent with
SiteWise's human-authority doctrine.

---

## 8. Acceptance criteria for this storyboard

This brief is ready for landing implementation when:

1. the fictional address and client-side AS 4000 point of view appear everywhere;
2. the corpus contains the complete consultant, drawing, tender and invoice
   registers described above;
3. the OSD requirement can be traced through real uploaded corpus documents;
4. three whole-builder tenders complete Tender Comparison in the townhouse project;
5. the civil appointment updates controlled project state from its source proposal;
6. the inbound S-202 Rev C email produces the expected Pulse item;
7. an authorised Pi turn changes PMP v3 → v4 inline, applies +$68,500 as forecast,
   adds the ten-day programme activity and drafts the reply;
8. the user, not Pi, sends the email;
9. Builder Invoice 04 / VO-007 opens as an unapproved-variation review item;
10. every landing claim can be captured from the current UI without compositing a
    capability that does not exist.

The exact project setup and capture order are in [`run-sheet.md`](run-sheet.md).
