# Build the SiteWise landing page — single page, one shot

Build a single dark scroll-narrative landing page for **SiteWise**, an AI construction
management platform. Think product film, not brochure: still screenshots of the real UI,
revealed progressively as the visitor scrolls, carried by six short lines of copy.

Discard any existing SiteWise landing page. This replaces it.

---

## 1. The rule that matters most

**Three motion patterns. Reused everywhere. Nothing else moves.**

Do not add a fourth. The page should feel expensive because the same restrained move
repeats with confidence — not because each section does something new. Opacity and
transform only.

1. **Rise** — anything textual enters at `opacity 0, translateY(26px), blur(6px)` and
   settles to rest. Curve `cubic-bezier(.22,1,.36,1)`, 420ms. Stagger siblings by 60ms.
   Drive it with `animation-timeline: view()` where supported, IntersectionObserver
   fallback. Range roughly `entry 10% cover 30%`.
2. **Plate drift** — every UI screenshot sits in a "plate" (spec in §5). As the plate
   crosses the viewport it un-tilts: from `perspective(2200px) rotateX(7deg) rotateY(-9deg)
   translateY(48px) scale(.97)` to flat and settled, tied to scroll position, then holds.
   Mirror the rotateY sign when the plate sits on the left. Never bounces, never loops.
3. **Prompt type-in** — inside a chat composer, the prompt text types out character by
   character (~22ms/char) once, when it enters view. A caret blinks, then the send glyph
   pulses once. Fires once per composer, never repeats on scroll-back.

Ambient exception, hero only: the cadastral background drifts ~4% vertically across the
first viewport. That is the whole ambient budget.

**Explicitly banned:** scroll-jacking, pinned/locked sections, horizontal scroll, counters
that tick, marquees, cursor followers, particle fields, parallax anywhere but the hero,
video, Lottie, canvas, 3D libraries, hover effects on non-interactive elements.
`prefers-reduced-motion: reduce` collapses all three patterns to a plain 150ms fade.

---

## 2. Brand tokens — use these exactly

```
Void   #060608   oklch(12% .006 265)   ground plane, page background
Panel  #131418   oklch(18% .008 265)   lit surface
Edge   #24262B   oklch(26% .010 265)   rules, hairlines
Blue   #2F72C4   oklch(52% .130 258)   primary action — the ONLY accent
Beam   #7FB0E4   oklch(72% .090 254)   links, highlights
Bone   #E8E8E4   oklch(92% .004  90)   type

Text: primary #E8E8E4 / secondary #B6B9BF / tertiary #8F939B / quiet #5C5F66

Sans: 'Hanken Grotesk' (Google Fonts), weights 200/300/400/500
Mono: 'IBM Plex Mono' (Google Fonts), 400 — labels and kickers ONLY

Display  clamp(52px, 8.2vw, 116px) / lh .94  / tracking -.045em / weight 200
Title    42px  / lh 1.05 / -.04em  / weight 200
Heading  25px  / lh 1.2  / -.015em / weight 300
Body-lg  19px  / lh 1.6                      / weight 300
Body     17px  / lh 1.6                      / weight 300
Label    11px  / tracking .16em / UPPERCASE / mono
Measure: cap body text at 52ch. Cap display headlines at 20ch.

Spacing (8px base): 8 / 16 / 26 / 40 / 56 / 110. Section rhythm holds at 110px
(scale to ~72px under 768px). Border radius is 0 everywhere — square, matching
the logo facets. Radius is reserved for status dots only.

Ease: enter cubic-bezier(.22,1,.36,1) · state cubic-bezier(.4,0,.2,1)
Durations: enter 420ms · state 180ms · stagger 60ms
```

**Light, not shadow.** Elevation is luminance. A raised surface gets a brighter top edge
(`1px rgba(255,255,255,.13)`, `.26` when raised), never a bigger drop shadow. Contact
occlusion is tight: `0 40px 60px -50px rgba(0,0,0,1)`. Add a 5% film-grain overlay across
the page to kill gradient banding.

Blue is the only chromatic move on the page. Everything else is a lighting state.

---

## 3. Assets

All in `./selected/`. Use every one; add nothing.

| File | What it is | Where it goes |
|---|---|---|
| `bg-cadastral.jpg` | Glowing blue cadastral/lot-line landscape receding to a horizon | Hero background only |
| `mark-open.png` | The SiteWise mark — open enclosure, graphite roof / bone floor / glazed face | Nav + hero + footer |
| `mark-iso.png` | Tighter isometric variant of the same mark | Optional, footer |
| `shot-cockpit.png` | Full application window — nav rail, project plan, document register, composer | The "one system" reveal, §4 act 3 |
| `panel-profile.png` | Project Profile — class, work type, subclass, scale, complexity, budget | Act 4 |
| `panel-procurement.png` | Generated RFT / procurement document with citations | Act 5 |
| `panel-programme.png` | Gantt programme — planning / procurement / delivery bars, milestones, links | Act 6 |
| `panel-costplan.png` | Cost plan — budget, approved contract, variations, forecast final cost | Act 7 |
| `panel-documents.png` | Document register — drawing numbers, titles, revisions, categories | Act 8 |
| `ui-composer.png` | The real chat composer strip: "Ask about your project documents", Fast / Thorough | Reference for §6 |
| `ui-tray.png` | Small "Add to tray" annotation popover | Optional garnish, once |

Do not crop or recolour the screenshots. They are already trimmed. Let plates bleed off the
container edge where noted — a fragment reads better than a full window.

**On the mark:** it is correct but reads clinical. Warm it without redrawing it. Let it be
large, off-centre and partly cropped by the viewport edge in the hero; let one soft key
light fall across it from above-left rather than lighting it evenly; let the cadastral
lines pass behind and just catch its bone floor edge. Treat it as an object standing in a
landscape, not a badge on a page.

---

## 4. The scroll script

Nine acts. Two layouts only — **Statement** (centred type, nothing else) and
**Prompt + Panel** (sticky text column one side, plate scrolling past on the other,
sides alternating down the page). Alternating those two is the page's whole rhythm.

**Act 0 — Nav.** Fixed, transparent, blurs to `rgba(6,6,8,.72)` after 40px. Mark at 24px,
wordmark "SiteWise" in sans 300. Right: one text link and one square Blue button,
"Request access". A 2px scroll-progress bar (Blue → Beam) pinned at the top of the viewport.

**Act 1 — Hero.** Full viewport. `bg-cadastral.jpg` covering, at ~55% opacity, with a Void
gradient dropped over the lower two-thirds so type sits clean. The mark, large, lower-right,
partly cropped by the edge.

> mono label: `CONSTRUCTION MANAGEMENT`
> **The intelligent construction management platform** ← Display
> Built for real world projects. Powered by AI. ← Body-lg, secondary

One Blue button, one quiet text link beneath. Rise-stagger the four elements. A thin
hairline scroll cue at the base.

**Act 2 — Statement.** Void, empty, generous. Centred:

> **Introducing SiteWise**
> The unified platform. ← Heading, tertiary

Nothing else in this viewport. The emptiness is the point.

**Act 3 — The one system.** `shot-cockpit.png` as a wide plate, slightly curved (see §5),
entering with plate-drift. Above it:

> **All in one integrated system**

Below it, four mono labels on one hairline rule, evenly spaced, each rising 60ms after the
last: `QUALITY` · `COST` · `TIME` · `PROCUREMENT`. Just labels on a rule. No icons, no
cards, no boxes.

**Acts 4–8 — Five prompt/panel sections.** Identical structure, sides alternating:

- Sticky column: mono kicker, one Title-size line, one sentence of body, and a **composer**
  containing the prompt (§6).
- Scrolling column: the plate, drifting.

| Act | Kicker | Line | Panel |
|---|---|---|---|
| 4 | `PROJECT PROFILE` | One brief. Every discipline reads it. | `panel-profile.png` |
| 5 | `PROCUREMENT` | Strategy and tender documents, drafted from the project. | `panel-procurement.png` |
| 6 | `PROGRAMME` | A programme that knows what the project actually is. | `panel-programme.png` |
| 7 | `COST` | Change the design, the cost plan already knows. | `panel-costplan.png` |
| 8 | `DOCUMENTS` | Every document read, registered and cross-referenced. | `panel-documents.png` |

**Act 9 — Close.** Return to the hero language, quieter. Cadastral background at 25%,
heavily darkened.

> **Built for real world projects.**
> Request access ← Blue button

Footer: mark, wordmark, one hairline, three quiet links, copyright. Nothing more.

---

## 5. The plate

Every screenshot sits in the same shell. Build it once, reuse it five times.

- Square corners. `1px solid #24262B` hairline frame.
- Top edge catches light: `inset 0 1px 0 rgba(255,255,255,.13)`.
- Contact occlusion below: `0 40px 60px -50px rgba(0,0,0,1)`.
- The image sits flush inside — no padding, no fake browser chrome, no traffic lights.
- Tall panels get a 90px bottom fade to Void so they dissolve rather than stop.
- A soft Blue key glow behind the plate at ~8% opacity, offset up-left, blurred 120px.
- A single specular sweep: a 20°-tilted white gradient at 4–6% opacity crossing the plate,
  moved slowly by scroll position. This is the plate's only decoration.

Plates may bleed past the container's outer edge and off the viewport — encouraged in acts
6 and 8, so the page reads as fragments of a larger system.

**The curve (act 3 only, once):** give the cockpit plate a very shallow cylindrical read —
`perspective(2400px)` plus a subtle horizontal mask that darkens both outer 12% by ~15%,
so the wide shot feels like it's bending away at the edges. Do not attempt real geometry
or slice the image. Flat CSS illusion, used exactly once.

---

## 6. The composer — the most important detail on the page

Rebuild the composer from `ui-composer.png` as live HTML (do not use the PNG). It is the
one element that proves the product is driven by language.

- Full-width bar, `rgba(11,12,15,.55)` over a Panel ground, `1px solid #24262B`, square.
- Placeholder ghost text sits in it before typing: `Ask about your project documents`
- Below the input: two small square segmented buttons, `Fast` and `Thorough`, with
  `Thorough` active in Blue text on a subtly lit ground.
- Right side: a small mic glyph, tertiary; and the SiteWise mark as the send affordance.
- A 1px Blue caret. On completion the send mark pulses once (opacity, 180ms).

The typed prompt replaces the placeholder. **Max two lines at desktop width.** Set the
prompt in the same sans as body copy, 17px, primary text — it must read as a person typing,
not as a code sample.

### The six prompts, in order

Use these verbatim. They are already trimmed to fit two lines.

| Act | Prompt |
|---|---|
| 4 | `Two storey new build, 12 townhouses across three lots. Set the project up.` |
| 5 | `Draft the procurement strategy and the first RFTs — architect, structural, civil.` |
| 6 | `Build a 20 activity programme. 6 months planning, 3 procurement, 12 construction.` |
| 7 | `The structural revision adds $180k. Update the cost plan, programme and PMP.` |
| 8 | `Sweep the project documents. Tell me what needs doing next.` |

And in act 3, under the cockpit shot, a sixth composer with no panel beside it — the line
that states the whole thesis:

| 3 | `Evaluate the open RFIs and draft the response to each consultant.` |

Every one of these deliberately crosses more than one discipline. That crossing is the
product.

---

## 7. Copy rules

- Use the six key statements as written. Do not embellish them.
- No invented metrics, percentages, time savings, customer counts or logos. No "10x",
  no "90 seconds", no "trusted by". Every number on the page must come from a screenshot.
- Avoid the words *ingest* and *generate* in written copy. (They may appear inside
  screenshots — that's the product's own UI and stays as captured.)
- Sentences, not fragments-with-full-stops. No exclamation marks. No em-dash-heavy
  marketing voice. Body copy caps at one sentence per section.

---

## 8. Build notes

- One self-contained HTML file. Inline CSS and JS. Google Fonts link is fine; nothing else
  external. Reference the images by their `./selected/…` paths.
- Semantic HTML, real `<h1>`/`<h2>`, alt text on every screenshot describing the panel.
- Responsive: below 900px the Prompt+Panel layout stacks — text first, plate beneath,
  full-bleed. Plates never force horizontal page scroll. Display type reflows via the clamp.
- Keyboard focus visible in Blue on every interactive element. AA contrast on all text.
- Ship it finished. No placeholder copy, no lorem, no TODO comments.
