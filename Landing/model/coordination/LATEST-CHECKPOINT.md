# Current integrated coordination checkpoint

Facade update, 10 September 2026: the current editable model and viewer export
are `sitewise-premium-v11.blend`, derived from `sitewise-chalk-v10.blend`.
Warm brick, bronze window-mounted louvres, rounded balcony wraps, softened front
window surrounds and access-checked balcony planting implement the approved
mock-up. See `v3/PREMIUM-FACADE.md` for rebuild commands and geometry checks.

Palette update, 9 September 2026: the current viewer exports from
`sitewise-chalk-v10.blend`, derived from `sitewise-decks-v9.blend`.
See `v3/CHALK-PALETTE.md` for the chalk materials and neutral daylight.
The facade refinements and side ground closures remain included.

9 September 2026: open `sitewise-integrated-v3.blend` for the registered site, reinforced-concrete structure, street utilities and enriched nearest dwelling. See `v3/VIEWER-CHECKPOINT.md` for the live viewer and validation. The interior-only checkpoint below is retained as the reproducible source.

## Earlier interior checkpoint

8 September 2026. Open `sitewise-interior-checkpoint.blend`.

The assembled scene contains the full development with the nearest dwelling enriched:

- The approved all-electric fitted kitchen, including fridge, induction hob, oven, microwave, sink and range hood.
- 26 ceiling/pendant luminaires across the three occupied levels, plus the kitchen hood task strip.
- 24 Australian/NZ double GPOs throughout the rooms, with extra bedside and general worktop points.
- One fitted open curtain pair and the retained source beds, sofa and dining setting.

Room and electrical endpoint IDs are recorded separately from rendering light sources. General-purpose outlets remain distinct from dedicated appliance power. Circuits, switching and services routes are still to be developed.

## Structural correction

The user corrected the primary structural direction to **reinforced-concrete columns and reinforced-concrete slabs**. The earlier timber model is superseded. They asked to leave it for now, so it remains available only in the clearly labelled archived scene and is hidden in the assembled interior. Do not present it as the agreed structural solution or continue polishing it. Roof and infill construction are not settled by this correction.

## Review images

- `13-dining-lighting.png` — fitted kitchen, dining pendants and general power provision.
- `14-bedroom-lighting.png` — bedroom lighting, curtains and outlets.
- `17-gpo-detail.png` — the authored double-GPO family.

Images 15, 16 and 18 are the superseded timber study, retained as process records only.

## Verification and records

All 26 luminaire mount centers and their edge samples hit actual source ceilings. All 24 GPO plate centers/corners hit their source wall, with no detected intersections against visible fixture/furniture geometry. The corrected curtain placement has no detected source-wall/window intersections. Original architectural transforms and source GLBs are preserved.

See `interior-checkpoint.json`, `lighting-checkpoint.json`, `lighting-mount-audit.json`, `gpo-checkpoint.json` and the asset extraction manifests for coordinates and provenance. These are geometry checks, not electrical or structural engineering validation.

Next work: connect the fitted appliance, lighting and GPO endpoints into illustrative electrical routes; re-anchor hydraulic and ventilation routes to the fitted kitchen. Revisit the concrete structural system as a separate checkpoint, then continue site/utility, vehicle and camera-sequence integration.

Historical chalk checkpoint: sitewise-chalk-v10.blend superseded the deck checkpoint.
The current viewer uses sitewise-premium-v11.blend. See v3/PREMIUM-FACADE.md.
