## Latest opening composition and white finish

The opening and project-focus view now use the supplied right-hand oblique angle (direction 0.48, 0.32, 1), retaining the wider 64% desktop fit and soft edge fade. The remaining upper-window figure is removed. Street service routes and all solar-panel frames, cells and mounts are white, including the panels on townhouse five; the building cutaway remains blue.

## Solar doubled to two rows per roof plane

Each townhouse now has 16 panels: two rows of four on each of the two broad upper roof planes (112 panels across seven townhouses). Flush low mounts and inverter connections are retained. Columns clear the whirlybirds, and the steep front roof stays clear.

## Front-view opening and soft ends

The landing model now opens straight from the front with a slight elevation (direction 0, 0.15, 1). Desktop framing uses a wider 64% site fit to approximate the supplied reference; the project-focus action restores the same view. A horizontal canvas mask softly fades both ends while leaving the page copy, map and controls unaffected. Mobile uses a separate, narrower edge fade.

## Solar layout correction

Eight panels per townhouse (56 total): four on each broad shallow upper roof plane. Panels follow the roof slopes with approximately 70 mm centre clearance and low mounting rails; the steep front roof and rear dormer cap are clear. Branch cables join at the ridge and continue to the garage inverter.

## Latest presentation and performance update

Road removed, footpath retained, poles moved toward the kerb, telecom street pit/cable and seven garage terminations added. Four solar panels per flat rear roof tilt left and connect to garage inverters. Spherical whirlybirds rotate; garage six opens once. Boxed controls align with the scroll arrow.

Runtime batching reduces mesh count from 2,206 to 242 and measured default-view draw calls from 4,393 to 481. Geometry detail, discipline ownership and animation roots are retained. Shadow rendering is cached between relevant changes.

## Bored piers and strip-footing grid

Added 24 bored piers on a 3-by-8 grid at the eight existing longitudinal footing lines. Each is 300 mm diameter, from model ground level to 3 m below ground. Three transverse strip-footing rows (front/middle/rear) connect the grid at the existing strip-footing elevation, -0.40 to -0.85 m. Existing longitudinal footings remain. All additions belong to structure, with townhouse five's portions blue.

## Service audit and filter refinement

Room-specific electrical reticulation, 200 mm supply ducts, rear/side wet-area extraction, spinning condenser fans, explicit wet-fixture connections and seven 2 x 2 x 0.5 m driveway detention tanks are now in the landing viewer. Civil filtering isolates drainage rather than paving. Hover changes the whole terrace whenever a discipline is already clicked. See [current services audit](terrace/STREET-SERVICES-AUDIT.md).

## Latest landing presentation update

Seven-home white terrace with blue cutaway TH05. Curtains, robes and partition framing are now removed from the cutaway. Connected blue street services, seven meters and entry lights, two poles with four thin conductors and a right-hand transformer/downfeed, varied trees, one upper-window silhouette, animated garage/two tiny white finches and seven rotating roof ventilators are included. Permanent compact discipline controls replace camera buttons; hover previews TH05, click toggles all dwellings. Hero platform copy and CTA sit lower.

See [services audit](terrace/STREET-SERVICES-AUDIT.md) for scope and validation. These viewer overrides supersede older presentation notes below; source BIM geometry is retained.

# Current integrated coordination checkpoint

## Landing viewer � seven-home terrace

The landing viewer uses the compressed `terrace-7.glb` asset with an elevated,
angled ISO opening view. The model is white, with TH05 opened to reveal blue
structure, interiors and services. TH05 drywall, ceilings and service-enclosure
finishes are removed while stairs, window coverings, furniture and appliances
remain. Lower fill/ambient light gives stronger shadow contrast. The road block is hidden. Static open-door,
blind and parked-car variation is present; the six shared rear balcony blades
are white and raked to continue the main roof slope. End wings and ground garden
walls are unchanged. These presentation edits are applied in the viewer without
altering the retained architectural master. See `terrace/README.md` for exact
poses, provenance and regeneration instructions.

The five-home production details below describe the retained previous model,
which is no longer the landing viewer asset.

## Separate brick-terrace redesign study

The user-authorised six- and seven-home street-facing redesign is under
`terrace/`. Start with `terrace/REVIEW.md` and `terrace/README.md`. Current
`terrace/option-7/terrace-7.blend` and `terrace/option-6/terrace-6.blend` use the
later supplied four-bedroom plan: ground living/kitchen to garden, two bedrooms
on each upper level, first-floor laundry and rear balconies. They include the
painted stair battens, flat fine-perforated rear screens, shared front/rear privacy
blades, reduced front loggias, double-width rear dormers and timber paling fences,
plus all eight discipline
collections. These are separate architectural concepts on a reshaped illustrative
site. The v23 editable master is retained; the landing viewer now uses the
seven-home export described above.

The latest frontage revision adds enclosed pure-white entries/garages, relocated
bins, a shallower pitched roof continuation, three windows at each exposed end,
and 2.2 m side gardens with picket fences on block dwarf walls. Targeted end-wall
openings are modelled; roof framing/drainage and window lintels await the next
structural/services review.

The next detailing pass closes roof joints, corrects the entry electrical route,
improves trees and their boundary clearance, and adds taller end windows with
opposing wedge privacy hoods. Raked rafters and steel roof supports now follow
the roof profile, with dormer trimmers, cheek/window frames, hood frames and end
lintels. See `terrace/option-7/roof-frame.png`. Member sizing/connections and roof
drainage remain concept-level; downpipes were preserved.

Current models mirror terraces 2, 4 and 6, including dwelling layouts, roof
framing, services, gardens and crossings. Shared boundaries and exposed end
treatments remain fixed. Seven-home garage pairs are 2–3, 4–5 and 6–7 with
the retained numbering. See `terrace/option-7/plan-TH02-0.png` for the alternate plan.

## Existing production model

The opening/Front camera uses the elevated street-side angle from the latest
reference, a closer 40 m base distance, and a leftward composition shift so the
near fence tucks beneath the headline. Street power lines remain visible.

The departure animation follows a rear-axle turning arc, with continuous travel
through the garage exit and corner. It accelerates on the straight and brakes
before the gate; regression checks cover rolling direction and speed continuity.

12 September entry/bin-store update: current editable master is
`sitewise-entry-bikes-v23.blend`, reproduced by `v3/entry_and_bikes.py`.
The sample entry stepping slabs, garage apron/crossing and frontage path segment
have TH02 blue ownership. The electricity pillar sits outside the east bin-store
wall, with its incoming and dwelling cables reconnected. Ten bins are packed at
550 mm centres; bins 2 and 7 are blue. Two authored illustrative bicycles occupy
the freed space. `v3/entry-v23-audit.json` records ownership and spacing checks.

## Stormwater/sewer checkpoint

12 September stormwater/sewer refinement: current editable master is
`sitewise-services-v22.blend`, reproduced by `v3/refine_site_services.py`.
Shared stormwater pipes and pits have sample-house blue ownership. Stormwater
pipe cross sections are doubled while their centrelines remain fixed; roof
downpipes and gutters retain their sizes. The sewer main is lowered 1.2 m and
moved 1.5 m toward the stormwater corridor, with its collector connections
adjusted. The enlarged stormwater and sewer mains have 250 mm vertical surface
clearance. Water routing is unchanged. Six open paving intervals between the
driveway and pedestrian path are filled, retaining the pit lids.
`v3/services-v22-audit.json` records diameter, clearance and infill checks.

## Connected-mains checkpoint

12 September mains/front-view update: current editable master is
`sitewise-connected-mains-v21.blend`, reproduced by `v3/connected_mains.py`.
Overhead conductors, the pole service cable/riser, site incoming power, water
mains/meter/site header and shared sewer collector/mains share TH02 reveal
ownership. Normal depth testing remains enabled. The viewer starts in the front
view, with closer desktop framing and extra distance on narrower viewports.
The Front control uses the same framing. `v3/connected-mains-v21-audit.json`
records the shared utility objects highlighted with the sample house.

## Solid-foundations checkpoint

12 September solid-occlusion correction: current editable master is
`sitewise-solid-foundations-v20.blend`, reproduced by `v3/solid_foundations.py`.
The viewer no longer bypasses depth testing for owned underground elements:
slabs, paving and foreground geometry occlude piles and services normally.
All fifteen 200 mm slabs retain their exact mesh vertices and opaque materials.
All sixty piles are now 2.25 m deep, seated into the underside of existing
perimeter strip footings; separate caps are removed. The sample roller slats,
hood and source roller assembly are removed, leaving its garage open.
`v3/solid-foundations-v20-audit.json` records the geometry checks. The earlier
x-ray overlay was the cause of the apparent slab transparency, not lost thickness.

## Sample-house checkpoint

12 September sample-house illustration: current editable master is
`sitewise-sample-house-v19.blend`, reproduced by `v3/sample_house.py`.
Both visitor bays contain stationary copies of the licensed vehicle. The moving
vehicle and roller door now belong to TH02; the old garage panel is restored.
Its animation anchor is exported from the measured sample garage position.
All TH02 rear garden objects, furniture and its rear boundary stretch have
explicit reveal ownership, as do its dedicated utility feeds and driveway pit 3.
The pit grate is raised 55 mm and the sample rear grate 40 mm for visibility.
Selected buried services and foundations render as blue cutaway overlays.
Each dwelling has twelve illustrative 300 mm diameter, 4 m deep piles and caps
on a four-by-three grid (60 piles total); TH02's twelve are blue in its exposed
view. `v3/sample-house-v19-audit.json` records ownership and geometry.
This remains presentation geometry, without geotechnical or foundation design.

## Compact-site checkpoint

12 September compact site: current editable master is
`sitewise-compact-site-v18.blend`, reproduced by `v3/compact_site.py`.
The townhouse group moves 2.5 m toward the fixed street/bin assembly, roughly
halving the intervening lawn. The rear fence moves from y=22 to y=17.5, reducing
the nominal site depth from 44 to 39.5 m. A continuous rear court has two visitor
bays, each 2.5 x 5.4 m, with a 6 m aisle; the driveway now reaches the court end.
Rear lawn and side boundaries are shortened with the site. Public footpath,
crossover, bins, enclosure and front entry geometry/positions are preserved.
`v3/compact-site-v18-audit.json` records the dimensions and protected objects.
The exporter carries the dwelling offset into the viewer's reveal masks;
`v3/export_outlines.py` rebuilds the moved floor/roof outlines.
Parking dimensions are illustrative layout geometry, not swept-path validation.

## Roof/civil checkpoint

12 September roof/civil coordination: current editable master is
`sitewise-coordinated-v17.blend`, reproduced by `v3/coordinate_roof_drainage.py`.
All five dwellings have perimeter roof gutters, two full-height rainwater drops
and branches into the existing pit network. Five entry ramp wedges are removed;
the source stair solids remain. Civil selection now includes the driveway and
garage aprons. All ten turbines are seated against the measured roof surface,
with copied flashings removed and their necks replaced.
TH02 trusses 5/6 retain the front half and rear quarter, with a trimmed opening
in the third quarter for the air handler. Front bearings and truss heels reach
the columns; the bedroom-side column 6 stack becomes a 1 m transverse blade wall
in each dwelling. `v3/coordination-v17-audit.json` records the changes and zero
air-handler/roof-member clashes. These are illustrative model connections;
structural sizing and stability have not been engineered.

## Previous checkpoints

12 September exposed-house refinement: current editable master is
`sitewise-exposed-v16.blend`, reproduced by `v3/refine_exposed_dwelling.py`.
The second closest dwelling starts exposed, including its blue rear deck,
awning and tree. Front balcony planters are removed across all five houses;
existing stair tread solids now belong to structure. TH02 trusses 5 and 6 are
removed to form the indoor-unit bay. The unit moves 0.5 m toward the party wall
and 1.02 m laterally; its supply plenum is shortened with connected routes adjusted.
`v3/check_exposed_clearance.py` verifies no unit-assembly/roof-member intersections.
This remains illustrative presentation geometry, not an engineered truss design.

Latest viewer refinement: v15 satin-white geometry now renders with darker
neutral shadows, sharp solid-blue discipline selections (no glow), and a
perspective camera with foreshortening. The view control is labelled Perspective.

12 September 2026 reference refinement: current master and web export are
`sitewise-satin-white-v15.blend`. Pure white materials use a satin finish,
with studio reflections and brighter neutral lighting in the viewer. All
non-architectural discipline selections use the same neon-blue emissive glow.
See `v3/SATIN-WHITE.md`.

12 September 2026 palette update: the current editable model and web export are
`sitewise-bright-chalk-v14.blend`. Every material is neutral bright chalk white,
with nonmetallic matte surfaces and untinted glazing. Viewer discipline selection
and day/night lighting also remain achromatic. See `v3/BRIGHT-CHALK.md`.

12 September 2026 roof correction: the current editable model and web export are
`sitewise-roof-frames-v13.blend`. The four newly detailed dwellings now have
varying compound-roof frames fitted below the existing roof coverings. The
original standalone pitched frame remains unchanged. See `v3/COMPOUND-ROOFS.md`.

12 September 2026: the current editable model is `sitewise-all-dwellings-v12.blend`.
All five dwellings now contain the first dwelling's structure, electrical,
mechanical and hydraulic detail. Townhouses 3 and 5 are mirrored; townhouses
4 and 5 are 300 mm lower. The web GLB exports this checkpoint.
See `v3/ALL-DWELLINGS.md` for rebuilding, checks and the review image.

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
The premium facade is retained in the current all-dwellings v12 checkpoint.
