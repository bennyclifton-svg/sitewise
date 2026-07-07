# Construction Management SaaS — Sequential Prompt Pack v3
### Aesthetic reference: labs.chaingpt.org — light grey, signal orange, clay 3D, spec-sheet borders

**v3 corrections from screenshot (supersedes v2 notes):** light greige canvas · vivid orange accent · CUSTOM blocky display font, now built by us (new Prompt 1.5) · monospace body text · hairline sheet grid with a full-height 4-column hero grid, marquee rendering OVER the rules · matte clay 3D with exactly ONE glowing orange accent (the robot's orange face equivalent) · 3D model sits on the open grid under the marquee, cropped by the partners strip · buttons are FLAT SHARP RECTANGLES (chamfer removed — the notch lives in the logo glyph and frame corner cut, not the buttons) · nav links Title Case mono, no desktop hamburger · near-black detail thumbnail with white corner brackets (new token --black) · thin mono chevron arrows (not pixelated) · orange square markers in loose left/right pairs · left-edge ✕ register cell · right-edge vertical social rail.

---

## How to use this pack

1. Paste **Prompt 0** at the start of your first message to the build agent (re-paste in any new session).
2. Run prompts **in order**; each builds one section and forbids touching others.
3. After each, critique against **"What to check"**, iterate with short follow-ups, then move on.
4. If the agent's colors drift, tell it to eyedropper-match your screenshot — the tokens below are close, but your screenshot is the source of truth.

---

## PROMPT 0 — Master Design Brief (paste first)

```
You are building a single-page marketing website for a SOFTWARE PRODUCT used by
construction managers and architects: design management, planning and procurement
in one platform. The aesthetic reference is labs.chaingpt.org and I will judge
results against a screenshot of it. Copy that aesthetic exactly; the only concept
swap is: their 3D robot becomes a 3D BUILDING (architectural massing model).

TECH: Single HTML file (or small static project), vanilla HTML/CSS/JS + Three.js
via CDN for the 3D building. Semantic HTML, all tokens as CSS custom properties,
responsive to 375px, prefers-reduced-motion respected.

DESIGN TOKENS (exact custom properties, use nothing else):
  --bg:        #E9E9E6;   /* light warm grey page canvas */
  --panel:     #EFEFEC;   /* slightly lighter panel fill */
  --ink:       #111111;   /* near-black text */
  --ink-dim:   #5A5A56;   /* secondary text */
  --line:      #ABABA6;   /* 1px hairline borders — used EVERYWHERE */
  --orange:    #F96416;   /* signal orange — buttons, markers, highlights ONLY */
  --white-3d:  #F2F2EF;   /* clay 3D model material, just lighter than bg */
  --black:     #0C0C0C;   /* near-black — hero detail thumbnail panel ONLY */

TYPE:
  Display: "SITEFORM DISPLAY" — a CUSTOM display face we build ourselves in
           Prompt 1.5: uppercase, ultra-wide, heavy, blocky outside with
           deep rounded counters inside, stencil-cut joints (the reference
           marquee's B reads almost as "З"). It carries the marquee, the
           logo wordmark and — once compiled — every display heading.
           Interim scaffold only: "Zen Dots" (Google Fonts) with wide
           letter-spacing; treat it as placeholder, never the target.
  Body & UI: EVERYTHING else is monospace — "Space Mono" or "IBM Plex Mono",
           400/700. Labels uppercase with wide tracking. There is no humanist
           sans anywhere on this site; the mono IS the voice.

VISUAL LANGUAGE (this is the core of the aesthetic — follow strictly):
  1. SPEC-SHEET FRAMING: the page reads like an engineering drawing sheet.
     Sections and sub-cells are boxed by 1px --line borders that BUTT against
     each other (collapse borders, no gaps, no rounded corners, no shadows).
     Think table/bento of hairline panels on grey.
  2. FLAT RECTANGLE BUTTONS: primary buttons are --orange fill, --ink mono
     uppercase text, sharp square corners — no radius, no chamfer, no shadow.
     (In the screenshot the CTAs are plain machined rectangles; the 45° notch
     language lives in the logo glyph and the sheet-frame corner cut only.)
  3. ORANGE SQUARE MARKERS: small solid --orange squares (~10px) pinned at
     grid intersections and label rows, often in loose left/right PAIRS.
     Used sparingly — 3-4 per viewport.
  4. CORNER BRACKETS: thin viewfinder-style corner brackets (camera focus
     marks) framing small thumbnails — WHITE on the hero's near-black detail
     panel, --ink elsewhere.
  5. CHEVRON ARROWS: prev/next controls are thin mono chevrons ‹ ›, --ink,
     each inside its own bordered square cell. Not pixelated, not bare.
  6. 3D STYLE: matte clay renders — soft studio lighting, material --white-3d,
     high roughness, NO wireframes. The clay almost merges with the page;
     form is read through soft shadow. EXCEPTION: exactly ONE orange accent
     element on the hero model (standing in for the reference robot's glowing
     orange face bezel + dark screen) — the only color on any 3D asset.
  7. NO decorative gradients (sole exception: the soft emissive glow on the
     3D model's orange accent), no glassmorphism, no rounded cards, no drop
     shadows. Flatness + hairlines + one loud orange. One sanctioned dark
     surface: the hero's --black detail thumbnail panel.
  8. SHEET GRID: a 4-column hairline grid runs the full height of the hero;
     the marquee letters render ON TOP of these rules. A short 45° cut joins
     the header's bottom rule to the page frame at the left edge.
  9. EDGE FURNITURE: a bordered square ✕ cell on the left edge just under the
     nav; a vertical social rail of stacked bordered square icon cells
     hugging the hero's right edge.

BRAND VOICE: terse, technical, mono. Placeholder product name: "SITEFORM"
(I'll swap later). Hero words: "BUILDING TOMORROW". Primary CTA: "BOOK A DEMO".

SIGNATURE ELEMENT: a matte clay 3D mid-rise building slowly rotating in the
hero, exactly where the reference site places its robot — with ONE softly
glowing --orange element (entry portal / glazed core with a near-black
recessed face) standing in for the robot's orange face bezel and screen.

RULES FOR EVERY TASK:
  1. Only build/modify the section I name.
  2. Every color from the tokens; no new hex values without asking.
  3. After each task, list what you changed and any judgment calls.

Reply "Ready" and wait for my first task.
```

---

## PROMPT 1 — Scaffold & global styles

```
TASK: Project scaffold only. No content sections yet.

1. index.html with empty semantic placeholders in order: header/nav, #hero,
   #partners, #platform, #capabilities, #results, #testimonials, #faq,
   #insights, footer.
2. Global CSS: import the interim display fallback ("Zen Dots") + mono fonts
   (the real display face arrives in Prompt 1.5); define all tokens; reset;
   --bg body; a page frame: the entire content column (max 1440px) is wrapped
   in a 1px --line border so the whole site sits inside one drawn "sheet";
   a reusable full-height 4-column hairline grid for the hero band.
3. Utility classes:
   .cell    — bordered panel (1px --line, no radius, borders collapse with
              neighbors via negative margin or shared-border technique).
   .label   — mono, uppercase, 12px, letter-spacing 0.12em, --ink-dim.
   .btn     — flat --orange rectangle, sharp square corners, mono uppercase
              --ink text; hover darkens fill ~8% and nudges 1px.
   .btn--ghost — same geometry, transparent fill, 1px --ink border.
   .marker  — 10px --orange square, absolutely positionable.
   .brackets — corner viewfinder marks for thumbnails (color inherits).
   .icon-cell — bordered square cell for icon glyphs (social rail, chevrons,
              hamburger, ✕).
4. prefers-reduced-motion plumbing from the start.

Output full file(s), nothing else.
```

**What to check:** Page reads as a light-grey drawing sheet with a crisp outer frame · borders are 1px and truly shared (no 2px doubling where cells meet) · buttons are crisp sharp-cornered rectangles · zero border-radius and zero shadows anywhere.

---

## PROMPT 1.5 — Custom display face "SITEFORM DISPLAY" (the hero asset)

```
TASK: Build the custom display font used by the marquee, the logo wordmark
and (eventually) every display heading. This is the single most
identity-carrying asset on the page — the Google-font fallback from
Prompt 1 is scaffolding only.

GLYPH DNA (reverse-engineered from the reference marquee — "OMORROW ЗΛ…"):
- Uppercase A-Z, digits 0-9, hyphen and ampersand, drawn on a 1000-unit
  grid (cap height 1000, no descenders).
- ULTRA-WIDE + HEAVY: advance width ≈ 1.1-1.3× cap height; stroke weight
  ~200-220 units, monolinear. A word must read as a train of near-square
  blocks.
- OUTER corners: near-square with a slight uniform rounding (~40-60 units)
  — softened machine blocks, not sharp brutalism, not bubbly.
- COUNTERS: deep rounded slots (radius ~150-250 units). The tension between
  blocky outside and rounded inside IS the font.
- STENCIL / LED DNA: strokes break at select junctions (~70-90 unit gaps).
  Signature glyphs visible in the screenshot: B reads almost as "З" (left
  side open), A reads almost as "Λ" (crossbar dropped to a low hairline or
  removed), M/W centre vertices stop well short of the baseline/cap line.
- Letter-spacing tuned tight and uniform, so the marquee reads as a wall
  of form.

BUILD PATH (do A now; B is an optional upgrade at the end of the project):
A. SVG GLYPH LIBRARY (single-file friendly): a JS map of character → SVG
   path on the 1000-unit grid, plus a renderDisplayText(el, text) helper
   that emits inline <svg><path>…</svg> glyph runs. Use it for the marquee
   and the logo wordmark; mirror the real text in a visually-hidden element
   for accessibility/SEO. Section headings keep the fallback font until B.
B. REAL FONT FILE: a small FontForge Python script that compiles the same
   paths into SiteformDisplay.woff2; @font-face it, point the display token
   at it, delete the Google fallback entirely.

DELIVERABLE: also generate font-spec.html — a proof sheet showing the full
character set on its design grid, plus the words "BUILDING TOMORROW" at
marquee scale for side-by-side comparison against the reference screenshot.
```

**What to check:** Put font-spec.html beside the screenshot — same weight, same width feel, same blocky-outside/rounded-inside tension · B and A carry the З / Λ stencil character · junction gaps read as machined cuts, not broken rendering · nothing drifts sci-fi kitsch — it should feel industrial, like plotter lettering · "BUILDING TOMORROW" set in it is indistinguishable in flavour from the reference marquee.

---

## PROMPT 2 — Navigation

```
TASK: Header/nav only.

- Full-width bar inside the page frame, --bg fill, 1px --line bottom border;
  a short 45° cut joins the bar's bottom rule to the frame at the left edge
  (drawing-sheet corner detail from the screenshot).
- Left: logo — a small square orange glyph (simple geometric "S" or building
  pictogram in a notched square, echoing the reference's notched-square logo)
  + "SITEFORM" wordmark in the display face (same custom letterforms as the
  marquee — the reference "LABS" uses the marquee font).
- Desktop links (Product, Capabilities, Results, FAQ, Insights) in mono
  TITLE CASE — not uppercase; the screenshot nav is Title Case — between
  logo and CTA; hover = --orange text, no underline.
- After the links, separated by a 1px --line vertical rule: a small orange
  ∷ glyph + "Our Platform" (the reference's "Our Ecosystem" slot).
- Far right: "BOOK A DEMO" .btn sitting flush against the frame's top-right
  corner. NO hamburger on desktop — every link is visible, exactly like the
  screenshot; the hamburger (three 2px --ink bars in an .icon-cell) appears
  only at the mobile breakpoint.
- Mobile menu: full-screen --bg overlay, links stacked in the display face,
  each row separated by 1px --line rules, orange square marker beside the
  active/hovered row. Close is an X in a bordered square cell.
```

**What to check:** Matches the screenshot's nav weight — logo left, Title Case mono links, loud orange rectangular CTA hard against the top-right corner, no desktop hamburger · mobile overlay rows are ruled like a table · no blur/transparency tricks — it's flat.

---

## PROMPT 3 — Hero with the 3D building (the signature)

```
TASK: Build #hero only. This mirrors the reference screenshot exactly, robot → building.

The hero is ONE bordered band divided by the full-height 4-COLUMN hairline
grid (vertical rules run from the marquee's top edge down to the partners
strip; content sits ON this grid — nothing floats in ad-hoc cards).

EDGE FURNITURE (build first):
- Left edge, directly under the nav: an .icon-cell containing an ✕ glyph
  (decorative register mark), beside the frame's 45° corner cut.
- Right edge: a vertical social rail hugging the frame — stacked .icon-cells:
  a target/radio glyph on top, then X, LINKEDIN, YOUTUBE, RSS icons (inline
  SVG, --ink, no emojis) — mirroring the reference's right-hand icon rail.
- Orange .marker squares in loose pairs: one above the marquee at far left,
  one at the marquee band's far right, one opening the label row, one at the
  label row's far right.

1. MARQUEE HEADLINE: "BUILDING TOMORROW" in SITEFORM DISPLAY (Prompt 1.5),
   --ink, one giant row scrolling horizontally in an infinite loop, so large
   it crops at the viewport edges (the screenshot shows "OMORROW ЗΛ…"). The
   4-column grid rules pass BEHIND the letters — do not box the text away
   from the grid. Slow, steady, plotter-like.
2. LABEL ROW under the marquee: [.marker] "BUILDING    TOMORROW" — mono
   uppercase, small, the two words wide-spaced, left-aligned (mirrors the
   reference's "▪ BACKING  TOMORROW" row).
3. CONTENT ROW (~55vh, the grid's middle band):
   - COLUMN 1: copy cell, mono --ink, left-aligned, generous padding:
     "Design management, planning and procurement for construction teams —
     one platform from concept to contract."
     Below the copy: a wide "BOOK A DEMO" .btn (the reference's orange
     "APPLY FOR INCUBATION" slot).
   - COLUMNS 2-3: THE 3D STAGE. The Three.js canvas sits on the open grid
     (no extra box of its own); the model rises from below-centre and is
     CROPPED by the partners strip beneath, exactly like the reference robot.
     · Model: stylized mid-rise building, ~8-10 floors — stacked slab
       volumes, a stepped setback or two, recessed window reveals as simple
       inset grooves (geometry, not textures), a roof plant block. It must
       read instantly as ARCHITECTURE: an architect's white massing model.
     · Material: MeshStandardMaterial, color --white-3d, roughness ~0.9,
       metalness 0. Lighting: soft hemisphere + one broad directional key;
       gentle contact shadow. The clay nearly matches the page grey — form
       read through shadow, exactly like the reference robot's body.
     · ONE ORANGE ACCENT: a single element — the entry portal / glazed
       double-height core — in --orange with a soft emissive glow and a
       near-black recessed face, mirroring the robot's orange face bezel
       and dark screen. Nothing else on the model gets color.
     · Motion: slow continuous Y rotation (~45s/rev) + a few degrees of
       pointer parallax. On load, floors assemble bottom-up over ~2s (rise +
       settle), once. Under reduced-motion: static three-quarter view, no
       assembly.
   - COLUMN 4: DETAIL THUMBNAIL — a square panel filled --black with WHITE
     .brackets corner marks, containing a mini clay render of a connector /
     joint block (tiny second canvas or 3D-ish SVG): white object on black,
     like the reference's jack-shaped detail. Docked at this column's
     bottom: a "WORKS WITH:" label cell + two .icon-cells with ‹ › chevrons
     (the partners strip controls — cells built here, wired in Prompt 4).
- Performance: pixel ratio capped at 2; pause render loop when hero
  off-screen.
- Fallback: no WebGL → static pre-styled SVG isometric massing model, same
  grey, same single orange accent.
```

**What to check (spend the most iteration here):** Silhouette unmistakably a building at a glance · clay matches the page grey — if it looks white-on-grey rather than grey-on-grey, darken it · shadows soft, no harsh speculars · the orange accent glows gently like the robot's face and is the ONLY color on the model · marquee crops at the edges and the column rules show behind the letters · label row, paired markers, ✕ cell and social rail all present · black thumbnail with white brackets sits in column 4 with the WORKS WITH controls docked below it · assembly feels like construction, then the rotation goes calm.

---

## PROMPT 4 — Partners / integrations strip

```
TASK: Build #partners only, copying the reference's partner table.

- The controls already scaffolded in the hero's column 4 ("WORKS WITH:"
  label cell + two ‹ › chevron .icon-cells, right-aligned directly above
  this strip) drive this section — wire them up now. (In the screenshot the
  "OUR PARTNERS:" label + arrows sit at the hero's bottom-right, not in a
  separate left-labelled band.)
- The strip: one full-width row of equal bordered cells directly below the
  hero, each holding one integration wordmark set LARGE and --ink, styled
  like a logotype: REVIT, AUTOCAD, IFC / BIM, MS PROJECT, PRIMAVERA P6,
  EXCEL, SHAREPOINT, XERO. (Text wordmarks only — no real logos; the
  reference uses real brand logos, this is our deliberate swap.)
- 4 cells visible on desktop, 2 on mobile — the screenshot shows exactly 4
  (Chainlink / TRON / BNB / OKX) in tall cells split by vertical rules.
- Arrows page through the row (slide N cells per click) with a snap
  transition; swipe on touch. Cells brighten to --panel on hover.
```

**What to check:** Reads as a drawn table, not a floating carousel · wordmarks sit big and dark in their cells like real partner logos · chevron cells match the hero furniture · paging snaps cleanly with no half-cells.

---

## PROMPT 5 — Platform overview (the "Beyond Capital" equivalent)

```
TASK: Build #platform only.

- Header band: mono label "// THE PLATFORM" left, and a display-face heading
  "ONE MODEL OF THE JOB" spanning the width below it, in its own bordered band.
- Three module panels in a shared-border row (stack on mobile), one per pillar:
  01 DESIGN MANAGEMENT — drawing registers, revisions, RFIs, approvals in one
     controlled thread.
  02 PLANNING — programmes linked to design status; see slippage before it
     costs you.
  03 PROCUREMENT — packages, tenders and lead times tracked against the
     programme.
- Panel anatomy: mono number top-left with an orange .marker beside it, title
  in the display face, 2-line mono description, and a mini "UI plate": a
  bordered inner cell with .brackets corner marks containing a simplified
  fake-UI mock (CSS-drawn table rows / gantt bars / status chips in --ink,
  --ink-dim and one orange element). No screenshots — draw it with divs.
- Footer band of the section: a .btn "BOOK A DEMO" + .btn--ghost "SEE PRICING".
```

**What to check:** The three fake-UI plates instantly telegraph register / gantt / procurement schedule · exactly one orange element per plate · numbering + brackets echo the hero's furniture.

---

## PROMPT 6 — Capabilities (numbered list, 01–10)

```
TASK: Build #capabilities only.

- Header band: mono label "// CAPABILITIES", display heading "EVERYTHING
  BETWEEN THE DRAWINGS AND THE KEYS".
- A two-column (1-col mobile) ruled list — each row a full-width bordered cell,
  not a card: mono number, capability name in display face (moderate size),
  one-line mono description, and a mono chevron glyph › at the row's right end.
  01 Drawing & document control
  02 Revision tracking & transmittals
  03 RFI & approval workflows
  04 Programme & milestone planning
  05 Design-to-programme linking
  06 Package & tender management
  07 Lead-time & delivery tracking
  08 Budget & commitment reporting
  09 Site diaries & progress records
  10 Handover & O&M documentation
- Hover/tap: row fills --panel and the number turns --orange.
```

**What to check:** Reads as a specification index, not a card grid · row rules align perfectly across both columns · hover state subtle.

---

## PROMPT 7 — Results (stat cards)

```
TASK: Build #results only.

- Header band: mono label "// RESULTS", display heading "MEASURED ON REAL JOBS".
- 2x2 grid (1-col mobile) of shared-border stat cells. Each: a giant stat in
  the display face --ink with the unit in --orange, and a mono caption:
    38%   faster drawing approvals
    2.1x  more tenders returned per package
    -19d  average procurement lead-time recovered
    100%  audit trail on every revision
- One customer strapline band beneath, mono: quote-style line from a placeholder
  firm ("Rolled out across 14 live projects in 6 weeks." — MERIDIAN BUILD GROUP).
```

**What to check:** Stats dominate — display face, huge · orange used only on units/one accent per cell · believable numbers (edit to your real ones later).

---

## PROMPT 8 — Testimonials

```
TASK: Build #testimonials only.

- Header band: mono "// CLIENTS", giant display heading "WORD ON SITE" cropped
  marquee-style or spanning two ruled rows.
- Carousel of 5 bordered quote cells: mono quote (3-5 lines), then a ruled
  footer row inside the cell: monogram square (initials, --panel fill,
  .brackets marks), name in display face small, role/company in mono --ink-dim.
  Personas: design manager at a contractor, project architect, procurement
  lead, project director at a developer, site manager.
- Chevron ‹ › prev/next in .icon-cells (identical to the partners controls);
  swipe on touch; one visible card mobile, two + a peek on desktop.
```

**What to check:** Quotes sound like people who chase drawing revisions for a living · controls identical to the partners strip (consistency) · swipe works on your phone.

---

## PROMPT 9 — FAQ

```
TASK: Build #faq only.

- Header band: mono "// FAQ", display heading "STRAIGHT ANSWERS".
- Accordion of 7 full-width ruled rows, single-open: question in display face,
  a "+" that rotates to "x" in --orange, smooth height animation, proper
  aria-expanded buttons.
  1. Who is SITEFORM for — contractors, architects, or clients?
  2. How does it connect design status to the programme?
  3. Can we run tenders and track lead times inside it?
  4. Does it work with Revit / IFC and our existing file storage?
  5. How long does rollout take on a live project?
  6. How is our project data secured and who owns it?
  7. What does it cost and how is it licensed?
- Write solid 2-4 sentence answers for each.
```

**What to check:** Open/close is smooth, rows stay ruled · answers are genuinely useful (this becomes SEO copy) · only one open at a time.

---

## PROMPT 10 — Insights + Footer

```
TASK: Build #insights and the footer. Nothing else.

INSIGHTS:
- Header band: mono "// INSIGHTS", display heading "FIELD NOTES", mono
  "ALL POSTS →" link.
- Row of 4 ruled article cells (horizontal scroll on mobile): mono date +
  category, title in display face, 1-line mono teaser. Placeholder titles:
  "Why drawing registers fail at revision C", "Linking procurement to the
  programme, properly", "The approvals bottleneck: a 6-project study",
  "IFC handover packs your client can actually use".

FOOTER:
- Top band: logo + newsletter — mono line "Field notes, monthly." + email
  input (bordered cell, mono placeholder) + .btn "SUBSCRIBE".
- Ruled link columns: Product / Company / Legal; social row in mono:
  LINKEDIN, X, YOUTUBE.
- Bottom band: "© 2026 SITEFORM. ALL RIGHTS RESERVED." mono --ink-dim, with
  one orange .marker in the corner and a tiny mono easter egg:
  "SHEET 01 OF 01 / REV F / SCALE NTS".
```

**What to check:** Footer reads like a title block on a drawing sheet — that easter egg should feel native · newsletter input matches the cell system · article row scrolls with momentum on mobile.

---

## PROMPT 11 — Motion pass (whole page)

```
TASK: Motion-only pass. No layout or copy changes.

1. Scroll reveals: sections' label, heading and cells stagger in (fade +
   16px rise, ~100ms stagger, once). Keep it crisp — this aesthetic is
   mechanical, not floaty.
2. Marquee (hero), partner paging, testimonial slides and 3D rotation tuned
   to one calm family of speeds.
3. Orange markers: a subtle one-time blink (opacity 0 → 1 in two steps, like
   an indicator lamp) when their section enters view.
4. Buttons: fill darkens + 1px translate on press; no scaling.
5. A 2px --orange scroll-progress bar along the top edge of the page frame.
6. All of it collapses to simple fades under prefers-reduced-motion.
List every animation with duration/easing for tuning.
```

**What to check:** Motion feels machined — steps and snaps, not bounces · nothing competes with the hero building · reduce-motion mode still works fully.

---

## PROMPT 12 — Responsive + QA pass (final)

```
TASK: Final QA. Fixes only, no redesign.

1. Test 375 / 768 / 1024 / 1440 / 1920px: no horizontal overflow, hairline
   grid never doubles or breaks, marquee and 3D stage scale sensibly, display
   headings crop intentionally (never mid-glyph gibberish on key words).
2. Performance: lazy-load below-the-fold, pause 3D + marquees off-screen,
   cap canvas pixel ratio, preconnect fonts, target fast hero interactive on
   mid-range mobile.
3. Accessibility: one h1, heading order, visible focus (2px --orange outline,
   offset), 4.5:1 contrast for --ink-dim on --bg (nudge the token if it
   fails), aria on carousels/accordion/menu, alt text.
4. Meta: title, description, OG tags, favicon = orange notched square glyph.
Report all fixes as a checklist.
```

**What to check:** Open on your actual phone next to the reference site — squint test: same family? · keyboard-tab the whole page · Lighthouse sanity.

---

## Iteration cheat-sheet (phrases tuned to THIS aesthetic)

- "The greys are drifting — everything derives from #E9E9E6, eyedropper the screenshot."
- "Too much orange. One accent per panel, maximum."
- "Those are cards — I want ruled cells. Kill the radius/shadow, share the borders."
- "The building looks like a toy/blob — strengthen slabs, setbacks and the roof block so the silhouette is architecture."
- "The 3D is too white — it should nearly merge with the page, form read through shadow."
- "Marquee slower; it should feel like a plotter, not a ticker."
- "Body text must be monospace everywhere — no sans has crept in, right?"
- "More mechanical: snaps and steps, not eases and bounces."
- "The marquee glyphs are too generic — blocky outside, ROUND inside, stencil
  gaps at the joints. Pull up font-spec.html beside the screenshot."
- "The building's orange element should glow softly like the robot's face —
  one accent, everything else stays clay."
- "Arrows are thin mono chevrons in their own bordered cells — not pixelated,
  not bare characters floating in space."