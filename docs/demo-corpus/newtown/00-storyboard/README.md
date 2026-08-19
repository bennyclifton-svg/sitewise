# 41 Georgina Street — the film

**What this is.** A ~2:55 landing film built on the Newtown demo corpus, refactored on the
assumption that the X1 / Pulse programme
([`docs/plans/2026-08-18-pulse.md`](../../../plans/2026-08-18-pulse.md)) is fully
implemented and in production.

The corpus is unchanged in substance: same house, same firms, same money, same dates. What
changes is **who is carrying it** and **how the work arrives**. Uploads become email.
Buttons become Pulse cards. A site walk becomes a voice note. The project stops being a
filing system and starts being something that tells her what changed and what needs her.

Companion file: [`run-sheet.md`](./run-sheet.md) — every prompt, in order, with expected
results and defect checks, for the capture session.

---

## The one change to the corpus

The owners in [`01-brief/owners-project-brief.md`](../01-brief/owners-project-brief.md) are
Daniel and Anthea Marchetti. **Anthea becomes Sarah.** Nothing else moves — every generated
invoice, proposal and quotation still addresses "the Marchettis", so
`generate-commercial.py` and the design-document generator do not need re-running.

Sarah Marchetti is the protagonist and the only decision-maker on screen. Daniel exists,
works, and is not in the film. That is deliberate, and it is true to how these projects
actually run: one person ends up holding it.

---

## Sarah

| | |
|---|---|
| **Age / work** | 41. Commercial litigator, mid-tier Sydney firm. Seven years off partnership. |
| **Domain knowledge** | None. She has never read a DCP, an NCC clause or a BASIX certificate. |
| **What she is unusually good at** | Finding the thing that is *missing* from a document. It is literally her job. |
| **Why that is the whole problem** | The skill does not transfer. She can tell a builder's quotation is thin. She cannot tell you that the thin part is a $78,000 plunge pool, a 4.2 m³ detention tank and a heritage brickwork condition. |
| **Constraint** | She cannot take a day off. Court dates do not move for site meetings. |
| **Stakes** | Two kids, 9 and 12. A rental for the whole build — rent *and* mortgage *and* progress claims. A hard ceiling of $950,000 all-in, not a preference. |
| **The room that matters** | The Parents' Retreat. 14 m², first floor, rear aspect, must take a sofa bed. It is for her parents, whose visits are getting longer. It is why she is extending instead of moving. |

### The emotion the film is actually about

Not delight. Not "wow, software".

Sarah's professional identity is *not being blindsided*. She is paid to be the person in
the room who saw it coming. On this project she is, for the first time in twenty years, the
least informed person at the table — and the exposure is her own money and her own family.
That is a specific and quite acute anxiety, and it is not solved by a prettier Gantt chart.

**The promise the film makes: you will not be blindsided.**

Every save in the film is the same shape — something was missing, and the missing thing was
found *before* it cost her. That is the emotional through-line, and it is also, conveniently,
the honest product claim.

---

## Constraints this script obeys

Read these before editing a word of copy.

1. **Doctrine copy rules** — `landing-messaging-doctrine`. The closing card is the spine:
   *You do the judgement. SiteWise does the assembly.* The words **INGEST** and **GENERATE**
   are banned on screen and in VO. Approved verbs: READ · SORT · RETRIEVE · BUILD.
2. **No fabricated benchmarks** (PRODUCT.md). No "saves 200 hours", no "10× faster", no
   time-to-completion claims. Every number on screen comes from the corpus and is verified
   by its own generator. The film's proof is *arithmetic*, not testimony.
3. **No autonomous action** (doctrine D7). Nothing sends, posts, approves or pays without
   Sarah. Every drafted email in the film is visibly *drafted*. This is not a compliance
   footnote — it is why the film works. She is not being replaced; she is being briefed.
4. **Disclosure.** A persistent, legible corner slug from 0:00: *Demonstration project.
   Firms, documents and figures are fabricated.* Non-negotiable — the corpus README is
   emphatic about it, and the audience is the one group who will check.

### One open positioning question — flagged, not resolved

The recorded landing doctrine rejected persona-led framing partly because **the audience is
the senior PM**, and a persona headline competes with the reader's own title. This film is
persona-led and the persona is a *lay client*. Those are different funnels.

Either this film sits on a different surface from the hero (owner / one-off-client entry,
while the hero keeps speaking to PMs), or the positioning has widened and
`docs/plans/2026-08-06-landing-messaging.md` needs updating to say so. **Worth deciding
before production spend, not after.** The script works either way; the placement does not
decide itself.

---

## Run of show

Timings are cut targets, not gospel. Total **2:55**.

| # | Time | Beat | Trigger | The feeling |
|---|---|---|---|---|
| 0 | 0:00–0:16 | One sentence, 11:40 pm | typed | dread |
| 1 | 0:16–0:32 | The profile resolves — and refuses to guess | — | first flicker of trust |
| 2 | 0:32–0:44 | She corrects it. It stays corrected. | hand + typed | authority |
| 3 | 0:44–1:00 | The brief arrives by email. 5 rows → 26. | email | competence |
| 4 | 1:00–1:18 | The heritage statement nobody priced | typed | **first save — money** |
| 5 | 1:18–1:34 | Sandstone rubble at 410 mm | photo + email | **second save — technical** |
| 6 | 1:34–1:44 | Revision C, and who is still holding Rev B | automatic | control |
| 7 | 1:44–1:58 | 34 conditions become 34 obligations | automatic | the fear, contained |
| 8 | 1:58–2:26 | The cheapest quote is the dearest job | typed | **the showpiece** |
| 9 | 2:26–2:36 | Saturday. Site. Spoken. | voice | ease |
| 10 | 2:36–2:50 | Monday. The car. Three things. | voice | mastery |
| 11 | 2:50–2:55 | The room upstairs | — | landing |

---

## Voice-over — full script

Delivery: unhurried, low, factual. **The numbers do the selling; the read must not.** No
rising inflection, no wonder. Closer to a case note read aloud than to an ad.

> **0:00** Sarah Marchetti reads contracts for a living.
> Four hundred pages, and she'll find the clause that costs you.
>
> **0:09** She had no idea what a BASIX certificate was.
>
> **0:14** One sentence. Twenty to twelve at night.
>
> **0:19** SiteWise reads it back. Class 1a. Extension. Heritage conservation area.
> Development application — not complying development, because of the overlay.
>
> **0:27** Then it stops. It doesn't know the floor area, so it leaves the floor area empty.
>
> **0:32** The first thing it ever did was refuse to guess.
>
> **0:38** She fills in what she knows. Adds the pool.
> That correction outranks the machine now. Permanently.
>
> **0:48** Her brief arrives by email. She doesn't file it — she forwards it.
>
> **0:55** Five rows become twenty-six. Two hundred and sixty-one square metres —
> including the five rooms somebody has to be paid to demolish.
>
> **1:04** Fifteen fee proposals. The cheapest architect, the cheapest planner.
> Twenty-one and a half thousand cheaper than the two she liked.
>
> **1:14** Both of them exclude the Heritage Impact Statement.
> In a conservation area, that document *is* the application. Neither of them carries it.
>
> **1:22** Her engineer opens up the footings. Sandstone rubble, four hundred and ten
> millimetres down, right on the party wall.
>
> **1:30** Underpinning. The cheap engineer would have charged it as a variation.
> The one SiteWise put in front of her carries it inside the fee.
>
> **1:38** Revision C. The heritage setback moved to one point eight metres.
> Three open questions still quote Revision B — and SiteWise knows whose they are.
>
> **1:48** Approved. Thirty-four conditions.
>
> **1:53** Thirty-four obligations. Seven of them block the Construction Certificate.
> Two of them have nobody's name against them.
>
> **2:02** Three builders. Seven-twelve. Seven-forty-nine. Seven-ninety-two.
>
> **2:10** The cheapest one has no pool. No detention tank. No scaffold. No prime cost sums.
> And none of the heritage brickwork Council made a condition of consent.
>
> **2:20** A hundred and ninety-seven thousand, seven hundred dollars — carried by a single
> exclusion clause.
>
> **2:26** *(sync, on site)* "Level three east, ceiling grid's out — fifteen mil over three
> metres. That's the ceilings package."
>
> **2:36** *(sync, in the car)* "Catch me up."
> — "Three things. The claim includes eight thousand four hundred against a variation you
> haven't approved."
> — "Hold it."
>
> **2:46** Month seven. On budget.
>
> **2:50** Sarah made every decision on this house.
> She just never made one blind.
>
> **2:55** *CARD:* **You do the judgement. SiteWise does the assembly.**

---

## Scene notes for the editor

### 0 · Cold open — 0:00

Dark. A solicitor's desk at home, 11:40 pm. Two monitors: one holds a discovery bundle with
half a page highlighted. The other holds empty SiteWise.

She types the kick-off prompt at real human speed — a typo, a backspace, a comma she
reconsiders. **Do not clean this up.** The roughness is the credibility.

Hold one full second on the finished sentence before anything happens. The audience needs to
register how little she gave it.

### 1 · It refuses to guess — 0:16

Profile fields resolve one at a time, each with its source. Then **GFA and Bedrooms stay grey
and empty**, and the shot holds there a beat longer than is comfortable.

This is the most important eight seconds in the film. Every AI demo in the category shows a
model filling in a form. This one shows a model declining to. If the audience remembers one
frame, make it this one.

Caption, small: `Not stated in the prompt.`

### 2 · The correction sticks — 0:32

She types the address, the bedroom count, the GFA, and a deliberate **0** for garage spaces —
a zero, not a blank, on a Newtown semi with no off-street parking.

Then the plunge pool line, typed. One row appears. Scheduled area reads **12 m²**, because
that is the only row with a number in it, and the schedule refuses to flatter itself.

On-screen chip, held: `Your correction · outranks classification · permanently`

### 3 · The brief, by email — 0:44

Phone, one-handed, in a lift. She forwards the brief to `georgina41@in.sitewise.au`. She
never opens the app.

Cut to the laptop. A Pulse card is already waiting:

```text
OWNER'S BRIEF RECEIVED
Accommodation schedule can be updated from this document.
21 spaces · 5 demolished · 4 external          [ Update ]  [ View evidence ]
```

She taps Update. **5 → 26.** 12 m² → 261 m². The demolished rows land in their own muted
group and stay out of the total.

Push in on the five `Demolished` rows for a beat. VO covers it: *including the five rooms
somebody has to be paid to demolish.* That line converts anyone who has ever been surprised
by a demolition claim.

### 4 · The heritage statement nobody priced — 1:00

Split screen, both proposals open, both exclusion clauses highlighted at once — Kestrel and
Loftus, the same document named in both.

```text
HERITAGE IMPACT STATEMENT
Kestrel Studio (architectural, cheapest)   excluded — "assumed covered by the planner"
Loftus Planning (town planning, cheapest)  excluded
                                           ⚠ Not carried by any proposal on file
```

Then the summary line, and let it sit:

> Cheapest five: **$92,300**. Appointed five: **$113,800**.
> The $21,500 buys a heritage statement, an underpinning design, an on-site detention design
> and an Occupation Certificate that the cheapest five do not include.

**This is the beat where a lawyer's face changes.** She recognises the move — she has run it
on opponents for twenty years. She has just never been on the receiving end of it in a domain
where she couldn't see it coming.

### 5 · Sandstone rubble at 410 mm — 1:18

The one genuinely tactile shot. Real texture: a hand-dug inspection pit, damp sandstone, a
tape reading 410.

The engineer emails the photo and two lines from site. It arrives as a `photo` +
`correspondence` pair, both filed to structural, both linked to the party wall risk that has
been sitting in her risk register since the brief in March.

Pulse:

```text
STRUCTURAL   Footing exposure confirms underpinning to the party wall.
             Raised in the brief 18 Mar as an unknown. Now evidenced.
             Ardent's appointment carries underpinning design inside the fee.
             Grimshaw Vale's proposal excluded it.        Cost impact: nil
```

**Cost impact: nil.** Hold on those two words. That is the fee comparison from scene 4 paying
out, eight weeks later, and the film should let the audience feel the connection without a
word of narration.

### 6 · Revision C — 1:34

Rev B and Rev C side by side, the setback dimension counting 1.5 → 1.8. Then the blast
radius, which is the actual point:

```text
REVISED   A-201 Rev C supersedes Rev B — heritage setback 1.5 m → 1.8 m
          14 sheets moved to Rev C
          3 open questions still quote Rev B    → Bower Lane, Ardent, Catchment
          Transmittal drafted to 3 recipients                  [ Review ]
```

Note **drafted**, not sent. The word is on screen and the button says Review. Doctrine D7 is
a selling point here, not a limitation: it is the difference between an assistant and a
liability.

### 7 · Thirty-four conditions — 1:44

The determination lands. Then the shot nobody can do without the classification spine
underneath it: 34 conditions decompose into a tracked obligation list, each with a trigger
stage, an owner and a required evidence type.

```text
DA/2025/0418 — APPROVED · 34 conditions

BEFORE CONSTRUCTION CERTIFICATE                7 outstanding
  11 · Heritage-matched face brickwork to street elevation   no owner
  14 · On-site detention — design certification              Catchment
  ...
BEFORE OCCUPATION                              12 outstanding
DURING WORKS                                   15
```

Highlight **condition 11**. Do not explain it. It comes back in ninety seconds, and the
audience will get there on their own — worth far more than being told.

### 8 · The showpiece — 1:58

Give this the most time. It is the scene people will describe to a colleague.

**Stage one — as submitted.** Three prices, Southbrook first and cheapest. Let the frame sit
long enough that the audience makes the obvious choice. They should be wrong, and they should
feel it.

```text
Southbrook Projects          $712,000     1 page   ·  6 lines   ·  no PC sums
Halden Building Co           $748,900     2 pages  · 22 lines   ·  $50,500 PC
Kingsford Bay Constructions  $792,400     4 pages  · 38 lines   ·  $70,500 PC
```

**Stage two — corrected for scope.** Adjustments land one line at a time, each with its
evidence. Pool. Detention tank. Scaffold. PC sums. Then the heritage brickwork — with
`DA condition 11` beside it, closing the loop from scene 7.

```text
Plunge pool, plant and barrier                      +$78,000
On-site detention, stormwater, kerb connection      +$24,500
Scaffolding, hoarding, site protection              +$18,400
PC sums — floor coverings, appliances, tapware      +$62,000
Heritage-matched brickwork      DA condition 11     +$14,800
                                                   ─────────
                                                   +$197,700
```

**Stage three — the reorder.** The table re-sorts. Southbrook falls from first to last.

```text
Halden Building Co           $780,100   corrected      1
Kingsford Bay Constructions  $792,400   corrected      2
Southbrook Projects          $909,700   corrected      3
```

> **The cheapest quote is the dearest job — by $129,600.**

Then the line that keeps the film honest and stops it reading as an anti-builder pitch:

> Halden excludes things too. Halden *says so.*
> *"We have priced the joinery to receive them but have not allowed for supply. Allow
> approximately $18,000."*

Sarah appoints Halden at **$748,900** against a $750,000 budget. She is $1,100 under, and she
knows exactly what she is carrying separately.

### 9 · Saturday, on site — 2:26

Daylight. Hard hat over weekend clothes. Kids waiting in the car. She holds her phone up and
talks — no typing, no forms, one hand free.

> *"Level three east, ceiling grid's out — about fifteen mil over three metres. That's the
> ceilings package. Needs fixing before tiles. Photo."*

The phone takes the photo. By the time she is back in the car:

```text
DEFECT LOGGED   L3 East · ceiling grid level · ceilings package
                Site instruction drafted, awaiting your approval   [ Review ]
```

⚠ **Production note:** voice capture does not exist in the X1 plan and must be built before
this scene can be captured live. See [`run-sheet.md`](./run-sheet.md) § *What must be built*.

### 10 · Monday, the car — 2:36

Windscreen, morning light, hands on the wheel. Entirely spoken, both directions.

> **Sarah:** "Catch me up."
> **SiteWise:** "Three things. Halden's claim seven includes eight thousand four hundred
> against variation seventeen — you haven't approved it. The certifier's frame inspection
> passed. And Bower Lane owe you the tiling setout they promised Thursday."
> **Sarah:** "Hold the claim. Tell him why."
> **SiteWise:** "Payment schedule drafted, with the reason. Ready when you are."

Cut to her in a courthouse corridor, gown over one arm, reading the drafted schedule on her
phone for maybe six seconds. She approves it, pockets the phone, and goes in.

**Do not show her reading it for long.** The entire claim of the film is that six seconds was
enough, because the thinking was already done and every figure points back at a document.

### 11 · The room upstairs — 2:50

Month seven. Frame up, roof on, light through a stud wall. She walks into a 14 m² room at the
back of the first floor.

The Parents' Retreat. No caption. No label. If the film has worked, the audience already
knows what that room is for.

Cut to black.

> **Sarah made every decision on this house.**
> **She just never made one blind.**

> **You do the judgement. SiteWise does the assembly.**

---

## Longer cut — 4:30

If the film earns more room, the three beats to restore, in order of value:

1. **The five unevidenced consultants** (survey, geotechnical, arborist, BASIX/ESD, QS).
   Their reports are on file. No appointment evidence exists for any of them, and SiteWise
   *says so* rather than assuming. Sarah — who spends her working life on what a document
   does and does not prove — recognises the discipline immediately. The single most credible
   beat available, cut only for time.
2. **The PMP writing itself, and being honest about it.** `Assumption` and `Not evidenced`
   rows visible on v1, upgrading to evidenced across v2 and v3 as documents land.
3. **Halden's two stated exclusions carried into the cost plan** as separately funded owner
   items — and the Milette appliance schedule landing at $12,950 against the $18,000
   allowance. The first good financial news of the project, arriving as arithmetic.

## Shorter cut — 0:45, paid social

Scenes 0, 1, 8, 11. The refusal to guess, the reordered tender, the room upstairs. The
$129,600 line carries it on its own.
