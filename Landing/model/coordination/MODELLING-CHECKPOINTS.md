# SiteWise modelling checkpoints

Updated 8 September 2026. This is a workplan, not a completion record.
The fitted kitchen has been approved. Lighting, GPOs and restrained furnishings are the current checkpoint.
The user's latest correction supersedes the earlier timber assumption: the primary structure should use reinforced-concrete columns and reinforced-concrete slabs. Keep the earlier timber geometry only as a superseded study; the user asked to leave it for now, so no immediate structural rebuild is required. Roof construction and infill details remain to be confirmed.
The user selected an all-electric kitchen; use an induction cooktop and no gas cooking connection.

## Direction to preserve

- Show the full development, then approach and enter one dwelling to explain its systems.
- Retain Camera B as the opening reference, chalk architecture and the assembled building.
- Reveal systems in place through selective translucency and a few useful feature edges.
- Use one cadastral scene for isometric and plan views, with identical building placement.
- Keep service accents distinct from amber decision markers; the final palette is still open.
- Use directional shadows and gentle depth of field in close-ups, keeping the active connection readable.
- Do not use the Impeccable skill. Follow `FLYTHROUGH-DIRECTION.md` where older studies differ.

## 0. Asset audit and selection

Audit `kitchen.glb`, `interior-design.glb` and `car.glb` before transplanting geometry.
Confirm appliances visually; record scale, triangle count, loose parts and source metadata.
The apartment audit confirms a fridge, cooktop, sink/tap, oven assembly, hood and dishwasher.
It also identifies reusable pendants, curtains and furniture; no microwave or actual scene lights were confirmed.
The car needs scale normalization, two remote components removed from the derived copy, and a wheel rig.
**Done when:** each proposed extract has an image, source identity and a reuse/simplify/author decision.
Reference: `asset-audit/SECONDARY-ASSET-AUDIT.md`; keep the kitchen audit alongside it.

## 1. Kitchen — immediate modelling checkpoint

Fit the focus dwelling's existing kitchen, retaining its room, openings and circulation.
Reuse the strongest compatible fixtures from the supplied models; do not import another apartment shell.
Provide a fridge, cooktop/stove, sink and tap, microwave, oven arrangement and range hood.
Check the oven assembly's usable geometry; author a simple microwave because none is verified in the audit.
Retain useful original cabinets and worktops; add only missing joinery needed to house the appliances.
Add one restrained pendant composition if it helps the camera study; full lighting follows next.
Register connection points for sink supply/waste, appliance power and hood exhaust without inventing completed networks.
**Done when:** a chalk close-up and a context view show every required appliance, sensible fit and clear service endpoints.
Deliver an editable derived Blender scene, appliance checklist and source-to-instance manifest for review.

## 2. Lighting and restrained interior detail

Add a small repeatable downlight family throughout the focus dwelling, with pendants at selected focal positions.
Add Australian/NZ-style double GPOs in chalk-white plates throughout the focus dwelling, with room and source-wall references; keep general outlets separate from dedicated appliance connections.
Distinguish visible luminaire geometry, illumination in the render and later electrical connection routes.
Fit one curtain set and a few existing soft furnishings to actual openings and occupied rooms.
Avoid decorative clutter, detailed accessories and importing the entire furnished apartment.
**Done when:** each room has a deliberate lighting provision and two close-ups retain clear building/service readability.

## 3. Structural system from ground to roof

First isolate and verify existing slab/foundation-labelled meshes and wall/roof extents.
Add conceptual concrete foundations and slabs; record true foundation dimensions and ground conditions as unverified.
When the structure is revisited, replace the superseded timber study with an illustrative reinforced-concrete column-and-slab system anchored to actual floor plates and openings.
Resolve column positions, transfers, slab edges and foundations as a coherent concept before representing it as coordinated. Roof and infill construction remain open; do not assume the correction specifies a concrete roof.
Begin with the focus dwelling, review its interfaces, then extend the agreed representation across the development.
Keep party-wall construction, load-bearing roles, spans and member sizes explicitly illustrative and unverified.
**Done when:** isolated foundation, wall, floor and roof views explain a coherent conceptual support arrangement.
This is a visual structural-system model, not engineered design, a member schedule or a compliance assessment.

## 4. Services and coordination decisions

Extend fixture-anchored hydraulics: water, waste and visible drainage interfaces, preserving source fixture references.
Add electrical distribution, lighting and selected appliance endpoints; route separately from luminaire geometry.
Add hood/room ventilation and a restrained mechanical equipment concept with access and envelope interfaces.
Show fire/separation and penetration questions without inventing a verified fire strategy or sprinklers.
Review one system at a time against the frame, slab, joinery and architectural shell.
Use a decision record: question, involved disciplines, illustrative chosen instruction and downstream trade scope.
**Done when:** each route connects to named endpoints and a clear interface; active-system stills keep architecture visible.

## 5. Site services, access and vehicle

Continue selected routes through the lot toward illustrative boundary/street investigation points.
Keep unknown utilities, easements, capacity and connection conditions as open investigation items.
Normalize the car, ground its wheels, simplify its geometry and rig tyre/rim assemblies around correct pivots.
First review a parked vehicle and driveway relationship; then trial a slow entry/exit with steering and wheel rotation.
**Done when:** matching plan/isometric views connect building, parcel, access and street consistently.
Vehicle motion illustrates traffic/access coordination; it does not establish swept-path or parking compliance.

## 6. Unified fly-through and delivery preparation

Combine the site and building studies into one coordinate system before animating the complete sequence.
Review a short low-resolution film: lot overview, dwelling approach, kitchen hold, service/frame reveals and site return.
Use slower holds for decisions; check camera clearances, transparency layering and focal blur throughout the path.
Carry reviewed detail across the development with linked instances where appropriate, keeping one dwelling richest.
**Done when:** the camera, opacity and focus transitions are approved before high-resolution output or web export.
Then simplify by viewing distance, consolidate materials and measure geometry, draw calls and exported size.
Landing integration follows motion review, with a still fallback, mobile treatment and reduced-motion states.

## Working records and checkpoint discipline

- Preserve source GLBs; add geometry in separate collections by dwelling, level and system.
- Record source file/group IDs, instance transforms, modifications and embedded attribution/license metadata.
- Mark authored fixtures, structural members and service routes as illustrative; source geometry is not verified design.
- Give each service endpoint a fixture ID and system; routes also reference their decision and scope/package example.
- At each checkpoint provide one context view, one detail/system view and a short changed/pending list.
- Resolve material placement or visibility problems before replicating detail; avoid polishing unseen objects.
