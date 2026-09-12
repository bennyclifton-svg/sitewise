# All five dwellings — 12 September 2026

Editable master: `../sitewise-all-dwellings-v12.blend`.
Preserved source: `../sitewise-premium-v11.blend`.

The first dwelling's 83 structural, 606 electrical, 282 mechanical and 55
hydraulic objects are replicated into the other four dwellings. Copies share
the approved source meshes and curves, retaining materials and service metadata.
Circuit and endpoint IDs are qualified by dwelling; rotor pivots follow each
placement. The exporter reverses face winding for mirrored objects.

Source floor slabs establish the placements, with the garage positions identifying
handedness. Dwellings 3 and 5 reflect across the site Y direction; dwellings 4 and
5 step down 300 mm. Source garage centres differ by up to 150 mm from an exact
copy, and some upper slab edges differ slightly. These remain illustrative
replicated services, not independently redesigned or engineering-validated layouts.

Original slabs replaced by the concrete structure are hidden. Existing wet fixtures
receive hydraulic membership where a matching source fixture is found. Existing
distribution boards and individual site feeds remain; short connections join them
to the copied internal services. A single common sanitary collector connects all
five local stacks to the street. Civil drainage, landscape and facade remain.

`dwelling-replication.json` records placement matrices, source slabs, replaced
slabs and fixture memberships. `dwelling-replication-check.json` records independent
checks of 4,104 saved copies: geometry identity, transforms, discipline counts,
replaced slabs and five retained distribution boards.

Review render: `all-dwellings-services.png` (architecture hidden to expose detail).

From the repository root:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/replicate_dwellings.py -- --export
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/check_dwellings.py -- --render
```

The standalone `export_web.py` also uses v12. Rebuild the viewer with
`pnpm viewer:build` in `frontend` after changing its discipline descriptions.
