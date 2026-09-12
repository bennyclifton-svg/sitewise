---
name: SiteWise
description: Drawing-office construction OS — handcrafted sheet meets agentic workbench
colors:
  formwork-ember: "oklch(0.55 0.12 52)"
  formwork-ember-hot: "oklch(0.48 0.11 51.5)"
  formwork-ember-soft: "oklch(0.972 0.012 54)"
  signal-orange: "#F96416"
  blueprint-azure: "oklch(0.52 0.12 245)"
  survey-ochre: "oklch(0.56 0.12 65)"
  kiln-clay: "oklch(0.52 0.15 28)"
  paper-white: "oklch(0.993 0.003 92)"
  paper-canvas: "oklch(0.977 0.004 92)"
  paper-ground: "oklch(0.955 0.005 92)"
  paper-line: "oklch(0.908 0.006 92)"
  paper-line-strong: "oklch(0.852 0.007 92)"
  sheet-bg: "#E4E4E4"
  sheet-panel: "#EFEFEC"
  sheet-line: "#ABABA6"
  clay-3d: "#F2F2EF"
  ink: "oklch(0.196 0.006 86)"
  ink-body: "oklch(0.278 0.007 86)"
  ink-muted: "oklch(0.47 0.008 90)"
  ink-faint: "oklch(0.585 0.008 92)"
  ink-marketing: "#111111"
  charcoal-base: "#1a1a1a"
  landing-ivory: "#faf9f5"
  landing-muted: "#5a6472"
  landing-charcoal: "#1c1c1c"
  landing-charcoal-ink: "#f1efec"
  landing-plane: "#cbc7bd"
  landing-blue: "#2563eb"
  landing-blue-press: "#1b4fc4"
  landing-blue-soft: "#9fb4d4"
typography:
  display:
    fontFamily: "Oxanium, system-ui, sans-serif"
    fontWeight: 600
    letterSpacing: "normal"
  body:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.5
  title:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.5
  label:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 500
    letterSpacing: "0.14em"
  marketing-body:
    fontFamily: "Hanken Grotesk, Helvetica, Arial, sans-serif"
    fontSize: "clamp(15px, 1.04vw, 16px)"
    fontWeight: 400
    lineHeight: 1.5
  landing-display:
    fontFamily: "Satoshi, Hanken Grotesk, Helvetica, Arial, sans-serif"
    fontSize: "clamp(48px, 3.8vw, 60px)"
    fontWeight: 300
    lineHeight: 1.2
    letterSpacing: "-0.028em"
rounded:
  none: "0px"
  sm: "3px"
  md: "5px"
  lg: "7px"
  xl: "10px"
  control: "0.4375rem"
  pill: "999px"
spacing:
  micro: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  card: "24px"
  card-sm: "16px"
components:
  button-primary:
    backgroundColor: "{colors.formwork-ember}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.formwork-ember-hot}"
    textColor: "{colors.paper-white}"
  button-marketing:
    backgroundColor: "{colors.landing-blue}"
    textColor: "#fff"
    rounded: "{rounded.pill}"
    padding: "0 36px"
    height: "44px"
  button-marketing-hover:
    backgroundColor: "{colors.landing-blue-press}"
    textColor: "#fff"
  landing-workspace-plaque:
    backgroundColor: "{colors.landing-charcoal}"
    rounded: "clamp(18px, 1.5vw, 26px)"
    size: "61.2vw × aspect-ratio 1.82"
  button-outline:
    backgroundColor: "{colors.paper-canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
    height: "36px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
  input-default:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "4px 10px"
    height: "36px"
  card-workbench:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    padding: "{spacing.card}"
  badge-default:
    backgroundColor: "{colors.formwork-ember}"
    textColor: "{colors.paper-white}"
    rounded: "9999px"
    padding: "2px 10px"
---

# Design System: SiteWise

## Overview

**Creative North Star: "The Drawing Office"**

Not the cliché architect loft with mood boards and espresso — a working drawing office where sheets are pinned, dimensions are checked, and decisions leave marks. SiteWise fuses two shipping visual dialects: the standalone **Offset Project Monolith** landing (`frontend/public/landing.html` + `landing-assets/landing-story.css`) and the product cockpit workbench (`frontend/src/index.css` + shadcn primitives). The landing is a warm sheet that lets one dark workspace plaque do the physical work; operate surfaces are dense IBM Plex UI, warm paper greys, micro-radii for finger targets, and a charcoal shell with subtle grain. The shared soul is material clarity, spatial hierarchy, and one purposeful action colour against quiet hardware.

The technology undertone is structural, not neon. On the landing, the evidence is the real Seven Hills workspace capture, framed as a machine; in product it is carried by registration-tick corners and tracked mono labels. The system is never purple glow or chatbot chrome. Hope is earned by a legible project state.

### Offset Project Monolith landing surface

The standalone landing page is a single static Persuade composition for D&C project directors and design managers delivering $5m–$50m projects. Its exact promise is “One live project. Every moving part connected.” A warm ivory ground holds a generous left reading column; a large, straight-on flat dark workspace tablet offsets to the right; and a graphite project plane rises across the base to name the synthetic Seven Hills Townhouse demonstration. The landing-only Open Datum mark is a flat graphite-to-blue construction path, not a shared app-logo change.

The actual palette is warm ivory, near-black ink and muted slate copy, graphite plaque and plane, with blue as the one action voice. Satoshi at a light weight carries the headline and project name; Hanken Grotesk carries every other landing word. The supplied dark Seven Hills workspace capture is the only product proof shown; the label explicitly says “Synthetic project demonstration.” There are no feature cards, chapter swaps, sticky scroll, theme controls, invented product chrome, customer proof or metric theatre.

At desktop size the composition is one viewport: header and actions sit above the left statement, the straight-on tablet sits to the right with a thin bezel, inset hairline and diffuse shadow, and the sloped graphite band anchors the project name beneath it. At `1024px` and below it becomes a normal reading sequence — header, copy, machine, then band — and at `560px` the hero actions stack. Hover is confined to a small blue-button lift and link-arrow nudge; reduced motion collapses transition duration. The surface-specific brief at `.impeccable/surfaces/frontend-public-landing-html.md` governs this landing-only exception.

**Key Characteristics:**
- Dual-register system: Offset Project Monolith landing vs workbench product, one brand spine
- Warm ivory and graphite on landing; Formwork Ember / Blueprint Azure remain product signals
- Satoshi + Hanken Grotesk for landing; IBM Plex for operate body
- One right-hand straight-on workspace tablet replaces feature-grid or chapter-spine marketing
- The landing's Open Datum mark and blue CTA are intentionally landing-only
- Tonal stack + restrained lift in the app; a physical plaque and graphite plane on landing

## Colors

Warm paper neutrals support the product workbench; the landing uses warm ivory, graphite and a single clear blue action signal. Blueprint Azure remains reserved for AI/assumed/info in product contexts.

### Primary
- **Formwork Ember** (`oklch(0.55 0.12 52)`, app `--brand` / blaze-600): Product brand fill, evidenced decisions, focus rings, zone-title ticks, OK/workflow success text. Hot accent — keep rare on dense screens.
- **Landing Blue** (`#2563eb`): The landing-only CTA, link-hover, focus and lower-band label signal; it gives the otherwise graphite composition its one active coordinate.
- **Signal Orange** (`#F96416`): Existing broader-system public accent; it is not used by the current standalone landing.

### Secondary
- **Blueprint Azure** (`oklch(0.52 0.12 245)`, `--azure-strong`): AI/assumed decision chips, info workflow states, workbook title cells, cockpit workflow icons. Cool counterweight that marks “model/inference” against evidenced ember.

### Tertiary
- **Survey Ochre** (`oklch(0.56 0.12 65)`): Warning / ready workflow states.
- **Kiln Clay** (`oklch(0.52 0.15 28)`): Alert / destructive.

### Neutral
- **Paper White / Canvas / Ground** (`oklch` gr-0 / gr-50 / gr-100): App surface stack — card, canvas, app chrome.
- **Paper Line / Strong** (gr-200 / gr-300): Hair borders in product UI.
- **Landing Ivory / Ink / Muted** (`#faf9f5` / `#111111` / `#5a6472`): The warm sheet, headline and explanatory-copy ladder.
- **Landing Charcoal / Charcoal Ink / Plane** (`#1c1c1c` / `#f1efec` / `#cbc7bd`): The dark project band and sloped graphite transition beneath the tablet.
- **Ink / Ink Body / Muted / Faint**: Product text ladder (gr-900 → gr-500).
- **Charcoal Base** (`#1a1a1a`): Dark cockpit shell panels (with grain overlays).

### Named Rules
**The One Hot Accent Rule.** Product operates with Formwork Ember; this standalone landing operates with Landing Blue. Keep each surface to its one hot voice — never competing accent chrome.

**The Evidence vs Inference Rule.** Blaze/ember marks evidenced or brand-owned actions; Blueprint Azure marks AI/assumed/info. Do not swap those meanings.

**The Paper Before Paint Rule.** Most of the UI is warm grey paper or charcoal plate. Color arrives as signal, not decoration.

## Typography

**Display Font:** Satoshi on the standalone landing; Oxanium where already established elsewhere in the system
**Body Font:** IBM Plex Sans (product UI)
**Label/Mono Font:** IBM Plex Mono (product eyebrows, traces)

**Character:** Engineered clarity with a construction-intelligence edge — light Satoshi gives the landing its calm authority, Plex supports long product work sessions, and mono holds product registers, ticks and labels.

### Hierarchy
- **Landing display** (Satoshi, 300, `clamp(48px, 3.8vw, 60px)`, 1.2): The landing hero and project name — spacious, plainspoken and not all-caps.
- **Title** (IBM Plex Sans, 500, ~16px / `text-base`): Card and panel titles in product.
- **Body** (IBM Plex Sans, 400, 13.5px, 1.5): Default operate reading size — dense but legible.
- **Marketing body** (Hanken Grotesk, 400, `clamp(15px, 1.04vw, 16px)`, 1.5): Landing prose, navigation and actions.
- **Label** (IBM Plex Mono, 11px, 500, 0.14em, uppercase): `.cockpit-eyebrow` / zone titles — tracked, faint, structural.

### Named Rules
**The Eyebrow is Structure Rule.** Uppercase tracked mono labels are frame, not decoration. Keep them faint (`ink-faint`) with an optional ember tick — never loud pill soup.

**The Dual Face Rule.** Satoshi/Hanken Grotesk own the standalone landing; IBM Plex owns operate. Crossing faces needs intent, not drift.

## Layout

Two spatial grammars, one brand:

1. **Offset Project Monolith (landing-only persuade):** One `100svh` desktop scene, with copy positioned left at `4.1vw` gutter and a straight-on tablet beginning at `38.4vw`; a `31svh` graphite band is cut on the diagonal beneath it. At `1024px` it becomes a normal vertical sequence, and its actions stack at `560px`.
2. **Workbench (operate):** Full-viewport cockpit grid — left nav, main panel, side panel; warm paper in light mode; charcoal plates with subtle radial wash + noise grain in dark. Dense 8/16/24 rhythm; cards use `--card-spacing` 24px (16px sm). Signature workbench cards may carry registration-tick corners (`.cockpit-signature-card`).

Multi-scale is intentional: generous landing statement → straight-on workspace tablet → project-name plane → tabular workbooks and registers in product. Prefer synthesis and reduction over dashboard clutter.

### Named Rules
**The Monolith vs Bench Rule.** The landing earns attention through one offset workspace machine and a graphite plane; product stays on the tonal workbench. Do not turn dense operating views into landing composition.

## Elevation & Depth

**Tonal workbench, flat landing tablet.** Product depth is mostly stacked greys (`bg-app` → `bg-canvas` → `bg-surface`) with light `shadow-xs` / `shadow-sm` on floating chrome. The landing's depth is singular and structural: a straight-on dark tablet has a thin outer bezel, an inset hairline and two diffuse shadows above the sloped project plane. It does not use a generic card field, 3D transform or clay model.

### Shadow Vocabulary
- **Resting chip** (`shadow-xs`): Outline controls, inputs, subtle card edge.
- **Floating chrome** (`shadow-sm` / `shadow-md`): Popovers, chat composer, menus.
- **Mark glow** (custom multi-layer on `.cockpit-sitewise-mark`): Brand seal only — not a general card style.
- **Landing tablet:** `1px solid rgba(241,239,234,.38)` bezel, `inset: 4px` / `1px solid rgba(255,255,255,.08)` inner hairline, and diffuse `0 18px 32px -18px rgba(10,9,8,.28)`, `0 38px 72px -48px rgba(10,9,8,.48)` shadows — the only persuasive-surface lift.

### Named Rules
**The One Machine Rule.** The landing's flat tablet is allowed one diffuse shadow treatment because it contains the product proof. Do not spread that lift across copy, controls or new cards.

**The Lift Is Earned Rule.** In product, shadows mark floating or interactive chrome. Surfaces at rest stay tonal.

## Shapes

- **Landing:** A straight-on, flat rounded tablet (`clamp(18px, 1.5vw, 26px)` outer, `clamp(11px, .8vw, 16px)` screen) sits against hard diagonal planes; the blue walkthrough CTA is fully pill-shaped (`999px`). The Open Datum mark is open stroked geometry, not a filled tile.
- **Product:** Tight radii — 3 / 5 / 7 / 10px (`--radius-sm`…`xl`), controls ~7px (`0.4375rem`). Pill badges only for compact status chips. Registration-tick corners on signature cards remain product language.

### Named Rules
**The Mark Is Landing-Only Rule.** The Open Datum mark belongs to this static landing; it does not authorise a global navigation or app-logo change.

## Components

Quiet hardware with one hot accent.

### Buttons
- **Shape:** Product — gently softened control radius (`~7px`); landing walkthrough — full pill (`999px`).
- **Primary (product):** Formwork Ember fill, paper-white text, h-9, medium weight; hover deepens toward blaze-700.
- **Primary (landing):** Landing Blue fill, white Hanken Grotesk text and a 44px minimum height; hover deepens to Landing Blue Press and lifts 2px.
- **Outline / Ghost / Secondary:** Quiet paper or transparent; ember only for primary commitment.
- **Focus:** Brand ring in product; `2px` Landing Blue outline with `4px` offset on the landing.

### Chips
- Soft evidenced (ember wash) vs assumed (azure wash) decision chips; workflow status chips use OK / warn / info / alert semantic pairs. Pill badges for compact counts — not as the main layout language.

### Cards / Containers
- **Workbench cards:** Paper surface, `rounded-xl` (~10px), light ring/shadow-xs, optional signature ticks.
- **Landing machine:** One dark, rounded workspace plaque with an inset screen; it is an image stage, not a reusable card grid.
- **Dark cockpit panels:** Charcoal base with grain; hair borders at white ~6% opacity.

### Inputs / Fields
- Transparent/paper field, hair border, h-9, control radius, `shadow-xs`; focus → brand border + ring. Invalid → Kiln Clay ring.

### Navigation
- **Landing:** Simple absolute header; Open Datum mark and SiteWise wordmark at left, Hanken Grotesk text link and blue walkthrough pill at right. At `1024px`, the text link hides and the header returns to normal document flow.
- **Product:** Left project nav + ribbon header (brushed metal gradient + grain); SiteWise circular mark as the lifted seal.

### Signature: Offset Project Monolith
The landing's one straight-on Seven Hills workspace tablet and diagonal graphite project plane carry the persuade story. Product retains `.cockpit-signature-card` ticks and mono zone titles with a 14×1px ember rule.

## Do's and Don'ts

### Do:
- **Do** use the landing's warm sheet, one straight-on flat workspace tablet and graphite project plane as a single composition.
- **Do** keep Landing Blue rare and purposeful on the landing; keep Formwork Ember purposeful in product.
- **Do** use Blueprint Azure for inference/AI/info and ember for evidenced/brand.
- **Do** use the supplied Seven Hills screenshot as labelled synthetic product demonstration, not customer proof.
- **Do** synthesise and reduce — architect clarity over dashboard clutter.

### Don't:
- **Don't** run purple/indigo “AI” gradients, glow stacks, or chatbot-bubble aesthetics.
- **Don't** add Signal Orange, Formwork Ember or a second hot accent to the current landing composition.
- **Don't** turn the landing into a feature-card grid, chapter scroller or sticky presentation.
- **Don't** distribute the machine's grounded shadow to copy or generic marketing cards.
- **Don't** invent testimonials, partner proof, or metric theatre without real evidence (product constraint).


### Current landing direction — 9 September 2026

For the standalone landing page, this supersedes the historical Offset Project
Monolith description above. User selected Funnel Display (SIL OFL 1.1) and ink blue. The wordmark uses
Funnel Display Medium with an original offset-plan corner symbol. The
headline overlays the cadastral map; the desktop composition is 45% live model /
55% map, with map-first stacking on mobile. Real NSW parcel geometry remains
undistorted. Fine illustrative contours and timed boundary pulses sit behind
the type. Palette: #071c39 ink, #f3f5fc foreground, #8ebeff signal. Body and
dense UI text retain Hanken Grotesk while the new display family is refined.
The existing product cockpit system is unchanged. See
`Landing/design/coordination-hero/EXPERIENCE.md` for behaviour and verification.
