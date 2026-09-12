# Compound roof framing correction

Current master: `../sitewise-roof-frames-v13.blend`.
Preserved input: `../sitewise-all-dwellings-v12.blend`.

The screenshot showed copied triangular trusses projecting above the other four
roof coverings. Those roofs have intersecting pitches and sloping ends, unlike
the original standalone pitched roof.

The four new frames use eight transverse trusses per dwelling, with top chords
following cross-sections of the actual source roof surfaces. Their heights and
pitch transitions vary along the building. Bottom ties, verticals, diagonals and
longitudinal pitch supports complete the illustrative frame. The old copied
trusses and constant-height ridges are hidden; the existing bearing beams remain.
Top chords are set below the tile surface, accounting for their member depth.

The user's townhouse numbering runs opposite to the internal replication IDs:
user townhouse 5 is internal dwelling 1 (the unchanged original); user townhouses
1–4 are internal dwellings 5–2. No renaming of unrelated model objects is required.

`compound-roof-frames.json` records the generated profiles and hidden members.
`compound-roof-check.json` records saved-model clearance checks and preservation
of all original objects' transforms, mesh vertex counts and visibility, except
the explicitly replaced roof members. Roof joints are resolved using adjacent
surface rays within 10 mm where an exact ray falls in a shingle seam.

Review images: `compound-roofs-envelope.png` and `compound-roofs-frame.png`.
This changes presentation geometry; member sizes and structural adequacy are
not engineering-validated.

From the repository root:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/rebuild_paired_roofs.py -- --export
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/check_compound_roofs.py -- --render
```

If rebuilding v12 from scratch, run the commands above afterwards. The standalone
`export_web.py` uses v13 directly.
