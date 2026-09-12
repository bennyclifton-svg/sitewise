# Facade refinement checkpoint — 9 September 2026

Current editable facade model: `../sitewise-facade-v6.blend`.
Source retained: `../sitewise-detail-v5.blend`.

Run `facade_revision.py` with Blender in background mode to rebuild the facade
checkpoint and web export. Run `pnpm viewer:build` in `frontend` afterward.
The standalone `export_web.py` now exports this facade checkpoint.

- 58 existing windows receive a hierarchy of shallow four-sided front surrounds,
  thin horizontal blades for wider secondary openings, and quiet small-window heads.
- Front surrounds project 270 mm, larger secondary blades 480 mm, small heads 120 mm;
  the previous uniform hoods were 650 mm deep. These are model dimensions.
- Balcony recess cladding and exterior soffit faces have a warm oak finish.
- Exterior covering finishes use warm limestone; window trim and balustrade metal
  share satin bronze. Existing covering geometry and opening cutouts are retained.
- Five narrow window stacks have segmented mineral-finish infill bays, leaving
  the existing openings clear.
- The whole-project viewer preserves Facade materials. Discipline highlighting
  retains its existing schematic colour behaviour.

Validation: all 4,990 retained source meshes have identical vertex coordinates and
world transforms. Original hoods alone are replaced. Room layouts, openings, roofs,
slabs and service geometry are preserved. The four facade PNGs were visually reviewed.
Frontend typecheck, lint and viewer build passed.

These are facade concept treatments; projection depths have not been solar-modelled.

Follow-up: current export is sitewise-facade-v7.blend. Run close_side_gaps.py after the facade pass. The approach infill now meets the footpath at Z=0.275 and overlaps the building edge; the rear setback ground cover extends to the inset ground-floor wall. All other object transforms are retained.
The follow-up also closes the exposed strip below each of the five ground-floor wall bases with a matching limestone plinth; existing walls and openings are unchanged.
