# Landing model detail checkpoint

The September 9 detail pass exports `sitewise-detail-v4.blend` from the registered
`sitewise-integrated-v3.blend`, preserving that source master.

Run Blender in background mode with `--python Landing/model/coordination/v3/enrich_model.py`.
Then run `pnpm viewer:build` in `frontend` to rebuild the interactive viewer.

Added window hoods derived from the existing glazing bounds; a roof-void air
handler, supply and return plenums, four ribbed flexible room branches and ceiling
diffusers (two at the upper ceiling and two dropping to the living-level ceiling);
an outdoor condenser at the side gable with fan grille, feet, plinth, concealed refrigerant pair and
electrical isolator; ground-cover infill at lawn seams, front/rear gardens, service corridor
and building setbacks. These are illustrative model details, not an engineered
services layout or approved landscape design.

One garage uses 21 roller slats. The web exporter preserves `sw_motion` batches
for each slat and the supplied vehicle. `garage-motion.ts` controls the departure:
door opens, vehicle clears the opening, turns into the shared drive, and the door
closes. It plays once on entry, can be replayed using Garage departure, and also
accompanies the camera tour. Motion stops offscreen, on interaction, and for
reduced-motion preferences. The reduced-motion pose shows the open garage and car.

Vehicle: PROJECT CAR90, *Land Rover Defender - Edition Grasmere Green*, CC BY 4.0.
Source and licence links are in the landing footer and original asset audit.
The supplied geometry is scaled by 0.5 in the export and a further 0.86 around
its ground-contact pivot in the viewer, following the scale review. It is
simplified, given chalk/trim materials, and repositioned. The two remote source
components are excluded.

Validation: measured vehicle bounds fit the opening at rest; targeted tests check
door clearance before departure, vehicle clearance before turning, closure and
replay. Desktop/mobile browser inspection covers visible vehicle, mechanical
isolation, survey-light map, and controls. Typecheck, lint and viewer build pass.

The follow-up pass classifies perimeter fencing, the front gate, the bin enclosure
and bins as Landscape in the export and saved detail checkpoint. The viewer uses
labelled drawing tabs (E for Electrical), wheel/pinch and button zoom, lower fill
lighting, and architectural shadow reception without emissive wash. The cadastral
map uses a broad moving light mask over stationary linework; model system changes
no longer select a parcel. Manual parcel selections clear with Escape.

`structure_revision.py` replaces the pad footings/pedestals with a continuous
strip and foundation stem following the ground slab's exterior edge (excluding
internal openings). It distributes eight trusses evenly between the original end
positions and adds two continuous bearing beams under their ends. The revision
is also applied by `enrich_model.py` so rebuilding retains these changes.
The bearing beams match the ridge member's section and material (approximately
100 × 120 model millimetres), replacing the earlier oversized concrete sections.

`condenser_placement.py` relocates the condenser off the rear patio to the side
gable at the end of the building. Its paired wall riser runs within the side wall
and crosses beneath the roof void before entering the air handler near the ridge.

`electrical_circuits.py` replaces the six lighting/GPO distribution manifolds
with fitting-to-fitting loop-in runs. Each floor has one lighting and one power
circuit; the five dedicated appliance circuits remain separate. Fourteen existing
wall-mounted room switches connect to their lighting groups. Cable routes have
rounded corners and slight lateral slack within the ceiling envelope. Original
light, GPO and switch positions are preserved. `electrical-circuits.json` records
the ordered circuits, cable paths and switch-to-light relationships for a later
on/off animation; no electrical animation is introduced in this revision.

`cable_tray.py` adds an open ladder tray at the garage switchboard, transfer and
main vertical service riser, plus a short roof header. Upper lighting and power
feeds run inside the header before peeling off; small saddles secure roof cables
at truss crossings. Floor circuit endpoints and switch connections are preserved.
The full enrichment pipeline applies this revision after rebuilding the circuits.

`civil_stormwater.py` moves rainwater equipment, gutters and downpipes into Civil.
Hydraulic retains potable supply and sanitary drainage. Four grated driveway
pits, five rear pits and one bin-room pit feed the retained tank and a single
road outlet beneath the driveway. Five side collectors avoid the slab footprints;
six existing downpipe bases connect into those collectors. The old collector and
overflow routes are replaced, avoiding a second road connection. Paving is
translucent in Civil selection so the buried network can be reviewed.
`civil-stormwater.json` records the connected graph and footprint checks. This
remains illustrative geometry; pipe grades, detention sizing and outlet control
have not been hydraulically designed.
