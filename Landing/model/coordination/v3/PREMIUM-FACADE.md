# Warm brick and bronze facade — 10 September 2026

Current editable model: `../sitewise-premium-v11.blend`.
Source retained: `../sitewise-chalk-v10.blend`.
The user approved the image mock-up and then authorised implementation, with
explicit requirements that louvres sit over windows and planting leave doors clear.

## Design

- Pale sand brick on 29 ground-floor and middle-level side-wall panels. Brick
  courses are modelled geometry, with 240 × 75 mm modules and 8 mm joints, so
  they survive the texture-free web export. A sweep unions the source covering
  polygons before clipping the brickwork, removing weatherboard overlaps while
  preserving the actual opening boundaries.
- Five front bedroom screens and seven tall side-window screens: 80 bronze
  vertical blades, mounted with top/bottom carriers and four frame stand-offs
  per screen. Blade spacing is adjusted around the actual glazing and mullions.
  The front screens cover approximately half the window width; remaining glazing
  stays open. Minimum separation from the modelled glazing envelope is 255 mm.
- Five softly rounded mineral window surrounds and three continuous balcony
  fascia wraps, following the existing single and paired blocks. The wraps have
  260 mm outer corner radii and return to the original fascia; existing structural
  slabs and inset glass balustrades remain intact.
- Warm timber balcony recesses and entrance doors; satin bronze window frames,
  balcony metalwork, garage doors and five slim entrance sconces. Pitched roof
  shapes remain, with a warm grey finish. Upper weatherboards are retained.
- Five small balcony planters, each with a contained soil bed and fine planting.
  No new ground-level beds, pots or planting obstruct garage aprons, steps or
  entrances. Existing rear gardens, decks and pergolas are retained.

## Verification

`premium-facade-audit.json` records 5,633 original meshes with unchanged vertices,
topology and world transforms. Replaced wall-covering and trim objects are hidden
in the new checkpoint, rather than deleted from the source. Every new screen
retains its named source window as metadata.

`check_premium_facade.py` opens the saved checkpoint independently. All 80 blades
hit their actual host glass at four sampled heights (320 successful checks).
Another 270 rays find no new brick across the tested opening interiors. All 35
planter/soil/planting objects clear door bounding volumes with a 100 mm margin.
The minimum depth from a planter's back to the balcony door frame is 1.291 m.

The web GLB retains all eight disciplines, the car and rotor motion metadata,
and facade materials. Export size is approximately 8.07 MB in 71 batches.
The Architecture selector now preserves the original finish colours. Local
browser checks confirmed model loading, material display and Architecture selection.
Frontend typecheck, lint and viewer build passed with Node 22.20.0 / pnpm 11.5.2.

This is a developed presentation model, not construction documentation. Screen
fixings, full sash operating envelopes, curved cladding support and planter
waterproofing/drainage still need construction detailing. Geometry checks above
describe the modelled state and do not certify building compliance.

## Rebuild and review

Run from the repository root using Blender 5.1:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/premium_facade.py -- --export
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/check_premium_facade.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/render_premium_facade.py
```

Run `pnpm viewer:build` from `frontend` after changes to the viewer code.
`export_web.py` also exports this checkpoint directly.

Review images are actual Blender renders: `premium-overview.png`,
`premium-front-detail.png`, `premium-rear.png` and `premium-window-detail.png`.
The render script uses temporary cameras and lights without saving over the model.
