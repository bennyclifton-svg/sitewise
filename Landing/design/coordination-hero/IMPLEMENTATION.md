# Coordination hero — page composition

Implemented 8 September 2026 at `http://localhost:5173/landing.html`.

The opening uses a 55/45 split: a Blender still of the chalk development on a
Petrol ground, paired with a white reading field and the same cadastral lot in
plan. On mobile the model sits above the copy and plan. Ground stays level;
the cadastral source supplies illustrative boundaries, not surveyed terrain.

These checkpoints are static compositions, not an interactive GLB viewer.
The registered Blender scene, model transforms and vector plan remain available
for the later camera approach and in-situ services reveal. See
`Landing/model/coordination/STATIC-HERO-CHECKPOINT.md` for asset generation.
The original animated decorative map is no longer loaded by this page.

The perspective revision replaces the first illustration's independent cobalt
with the canonical Petrol/Air family: cyan-700 #12606D, cyan-300 #93CEDD,
and cyan-600 #1E7F92. The Blender shader converts those sRGB values to scene
linear; the final pixels vary with lighting and the view transform. The HTML
field and caption fade now use the same canonical cyan token family.

The right map uses a wider 280×220 viewBox, stronger non-scaling blue strokes,
and fills its available field. The shared cadastral context expands from 60 to
1,912 source-derived segments, with 184 intersecting the uncropped SVG viewBox.
Both views keep the same registered lot and roof projection. Reproduce this
data with `python Landing/model/coordination/export_perspective_context.py`.
The shared JSON includes source hashes, clipping bounds and geometry checks.

The revised camera is perspective at approximately 16° elevation, with the
horizon at 21.5% of the source image height. Fence centrelines follow the
selected parcel edges; the old ground fence is suppressed in the derived scene,
while source building transforms and balcony guards stay fixed. Near-white
emissive linework stays legible in the distance. The full development and fence
fit the central image region so desktop crops retain them and the horizon.

The CTA leads to the existing interactive tablet below the hero. Project plan,
cost plan, program and procurement remain accessible. A camera-to-tablet reveal
is intentionally deferred to the next motion study; no scroll interception is
introduced. The existing tablet scene respects reduced-motion preferences.

The tablet dark canvas now uses charcoal-950 (#0A0A0A), with charcoal-900
(#171717) side panels and neutral charcoal frame tones. The palette was already
current; the surface assignments and warm bezel were corrected. Light mode is
unchanged. Asset version references were refreshed in the landing HTML.

A separate concept study under `Landing/design/cadastral-mark/` explores two
identical angular parcel forms rotated 180 degrees into an S. It has not replaced
the live logo. The model source credit is included in the page footer.

## First checkpoint validation

- Desktop composition and model/plan pairing inspected in browser.
- No horizontal page overflow at 320, 390, 768, 1024, 1440 and 1920 px widths.
- All hero assets load; no browser JavaScript errors in the reviewed page.
- Native CTA reaches the tablet; dark/light toggle preserves the white outer page.
- Landing theme, controls, procurement, PMP and composition: 38 tests passed.
- Typecheck, lint, six generated colour export checks and production build passed.
- Existing separate Three.js style-demo chunk warning remains; enforced app bundle
  budgets pass. No runtime dependency was added.

Review screenshots are in `output/coordination-desktop.png`,
`output/coordination-mobile.png` and `output/coordination-tablet-dark.png`.

## Integrated 3D checkpoint — 9 September 2026

The left hero now uses a live, compressed model with discipline preview/selection and a dwelling-detail camera. See `Landing/model/coordination/v3/VIEWER-CHECKPOINT.md` for model scope, component ownership, reproducible build and browser validation. The previous static hero is retained as the loading/failure poster, updated from the integrated scene. The tablet and right cadastral plan remain in their existing composition.

## Right-hand plan revision — 9 September 2026

The right panel now uses real NSW Spatial Services cadastral polygons from a
Seven Hills neighbourhood. The prior perspective tracing and estimated
rectification were rejected because they could not establish lot proportions.

Regenerate offline with `python Landing/model/coordination/export_flat_plan.py`.
The input is `Landing/model/coordination/nsw-cadastre-source.json`; its recorded
query covers 150.928,-33.770 to 150.941,-33.757 (longitude/latitude), with all
1,805 features paginated in object-ID order. Downloaded 9 September 2026.
The server returns GDA2020 / MGA zone 56 (EPSG:7856), in metres.

Rendering only translates coordinates and reflects the Y axis: equal horizontal
and vertical scale, north up, no perspective, skew, resampling or lot reshaping.
The 560 × 720 m initial crop shows approximately 477 parcels, with a median
polygon area of 605.8 m². Export rounding changes source edge lengths by at most
0.0013 m. These are preservation checks against the source, not survey accuracy
claims. See `Landing/model/coordination/cadastral-plan-audit.json`.

Outputs under `frontend/public/landing-assets/coordination/`:
- `sitewise-cadastral-plan.svg`: deduplicated boundary strokes, no sample site.
- `sitewise-cadastral-plan.json`: full local parcel rings with source IDs and
  polygon areas, plus endpoint-matched boundary segments and owning parcel IDs.
  Retained for future animation; not fetched by the current static page.

The graph shares exactly matching segments at millimetre precision; it is not
an asserted fully noded topology where neighbouring rings split edges differently.
The left 3D model is unchanged and is illustrative, not a surveyed building on
this map. This replaces only the right-hand map source.

Source: https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer/9
Dataset: https://data.nsw.gov.au/data/dataset/spatial-services-nsw-cadastre
Licence record: https://data.gov.au/data/dataset/nsw-spatial-services-nsw-cadastre
© State of New South Wales (Spatial Services), CC BY 3.0 Australia:
https://creativecommons.org/licenses/by/3.0/au/
The page credits the source and licence and identifies the styled extract.
