# Satin-white model with neon-blue discipline selection

Superseded viewer styling: the latest viewer uses solid blue selection without
emission or blur, darker neutral shadows, and a 42-degree perspective camera
(adapted to narrow viewports). The satin-white v15 material master remains current.

Current master: `../sitewise-satin-white-v15.blend`; preserved input: v14.
Pure white replaces the previous 98% white. Opaque roughness is 0.38 rather than
0.86; untinted glazing roughness is 0.16. Geometry is unchanged.

The viewer uses a procedural studio reflection environment, brighter exposure
and neutral fill to lift shadows without eliminating the modelled surface detail.
Whole-project and Architecture views remain white. Structure, Electrical,
Mechanical, Hydraulic, Civil, Landscape and Interiors share one blue emissive
selection style on hover, keyboard focus or click. Leaving an unpinned hover
restores the current selection.

`frontend/src/landing/service-glow.ts` adds a two-pass, half-resolution blue halo
only while a discipline is selected. The composite preserves canvas transparency
so the existing cadastral background remains visible. No dependency was added.

Rebuild the material master with Blender:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/satin_white.py -- --export
```

Rebuild the viewer using `pnpm viewer:build` from `frontend`. The standalone
`export_web.py` also uses v15. Neon selection is interactive viewer styling,
not permanently coloured materials in the editable master.
