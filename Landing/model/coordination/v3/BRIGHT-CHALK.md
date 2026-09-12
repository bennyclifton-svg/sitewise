# Bright white chalk finish

Current master: `../sitewise-bright-chalk-v14.blend`.
Preserved input: `../sitewise-roof-frames-v13.blend`.

All materials, including brick, doors, windows, louvres, roofs, garden planting,
site elements, interiors and services, now use neutral bright white. Metallic
response is removed and opaque surfaces use 0.86 roughness. Glazing remains
untinted and translucent with 0.32 roughness. Directional illumination, shadow
and the existing modelled surface detail provide contrast.

The viewer uses the same white finish across whole-project and discipline views.
Daylight and night lighting are neutral white. Interface discipline labels retain
their existing colours, but these no longer tint model geometry.

Geometry, transforms and object visibility are preserved. `bright-chalk-audit.json`
records the material inventory and preserved object count. The review image is
`bright-chalk-overview.png`.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python Landing/model/coordination/v3/bright_chalk.py -- --export --render
```

Run `pnpm viewer:build` in `frontend` after viewer code changes. The standalone
`export_web.py` exports v14. If rebuilding geometry from v13, rerun the palette
script afterwards.
