# Brick terrace — architectural coordination concept

12 September 2026. Seven-home preferred study and six-home comparison, updated
to the four-bedroom floor-plan reference supplied during design.

## Decision and provenance

The user authorised a new street-facing illustrative site, complete floor-plan
reconsideration and integration of all existing discipline functions. The existing
five-home master `../sitewise-entry-bikes-v23.blend` and production landing-page
export are retained. This is a separate, newly authored design option.

The references establish warm brick, sheltered loggias, slim metal balustrades,
expressed pale entries, single garages, vertical front fencing and roof-integrated
upper accommodation. The facade photographs do not establish dimensions or
construction. The later floor-plan image establishes the four-bedroom planning basis.

The editable source was opened and inventoried in Blender. `source-audit.json`
and `source-inventory.json` record the existing systems and measured object bounds.
The source contains five dwellings, with extensive service geometry and a shared
internal driveway; the new scheme deliberately changes that site arrangement.

## Options on the same 49 m building frontage

| | Seven homes | Six homes |
|---|---:|---:|
| Nominal dwelling frontage | 7.00 m | 8.167 m |
| Building depth | 14.40 m | 14.40 m |
| Front boundary to facade | 3.90 m | 3.90 m |
| Rear outdoor zone | 6.00 m | 6.00 m |
| Clear passage beside garage/stair screen | 0.93 m | 2.097 m |
| Garage opening | 3.10 m | 3.10 m |
| Loggia opening (width × height) | 2.90 × 2.00 m | same |
| Levels above concept datum | 0.35 / 3.45 / 6.55 m | same |
| Main roof ridge | 10.30 m | same |
| Bedrooms | 4 | 4 |
| Rear upper balconies | 2.70 m deep on both levels | same |

The initial 6.6 m seven-home module left a narrow passage and was widened to
7 m. The building was subsequently deepened to 14.4 m to adopt the supplied
four-bedroom plan. These are designed concept dimensions on an invented site, not a finding
that seven homes fit the original parcel. The six-home option deliberately uses
the same room/core arrangement to expose the extra width; its larger residual
spaces can support a larger loggia, study or revised stair in a subsequent choice.

## Floor planning

Terraces 2, 4 and 6 are mirrored in the current models. All dwelling disciplines,
front fencing/gates, gardens, driveway crossings and local service connections
follow the mirror. Shared party boundaries, bearing walls/foundations and exposed
end-window treatments remain on their original boundaries. Numbering is retained:
the seven-home garage pairs are 2–3, 4–5 and 6–7; the six-home option pairs 2–3
and 4–5, with garages 1 and 6 at its outer ends. `alternating-audit.json` records
garage positions and the scope. Separate TH02 plan cuts show the mirrored layout.

- Ground: recessed single garage and independent entry; two-flight stair and
  powder room; rear kitchen, dining and living opening to the garden.
- First: Bedrooms 3 and 4, front loggia, rear balcony, central bathroom and rear
  laundry. Ducted air-conditioning sits in a central bulkhead.
- Roof level: front Bedroom 2 and rear master, boxed dormers, rear balcony,
  central bathroom, landing and dressing/wardrobe space. Usable area depends on
  the detailed roof section.

The supplied plan's legible room labels and dimensions guide the arrangement;
it is not a measured CAD source and has not been traced to claim exact geometry.
The original two-bedroom/flexible-room studies are retained as
`option-N/terrace-N-initial.blend`. Current `terrace-N.blend` files use four bedrooms.
Room layouts are concept layouts. Window operation, furniture clearances, accessible
provisions and storage schedules still need design development.

## Architecture and materiality

Three related warm brick colours are distributed in pairs. Brick courses are
procedural in Blender at nominal 230 x 76 mm modules. Brick returns make the
balcony openings three-dimensional; linen curtains are modelled behind glazing.
Pale shared garden blades and fences contrast with bronze-charcoal metalwork.
The blades sit on dwelling boundaries and slope from 3.45 m at the facade to
the 1.25 m front fence. The tall adjacent windows have plain framed glazing;
the earlier privacy fins have been removed. Single-garage doors and bin screens are coordinated with
the front boundary rhythm. Rear gardens include pergolas and screened plant.

The steep front roof and its boxed dormers remain. A shallower pitched section
replaces the long flat top and steep rear slope: the profile runs through
(depth, height) 2/9.65, 7.8/10.30 and 14.6/8.95 m. Brick gables close both ends.
This interprets the reference rather than reproducing measured roof geometry.
No alternation in actual storey count is assumed.

The ground-floor street frontage is enclosed in pure-white render, including the
garage doors and a fascia over the existing beam. Each single white entry door
faces the approach to the first stair flight, with a narrow full-height sidelight.
Bin enclosures turn along the garden boundary beside the tree, clear of both
garage and entry approaches. Three framed windows puncture each exposed end wall.
Side gardens are approximately 2.2 m wide; white picket fences turn the corners
on 0.5 m rendered block dwarf walls with cappings.

`detail_review.py` closes the roof edges at party boundaries and adds continuous
joint flashings. The misplaced diagonal electrical service stays below ground
until its existing indoor connection; downpipes remain unchanged. Individually
modelled leaves and branches replace the faceted tree placeholders, with foliage
checked clear of each dwelling's party boundaries.

End windows are now 1.45, 1.80 and 2.00 m tall from bottom to top. The lower
window has no hood. Upper hoods project 620 mm with triangular tops/bottoms and
an opaque diagonal privacy face: the first-floor hood opens to the rear, the
roof-floor hood to the front. Metal perimeter frames support their outlines.

The user's later references add full-height painted stair battens, timber
handrails, fine flat perforated metal screens at the rear upper glazing, pale
terrace privacy walls and individually modelled curved brick garden seats.
The current rear screens have a regular 20 mm pitch with 14 mm clear openings,
without the earlier folded pattern. One shared full-height privacy wall separates
each pair of rear balconies, extending from the first-floor slab to 9.38 m.
Rear dormers are 5.40 m wide, twice their previous width; balcony sizes are retained.
Rear boundary and garden dividing fences use timber palings, posts and rails.
`architecture_feedback.py` applies these latest changes after the four-bedroom replan.
The garage partition is moved 70 mm
to preserve the passage beside the screen. Rear screens are a privacy/guarding
concept; their fixings and performance have not been engineered.

## Integrated discipline content

| Discipline | Modelled content |
|---|---|
| Structure | Continuous strip foundations and masonry stems; ground slab; upper slabs with stair voids; masonry bearing walls; opening beams and trimmers; steel roof posts/beams at roof-profile heights; raked timber rafters, trimmed dormers, cheek/window frames, hood frames, end lintels, partition studs/plates and stairs. |
| Electrical | Street conduit, dwelling meters and boards, risers, lighting and power routes, downlights, sockets, switches, smoke-alarm objects and appliance/plant circuits. |
| Mechanical | Rear condensers; three indoor ducted units per home; supply/return grilles, ducts, refrigerant routes, bathroom extracts and independent kitchen exhaust. |
| Hydraulic | Street water and sewer, dwelling water supply, hot/cold risers and wet-area branches, soil/vent stacks, kitchen supply/waste, water heating, roof gutters/downpipes, loggia drainage and AC condensate routes. |
| Interiors | Fitted kitchens and appliances, bathrooms, laundry, wardrobes, beds, lounge and dining furniture, pleated curtains/tracks, timber floors, wall linings, ceilings and service access hatches. |
| Landscape | Individual rear gardens, trees, front planting, pergolas, boundary gates/fences, equipment and bin screens. |
| Civil | New public road/footpath, crossings, garage approaches, pedestrian entries, pits/grates, utility mains and a schematic shared detention tank/overflow. |

Every authored object has a discipline and dwelling identifier. The Blender
collections can be isolated for inspection. `service-routes.json` records each
route's points and radius, and `manifest.json` records the model inventory.

Existing v23 assets are not transplanted indiscriminately: geometry has been
reauthored around the new floor plans. The new model is not equivalent to a full
engineering handover of the old model's detailed circuit and equipment schedules.

## Review files

Each `option-6` / `option-7` directory contains an editable `.blend`, a portable
`.glb`, a manifest, service-route data and renders. The seven-home set includes
street, front, detail, rear, coordination, section and three floor-plan views. The six-home
comparison includes street, front and three floor-plan views.

Blender preserves procedural brickwork. Standard GLB does not reproduce this
procedural shader; the export carries the base material colours. Use the Blender
renders to judge materiality. No external asset downloads or new packages used.

## Coordination limits and next design decisions

This is a detailed schematic model, not a fully engineered or clash-free model.
Explicit checks cover discipline/component presence, finite geometry, stair slab
openings, passage allowance and route segments. They do not certify construction.
The latest architectural revision also checks unchanged transforms and geometry
for all structural, electrical, mechanical, hydraulic and civil objects against
its saved starting model. Results are in `architecture-feedback-audit.json`.
That audit applies to the preceding privacy-wall revision. The subsequent
`frontage-revision-audit.json` checks entries, end windows and bins clear of garage
and pedestrian approaches. It makes targeted openings in the two end masonry
walls and their linings, relocates bins, and extends the entry paths. The new
pitched roof was subsequently framed in `detail_review.py`: flat joists are
replaced by raked rafters, steel cross-beams/posts follow the roof height, dormers
have trimmed openings and matching window/cheek/cap frames, and end windows have
lintels. `detail-review-audit.json` records roof-profile alignment, service-route
correction, unchanged downpipes and tree boundary clearances. Member sizing,
connections, stability, roof drainage and service terminations remain unresolved.

Before construction-level development:

1. Fix a real site, north orientation, dwelling mix, area targets and authority
   constraints. Seven independent crossovers are an illustrative assumption.
2. Engineer masonry/slab spans, large openings, roof stability, foundation type
   and movement joints. Strip foundations replace the previous illustrative piles;
   there is no geotechnical basis yet for selecting between them.
3. Resolve continuous party-wall fire/acoustic separation through the roof;
   coordinate waterproofing, insulation, flashings and dormer junction build-ups.
4. Size plant and services; resolve all branch connections, valve/access positions,
   duct fittings, condensate terminations and slab penetrations. Check routes with
   consultant models; some service geometry denotes reserved routes, not shop detail.
5. Resolve detention versus rainwater reuse, pump/tank capacity and overflow
   approval. The new tank is a detention placeholder, not the original reuse design.
6. Develop end-home windows, exact shading angles, lighting specification,
   furniture clearances, electrical circuit schedules and detailed joinery.

## Reproduce

`mirror_terraces.py` is the final geometry step. It retains the preceding model
and route/manifest snapshots under `before-alternating` names and reloads those
snapshots on repeat runs, preventing a second run from undoing the mirror.

From repository root, using the installed Blender:

The architectural review script retains and reloads
`option-N/terrace-N-before-architecture-feedback.blend` so the changes are
repeatable without accumulating geometry. It represents the four-bedroom model
immediately before this review; the current editable result is `terrace-N.blend`.
`frontage_revision.py` similarly reloads its own `before-frontage-revision` backup,
which includes the preceding privacy-wall changes.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/inspect_source.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/build_terrace.py -- --count 7 --render --export
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/build_terrace.py -- --count 6 --render --export --views street,front
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/refine_screens.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/refine_screens.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/replan_reference.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/replan_reference.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/coordinate_door_risers.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/coordinate_door_risers.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/architecture_feedback.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/architecture_feedback.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/frontage_revision.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/frontage_revision.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/detail_review.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/detail_review.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/mirror_terraces.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/mirror_terraces.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/render_review.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/render_review.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/validate_terrace.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/validate_terrace.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/render_plans.py -- 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/render_plans.py -- 6
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/render_plans.py -- --dwelling 2 7
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/terrace/render_section.py
```

## Landing-page integration � 12 September 2026

The landing viewer loads `frontend/public/landing-assets/coordination/terrace-7.glb`.
The opening ISO view is elevated and angled, with the complete seven-home scheme
in the existing hero position. The model is a white study with TH05's envelope
removed and its structure, interiors, landscape, civil and building services blue.
The public road asphalt block is excluded from rendering and camera framing.
All eight discipline controls remain available; returning from a layer restores
the single-home cutaway. Unit 5 additionally omits 60 measured drywall, ceiling,
bulkhead and service-riser finish objects. Stairs, structural framing, window
coverings, furniture, kitchen appliances, the washing machine and all service
geometry remain. Removal is restricted by dwelling, source material and measured
bounds. Lighting uses a stronger key with lower ambient/environment/fill levels
for brighter lit faces and substantially darker shadows.

Static lived-in variation opens TH03's garage fully, TH06's partly, and TH01's
front entry by 72 degrees. Eighteen front window openings carry a fixed mixture
of open, partially lowered and fully lowered blinds. The existing simplified
PROJECT CAR90 vehicle sits halfway through TH03's garage threshold. These are
static poses; no new animation has been added.

The six shared full-height rear balcony privacy blades are white. Their tops
continue the main roof slope (depth/height: 7.8/10.3 to 14.6/8.95) out to the
balcony edge. Their bases remain at 3.45 m. Ground garden walls and the shorter
end balcony wings are unchanged. These are landing presentation overrides;
the original architectural source remains intact.

`export_web.py` builds the compressed asset from `option-7/terrace-7.glb` without
modifying either architectural master. Run it with Blender in background mode
from the repository root. `export_life.py` extracts measured source opening/blade
bounds and the existing vehicle into the supplementary viewer assets; it runs
with ordinary Python. Then run `pnpm viewer:build` in `frontend`.
The main web export is approximately 2.75 MB and 451 meshes; the vehicle is 1.42 MB.
`terrace-life.ts` applies the reversible door, blind and rear-blade geometry edits
before rendering. Geometry removal is restricted to the measured original object
bounds. The old five-home reveal and vehicle animation are not used by this viewer.


## Current presentation overrides

See [street services audit](STREET-SERVICES-AUDIT.md) for the latest cutaway omissions, connected services, animation and discipline-control behavior. This supersedes the earlier static presentation and retained-curtain notes.


## Runtime batching and latest presentation

`terrace-batching.ts` compacts referenced vertices, bakes static transforms and merges by dwelling, discipline, service associations, context visibility, colour and material state. Moving roof ventilators, condenser fans and birds batch within their local animation roots; roller slats keep independent transforms. Default-view measurements in the same desktop preview changed from 2,206 to 242 meshes and 4,393 to 481 draw calls (about 89% fewer). This is a rendering-work comparison, not a measured FPS claim. Shadow maps are cached between model/filter changes, with updates during the one-time garage opening. Reduced motion and offscreen animation pausing remain supported.

The road mesh is removed; footpath and kerb remain. Pole centres move 0.75 m toward the kerb. A telecom pit and street cable feed seven garage-wall NBN terminations. Each townhouse carries sixteen solar panels, two rows of four flush to each broad shallow upper roof plane on low mounts, wired down the party wall to a garage inverter and switchboard. The steep front roof and rear dormer cap remain clear. Whirlybirds now have spherical bodies with curved seams. Garage six opens once and stays open. Boxed discipline controls align with the scroll arrow, including on mobile.
