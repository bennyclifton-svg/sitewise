# Capture run sheet — Sarah's build, post-Pulse

**Companion to** [`README.md`](./README.md) (the film). This file is the ordered prompt
series for the capture session: what Sarah types, forwards or says; what SiteWise must do;
and what would be a defect.

It replaces [`../00-prompts/`](../00-prompts/) for a post-X1 capture. The old six prompts
are still correct for the current build — keep them until the programme lands.

**Assumed state:** X1 Stages 0–22 complete. One canonical classification per document.
Automatic filing. Project events and Pulse live. Project email alias active. Invoice review
with immutable machine extraction and an approval boundary.

---

## What changes from the old run sheet

| Old behaviour | Post-Pulse behaviour |
|---|---|
| 17 steps, most of them "upload N files, press a button" | 12 scenes, most of them triggered by evidence arriving |
| Manual **Sort Files** after each batch | Filing happens on classification. Sort survives only as recovery. |
| Run **Update PMP** manually after the brief | Pulse offers it: *"Accommodation schedule can be updated from this document."* |
| Upload the brief through the file picker | Forward it to `georgina41@in.sitewise.au` from a phone |
| Drawings become register rows and lose their text | Drawing notes are searchable (D3). Rev C is diffed against Rev B. |
| Fee comparison is a prompt | Still a prompt — but Pulse raises it when the last proposal lands |
| Nothing after the cost plan | Construction: claims, variations, defects, time bars, voice |

Two deletions worth stating plainly, because they are the product argument:

- **There is no Sort Files button in this film.** If a shot contains one, the scene is
  wrong.
- **There is no "0 files moved" state.** Every file resolves to exactly one visible outcome:
  `moved` · `already-filed` · `waiting` · `needs-review` · `unresolved` · `failed` ·
  `skipped`.

---

## Scene 0 · The one sentence

**11:40 pm. Empty project. Typed at human speed, roughness intact.**

> Rear extension and second storey addition to a semi in Newtown. Master bedroom and a
> parents' retreat upstairs, new kitchen opening onto an open plan living dining. Heritage
> conservation area. Budget around $750k.

Unchanged from [`01-kickoff.md`](../00-prompts/01-kickoff.md), and it should stay unchanged —
it is a good prompt precisely because it is a bad one.

### Must resolve

Residential · House (Class 1a) · **extend** · NSW · S band · $750,000 · 2 storeys · **DA** ·
Newtown NSW. Accommodation schedule: **4 rows**, the four spaces named.

### Must not

- Invent GFA, bedroom count or street number. **This is the scene.**
- Resolve work type to `new`.
- Name an appointed architect.
- Add a study, ensuite or laundry — none are in the prompt. They arrive with the brief.

### Capture

`GFA` and `Bedrooms` grey and empty, held for a beat, with `Not stated in the prompt`
underneath. Everything the film argues about evidence discipline starts in this frame.

---

## Scene 1 · Why DA, not CDC

**Typed. New — this scene does not exist in the old run sheet, and it should.**

> Why do I need a DA? My neighbour said we could do this as a complying development.

### Must resolve

The land is inside the Newtown/Enmore Heritage Conservation Area, and land in an HCA is
excluded from complying development under the Codes SEPP. Therefore: DA, with a Heritage
Impact Statement. Cited, not asserted.

### Must not

Answer from the model's general knowledge with no citation. The answer must point at the
control that produces it. If it cannot cite, it should say the pathway needs confirming.

### Capture

The first moment SiteWise gives Sarah something **she could not have known to ask**, with a
source she can check. Twelve seconds. It sets up every later save. Cuttable for the 2:55
edit, essential for the 4:30.

---

## Scene 2 · The correction that outranks the machine

**By hand in the profile panel, then one line typed.**

| Field | Change |
|---|---|
| Site address | → `41 Georgina Street, Newtown NSW 2042` |
| Storeys | confirm `2` — confirming is a different gesture from correcting |
| Bedrooms | → `4` |
| GFA | → `175` m² |
| Garage spaces | → `0` (a deliberate zero, not a blank) |

> Add a plunge pool in the rear courtyard, about 12 square metres. Site is 232 square metres,
> 6.4 metre frontage. The semi is attached on the eastern side to number 43.

### Must resolve

One row: **Plunge Pool · External · 12 m² · New**. The party wall fact recorded — structural
and planning scope both depend on it later. Scheduled area **12 m²**.

### Must not

Recalculate or "improve" the 12 m² total to look less sparse. The honesty of that number is
the point.

### Capture

The override chip. Under D4 this correction now survives re-ingest, re-classification, file
moves, workflow reruns and classifier upgrades. Say so on screen in four words, then move on.

---

## Scene 3 · The brief, forwarded

**Phone, in a lift. Not an upload.**

She forwards [`owners-project-brief.md`](../01-brief/owners-project-brief.md) to
`georgina41@in.sitewise.au` with no message body.

### Must resolve

1. Email lands, project matched by alias, `document_class = correspondence` for the body.
2. The attachment enters **canonical intake** — byte-identical downstream behaviour to a
   manual upload. This is Stage 16's exit test and it is the reason the scene exists.
3. Filed automatically to `00-brief-pmp/`. No Sort press.
4. Pulse raises a card offering the schedule update.

Then she taps **Update**:

| | Before | After |
|---|---|---|
| Rows | 5 | 26 |
| Rows with parseable area | 1 | 26 |
| Demolished rows | 0 | 5 |
| External rows | 1 | 4 |
| **Scheduled area** | 12 m² | **261 m²** |

### Must not

- Reconcile 261 m² against the profile's 175 m² GFA. They measure different things; the
  86 m² difference is external space.
- Delete the demolished rows. Someone has to be paid to remove them.
- Invent characteristics for the `TBC` rows (walk-in robe, bedroom 3, understair store,
  stair and landing all have an area and no description — leave it).
- **Flip any consultant row to appointed.** Nobody is engaged yet. A brief from the owner is
  not engagement evidence. If the consultant table moves here, stop the capture.

### Capture

5 sparse rows → a full schedule with a real total. Still the best frame in the corpus and it
needs no narration.

---

## Scene 4 · Fifteen proposals, arriving as they actually arrive

**Email, over two weeks of project time.**

Send all 15 from [`02-fee-proposals/`](../02-fee-proposals/) to the project alias, from
plausible sender domains, spread across dates. Then, when the last one lands, Pulse raises it
and Sarah types:

> Compare the fee proposals for each discipline. Show the fee, what's in and what's out, and
> flag anything one of them has excluded that the others have priced.

### Must resolve

| Discipline | Cheapest | **Appointed** | Dearest |
|---|---|---|---|
| Architectural | Kestrel $68,500 | **Bower Lane $82,000** | Harrow & Vine $96,500 |
| Town Planning | Loftus $7,800 | **Verity $9,900** | Callan $13,500 |
| Structural | Grimshaw Vale $8,400 | **Ardent $11,500** | Bellhaven $15,900 |
| Civil / Stormwater | Stormline $4,200 | **Catchment $5,800** | Ridgeway $7,900 |
| Certification | Pinnacle $3,400 | **Meridian $4,600** | Statewide $6,200 |
| **Total appointed** | | **$113,800** | |

And the cross-proposal finding that no single-document read can produce: **Kestrel and Loftus
both exclude the Heritage Impact Statement.** Priced separately, neither carries it.

### Must not

Rank on fee and recommend the five cheapest ($92,300). That apparent $21,500 saving buys an
unpriced heritage statement, an unpriced underpinning design, an unpriced OSD design and an
unpriced Occupation Certificate. **This is the defect the scene exists to catch.**

### Capture

Both exclusion clauses highlighted simultaneously, one line drawn between them. A comparison
that reads each proposal alone misses it; one that reads them against each other finds a
document nobody priced.

---

## Scene 5 · The footings

**Email with a photo, from the structural engineer, 2 May.**

> Exposed the footing on the party wall line this morning. Sandstone rubble at 410 mm.
> Underpinning will be required — S-300 to follow. Photo attached.

### Must resolve

- Photo classified `photo`, body `correspondence + structural`, both filed to structural.
- Linked to the **unknown footings** risk raised in the brief on 18 March.
- Pulse signal: `approval_received` is wrong here — this is `potential_cost_change`
  **resolved to nil**, because Ardent's appointment carries underpinning design inside the
  fee. Grimshaw Vale's proposal excluded it.

### Must not

Raise a cost variation. There isn't one — that is the whole payoff. If SiteWise flags a fee
variation here, the link back to scene 4 is broken.

### Capture

`Cost impact: nil`, with the March risk row turning from *unknown* to *evidenced* behind it.

---

## Scene 6 · Revision C

**Email from Bower Lane, 19 June. No prompt at all.**

The design documentation arrives across June to November — 47 drawings and 12 reports, the
DA set at Rev C in June and the For Construction sheets with the CC in November. For capture,
batch all 59 in one go: it is the largest single load in the corpus and the best shot of the
repository under pressure. Do not drip-feed.

### Must resolve

- 59 documents filed by discipline, **not by firm**. Catchment authored both the `C-` and
  `H-` sets under different job numbers (`CCH-2604`, `CCH-2604-H`) — two packages, one firm.
- `A-000` is a drawing register *inside* the document register. One sheet. It must not
  expand.
- Revision spread preserved: 18 at Rev A, 14 at Rev B, 15 at Rev C.
- Issue purpose splits the set: 33 *For Development Application*, 14 *For Construction*.
- **Drawing text is searchable** (D3). Under the old build every one of these lost its notes
  to `register_only`. Prove it on camera: search for a note that only exists on a drawing.
- Rev C diffed against Rev B: heritage setback 1.5 m → 1.8 m, and the list of open items
  still quoting Rev B.
- Transmittal **drafted**, not sent.

### Must not

- Appoint the five firms with reports but no engagement evidence — Larkin & Vale, Stratum,
  Canopy, Solaris, Redwood. List them as document authors, hold appointment status as
  unevidenced. **A report arriving does not prove anyone was engaged.**
- Flatten revisions to "current".

### Follow-up prompt, if the cut has room

> What went to Council in the DA?

29 drawings and 8 reports, all `For Development Application`, 26 June 2025. Explicitly not in
the pack: hydraulic, electrical and mechanical drawings, the three construction detail sheets,
the BCA and access statements, and the geotechnical report.

---

## Scene 7 · Thirty-four conditions

**Determination arrives by email, 30 September. No prompt.**

### Must resolve

Each condition decomposes into an obligation carrying: trigger stage (pre-CC / pre-works /
pre-occupation / during works), an owner, and the evidence type that discharges it. As later
documents arrive they attach to the condition they satisfy. Programme milestones inherit
their blocking conditions.

Headline: **7 outstanding before Construction Certificate. 2 with no owner.**

### Must not

Store the determination as one more filed PDF with a `certificate + planning`
classification and stop there. Correct classification is table stakes; the obligation graph
is the product.

### Capture

Condition **11** — heritage-matched face brickwork to the street elevation — visible but
unexplained. It returns in scene 8.

⚠ **Corpus gap.** There is no Notice of Determination in the corpus. See *Corpus additions
required*.

---

## Scene 8 · The showpiece

**Three quotations arrive by email, 15–17 October.**

> The builder quotes are all in. Compare them.

### Stage one — as submitted

```text
Southbrook Projects          $712,000     1 page   ·  6 lines   ·  no PC sums
Halden Building Co           $748,900     2 pages  · 22 lines   ·  $50,500 PC
Kingsford Bay Constructions  $792,400     4 pages  · 38 lines   ·  $70,500 PC
```

### Stage two — corrected for scope

Southbrook's exclusion clause — *"anything not shown on the drawings supplied… items subject
to client selection… specialist works and trades outside our normal scope"* — is broad enough
to carry five omissions that are never stated. They are simply absent from six lines of
pricing.

| Omission | Adjustment |
|---|---:|
| Plunge pool, plant and barrier | +$78,000 |
| OSD tank, stormwater, kerb connection | +$24,500 |
| Scaffolding, hoarding, site protection | +$18,400 |
| PC sums — floor coverings, appliances, tapware, lighting | +$62,000 |
| Heritage-matched face brickwork — **DA condition 11** | +$14,800 |
| | **+$197,700** |

### Stage three — the reorder

```text
Halden Building Co           $748,900  →  $780,100   corrected      1
Kingsford Bay Constructions  $792,400  →  $792,400   corrected      2
Southbrook Projects          $712,000  →  $909,700   corrected      3
```

> **The cheapest quote is the dearest job, by $129,600.**

### Must resolve

Every adjustment must cite its basis — the drawing, the schedule or the DA condition that
proves the scope exists. An unevidenced adjustment is worse than no adjustment: it is exactly
the stochastic guessing the whole architecture exists to prevent.

The comparison must also state the distinction that keeps it fair: **Halden excludes things
too, and Halden says so.** Appliances ~$18,000, soft landscaping ~$13,200, both stated, both
carried into the cost plan as separately funded owner items.

### Must not

Rank on submitted price. Rank on submitted price and Southbrook wins.

### Capture

The re-sort animation. Give it time — it is the scene people describe to a colleague.
Answer key: [`tender-comparison-answer-key.md`](../04-builder-quotes/tender-comparison-answer-key.md).
**Do not upload it.** The comparison has to find the gaps itself.

---

## Scene 9 · Saturday, on site

**Spoken. Phone held up, one hand free.**

> "Level three east, ceiling grid's out — about fifteen mil over three metres. That's the
> ceilings package. Needs fixing before tiles. Photo."

### Must resolve

Transcript plus photo → one `photo` document, location and level tagged, matched to the
ceilings trade package, one defect register row, and a **drafted** site instruction citing
the workmanship clause of that subcontract. Checked against the programme: the ceiling-tile
activity is the constraint that makes it urgent.

### Must not

Send anything. Direct anyone. Update the defects register without her.

⚠ **Not in the X1 plan.** See *What must be built*.

---

## Scene 10 · Monday, the car

**Spoken, both directions.**

> "Catch me up."

### Must resolve

Three items, in decision order, synthesised — never a count of records. The failure mode is
named explicitly in the plan and it is the one thing that would sink this scene:

```text
never:   48 emails · 26 documents · 12 events
always:  3 things changed · 2 decisions · 1 risk
```

1. **Claim 7 includes $8,400 against VO-17, which is not approved.** Coded issue
   `UNAPPROVED_VARIATION`. Approval would move the structural forecast.
2. Certifier's frame inspection passed — evidence attached, condition discharged.
3. Bower Lane owe the tiling setout promised for Thursday. Overdue commitment, follow-up
   drafted.

Then: **"Hold the claim. Tell him why."** → payment schedule drafted with a written reason
against the withheld amount, awaiting approval. Nothing crosses the approval boundary
silently.

### Must not

- Approve, post or pay anything by voice alone.
- Summarise the claim in a way that replaces the raw document. Raw stays raw (D5).

### Capture

Six seconds of her reading it in a courthouse corridor, then approving. The claim of the
film is that six seconds was enough.

⚠ **Corpus gap + not in the X1 plan.** See both sections below.

---

## Scene 11 · The room

No prompt. Month seven. She walks into the Parents' Retreat, framed, roof on.

Cost plan behind her: contract sum **$748,900** against a $750,000 budget, appliances landing
at **$12,950** against an $18,000 allowance.

---

# What must be built

Everything in scenes 0–8 is deliverable on the X1 programme as written. Scenes 9 and 10 are
not. Stating that plainly here is cheaper than discovering it in a studio.

| Capability | Status in the X1 plan | Needed for |
|---|---|---|
| Project email alias `georgina41@in.sitewise.au` | Stage 22 — planned, last in the programme | Scenes 3–8 |
| Automatic filing, no Sort press | Stage 7 — planned | All |
| Searchable drawing text | Stage 1 — **already landed**; Stages 1–2 complete at `563eee84` | Scene 6 |
| Rev-to-rev diff + blast radius | Partly: `drawing-compare` exists; the *blast radius* (who holds the superseded rev) does not | Scene 6 |
| Conditions-of-consent obligation graph | **Not in the plan.** Closest is Stage 13 events. | Scene 7 |
| Invoice review with approval boundary | Stages 10–12 — planned | Scene 10 |
| Progress claim assessment + payment schedule | **Not in the plan** — Stages 10–12 cover invoices, not claims under a head contract | Scene 10 |
| Commitment / promise ledger | Seeded in the spec §9 as "candidates"; no durable record | Scene 10 |
| **Speech in** | **Absent.** `voice`, `speech`, `dictation` appear zero times across the plan folder. | Scenes 9, 10 |
| **Speech out** | Absent | Scene 10 |
| Site photo as a first-class input | `photo` is in the taxonomy with **no consumer anywhere** | Scenes 5, 9 |

The honest read: **the film is roughly 70% capturable on the programme as scoped.** The
remaining 30% is one coherent chunk of work — capture from site (voice + photo) and the
construction-phase loop (claims, directions, commitments) — and it happens to be the half
that carries the emotional payload.

If the film ships before that work does, scenes 9 and 10 are storyboard animation rather than
screen capture, and the launch page must not imply otherwise.

---

# Corpus additions required

The corpus stops at the cost plan. The film runs to month seven. Six documents are missing,
all cheap to write and all consistent with existing dates and figures:

| # | Document | Date | Why |
|---|---|---|---|
| 1 | **Notice of Determination — DA/2025/0418**, 34 numbered conditions, condition 11 = heritage-matched face brickwork | 2025-09-30 | Scene 7. Currently only *referenced*, in `INV-VUP-1044`. |
| 2 | **Halden progress claim 7**, including $8,400 against VO-17 | 2026-08-05 | Scene 10 |
| 3 | **VO-17** — variation request, unapproved, tied to something plausible in the underpinning remeasure | 2026-07-xx | Scene 10 |
| 4 | **Certifier's frame inspection record**, passed | 2026-08-12 | Scene 10, discharges a condition |
| 5 | **Bower Lane email** promising tiling setout by Thursday | 2026-08-06 | Scene 10, the commitment ledger |
| 6 | **Three site photographs** — footing pit at 410 mm, frame at month 7, the L3 ceiling grid | various | Scenes 5, 9, 11 |

Extend `generate-commercial.py` for 2–4 so the arithmetic keeps asserting itself. Claim 7
must reconcile against the $748,900 contract sum, previous claims and retention, or the
scene-10 assessment is fiction.

**Two inconsistencies found while reading, neither fixed:**

1. [`01-brief/owners-project-brief.md`](../01-brief/owners-project-brief.md) is dated
   **18 March 2026**; the corpus timeline in [`../README.md`](../README.md) puts the brief at
   **2025-03-18**. One is wrong. Settle it before capture — the brief date is on screen in
   scene 3 and again in scene 5.
2. [`../00-prompts/01-kickoff.md`](../00-prompts/01-kickoff.md) says *"Five rows is the right
   answer from this prompt"* directly above a four-row table. Four is correct; the plunge pool
   makes five in the next step.
