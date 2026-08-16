# Cockpit Film — animation brief

**Working title:** *Six classes, one cockpit*
**Date:** 2026-08-14
**Runtime:** 140s hero · 60s paid cut · 30s / 15s / 6s derivatives
**Medium:** real-UI screen-capture compositing (not abstract 3D)
**Status:** brief ready for capture + Claude Design handoff

---

## 0. What this is, and what it is not

This is **not** a replacement for the five-chapter abstract film in
[2026-08-12-landing-film-design.md](2026-08-12-landing-film-design.md). That film is the
*poster* — cubes, light, 106s, no real pixels. It sells the idea.

This is the **proof**. Real cockpit, real panels, real artefact text, real taxonomy values,
real measured output. It answers the only question the poster film leaves open: *yes, but
does the thing actually do that?*

The two are complementary and should live on the same page — abstract film above the fold,
cockpit film immediately below, under a heading that hands over the burden of proof.

| | Landing film (exists) | Cockpit film (this brief) |
|---|---|---|
| Register | Cinematic, abstract, material | Forensic, fast, literal |
| Content | Cubes, kits, light | Screenshots, artefact text, tables |
| Camera | Orbits a solid | Zips between panels |
| Proves | We have taste | We have a product |
| Claim | Emotional | Checkable |

**One structural rule that separates this from every other product film:** the camera
**never leaves the cockpit**. No cuts to logos, no cuts to stock footage of a construction
site, no cuts to a person at a laptop. One continuous space. What changes is the *project
inside it* — and it changes eight times.

---

## 1. Objective and the single claim

**Objective.** Demonstrate, in under two minutes, that a short rough prompt typed by a
project manager becomes a *class-correct, scale-proportionate, evidence-disciplined*
delivery artefact set — across radically different buildings — and that the loop closes
when invoices arrive months later.

**The single claim the film must land**, in the spine's language:

> **You do the judgement. SiteWise does the assembly.**

Everything on screen serves one half or the other. If a beat serves neither, cut it.

**The one thing this film must not do:** look like a demo of a chat app that writes
documents. Twenty products do that. The differentiator is *the same three sentences of
rough input produce a completely different document for a $160k roof than for a $180m data
centre* — and we can measure it.

---

## 2. Non-negotiables

Carried from [2026-08-06-landing-messaging.md](2026-08-06-landing-messaging.md) and
`PRODUCT.md`. These bind captions, VO, and any text composited over the UI.

### Banned on screen

- **INGEST** — no CM says it, and it is the least interesting step.
- **GENERATE** — contradicts the determinism boundary.

### Approved verb set

`READ → SORT → RETRIEVE → BUILD`

Extended for this film: *reads, sorts, files, retrieves, builds, assembles, drafts,
reconciles, checks, re-checks, rebuilds.* Never *generates*, never *creates content*,
never *magically*.

### The determinism boundary must be visible, not stated

> The model is a language interface and classifier. It is never the calculator and never
> the source of a project fact.

Show it: when the cost plan totals, the arithmetic resolves in one frame with no token
stream. When a fact has no evidence behind it, the artefact says `Assumption` or
`Not evidenced` — **on screen, legible, not hidden**. The film's most persuasive frames are
the ones where SiteWise *declines to know something*.

### No invented proof

No fabricated testimonials, customer logos, win rates, or time-saved claims. Every number
that appears on screen must trace to §14. Placeholder client names in project data are
fine — they are the corpus's own fiction — but nothing may be dressed as a real customer.

### Register

Ordinary Australian, intelligent, built-environment. Not corporate, not tech-bro, not
breathless. The pace is fast; the tone is calm. Speed is the argument — it does not need
to be narrated.

---

## 3. Structural concept — the relay

The original brief followed one project (Sarah, $750k, second storey) end to end. That is
a good *story* and a weak *proof*: one project cannot show that classification is doing
any work.

**Replace it with a relay.** The cockpit stays put. The project switcher flicks. Eight
projects hand the baton to each other, each entering on a short rough prompt, each leaving
behind a different-shaped artefact. Sarah's project survives — it is the **anchor**,
opened first and returned to at the close, so the film still has a spine of continuity —
but between her first prompt and her last invoice, seven other buildings pass through the
same six panels.

```
ANCHOR OPEN  ─────────────────────────────────────────────  ANCHOR CLOSE
  Newtown semi                                              Newtown semi
  $750k, extend                                             invoice #4 lands
      │                                                            ▲
      ▼                                                            │
      └──▶ AC plant ──▶ warehouse ──▶ data centre ──▶ hospital ──▶ rail ──┘
           XS $180k     M $18m       L $180m        L $85m       L $120m
           refurb       new          new            refurb       refurb
           commercial   industrial   industrial     institution  infrastructure
```

Why the relay wins:

1. **It proves classification.** Six building classes, five work types, four scale bands —
   in one continuous shot. Nothing else demonstrates a taxonomy.
2. **It gives the film a rhythm.** Prompt → resolve → build → cut. Eight times. The
   audience learns the beat by the third repetition and starts predicting it, which is
   exactly when you break it (Reel V) for the proof.
3. **It makes the cockpit the hero,** not the project. The cockpit is what we sell.

---

## 4. Cast — the eight projects

All drawn verbatim from `docs/plans/test-prompt-corpus/sitewise-test-prompt-corpus.md`.
Use the prompt text **exactly as written, roughness intact** — the run-on sentences and
missing punctuation are the point. A cleaned-up prompt undermines the whole film.

| Role | # | Prompt (typed on screen, verbatim) | Class / subclass / work type | Band |
|---|---|---|---|---|
| **Anchor** | 14 | *"Second storey addition and rear extension to a semi in Newtown. Heritage conservation area. Adding 2 beds and a bathroom up, opening the rear to a new kitchen and living. Clients living elsewhere during works. Around $750k."* | residential / house / **extend** | S · $750k |
| Relay 1 | 1 | *"Two Pioneer AC systems servicing the service centre and western office are 30+ years old, beyond economical repair, still on R22… Recommending full replacement of both with Actron 30kW split ducted units… Budget around $180k. Need a PMP and cost plan."* | commercial / office / **refurb** | XS · $180k |
| Relay 2 | 31 | *"New 12,000sqm warehouse with 800sqm office, 12m clear height, 8 recessed docks. Estate site in Eastern Creek. $18m. Need a PMP."* | industrial / warehouse / **new** | M · $18m |
| Relay 3 | 35 | *"15MW data centre, Tier III, on a greenfield site. Client wants N+1 across power and cooling. $180m. Need a PMP."* | industrial / data_centre / **new** | L · $180m |
| Relay 4 | 47 | *"Redeveloping the emergency department and adding two operating theatres at a regional hospital. Hospital fully operational, ED cannot close. $85m. Need a PMP."* | institution / healthcare_hospital / **refurb** | L · $85m |
| Relay 5 | 61 | *"Station upgrade — new lifts, footbridge, accessible platforms and canopies. Rail line stays operational, work in possessions. $120m."* | infrastructure / rail_metro / **refurb** | L · $120m |
| Relay 6 | 6 | *"Concrete cancer in the basement carpark and spalling on the eastern facade. Building is 1970s, 6 levels, residential strata… maybe $1.2m."* | residential / apartments / **remediation** | S · $1.2m |
| Relay 7 | 10 | *"Client wants us to assess the condition of their medical centre and give them a 10-year capital works plan with indicative costs. No construction yet."* | institution / healthcare_medical_centre / **advisory** | XS |

**Coverage achieved:** 6 of 6 building classes · 5 of 5 work types · 4 of 4 scale bands ·
$160k → $180m, a **1,125× spread**.

### Bench — flash frames only (Reel II)

Sub-second cards during the class cascade. Each needs only a project name, a class chip,
and one arresting number. Pull from the same corpus:

| # | Flash card | Hook on screen |
|---|---|---|
| 34 | Cold storage | `−25 °C · ammonia · 8,000 sqm` |
| 39 | Pharmaceutical GMP | `Grade B/C cleanrooms · TGA licensed · $95m` |
| 3 | School switchboard | `MSB at capacity · summer holidays only · $220k` |
| 28 | F&B fitout | `90 seats · open in 14 weeks · $980k` |
| 59 | Adaptive reuse | `Heritage listed warehouse · three uses · $38m` |
| 43 | Solar + battery | `2 MW rooftop · 1 MWh · site stays live` |
| 52 | Correctional wing | `120 beds · facility stays secure · $70m` |
| 63 | Solar farm | `120 MW · 300 hectares · grid connection` |
| 42 | Waste to energy | `300,000 tpa · $400m` |
| 49 | Allied health clinic | `180 sqm · four rooms · $290k` |

The tonal joke that lands without a caption: **$290k physio clinic** cut against
**$400m waste-to-energy plant**, same interface, four frames apart.

---

## 5. The cockpit — panel geography

Capture from the live SPA. Real component names below so the animation maps to actual
screens rather than invented ones.

```
┌────────┬──────────────────────────────┬───────────────────┐
│  NAV   │        MAIN PANEL            │   REPOSITORY      │
│ 190px  │                              │      368px        │
│        │  WorkflowDraftPreview        │ DocumentRepo-     │
│ Project│  DraftReviewPanel            │   sitoryPanel     │
│ Profile│  InlineMarkdownEditor        │ IngestProgress-   │
│ Project│  InlineTableRowEditor        │   Strip           │
│  Plan  │  DecisionControl             │ SortFilesResult-  │
│  Cost  │  CostPlanGrid                │   Panel           │
│  Plan  │  CostInvoiceRegister         │ WorkspaceExplorer │
│Procure-│  WorkbookGrid                │ WorkspaceFilePanel│
│  ment  │                              │                   │
│ Tender │  ── below the action ──      │                   │
│  Comp  │  WorkflowTracePanel          │                   │
├────────┴──────────────────────────────┴───────────────────┤
│  CHAT RAIL — ChatComposer · ActivityStream ·               │
│  ToolActivityFeed · WorkflowRunCard · StreamingIndicator · │
│  CitationChip · ArtefactCard · AnswerTrace                 │
└────────────────────────────────────────────────────────────┘
```

Default widths are real: left nav **190px**, repository panel **368px**
(`cockpitShellLayout.ts`). Hold them — a viewer who later opens the product should
recognise the proportions immediately.

### Panels the film must visit at least once

| Panel | Real component | Beat it earns |
|---|---|---|
| Chat composer | `ChatComposer` | Every prompt |
| Live status ticker | `ActivityStream`, `ToolActivityFeed` | Reel I, IV |
| Profile strip | `ProfileProposalStrip`, `TaxonomyPicker` | Reel I, II |
| Repository | `DocumentRepositoryPanel`, `WorkspaceExplorer` | Reel III |
| Upload progress | `IngestProgressStrip` | Reel III |
| File routing result | `SortFilesResultPanel` | Reel III |
| Workflow progress | `WorkflowProgressStrip` | Reel IV |
| Draft preview | `WorkflowDraftPreview`, `DraftReviewPanel` | Reel IV, V |
| Selection → instruction | `SelectionInstructionCard` | Reel VI |
| Queued changes | `InstructionTray` | Reel VI |
| Direct inline editing | `MarkdownContent`, `InlineMarkdownEditor`, `InlineTableRowEditor`, `InlineListItemEditor` | Reel VI |
| Decision widget | `DecisionControl` | Reel VI |
| Cost plan | `CostPlanGrid`, `WorkbookGrid` | Reel VII |
| Mid-project update | `update_pmp` via `ProjectControlBoard` / chat command | Reel VIII |
| Procurement | `ProcurementRequestPanel` | Reel IX |
| Tender | `TenderCockpitPage` | Reel IX |
| Invoice register | `CostInvoiceRegister`, `InvoiceProcessStatus` | Reel X |
| Trace | `WorkflowTracePanel`, `AnswerTrace`, `SourcePassagePanel` | Reel V, XI |

### Real workspace folder tree — use these exact strings

```
00-brief-pmp/          PMP, owner project brief
01-cost/               cost_plan_v01.md · Cost_Plan_v01.draft.xlsx
02-consultant/         consultant_procurement_structural_v01.draft.md
04-planning-and-authorities/
05-procurement/        quotes/ · 00-transmittals/ · {package}/02-tender-pack/
05-progress-claims/
06-geotechnical/
07-construction/
```

---

## 6. Shot list — twelve reels, 140 seconds

Timings are targets, not law. The rhythm matters more than the clock: **prompt beats are
slow, resolution beats are fast.** Every reel must contain at least one moment where
nothing moves for 200ms — the film needs to breathe or the density reads as noise.

| Reel | In | Out | Beat |
|---|---|---|---|
| 0 | 0:00 | 0:05 | Cold open |
| I | 0:05 | 0:16 | The anchor prompt |
| II | 0:16 | 0:32 | The class cascade |
| III | 0:32 | 0:42 | Evidence lands |
| IV | 0:42 | 0:53 | The build |
| V | 0:53 | 1:05 | **The proof** |
| VI | 1:05 | 1:21 | **Three ways to change it** |
| VII | 1:21 | 1:33 | The cost plan |
| VIII | 1:33 | 1:49 | **The report arrives** |
| IX | 1:49 | 2:00 | Procurement |
| X | 2:00 | 2:11 | The loop closes |
| XI | 2:11 | 2:19 | Full cockpit |

Reels VI and VIII are new against the first pass — they carry the editing surfaces and the
mid-project document update. The film grew from 110s to 140s to hold them; §12 shows where
to take it back down.

---

### REEL 0 — Cold open · 0:00–0:05

**Camera.** Extreme close on an empty `ChatComposer`. Cursor blinking. Everything else in
the cockpit is present but out of focus, sitting in soft bokeh behind — the viewer can
tell there's a whole instrument there without being able to read it yet.

**Action.** Nothing for a full second. Then the cursor clicks in.

**On screen.** Nothing. No logo, no title card.

**Note.** Resist the title card. The film earns its name at the end, not the start. Five
seconds of restraint buys the density that follows.

---

### REEL I — The anchor prompt · 0:05–0:16

**Camera.** Hold on the composer. Pull back **very slightly** — 4–6% — as the text lands,
so the frame opens as the sentence completes.

**Action.** Sarah types prompt 14, verbatim, at realistic human speed with one visible
backspace correction. Send.

**Then, in the `ActivityStream`, in fast sequence:**

```
● Updated project profile
  revision 2 · changed: building_class, work_type, subclasses,
  scale, scope_narrative, budget, site_address
```

**The profile strip resolves, field by field** (`ProfileProposalStrip`):

| Field | Value |
|---|---|
| Building class | Residential |
| Subclass | House (Class 1a) |
| Work type | Extension / addition |
| Scale band | S · $250k–$2m |
| GFA | *not supplied* |
| Storeys | 2 |
| Budget | $750,000 |
| Planning | DA |

**On screen (caption).** `You do the judgement. SiteWise does the assembly.`

**Motion note.** Fields must **resolve**, not appear. Each one flickers through two or
three candidate values for ~80ms before settling — a classifier deciding, not a form being
filled. Subclass should visibly consider `house` / `townhouses` before landing on `house`.
This 80ms flicker is the film's signature motion and recurs at every classification.

**Critical detail.** `GFA` stays empty and greys out. Sarah didn't say. Nothing invents it.
Hold that empty field for a beat longer than feels comfortable.

---

### REEL II — The class cascade · 0:16–0:32

**The film's thesis, delivered as a barrage.**

**Camera.** Snap to the `ProjectSwitcher`. From here the camera locks to a fixed
three-quarter view of the cockpit and **does not move for 18 seconds** — only the contents
change. After Reel I's drift, this stillness is what makes the cascade feel violent.

**Action.** Eight project switches, each ~2.2s, each following an identical four-frame
grammar:

```
frame 1  prompt lands in composer     (0.8s — long enough to read the hook)
frame 2  taxonomy chips flicker       (0.4s — the 80ms signature, three cycles)
frame 3  chips lock, profile fills    (0.6s)
frame 4  left-nav tiles change state  (0.4s — Blocked → Ready)
```

**Sequence and the one value the eye must catch each time:**

| # | Project | The chip that lands |
|---|---|---|
| 1 | AC plant replacement | `commercial · office · refurb · XS` — **no Architect** |
| 2 | Eastern Creek warehouse | `industrial · warehouse · new · M` — `clear_height_m: 12` |
| 3 | 15MW data centre | `industrial · data_centre · new · L` — `redundancy_tier: 3` |
| 4 | Hospital ED | `institution · healthcare_hospital · refurb · L` — `ed_bays` |
| 5 | Rail station | `infrastructure · rail_metro · refurb · L` — `NCC: not_applicable` |
| 6 | Remedial concrete | `residential · apartments · remediation · S` |
| 7 | Advisory capital plan | `institution · healthcare_medical_centre · advisory · XS` |
| 8 | *bench flash* ×4 | cold storage, GMP, F&B, allied health — 0.4s each |

**Two frames that must be legible even at speed** — these are where a construction
professional either believes the film or doesn't:

1. **`NCC: not_applicable`** on the rail station. A taxonomy that knows infrastructure
   isn't a building class is a taxonomy someone in the industry built.
2. **The AC job's consultant list contains no Architect.** A mechanical engineer leads.
   Every generic AI tool puts an architect on a $180k plant swap. Hold this frame 400ms
   longer than the others and let the absence do the work.

**On screen (caption).** `Six classes. Five work types. $160k to $180m.`

**Sound.** This is the reel that carries the film's only real percussive motif — a soft
mechanical click per classification, like a rotary switch finding a detent. Eight clicks,
accelerating, then silence at the cut.

---

### REEL III — Evidence lands · 0:32–0:42

**Camera.** Glide right, over the main panel, into the `DocumentRepositoryPanel`. Slight
downward tilt — the sense of looking into a drawer.

**Action.** A drag of mixed files onto the repository. Deliberately messy, the way a real
project arrives — including the filename discipline no PM actually has:

```
Geotech_Report_Rev_C_FINAL.pdf
DA-Consent-Conditions.pdf
STRUCT-SK-01_to_SK-14.pdf
Hydraulic Quote - Wetherill Park.pdf
survey_detail&level.dwg
IMG_4471.HEIC
Scan 24-08-14 0932.pdf
Acoustic Report DRAFT v2.docx
```

**`IngestProgressStrip` runs.** Skeleton rows appear immediately, before any server work
completes — the optimistic-row pattern already in the product. Files fill in behind them.

**Then `SortFilesResultPanel` — the beat that sells it.** Each file animates from the drop
zone into a real folder, with the routing rule visible for a frame:

| File | Routed to | Rule shown |
|---|---|---|
| `Geotech_Report_Rev_C_FINAL.pdf` | `06-geotechnical/` | `report · geotechnical` |
| `DA-Consent-Conditions.pdf` | `04-planning-and-authorities/` | `consent · conditions` |
| `Hydraulic Quote - Wetherill Park.pdf` | `05-procurement/quotes/` | `quote → price schedule` |
| `Scan 24-08-14 0932.pdf` | `01-cost/` | `invoice` |
| `STRUCT-SK-01_to_SK-14.pdf` | `03-design/` | `drawing set` |
| `IMG_4471.HEIC` | `07-construction/` | `site photo` |

**On screen (caption).** `READ → SORT → RETRIEVE → BUILD`

Set the four words as a rail that fills left-to-right across this reel and the next two —
`READ` and `SORT` illuminate here, `RETRIEVE` in Reel IV, `BUILD` at the artefact reveal.
This is the same four-step rail the current landing hero uses; reusing it stitches the two
films together.

**Note.** `Scan 24-08-14 0932.pdf` routing itself to `01-cost/` is a planted seed. It pays
off in Reel X when the invoice loop closes. Nobody notices on first viewing. Everybody
notices on second.

---

### REEL IV — The build · 0:42–0:53

**Camera.** Swing back to the main panel. This is the film's widest move — a long arc
across the whole cockpit, ending square on the draft.

**Action.** `WorkflowRunCard` appears in chat. `WorkflowProgressStrip` runs. The PMP
**scaffolds first** — section headings land as an empty skeleton, all of them at once, and
*then* fill. This is the correct depiction and also the more impressive one: the audience
sees the shape of the finished document before any prose exists, which reads as
architecture rather than autocomplete.

**Sections landing, in order** (real section IDs):

```
snapshot · scope-client-requirements · consultants · ffe-schedule ·
compliance-approvals · programme · cost-budget · procurement-delivery ·
risks · actions-decisions · citation-key
```

**On screen, in the draft, held long enough to read** — real text from the corpus runs:

> | Discipline | Firm | Fee | Status | Citation |
> | --- | --- | --- | --- | --- |
> | Structural Engineer | — | | **Assumption / Not evidenced** | — |
> | Heritage Consultant | — | | **Assumption / Not evidenced** | — |

**Caption over this frame.** `It tells you what it doesn't know.`

**This is the most important caption in the film.** Every competitor's demo shows a
confident table. Ours shows a table admitting five of its rows are unevidenced. In a
domain where outputs become contract instruments, that admission *is* the product.

**Motion note.** The `Assumption` markers should land in a different weight and colour
from the evidenced content — the eye must be able to scan a page and separate what is
known from what is assumed in under a second. If the current UI doesn't differentiate them
strongly enough, the film is allowed to lead the product here; flag it as a design finding.

---

### REEL V — The proof · 0:53–1:05

**Stop the film.**

Twelve seconds where the pace breaks completely. Everything before this is fast; this is
slow, and the contrast is the whole point. Camera pulls back to a flat, orthographic,
straight-on view — the only non-perspective shot in the piece.

**Four PMPs, side by side, rendered at true relative length as four columns of text:**

```
   ROOF              RETAIL            WAREHOUSE          DATA CENTRE
   $160k             $7m               $18m               $180m
   XS                M                 M                  L
   commercial        commercial        industrial         industrial
   retail_standalone retail_standalone warehouse          data_centre

   ▓▓▓               ▓▓▓▓▓▓▓           ▓▓▓▓▓▓             ▓▓▓▓▓▓▓▓▓
   767 words         1,570 words       1,361 words        1,943 words
   ✓ in band         ✓ in band         ✓ in band          ✓ in band
     489–1,015         1,050–2,175       1,050–2,175        1,330–2,755
```

Then, under them, one line resolves:

```
Same product. Same prompt shape. 27.9% identical lines.
```

**Source.** Every figure is from
[`runs/wave-3-outcome-sheet.md`](test-prompt-corpus/runs/wave-3-outcome-sheet.md), run
2026-08-14, mechanically verified against the database, the generation manifest and the
artefact text. The 27.9% is prompt 5 vs prompt 26 — *same subclass*
(`commercial/retail_standalone`), different scale band. The hardest possible comparison,
and the documents still share barely a quarter of their lines.

**Why this beat exists.** It is the only moment in any SiteWise film that offers a
falsifiable number. Everything else asks for trust; this asks to be checked. Give it more
screen time than instinct suggests — 12 seconds of near-stillness in a 140-second film
feels wrong on paper and correct on screen.

**On screen (caption).** `A $160k roof does not need a $180m document.`

**Optional stinger, 1s, if the pace allows.** The same four-column diagram flashes to a
"before" state — Wave 1, where the same four documents were **94–98% identical** — then
snaps back. It shows the product was fixed rather than born perfect, which is more
credible, not less. Use only if the film can afford it; cut first if over length.

---

### REEL VI — Three ways to change it · 1:05–1:21

**The human half of the spine. If Reel V is what the machine does, this is what Sarah does.**

The product offers three distinct routes to change an artefact, and they escalate in
directness. The film shows all three, **in this order**, because the sequence itself is
the argument: the AI editor is available, but you are never trapped inside it.

**Camera.** Push in tight — closer than any other shot in the film. Text nearly fills the
frame. The intimacy is deliberate: this is the one moment the viewer is meant to imagine
their own hands.

---

#### VI-a · The AI editor — queue several, apply once · 1:05–1:14 (9s)

**This is the beat the first pass missed and it is the most important editing beat in the
film**, because it is the one no chat interface can do. Chat applies one change at a time
and re-runs the whole document. This marks up a document like a red pen, then commits the
lot in a single pass.

**Action — four instructions queued in sequence, each ~1.6s:**

| # | Section | Sarah selects | She types |
|---|---|---|---|
| 1 | Consultants | *the heritage consultant row* | `Add the party wall surveyor` |
| 2 | Programme | *"Stage 1 concept and schematic design"* | `Split this — DA lodgement is its own milestone` |
| 3 | Risks | *the adjoining-owner risk line* | `Raise this to high, the neighbour has objected before` |
| 4 | Compliance | *the conservation area paragraph* | `Name the heritage DCP clause we're working to` |

**The grammar of each one, shot identically four times:**

```
select passage        text highlights, offsets anchored
                      SelectionInstructionCard portals in below the selection
type instruction      Enter sends (Shift+Enter newlines — same contract as chat)
tray increments       "1 change queued" → "2 changes" → "3" → "4"
```

**The tray counter is the shot.** Push in on it as it climbs. Four sections marked up
across a document Sarah never scrolled away from, nothing applied yet, everything
reversible — each row carries its own `×` to remove, and `Clear all` sits beside it.

**Then one click.** The button reads exactly: **`Apply 4 changes`**. It is pressed once.

```
Applying…
StreamingIndicator: "Revising the sections you marked…"
```

Four sections revise **in parallel**, not sequentially — they light up together and settle
together. Every untouched sentence in the document stays byte-identical, which the film
shows negatively: the four marked sections shimmer, and *nothing else on the page moves*.
That stillness around the change is the whole point and must be legible.

**Caption.** `Mark up four sections. Apply them in one pass.`

**Precision notes for the animator — these are real behaviours, honour them:**

- The tray is **keyed to the draft version**. A tray built against v3 cannot apply to v4.
  If a stale tray is shown at all, it appears as a rebase prompt, never as silent loss.
- The tray persists in session storage — collapse the panel, come back, still there.
- Each queued row shows **section heading + the instruction text**, truncated. Not the
  selected quote. The heading is what the eye needs.
- If one instruction fails, it fails **alone** — that row turns red and keeps its error
  text, the other three land. Optional 1s beat if the film has room; it is a strong trust
  signal, and it is real.

---

#### VI-b · Direct editing — just double-click it · 1:14–1:18 (4s)

**No AI in this beat at all.** That is why it exists.

**Action, two edits, fast:**

1. **Double-click a paragraph.** It becomes editable in place. Sarah changes a few words —
   *"Clients living elsewhere"* → *"Clients living elsewhere until lock-up"* — and clicks
   out. Saved.
2. **Double-click a table cell.** The cell — not the row, not a modal — becomes editable in
   place. She corrects a figure. Enter. Saved.

Show the `<!-- clerk:block id=blk_… -->` marker for a single frame as each commits, so the
audience registers that edits are addressed and durable rather than re-drafted.

**Caption.** `Or just double-click and type.`

**Why this beat earns four seconds in a 140-second film.** Every AI document tool has a
trust ceiling, and it is reached the moment a professional wants to change three words and
is forced to *ask* for it. Showing a plain double-click, with no model in the loop, is what
converts a sceptical PM. It says: this is a document, it is yours, and the AI is optional.

Play it **completely straight** — no glow, no assist, no shimmer, no sparkle. It should
look boring. Boring is the message.

---

#### VI-c · The decision widget — it proposes, you decide · 1:18–1:21 (3s)

`DecisionControl` for the approvals pathway. The draft proposed `DA`, and the rationale is
visible and honest about itself:

> *"Placeholder only: no site, planning instrument, consent record or authority advice is
> available. DA is selected for working programme planning pending constraints review."*

Sarah reads it. Changes it to `CDC`. Behind the widget the stored state flips:

```
source:     agent  →  user
evidenced:  false  →  true
```

**Caption.** `It proposes. You decide.`

---

### REEL VII — The cost plan · 1:21–1:33

**Camera.** Slide down-left to `CostPlanGrid`. Lower, flatter angle — ledgers want to be
looked *down* at.

**Action.** The cost plan builds by category, in real structure:

| Cost Code | Category | Cost Items | Budget | Status | Basis |
|---|---|---|---|---|---|
| 1 | Fees and charges | Architect-PM fee | — | confirmed | Engagement letter |
| 6 | Consultants | Structural engineer | — | proposed | Not yet appointed |
| 12 | Construction | Investigations, surveys and opening-up | — | proposed | Structure only — no rate pack |
| 15 | Construction | Existing-structure repair and new structural work | — | proposed | Structure only — no rate pack |
| 21 | PC allowances | Kitchen joinery PC | — | proposed | Selection pending |
| 25 | Contingency | Owner-held contingency | — | proposed | 5–10% construction (benchmark) |

**The determinism beat.** When the total resolves, it does **not** stream. Every other
number in this film types itself in character by character. This one **snaps** — one
frame, no animation, hard. The visual grammar teaches the boundary without a word of
copy: *narrative is written, arithmetic is computed.*

If the film has budget for one piece of custom sound design, spend it here. A single dry
mechanical *thunk* against 140 seconds of soft interface tones.

**Caption.** `Narrative is drafted. Arithmetic is computed. Never the other way around.`

**Then the third editing mode — 4s.** Sarah clicks straight into the **Budget** cell on
code 21 and types a number. No dialogue, no instruction, no model. The cell is an input;
it always was.

```
click cell  →  type  →  Enter  →  committed
                               →  totals resnap in one frame
```

She does the same on a **forecast variation** cell one row down. Two edits, four seconds,
zero ceremony.

**Caption.** `Type over any sum. It recalculates, you don't.`

**Note.** The re-snap of the totals after a hand-typed figure is the determinism boundary
demonstrated from the *other* direction — the human supplies the number, the software does
the arithmetic. Same rule, inverted. Worth one deliberate frame.

**Closing beat, 3s.** The `Basis` column scrolls. Every line has one: `Engagement letter`,
`Benchmark`, `Not yet appointed`, `Structure only — no rate pack — pending head-builder
tender`. No line is silently sourced. Hold on the column, not the numbers.

---

### REEL VIII — The report arrives · 1:33–1:49

**The beat that proves the artefacts are alive.** Everything before this is a project being
set up. This is a project *running* — weeks later, a document lands that nobody planned
for, and the plan absorbs it.

**Camera.** Return to the repository, then a slow move across to the draft. This is the
only reel that crosses the full cockpit in one continuous unbroken move — the physical
distance from *where evidence lands* to *where it changes something* is the point.

**Action, four movements:**

**1. The document lands.** A single file into the repository:

```
Structural_Investigation_Report_47_Wilford_St.pdf
```

An opening-up and structural adequacy investigation on the existing semi — the survey that
in the corpus checks for prompt 14 sits behind *"structural adequacy of existing"*. It
routes itself to `03-design/` or `06-geotechnical/` depending on classification. No
workflow runs. The document just sits there. **Hold on that stillness for a full second** —
the film has trained the audience to expect immediate machine activity, and withholding it
here makes the next beat land.

**2. Sarah asks.** Back to the composer, one plain sentence:

> *"The structural investigation report is in. Update the PMP and the cost plan to reflect
> it."*

**3. The update runs.** `update_pmp` — and critically, it does **not** rebuild from
scratch. It retrieves only the evidence added *since the last draft* and revises against
the baseline. The `WorkflowProgressStrip` and trace should make this legible:

```
baseline          PMP v4
evidence delta    1 document since v4
sections revised  4 of 11
sections untouched 7 — byte-identical
```

**4. The rows change — and this is the shot.** Camera tight on the consultants and
compliance tables as `Assumption` rows upgrade to evidenced fact, each acquiring a
citation chip:

```
BEFORE                                          AFTER
Structural adequacy | Assumption            →   Structural adequacy | Fact  [2]
Existing footings   | Not evidenced         →   Mass concrete, 450 deep    [2]
Party wall condition| Assumption            →   Fact — cracking recorded   [2]
Structural Engineer | Assumption/Not evid.  →   Assumption / Not evidenced   ← UNCHANGED
```

**The last row is the most important frame in the film after 0:54.**

The consultant appointment row does **not** upgrade. A report arriving does not prove
anyone was engaged. The product's own text says so, and the film should surface it as a
tooltip or margin note held for a beat:

> *"A report or design input later received will not establish an appointment without
> engagement evidence."*

**Caption over that frame.** `It upgrades what the evidence proves. Nothing further.`

That single held row is the difference between a product that reads documents and a
product that reasons about what a document *is*. Every competitor's demo flips every field
green. Ours refuses one, and shows why.

**5. The cost plan follows.** Cut down to `CostPlanGrid`. The provisional line collapses
into a measured one:

```
15 | Existing-structure repair and new structural work
     proposed  · Structure only — no rate pack        ← before
     proposed  · Investigation report — measured      ← after
```

Contingency re-weights. The total re-snaps in one frame. The risk register gains a row and
the adjoining-owner risk moves up a band.

**Caption.** `One report. Four sections. Nothing else touched.`

**Alternative project for this reel, if remediation reads stronger:** corpus prompt 6 — the
1970s strata block with concrete cancer, whose checks are literally *"investigation before
scope lock"* and *"provisional sums for unknown extent"*. An investigation report there
collapses a provisional sum into a measured quantity, which is a purer cost story. It costs
the film its anchor continuity, which is why the Newtown version is primary. Pick one; do
not shoot both.

---

### REEL IX — Procurement · 1:49–2:00

**The one hard cut in the film.** Everything else glides; this snaps. Earn it here.

**Camera.** Hard cut to `ProcurementRequestPanel`, then a slow controlled pull back as the
documents stack.

**Action, three-part:**

**1. Consultant RFP.** Sarah asks in chat:

> *"Draft the RFP for the structural engineer."*

`consultant_procurement` runs. Document lands at
`02-consultant/consultant_procurement_structural_v01.draft.md`. Scope-of-services
sections stack up: design scope, documentation, certification, site-phase allowances.

**2. Trade RFT.** Switch project — the warehouse. Trade package procurement.
`05-procurement/{package}/02-tender-pack/`. The price schedule requirement is legible for
one frame:

> *"Detailed completed price schedule, trade breakdown, GST, provisional sums, allowances,
> options, and rates"*

**3. Tender comparison.** Cut to `TenderCockpitPage`. The matrix builds. Columns are
tenderers, rows are scope lines. The frames that matter are the **gaps** — the cells where
one tenderer has priced something the others silently omitted, flagged and rising.

**Caption over the matrix.** `Every tender against the scope, not just against the price.`

**Note on scope claim.** Beat 3 of the landing copy broadens tender comparison to
consultants **and** contractors **and** trades. That claim is flagged unverified in
[2026-08-08-landing-iteration-beats.md](2026-08-08-landing-iteration-beats.md). This film
should show whichever paths are genuinely supported at capture time and no more. See §14.

---

### REEL X — The loop closes · 2:00–2:11

**Back to the anchor.** Newtown. Months later — signalled only by the project switcher
landing on the same name and the draft version reading `v5` instead of `v1`.

**Camera.** Return to the exact framing of Reel I. Same angle, same distance. The
repetition is the message: *this is the same project, and it is still here.*

**Action.** An invoice arrives — the same `Scan 24-08-14 0932.pdf` shape planted in Reel
III. `InvoiceProcessStatus` runs. Then, in sequence, without a click:

```
invoice read           →  allocations mapped to cost items
CostInvoiceRegister    →  rows fill: date, supplier, amount, cost code, paid
CostPlanGrid           →  affected line moves from proposed → confirmed
                          Basis: "Not yet appointed" → "Invoice"
PMP                    →  draft advances v5 → v6
```

**And now the row from Reel VIII finally turns over.**

The structural engineer's consultant row — the one the investigation report pointedly did
**not** upgrade — flips at last, because an invoice *is* engagement evidence in a way a
report is not:

```
Structural Engineer | Assumption / Not evidenced   →   Appointed  [7]
```

**Caption over that flip.** `The report didn't prove it. The invoice does.`

This is the film's long rhyme, thirty seconds apart, and it is the single most persuasive
thing in the piece for anyone who has ever argued about whether a consultant was actually
engaged. It rewards a second viewing and costs nothing to build — the two frames are
already being shot.

**One allocation flags `needs_review`** and stops, waiting. It does not guess.

**Caption.** `Two rows reconciled. One flagged for you.`

**Why this is the right ending.** Most product films end at the moment of creation — the
document appears, music swells, cut to logo. Ending at *reconciliation months later* says
something no creation-moment can: the artefact is alive, and the system is still holding
the thread. The flagged row is the closing argument for the spine — the machine did the
assembly and handed the judgement back.

---

### REEL XI — Full cockpit · 2:11–2:19

**Camera.** The longest, slowest pull in the film. All the way out. Soft parallax across
four depth planes:

```
plane 1 (front)   chat rail, cursor
plane 2           main panel — PMP v4 open
plane 3           repository — folders populated
plane 4 (back)    left nav — every tile now reading Ready or Draft v4
```

Everything idles. `StreamingIndicator` breathes. A folder count ticks. Nothing demands
attention. After 115 seconds of density this stillness should feel like arriving somewhere.

**Text lands in two parts, 1.2s apart:**

```
You do the judgement.
SiteWise does the assembly.
```

Then, small, beneath:

```
sitewise.au
```

No logo animation. No swoosh. The mark appears at rest.

---

## 7. Motion and camera language

### The grammar

| Movement | When | Duration |
|---|---|---|
| **Glide** — eased pan/zoom between panels | Default. All inter-panel transitions | 400–700ms |
| **Snap** — instant, no tween | Project switches in Reel II; the cost total | 1 frame |
| **Drift** — sub-3% slow push | Under any beat holding >3s | continuous |
| **Lock** — camera absolutely still | Reel II cascade, Reel V proof | 12–18s |
| **Hard cut** — the only one | RFP stack reveal, Reel IX | 1 frame |

### Easing

`cubic-bezier(0.32, 0.72, 0, 1)` for all glides. Slight overshoot on arrival, no bounce.
The camera should feel like it is on a rig with real mass — heavy, damped, precisely
stopped. Never floaty, never elastic.

### The 80ms flicker — the film's signature

Every classification event flickers through 2–3 candidate values at ~80ms each before
settling. Not a slot machine, not a scramble effect: two or three *plausible* alternatives,
legibly wrong, then the right one. `townhouses` → `house`. `refurb` → `extend`. This
single motif carries the entire "it is deciding, not filling in" argument, and it should
appear at least fourteen times.

### Text behaviour — three distinct treatments the viewer learns

| Treatment | Means | Used for |
|---|---|---|
| **Types** — character by character, variable speed | A person or a model is composing | Prompts, narrative prose |
| **Resolves** — 80ms flicker then settle | A classifier is deciding | Taxonomy, chips, profile fields |
| **Snaps** — one frame, no animation | Software computed it | Totals, counts, deltas |

By Reel VII the audience has internalised this without being told, which is exactly why
the cost total landing in one frame reads as *computed* rather than *fast*.

### The cursor

One cursor, throughout. It is the only anthropomorphic element in the film and the
viewer's sole proxy. Rules:

- It **never** moves faster than a human hand could move it.
- It **rests** during machine work. A cursor that keeps twitching while the system works
  reads as impatience; a cursor that goes still reads as trust.
- It has a faint trail on fast moves — 2 frames, 20% opacity, no more.
- It never clicks anything the film hasn't shown the viewer first.

### Parallax

Reserve for the two widest shots (Reels V and XI). Four depth planes, maximum 8px
separation at the extremes. Enough to sell that the cockpit is a space; not enough to
notice as an effect.

---

## 8. Typography, colour, atmosphere

**Type.** Whatever the SPA ships. Do not introduce a display face for captions — set
captions in the product's own UI font at large size. The film should look like the product
grew captions, not like a marketing layer was painted over it.

**Colour.** The cockpit's own palette, unmodified. Two exceptions, and only two:

1. `Assumption` / `Not evidenced` markers may be pushed one step in contrast so they read
   at video compression. If they need pushing for the film, they probably need pushing in
   the product — log it.
2. The `needs_review` flag in Reel X gets the film's single moment of saturated colour.
   It should be the most colourful frame in 125 seconds. One flag, once, and it is the
   thing the viewer remembers.

**Atmosphere.** Reuse `SwAtmosphere` if it composites cleanly. Otherwise a very slight
vignette and 1–2% film grain to stop large flat panels from banding under compression.

**Screen realism.** Real cursor, real focus rings, real scrollbars, real 60fps scroll
inertia. Do not clean up the UI for the camera. A visible loading skeleton is worth more
than a perfect frame — it is the texture of software that actually runs.

---

## 9. Caption script — full, timecoded

Silent-with-music is the default. Captions carry the argument. VO optional (§10).

| In | Out | Caption | Reel |
|---|---|---|---|
| 0:11 | 0:15 | You do the judgement. SiteWise does the assembly. | I |
| 0:18 | 0:23 | Six classes. Five work types. $160k to $180m. | II |
| 0:27 | 0:31 | The same three sentences. Eight different buildings. | II |
| 0:34 | 0:40 | READ → SORT → RETRIEVE → BUILD | III |
| 0:44 | 0:48 | It builds the plan you were going to write by hand. | IV |
| 0:49 | 0:53 | **It tells you what it doesn't know.** | IV |
| 0:56 | 1:01 | A $160k roof does not need a $180m document. | V |
| 1:02 | 1:05 | Measured, not asserted. | V |
| 1:11 | 1:14 | Mark up four sections. Apply them in one pass. | VI-a |
| 1:15 | 1:18 | Or just double-click and type. | VI-b |
| 1:18 | 1:21 | It proposes. You decide. | VI-c |
| 1:24 | 1:28 | Narrative is drafted. Arithmetic is computed. | VII |
| 1:29 | 1:33 | Type over any sum. It recalculates, you don't. | VII |
| 1:41 | 1:45 | **It upgrades what the evidence proves. Nothing further.** | VIII |
| 1:46 | 1:49 | One report. Four sections. Nothing else touched. | VIII |
| 1:53 | 1:58 | Every tender against the scope, not just against the price. | IX |
| 2:03 | 2:06 | The report didn't prove it. The invoice does. | X |
| 2:07 | 2:10 | Two rows reconciled. One flagged for you. | X |
| 2:12 | 2:19 | You do the judgement. SiteWise does the assembly. | XI |

**Caption rules.**

- Maximum 9 words. Most should be 5–7.
- Bottom-left, aligned to the cockpit's own left margin, never centred.
- Fade in 200ms, hold, fade out 200ms. Never slide, never scale, never typewriter.
- Never over a moment the viewer needs to read UI text. Captions and artefact text must
  never compete — if they collide, the caption loses.
- **The two bolded captions are the film's hinges** — 0:49 (*it tells you what it doesn't
  know*) and 1:41 (*it upgrades what the evidence proves*). They are the same argument
  stated once negatively and once positively, fifty seconds apart. Both get 200ms more air
  on each side than any other caption. If the film has to lose captions for length, these
  two are the last to go.
- Reel VI carries three captions in sixteen seconds — the densest run in the film. That is
  correct: three modes, three labels. Do not merge them into one summarising line, because
  the point is precisely that they are *different routes*, not one feature.

---

## 10. Audio

**Default: music + interface sound, no VO.** The film is dense; a voice would compete with
fourteen classification events and four tables. Let the pictures argue.

**Music.** Something with a mechanical pulse rather than a melodic arc — the sonic
equivalent of the product's own tension between material and computational. It must do
three things: sit still under Reel V, accelerate through Reel II, and resolve — not
crescendo — at Reel XI. No trailer risers, no vocal chops, no drop.

**Interface sound.** Sparse and diegetic:

- Soft mechanical detent per classification (Reel II — eight of them, accelerating)
- Paper-adjacent shuffle on the RFP stack reveal (Reel IX)
- One dry *thunk* on the cost total (Reel VII) — the film's only hard sound
- Silence under Reel V. Total. The proof beat has no soundtrack at all, and that
  twelve-second hole is what makes it land.

**If VO is required** (paid placements often demand it): write to the caption script, not
over it. Same words, spoken. Australian voice, not performed. Under-energised rather than
over. Never explain something the picture already shows — VO exists to say the things the
film cannot draw, and there are only three: the boundary, the measurement, and the spine.

---

## 11. The proof beat — build notes

Reel V carries more argumentative weight than the rest of the film combined. Detail so it
can be built without re-deriving anything.

**Source of record:**
[`docs/plans/test-prompt-corpus/runs/wave-3-outcome-sheet.md`](test-prompt-corpus/runs/wave-3-outcome-sheet.md)

**Run provenance** — available if a "how was this measured" overlay is wanted:

```
run date      2026-08-14, 10:17–11:17 UTC
prompts       corpus 5, 26, 31, 35
build         bfe7a350-dirty
queue_scope   dev
compiler      adaptive_scaffold
attempt       1 · state complete
grading       C1–C4, C6, C8 mechanically verified
              C5, C7, C9 marked [J] — judged
```

**The four documents:**

| Prompt | Project | Class / subclass / work | Band | Words | Band range | In band |
|---|---|---|---|---:|---|---|
| 5 | Roof replacement | commercial / retail_standalone / remediation | XS · $160k | 767 | 489–1,015 | ✓ |
| 26 | Standalone retail | commercial / retail_standalone / new | M · $7m | 1,570 | 1,050–2,175 | ✓ |
| 31 | Warehouse | industrial / warehouse / new | M · $18m | 1,361 | 1,050–2,175 | ✓ |
| 35 | Data centre | industrial / data_centre / new | L · $180m | 1,943 | 1,330–2,755 | ✓ |

**Identical-line similarity** — the number that actually proves it:

| Pair | Identical | Note |
|---|---:|---|
| 5 vs 26 | **27.9%** | *same subclass*, XS vs M — the diagnostic pair |
| 5 vs 31 | 26.1% | |
| 5 vs 35 | 27.8% | class, work type and band all differ |
| 26 vs 31 | 49.5% | both band M, different class |
| 26 vs 35 | 23.3% | |
| 31 vs 35 | 25.5% | industrial M vs L |

No pair above 50%. Wave 1 was 94–98%.

**On-screen numbers must match this table exactly.** If the animator needs a round number
for composition, change the composition, not the number. The entire value of this beat is
that someone could go and check it.

**Honesty note for the optional 94–98% stinger.** That figure is Wave 1 — an earlier build
of the product, not a competitor. If it appears on screen it must be labelled as
SiteWise's own earlier behaviour. Framing our own former weakness as a rival's is the one
move that would make this beat dishonest, and it is the beat whose whole job is honesty.

---

## 12. Cut-downs

Build the 140s master so these fall out of it without re-shooting.

### 90s — landing page alternate

Drop Reel III and Reel IX. Keeps both editing reels and the report update — the two things
a considering buyer actually wants to see. Loses file routing and procurement.

### 60s — paid social / pre-roll

Drop Reels III, VI-b, VI-c, VII's direct-sum beat, and IX. Keeps: prompt → cascade → build
→ proof → tray → report update → invoice loop.

```
0:00  cold open + anchor prompt        (compressed to 8s)
0:08  class cascade                    (5 projects, not 8)
0:20  the build + "tells you what it doesn't know"
0:28  the proof — four documents        (8s, not 12)
0:36  the tray — 4 queued, applied once (6s)
0:42  the report arrives, rows upgrade  (10s)
0:52  invoice loop closes
0:56  full cockpit + spine
```

**Note on what survives the cut.** The tray beat stays in the 60s even though it is the
newest addition, because it is the only sequence in the film a competitor cannot shoot. The
proof beat and the tray beat are the two non-negotiables at every length above 30s.

### 30s — performance

Cascade and proof only. Prompt at 0:00, five classifications by 0:14, four-document
comparison 0:14–0:24, spine 0:24–0:30. No cost plan, no procurement, no invoices. This cut
makes exactly one argument — *it knows what kind of building this is* — and makes it hard.

### 15s — top of funnel

Three classifications and the four-document diagram. Nothing else.

### 6s — bumper

The 80ms flicker resolving `industrial · data_centre · new · L`, then the spine. One
classification, one line of text. The whole product compressed to a single detent click.

### Loopable 12s — trade show / in-page autoplay

Reel II cascade only, seamlessly looping, no captions, no audio. Runs silently beside a
headline on the landing page or on a stand screen. Should be watchable for two minutes
without irritation, which means: no hard cuts, no bright flashes, and the loop point must
land mid-cascade rather than at a natural end.

---

## 13. Capture list — what to send

You offered screenshots and screen movies. Precisely what is needed, in priority order.
**Real captures beat anything reconstructed** — a rebuilt UI always reads slightly wrong to
people who use the real one, and this audience will.

### Priority 1 — without these the film cannot be built

| # | Capture | Notes |
|---|---|---|
| 1 | **Full cockpit, wide, populated project** | Default panel widths (190/368). Every panel visible. This is the master plate for Reels 0, V, X. |
| 2 | **Chat rail, empty composer, cursor** | Clean start state. |
| 3 | **Chat rail mid-run** | `ActivityStream` + `ToolActivityFeed` + `WorkflowRunCard` + `StreamingIndicator` all live. **Screen movie, not still.** |
| 4 | **`ProfileProposalStrip` resolving** | Movie. From empty to populated. The single most valuable capture in this list. |
| 5 | **`TaxonomyPicker` open** | Showing class → subclass → work type. Still is fine. |
| 6 | **PMP draft, scrolled** | Must include visible `Assumption` and `Not evidenced` markers, a consultant table, and a ```pmp-decision``` widget. |
| 7 | **`CostPlanGrid` populated** | Cost Code / Category / Cost Items / Budget / Status / Basis columns all legible. |
| 8 | **`CostInvoiceRegister` with rows** | Include at least one `needs_review` allocation if one exists. |
| 9 | **`SelectionInstructionCard` open** | Movie. Text selected in the PMP, card portalled below it, instruction being typed. Repeat on 4 different sections. |
| 10 | **`InstructionTray` filling and applying** | Movie, and the highest-value capture in this list after #4. Must show the counter climbing 1→2→3→4, the `Apply 4 changes` button, the `Revising the sections you marked…` indicator, and the sections settling. |
| 11 | **Double-click into a paragraph** | Movie. Real double-click sequence — hover, double-click, edit in place, click out, saved. Do not stage it as a click on a pen icon; there isn't one. |
| 12 | **Double-click into a table cell** | Movie. The *cell* becomes editable, not the row, not a modal. |
| 13 | **`CostPlanGrid` money cell being typed into** | Movie. Click cell → type → Enter → totals resettle. Capture a `forecast_variations` cell too if populated. |
| 14 | **An `update_pmp` run against new evidence** | Movie + before/after markdown. See the run recipe in §14 — this one has to be *performed*, not found. |

### Priority 2 — needed for full 140s, not for the 60s cut

| # | Capture | Notes |
|---|---|---|
| 15 | `IngestProgressStrip` running | Movie. Skeleton rows → filled. |
| 16 | `SortFilesResultPanel` after a sort | Files routed into real folders. |
| 17 | `WorkspaceExplorer` folder tree expanded | All 8 folders visible. |
| 18 | `InlineTableRowEditor` in use | Movie. Add, edit, delete. |
| 19 | `DecisionControl` widget | Both states — agent-proposed and user-overridden. |
| 20 | `ProcurementRequestPanel` with a draft | Consultant RFP preferred. |
| 21 | `TenderCockpitPage` matrix | Populated with 3+ tenderers. |
| 22 | `WorkflowTracePanel` expanded | Proves the trace exists. Even 2s on screen is worth it. |
| 23 | `ProjectSwitcher` open | Must list projects of visibly different classes. |
| 24 | `InstructionTray` with one failed item | The red row with its error text. Small, and a real trust signal. |

### Priority 3 — nice to have

| # | Capture |
|---|---|
| 25 | `InsufficientEvidenceBanner` — a real one, if it can be triggered |
| 26 | `CitationChip` → `SourcePassagePanel` opening |
| 27 | `WorkflowProgressStrip` at 3–4 different percentages |
| 28 | Left nav with mixed tile states — Ready / Blocked / Draft v2 / Running |
| 29 | A stale-tray rebase prompt (tray built on v3, draft now v4) |

### Capture technical spec

- **Resolution:** 2560×1440 minimum. 3840×2160 preferred — the film crops and pushes in
  hard, and Reel VI's tight push will expose anything softer.
- **Frame rate:** 60fps for all movies. Non-negotiable for the scroll and streaming shots.
- **Chrome:** browser UI hidden. No bookmarks bar, no tabs, no extensions, no OS dock.
- **Theme:** capture **both** light and dark for the master plate (#1). Decide after, when
  the music is in — the atmosphere may want dark and the tables may want light.
- **Data:** use real corpus projects. Names from §4 are ideal. Nothing that could be
  mistaken for a real client.
- **Cursor:** visible in movies. Move deliberately and slowly — it will be retimed, but
  it can't be un-jittered.
- **Length:** capture 3–5× longer than needed on every movie. Runway for retiming is worth
  more than tidy files.

---

## 14. Claims ledger

Every factual assertion the film makes, and whether it can be defended. `PRODUCT.md` bars
fabricated time-saved claims — this table is how the film stays inside that.

| Claim | Status | Source / required action |
|---|---|---|
| Six building classes, 47 subclasses, five work types | **Defensible** | `data/taxonomy/building-classes.json` |
| Four scale bands XS/S/M/L with those thresholds | **Defensible** | corpus rubric |
| 767 / 1,570 / 1,361 / 1,943 words, all in band | **Defensible** | wave-3 outcome sheet, mechanically verified |
| 27.9% identical lines, prompt 5 vs 26 | **Defensible** | wave-3 outcome sheet |
| Wave 1 was 94–98% identical | **Defensible, label carefully** | Must be labelled as SiteWise's own earlier build |
| Four PMPs across four classes in one run window | **Defensible** | wave-3 sheet: 10:17–11:17 UTC, 2026-08-14 |
| Arithmetic computed in software, not by the model | **Defensible** | `PRODUCT.md` positioning; deterministic cost/tender arithmetic in Python |
| Facts trace to evidence or versioned doctrine | **Defensible** | `Assumption` / `Not evidenced` markers, citation key |
| Files route automatically to workspace folders | **Defensible** | `intake/classifier.py` |
| Invoices reconcile to cost items with review flags | **Defensible** | `process_invoices.py`, `map_invoice_allocations` |
| Several instructions queue and apply in one pass | **Defensible** | `InstructionTray` + `lib/instruction-tray.ts` + `draft_instructions.py` |
| Untouched sentences come back byte-identical | **Defensible** | `draft_instructions_instructions.md`: *"Every sentence you touch that was not part of a requested change is damage."* |
| The tray is version-keyed and rebases rather than silently dropping | **Defensible** | `lib/instruction-tray.ts` — `loadStaleTray` |
| Any paragraph or table cell edits in place on double-click | **Defensible** | `MarkdownContent.tsx` `onDoubleClick`; covered by tests in `MarkdownContent.test.tsx` and `DraftReviewPanel.test.tsx` |
| Cost plan sums are typed over directly | **Defensible** | `CostPlanGrid.tsx` — `cost-plan-grid-cell--editable` money inputs with `onCommit` |
| A new document updates the plan against only the evidence delta | **Defensible (mechanism)** | `update_pmp.py` — `retrieve_project_evidence_delta(since=baseline.created_at)`; prompt instructs *"Upgrade Assumption rows to Fact where new evidence supports it"* |
| A report does not establish a consultant appointment | **Defensible** | Verbatim in generated artefacts: *"A report or design input later received will not establish an appointment without engagement evidence."* |
| **"Saves PMs X hours"** | **NOT defensible** | No source. **Do not put a time figure on screen.** |
| **"X% more accurate"** | **NOT defensible** | No baseline study exists. |
| Tender comparison spans consultants **and** contractors **and** trades | **UNVERIFIED — open** | Flagged open in the 2026-08-08 doc. Confirm all three paths run before Reel IX shows all three. |

### The one gap — Reel VIII has no recorded run behind it

**The mechanism is real and first-class. The evidence of it running is not on file.**

`update_pmp` exists, is wired to an `Update PMP` button in `ProjectControlBoard.tsx` and to
a chat command, retrieves only evidence added since the baseline draft, explicitly upgrades
`Assumption` rows to `Fact`, and **fails validation if new evidence arrived and the revised
document cites none of it** (`has_evidence_delta and not output.evidence_refs`). That last
check is a strong guarantee and worth showing.

But every follow-up in the test corpus is **text-only** — *"Add a provisional sum of $25k
for asbestos"*, *"The chillers have a 26 week lead time"*, *"Infection control have said we
need negative pressure hoarding"*. None of them upload a document and ask for an update. So
there is **no captured artefact pair** showing a report landing and rows upgrading, which is
exactly the frame Reel VIII is built around.

**Run it before capture.** Recipe:

1. Open corpus prompt 14 (Newtown extension). Let `create_pmp` complete — that is the
   baseline.
2. Upload a structural investigation report into the workspace. A real one, or a plausible
   opening-up report naming footing type, depth, and party-wall cracking — enough that
   specific `Assumption` rows have something concrete to resolve against.
3. Prompt: *"The structural investigation report is in. Update the PMP and the cost plan to
   reflect it."*
4. Capture the run, and diff `v_n` against `v_n+1`.

**What the run has to demonstrate for the reel to work as written:**

- Some `Assumption` rows upgrade and acquire citations.
- The consultant appointment row **does not** upgrade.
- Most sections come back untouched.
- The cost plan basis on the affected line changes.

If the run doesn't produce that shape, **the film is wrong, not the product** — rewrite
Reel VIII to what actually happened. Do not animate the intended behaviour. This is the
single highest-risk dependency in the brief; everything else can be shot from what exists
today.

**Second-choice project** if the anchor doesn't produce a clean diff: corpus prompt 6, the
remedial concrete strata block, whose whole work type is built on investigation preceding
scope lock.

### On the time-saving ask

The brief calls for "saving PM time." The film should absolutely
make that argument — it just can't make it with an invented number. Two honest routes:

1. **Show it instead of claiming it.** The relay *is* the time argument. Eight projects,
   six classes, $160k to $180m, in 140 seconds. Nobody watching needs to be told what that
   would have taken by hand.
2. **Use the real run window.** *"Four project management plans. Four building classes.
   One hour."* That is measured, sourced, and stronger than a made-up multiple — because
   it can be checked.

Route 1 is the default. Route 2 is available if a hard number is commercially required.

---

## 15. Handoff prompt

Hand this with the §13 captures.

> Build a 140-second product film for SiteWise, an agentic construction project delivery
> platform for Australian built-environment professionals. Use the attached real UI
> captures. Do not invent interface — animate the actual screens provided.
>
> **Structure — a relay, not a story.** The camera never leaves the product cockpit. What
> changes is the project inside it. A project manager types one short, rough,
> unpunctuated prompt; the system resolves the building's class, subclass, work type and
> scale band, and builds a delivery plan proportionate to it. Then the project switches
> and it happens again — eight times, across eight completely different buildings: a
> $750k heritage-area house extension; a $180k air-conditioning plant replacement; a
> 12,000sqm warehouse; a 15MW Tier III data centre; a hospital emergency department that
> cannot close; a rail station upgrade worked in track possessions; concrete remediation
> on a 1970s strata block; a ten-year capital works advisory.
>
> **Twelve reels.** (0) Cold open on an empty composer. (I) The anchor prompt lands; the
> project profile resolves field by field, and one field stays deliberately empty because
> the prompt didn't say. (II) The class cascade — eight projects in sixteen seconds,
> camera locked still, taxonomy chips flickering through candidates and locking. (III)
> Mixed real-world files dropped in and routed to real workspace folders. (IV) The plan
> scaffolds first as empty headings, then fills — and the consultant table openly reads
> "Assumption / Not evidenced". (V) **The proof: the film stops.** Four plans side by side
> at true relative length — 767, 1,570, 1,361 and 1,943 words, each inside its scale band,
> sharing only 27.9% of their lines. Twelve seconds. No sound at all.
>
> (VI) **Three ways to change it, in escalating directness.** First the AI editor: she
> selects a passage, types a short instruction, and it queues — then does it three more
> times in three more sections, the tray counter climbing 1, 2, 3, 4, nothing applied yet
> and everything reversible. One click on "Apply 4 changes", and all four sections revise
> together in a single pass while every untouched sentence on the page stays perfectly
> still. Then, with no AI at all: she double-clicks a paragraph and simply types over it,
> then double-clicks a table cell and corrects it in place — play this completely straight,
> no glow, no shimmer, boring on purpose. Then the decision widget: the plan proposed a
> planning pathway and admitted in writing that it was a placeholder; she overrules it.
>
> (VII) The cost plan builds; the total lands in a single frame with no animation because
> software computed it, not the model — then she clicks straight into a budget cell, types
> a figure, and the totals resettle in one frame. (VIII) **Weeks later, a document arrives
> that nobody planned for** — a structural investigation report. It lands in the repository
> and nothing happens; hold on that stillness. She types one sentence: "the structural
> investigation report is in, update the PMP and the cost plan to reflect it." The plan
> revises against only the new evidence: several rows that read "Assumption" upgrade to
> evidenced fact with citations — **and one row pointedly does not**, because a report
> arriving does not prove a consultant was ever engaged. Hold that refusal. Seven of eleven
> sections come back untouched. (IX) One hard cut — the only one in the film — to a stack
> of procurement documents; then a tender comparison matrix where the gaps light up. (X)
> The loop closes: months later an invoice arrives, reconciles itself into the register,
> flips a cost line from proposed to confirmed — and the consultant row the report refused
> to upgrade finally turns over, because an invoice is engagement evidence in a way a
> report is not. One allocation flags for human review and stops. (XI) Pull all the way out
> to the full cockpit at rest.
>
> **Motion grammar — three text behaviours the viewer learns without being told.** Text
> that a person or model composes **types**, character by character. Text a classifier
> decides **resolves** — flickering through two or three plausible wrong values at 80ms
> each, then settling. Text that software computed **snaps** in a single frame with no
> animation. By the time the cost total lands, the audience reads "computed" rather than
> "fast". Camera glides between panels on eased 400–700ms moves with real mass and no
> bounce; locks absolutely still for the cascade and the proof; cuts hard exactly once.
> One cursor throughout, moving no faster than a hand, resting while the machine works.
>
> **Tone.** Precise and calm, not flashy. Fast, but never frantic. The persuasion comes
> from fluency and honesty, not effects — the single most important frame in the film is
> the one where the document admits what it doesn't know.
>
> **Language rules, strict.** Never use the words "ingest" or "generate". Approved verbs:
> reads, sorts, files, retrieves, builds, assembles, drafts, reconciles, checks. The
> closing line is "You do the judgement. SiteWise does the assembly." Captions maximum
> nine words, bottom-left, fade only. No invented statistics — every number on screen is
> supplied in the accompanying brief and must be reproduced exactly.
>
> **Deliver a timecoded shot-by-shot storyboard first**, then the film, then the 60s, 30s,
> 15s and 6s cuts falling out of the same master.

---

## 16. Open decisions

Resolve before capture — each changes what gets shot.

| # | Decision | Recommendation |
|---|---|---|
| 1 | Light or dark cockpit? | Capture both. Decide with music in. Dark suits the atmosphere; the tables in Reels V and VII want light. |
| 2 | VO, captions, or silent? | Captions + music. VO only if a paid placement demands it. |
| 3 | Does the Wave 1 94–98% stinger appear? | Include if length allows, labelled as our own earlier build. First to cut. |
| 4 | Does Reel IX show all three tender paths? | Only those verified running at capture time. See §14. |
| 5 | Anchor project — keep the Newtown semi? | Yes. It preserves the original brief's $750k second-storey story and is the most relatable entry point in the corpus. |
| 6 | Where does this sit on the landing page? | Directly below the abstract film, under a heading that hands over the burden of proof. |
| 7 | Do `Assumption` markers need more contrast in the product? | Probably. If the film has to push them, that is a product finding, not a film problem. |
| 8 | Does the invoice loop use a real processed invoice? | Strongly preferred. A real reconciliation is the hardest thing in the film to fake convincingly. |
| 9 | **Who runs the Reel VIII update before capture?** | Blocking. §14 has the recipe. Nothing else in the film depends on work that hasn't happened yet. |
| 10 | Reel VIII on the anchor, or on the remediation project? | Anchor (Newtown) for continuity; prompt 6 if the diff is cleaner. Decide from the actual run output, not in advance. |
| 11 | Does the failed-tray-item beat make the cut? | Include if the 140s holds. It is a small frame with disproportionate trust value. |
| 12 | Is 140s too long for the landing page? | Probably fine below the abstract film, where the viewer has already self-selected. Use the 90s cut if analytics say otherwise. |

---

## Appendix — one-line summary of every reel

| Reel | Seconds | One line |
|---|---|---|
| 0 | 5 | An empty box and a cursor. |
| I | 11 | Three rough sentences become a classified project. |
| II | 16 | Eight buildings, one interface, camera never moves. |
| III | 10 | The mess of a real project files itself. |
| IV | 11 | The plan builds — and admits what it doesn't know. |
| V | 12 | Four documents, four sizes, measured. Silence. |
| VI | 16 | Queue four changes and apply them at once — or just double-click and type. |
| VII | 12 | Narrative streams. Arithmetic snaps. You type over the sum. |
| VIII | 16 | A report lands weeks later. Rows upgrade. One refuses to. |
| IX | 11 | The only hard cut, and a matrix that finds the gaps. |
| X | 11 | An invoice closes the loop — and proves what the report couldn't. |
| XI | 8 | Everything at rest. The spine lands. |
