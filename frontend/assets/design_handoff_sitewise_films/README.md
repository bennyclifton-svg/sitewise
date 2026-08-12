# Handoff: Sitewise Cube Films

## Overview
Three animated brand films built around a rotating 3D cube (the Sitewise mark) that dissolves into product screens rendered on its faces. All motion is driven from a single authored clock (`animations-v3.jsx`'s scene engine), so any frame is reachable deterministically — useful for scrubbing, trimming, or re-timing in code.

## About the Design Files
The files in this bundle are **design references built in HTML/JS/Three.js** — working prototypes of the intended look, motion and timing, not production code to copy verbatim. The task is to recreate this experience in the target codebase's environment (React + Three.js/react-three-fiber, or whichever 3D/animation stack the project already uses) using its own conventions — or, if no such environment exists, to pick the most suitable stack and implement there. The **logic (camera moves, timing curves, canvas-drawn screen content) is exact and should be ported faithfully**; only the file structure/tooling needs to adapt.

## Fidelity
**High-fidelity.** Every camera position, scene duration, easing curve, and on-screen pixel value (colors, type sizes, row layouts) in the JS is final and intended to be reproduced exactly, not restyled.

## The three films
| File | Global export | Scene JSX | Runs |
|---|---|---|---|
| `Sitewise Film.dc.html` | `SitewiseFullFilm` | `sitewise-full.jsx` | Full 106s film: Reveal → Invoice → Profile → Transmittal |
| `Sitewise Landing Film.dc.html` | `SitewiseFilm` | `sitewise-film.jsx` | Landing-page cut (Reveal + Invoice) |
| `Sitewise Transmittal Film.dc.html` | `SitewiseTransmittal` | `sitewise-transmittal.jsx` | Transmittal-only cut |

All three load the shared animation engine `animations-v3.jsx` plus the 3D module scripts under `style-guide/3d/` via `<script type="module">` tags in `<head>`. Each `.dc.html` declares its scene list as a JSON string in `window.OM_SCENES` (name, duration, description) — this is the authoritative shot list; the engine derives its cue table from it.

### Scene breakdown (full film, from `Sitewise Film.dc.html`)
1. **Reveal** — 8s. One light finds the cube, it settles and locks, six sectors sweep away and back, camera moves down onto the roof.
2. **Invoice** — 32s. Assistant appears on the roof, workspace on the glazing: a question is typed and sent, answered while the repository, invoice register and cost plan swipe through underneath. Faces clear, camera lifts back to the roof.
3. **Profile** — 29.6s. Camera moves square to the glazing; a profile sheet is built from scratch with no source documents, cursor-driven. Camera hands back to the roof frame.
4. **Transmittal** — 36.4s. Composer typed and clicked; the document register slides in and searches itself; nineteen basement drawings select as they pass; cursor opens the draft transmittal; film closes back to the opening frame.

## Architecture / File Map
- **`animations-v3.jsx`** — shared continuous-composition timeline engine (single element tree, authored-time clock, cue table derived from `OM_SCENES`). All three films depend on this.
- **`sitewise-full.jsx` / `sitewise-film.jsx` / `sitewise-transmittal.jsx`** — per-film scene composition: camera paths, cube state machine, timing of each beat.
- **`three-d-stage.js`** — 3D viewer shell (renderer, studio lighting, ground shadow, camera framing) the films mount into.
- **`style-guide/3d/cube-geometry.js`** — the cube mesh/material construction (flat gradient faces with edge light-catch bands only — no procedural textures).
- **`style-guide/3d/film-stage.js`** — the Invoice-act canvas-drawn face content (repository/invoice register/cost plan) plus the cost-item dropdown interaction.
- **`style-guide/3d/screens.js`** — invoice register screen + "Choose cost item" dropdown logic (6 rows, cursor and row-highlight driven off one shared timing clock).
- **`style-guide/3d/transmittal-stage.js`** — camera/composition control for the Transmittal act; owns the panel centroid-shrink insets so screens never run flush to cube edges mid-turn.
- **`style-guide/3d/transmittal-screens.js`** — document register + transmittal draft canvas-drawn content. All rows/panels are transparent line work (text + hairline dividers only, no filled backgrounds) to match the invoice act.
- **`style-guide/3d/composer.js`** — the reusable text-composer UI drawn onto cube faces (semi-transparent `rgba(11,12,15,0.55)` shell, consistent across all sections).
- **`style-guide/3d/profile-screens.js`, `reveal.js`, `mark.js`, `scroll-mark.js`, `surfaces.js`, `photo-surface.js`** — remaining per-scene/per-surface canvas draw modules and reveal-sequence logic.
- **`style-guide/3d/lighting.json`** — studio lighting rig config consumed by `three-d-stage.js`.
- **`style-guide/3d/sources/`** — reference source images used while iterating on cube surface textures (concrete, metal, timber, photos, documents). **Textures built from these were removed from the final cube** — faces are now flat gradients — so treat these as historical reference only, not assets to wire up.
- **`support.js`** — Design Component runtime loader (streaming template/logic support for the `.dc.html` wrapper). Not needed if you're not keeping the `.dc.html` structure — its only real job is defining `<x-dc>`/`<x-import>` so the browser can preview the design; the actual film logic lives in the `.jsx`/`.js` files above.
- **`Sitewise Landing.dc.html`, `Sitewise Composer.dc.html`, `Sitewise Logo Reveal.dc.html`, `Sitewise Mark 3D.html`** — adjacent/earlier standalone pieces (landing page shell, isolated composer demo, logo-only reveal, bare 3D mark viewer) included for context; not part of the three films above.
- **`Sitewise Style Guide.dc.html` / `Sitewise Style Guide v2.dc.html`** — the brand style guide the films draw their palette/type from.

## Interactions & Behavior
- **Camera**: continuous arcs (never straight lerps between positions, to avoid cutting through the cube), timed per scene per the durations above.
- **Cube state**: sectors sweep open/closed; faces swap between idle gradient and "screen" (canvas texture) states as scenes demand.
- **Composer**: types out a question character-by-character, cursor click sends it; consistent `rgba(11,12,15,0.55)` translucent shell across Reveal/Invoice/Transmittal.
- **Document register (Transmittal)**: 19 rows scroll past a fixed "read line"; rows flagged as selected flash and get a left accent bar as they cross it; row/header backgrounds are transparent — only the accent highlight and hairline dividers render.
- **Cost-item dropdown (Invoice)**: opens over an "orphan" row the model couldn't auto-map; 6 rows (2 group headers + 4 items); the row highlight and the mouse cursor are driven off one shared `travel` clock so they never desync.
- **Transmittal draft**: meta rows (Project/To/Purpose) and the documents table are transparent line work; only the "To" row keeps a subtle blue tint as the field needing confirmation.

## Design Tokens
Pull full palette/type/spacing from `style-guide/tokens.css` and `style-guide/tokens.json` (already in this bundle). Key colors used directly in the film canvases (`style-guide/3d/*.js`):
- `#0B0D10` / `#101319` / `#1E232B` / `#161A21` — near-black backgrounds, panel, line, head (panel/head fills have been removed from the final render in favor of transparency; keep the hex values for reference)
- `#D6D6D0` ink (primary text), `#8A8F98` dim (secondary text)
- `#2F72C4` blue / `#7FB0E4` sky — link/accent, active states
- `#E0A44A` amber — needs-attention state, `#57A87A` green — confirmed state, `#B49BE0` violet
- Composer shell: `rgba(11,12,15,0.55)`
- Fonts: Hanken Grotesk (sans), IBM Plex Mono (mono, used for labels/table headers)

## Assets
- `style-guide/3d/sources/*` — reference photos/scans used during texture exploration (concrete, metal, architectural plan, invoice, legislation, structural notes, technical spec, photo stills). Not wired into the final render; kept for historical reference.
- `style-guide/logo/*.svg` — Sitewise mark (solid, mono, favicon variants) used for the cube identity and composer send icon.

## Files
See the Architecture section above for what each file contains. Open any `.dc.html` directly in a browser to preview; the underlying logic to port lives in the `.jsx` and `.js` files it imports.
