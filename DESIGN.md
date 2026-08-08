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
    fontFamily: "Space Mono, IBM Plex Mono, ui-monospace, monospace"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  none: "0px"
  sm: "3px"
  md: "5px"
  lg: "7px"
  xl: "10px"
  control: "0.4375rem"
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
    backgroundColor: "{colors.signal-orange}"
    textColor: "{colors.ink-marketing}"
    rounded: "{rounded.none}"
    padding: "16px 28px"
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

Not the cliché architect loft with mood boards and espresso — a working drawing office where sheets are pinned, dimensions are checked, and decisions leave marks. SiteWise fuses two already-shipping visual dialects into one identity: the **SITEFORM marketing sheet** (`frontend/public/landing.html` + `landing-assets/landing.css`) and the **product cockpit workbench** (`frontend/src/index.css` + shadcn primitives). Persuade surfaces speak in hairline frames, zero-radius machined chrome, Oxanium display, and clay 3D massing. Operate surfaces speak in dense IBM Plex UI, warm paper greys, micro-radii for finger targets, and a charcoal dark shell with subtle grain. The shared soul is the same: handcrafted texture, multi-scale structure (from sheet grid to Y-frame / BIM-like volumetric undertone), and one hot construction accent against quiet hardware.

The technology undertone is structural, not neon. 3D clay models, viewfinder brackets, registration-tick corners, and tracked mono labels carry “agentic construction intelligence” the way a building information model carries coordination — visible as frame and mass, never as purple glow or chatbot chrome. Quiet hardware with one hot accent. Hope earned by substance.

### Mark 3 landing surface

The current standalone landing page is a deliberate Mark 3 branch of the
persuade register. Its source of geometry is the SiteWise mark itself: a point-up
isometric hex divided by three 60-degree axes, five occupied material facets
(parse, retrieve, filter, calculate and validate) and one open issue aperture.
The actual Greenbank project-profile application view establishes product
reality in the first viewport. Small, attributable public-document thumbnails
leave a compact incoming window and land inside the screenshot's real
right-hand repository column. One small Blueprint Azure token then represents
language judgement and visits the five deterministic facets; the open aperture
issues the current application document template. The demonstration PMP cites
only the `DA-1100` Ground Floor Plan, while the other four records remain
available but uncited. Text and controls remain semantic DOM content. On
desktop, WebGL owns only the scroll-driven camera transition. At `900px` and
below, the project profile, facet engine and issued sheet appear sequentially
in normal document flow. Reduced-motion mode also removes document and token
travel.

For this surface, graphite, bone and Blueprint Azure are the complete palette,
and Chillax Light with Hanken Grotesk replaces the older SITEFORM
Oxanium/Space Mono pairing. Public source previews must link to attributable
originals; never fabricate a project document for visual credibility. The
surface-specific brief at
`.impeccable/surfaces/frontend-public-landing-html.md` governs this exception.

**Key Characteristics:**
- Dual-register system: sheet marketing vs workbench product, one brand spine
- Warm paper greys + Formwork Ember / Signal Orange as the only hot voice
- Mono eyebrows and labels; Oxanium for persuade display; IBM Plex for operate body
- Hairlines, brackets, corner ticks — drawn structure over soft SaaS cards
- Subtle grain/texture and clay 3D for material + BIM undertone
- Flat sheet on marketing; tonal stack + restrained lift in the app

## Colors

Warm paper neutrals with a construction-orange accent family; cool Blueprint Azure reserved for AI/assumed/info contrast against evidenced blaze.

### Primary
- **Formwork Ember** (`oklch(0.55 0.12 52)`, app `--brand` / blaze-600): Product brand fill, evidenced decisions, focus rings, zone-title ticks, OK/workflow success text. Hot accent — keep rare on dense screens.
- **Signal Orange** (`#F96416`, landing `--orange`): Marketing CTAs, 10px grid markers, selection, logo tile. Hotter public twin of Formwork Ember; do not mix both accents in one composition — pick the register.

### Secondary
- **Blueprint Azure** (`oklch(0.52 0.12 245)`, `--azure-strong`): AI/assumed decision chips, info workflow states, workbook title cells, cockpit workflow icons. Cool counterweight that marks “model/inference” against evidenced ember.

### Tertiary
- **Survey Ochre** (`oklch(0.56 0.12 65)`): Warning / ready workflow states.
- **Kiln Clay** (`oklch(0.52 0.15 28)`): Alert / destructive.

### Neutral
- **Paper White / Canvas / Ground** (`oklch` gr-0 / gr-50 / gr-100): App surface stack — card, canvas, app chrome.
- **Paper Line / Strong** (gr-200 / gr-300): Hair borders in product UI.
- **Sheet Bg / Panel / Line** (`#E4E4E4` / `#EFEFEC` / `#ABABA6`): Marketing page sheet and 1px rules.
- **Clay 3D** (`#F2F2EF`): Landing GLB / clay massing material.
- **Ink / Ink Body / Muted / Faint**: Product text ladder (gr-900 → gr-500).
- **Ink Marketing** (`#111111`): Landing primary text.
- **Charcoal Base** (`#1a1a1a`): Dark cockpit shell panels (with grain overlays).

### Named Rules
**The One Hot Accent Rule.** On any given surface, either Formwork Ember (operate) or Signal Orange (persuade) is the hot voice — never both competing, never rainbow status chrome.

**The Evidence vs Inference Rule.** Blaze/ember marks evidenced or brand-owned actions; Blueprint Azure marks AI/assumed/info. Do not swap those meanings.

**The Paper Before Paint Rule.** Most of the UI is warm grey paper or charcoal plate. Color arrives as signal, not decoration.

## Typography

**Display Font:** Oxanium (marketing / hero / persuade headlines)
**Body Font:** IBM Plex Sans (product UI)
**Label/Mono Font:** IBM Plex Mono (product eyebrows, traces); Space Mono (marketing body + labels)

**Character:** Engineered clarity with a construction-intelligence edge — blocky Oxanium display for the public face; Plex for long work sessions; mono for registers, ticks, and “drawn on the sheet” labels.

### Hierarchy
- **Display** (Oxanium, marketing weights, large hero/marquee): Persuade headlines and SITEFORM wordmarks only — not cockpit denseness.
- **Title** (IBM Plex Sans, 500, ~16px / `text-base`): Card and panel titles in product.
- **Body** (IBM Plex Sans, 400, 13.5px, 1.5): Default operate reading size — dense but legible.
- **Marketing body** (Space Mono, 15px, 1.55): Landing running text and nav.
- **Label** (IBM Plex Mono, 11px, 500, 0.14em, uppercase): `.cockpit-eyebrow` / zone titles — tracked, faint, structural.

### Named Rules
**The Eyebrow is Structure Rule.** Uppercase tracked mono labels are frame, not decoration. Keep them faint (`ink-faint`) with an optional ember tick — never loud pill soup.

**The Dual Face Rule.** Oxanium/Space Mono own persuade; IBM Plex owns operate. Crossing faces needs intent (e.g. a marketing strip inside app), not drift.

## Layout

Two spatial grammars, one brand:

1. **Sheet (persuade):** Entire page as a drawn sheet (`max-width: 1440px`), 1px hairline frame, 4-column hero grid collapsing to 2, gap-as-border cell matrices, 45° corner cuts, viewfinder brackets. Zero radius by default. Structure reads like a construction drawing set.
2. **Workbench (operate):** Full-viewport cockpit grid — left nav, main panel, side panel; warm paper in light mode; charcoal plates with subtle radial wash + noise grain in dark. Dense 8/16/24 rhythm; cards use `--card-spacing` 24px (16px sm). Signature workbench cards may carry registration-tick corners (`.cockpit-signature-card`).

Multi-scale is intentional: sheet grid → panel plates → Y-frame / clay 3D massing on marketing heroes → tabular workbooks and registers in product. Prefer synthesis and reduction over dashboard clutter.

### Named Rules
**The Sheet vs Bench Rule.** Marketing stays on the hairline sheet; product stays on the tonal workbench. Borrow motifs (brackets, ticks, mono labels, ember) across — do not paste landing zero-radius chrome into dense forms without reason.

## Elevation & Depth

**Tonal workbench, flat sheet, volumetric models.** Chosen from the incumbent code: product depth is mostly stacked greys (`bg-app` → `bg-canvas` → `bg-surface`) with light `shadow-xs` / `shadow-sm` on floating chrome (menus, composer, outline buttons, cards). Marketing is explicitly flat — no box shadows, no radius; depth comes from hairlines and real 3D clay GLBs. The SiteWise mark on the cockpit ribbon is the rare lifted object (soft glow + shadow stack).

### Shadow Vocabulary
- **Resting chip** (`shadow-xs`): Outline controls, inputs, subtle card edge.
- **Floating chrome** (`shadow-sm` / `shadow-md`): Popovers, chat composer, menus.
- **Mark glow** (custom multi-layer on `.cockpit-sitewise-mark`): Brand seal only — not a general card style.
- **Marketing:** none — flat sheet; volume from 3D.

### Named Rules
**The Flat Sheet Rule.** Persuade surfaces do not grow drop shadows to look “premium.” If it needs depth, use a clay model, a bracket, or a hairline — not a soft SaaS shadow.

**The Lift Is Earned Rule.** In product, shadows mark floating or interactive chrome. Surfaces at rest stay tonal.

## Shapes

- **Marketing:** Radius 0 everywhere; machined rectangles; 45° sheet corner cuts; square 10px ember markers; viewfinder brackets (14–20px strokes).
- **Product:** Tight radii — 3 / 5 / 7 / 10px (`--radius-sm`…`xl`), controls ~7px (`0.4375rem`). Pill badges only for compact status chips. Registration-tick corners on signature cards echo landing brackets without copying zero-radius dogma into every input.
- **3D massing:** Soft clay building volumes (tower-house / genome builder) — the Y-frame / BIM undertone lives here, not in UI chrome.

### Named Rules
**The Bracket is a Viewfinder Rule.** Corner ticks and brackets mean “this is scoped / registered / under inspection.” Use sparingly on signature work surfaces.

## Components

Quiet hardware with one hot accent.

### Buttons
- **Shape:** Product — gently softened control radius (`~7px`); Marketing — sharp rectangle (`0`).
- **Primary (product):** Formwork Ember fill, paper-white text, h-9, medium weight; hover deepens toward blaze-700.
- **Primary (marketing):** Signal Orange fill, near-black text, uppercase mono, tracked, 16×28 padding; hover darkens ~8%, presses 1px down.
- **Outline / Ghost / Secondary:** Quiet paper or transparent; ember only for primary commitment.
- **Focus:** Brand ring (`--brand-ring` / orange outline on landing).

### Chips
- Soft evidenced (ember wash) vs assumed (azure wash) decision chips; workflow status chips use OK / warn / info / alert semantic pairs. Pill badges for compact counts — not as the main layout language.

### Cards / Containers
- **Workbench cards:** Paper surface, `rounded-xl` (~10px), light ring/shadow-xs, optional signature ticks.
- **Marketing cells:** Hairline borders, gap-as-border matrices, panel fill `#EFEFEC` — no soft card shadow.
- **Dark cockpit panels:** Charcoal base with grain; hair borders at white ~6% opacity.

### Inputs / Fields
- Transparent/paper field, hair border, h-9, control radius, `shadow-xs`; focus → brand border + ring. Invalid → Kiln Clay ring.

### Navigation
- **Landing:** Sheet header, mono links, orange CTA, notched logo tile.
- **Product:** Left project nav + ribbon header (brushed metal gradient + grain); SiteWise circular mark as the lifted seal.

### Signature: Clay 3D / brackets / registration ticks
Marketing heroes mount clay GLB models in bracketed stages; product echoes the registration language with `.cockpit-signature-card` ticks and mono zone titles with a 14×1px ember rule.

## Do's and Don'ts

### Do:
- **Do** fuse sheet language (hairlines, brackets, mono labels, clay 3D) with workbench language (Plex, tonal greys, micro-radii) under one Drawing Office north star.
- **Do** keep Formwork Ember / Signal Orange rare and purposeful — quiet hardware, one hot accent.
- **Do** use Blueprint Azure for inference/AI/info and ember for evidenced/brand.
- **Do** prefer subtle grain, paper texture, and structural 3D over decorative gradients.
- **Do** synthesise and reduce — architect clarity over dashboard clutter.

### Don't:
- **Don't** run purple/indigo “AI” gradients, glow stacks, or chatbot-bubble aesthetics.
- **Don't** mix Signal Orange and Formwork Ember as competing accents on one screen.
- **Don't** apply marketing zero-radius + heavy uppercase mono to every dense form control — operate needs Plex and soft hit targets.
- **Don't** fake depth on the marketing sheet with soft drop shadows; use models and hairlines.
- **Don't** invent testimonials, partner proof, or metric theatre without real evidence (product constraint).
