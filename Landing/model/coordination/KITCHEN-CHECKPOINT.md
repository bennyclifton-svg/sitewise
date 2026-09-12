# Checkpoint 01 — fitted kitchen

The current working scene is `sitewise-kitchen-checkpoint.blend`. It retains the full
development and a perspective camera inside the nearest dwelling's living-level kitchen.
The placement is a first fit for review, not a completed kitchen design.

## Included

- Adapted cabinetry and countertop from `kitchen.glb`.
- Supplied sink/drainer, mixer and range hood.
- Separate fridge/freezer and oven assembly extracted from `interior-design.glb`.
- Authored microwave with real housing, door, handle and controls.
- User-selected induction cooktop with geometric cooking-zone markings; source gas
  grate/burner geometry removed. No gas cooking connection is assumed.
- Four initial kitchen ceiling lights and a range-hood task light, with actual render
  illumination rather than bright fixture materials alone.

The original two kitchen cabinet/worktop meshes and original sink/cooktop are retained
but hidden in the working copy. Imported appliance fronts that depended on textures
are replaced; decorative plants/jars are omitted. The imported overhead cupboards
crossed the source kitchen window, so those cupboards are removed from the fitted copy.
Original architecture, openings and source GLBs remain unchanged.

Source kitchen units are scaled by 0.001 to match the supplied building. Appliance widths
and depths are deliberately adjusted to the existing source cabinet bays. These are
illustrative fit dimensions, not manufacturer requirements. Check appliance door swings,
ventilation, installation clearances and dining circulation before calling the fit final.

## Evidence and traceability

- `11-fitted-kitchen.png`: interior detail, with restrained warm lighting and depth of field.
- `12-kitchen-placement-review.png`: overhead room review; concealment is for inspection
  only, and is not saved into the full fly-through scene.
- `kitchen-checkpoint.json`: source/instance records, placement matrix and service checklist.
- `asset-audit/KITCHEN-ASSET-AUDIT.md` and `SECONDARY-ASSET-AUDIT.md`: findings and credits.
- `asset-audit/appliance-library.blend`: reusable fridge, oven and two pendant extracts.

The sink and appliance positions now differ from the previous hydraulic concept. Its
routes must be re-anchored to these new fittings before the next system reveal. The
asset manifest records service requirements, but exact electrical terminals, circuit
loads, hood duct routes and plumbing endpoints remain to be detailed.

## Next checkpoints

1. Review the kitchen footprint, window clearance and level of visible appliance detail.
2. Add a restrained lighting layout throughout this dwelling, then selected pendants,
   one curtain set and limited soft furnishings. The extracted pendants are ready;
   they are not placed in this first scene.
3. Follow the later structural correction in `MODELLING-CHECKPOINTS.md`: reinforced-concrete columns and slabs. The subsequently built timber study is superseded and retained for now at the user's direction.
4. Connect services and coordination decisions, then site/utility and vehicle stories.

The full sequence and review criteria are in `MODELLING-CHECKPOINTS.md`.
