# Integrated coordination and interactive viewer — 9 September 2026

Master: `../sitewise-integrated-v3.blend`. Source remains `../sitewise-interior-checkpoint.blend`.
Browser: `http://localhost:5173/landing.html`.

## Revision: envelope, access and structure corrections

Default presentation is chalk white across all development geometry, including civil works, planting, fencing, poles and overhead conductors. Glazing stays transparent. Discipline colours appear only during selection/preview. The blue cadastral context remains; the street carriageway surface is omitted while the public footpath and utility connections are retained. Consolidating these default materials reduces the final web model to 14 batches and 5.59 MB; earlier batch counts below are historical.

The latest master supersedes the initial geometry described below. The kitchen assembly is translated approximately 500 mm inside the actual room with 20 mm north/east clearance; electrical and wet-service ports follow that placement. Electrical distribution and soil/water/hood routes are concealed inside measured wall outlines, and chalk rainwater drops follow supported rear wall sections. Existing source downpipes remain. The patio water heater is relocated to the garage utility area as a compact cylinder, clear of the overhead door assembly.

The pedestrian strip is now between the driveway and buildings. Landscaping continues through front/rear strips and outdoor gaps. Garden fences use measured dwelling seams and extend to the garage-facing alignment through genuine outdoor gaps. Three closed 200 mm slabs replace source plaster shells and preserve stair openings; seven concrete column stacks and five fitted roof trusses replace the initial five-stack study.

The selector is a centred vertical rail: A, S, D (electrical distribution), M, H, C, L and I (Interiors), plus Whole project. Hover/focus labels retain full names. Interiors includes 63 authored/source furniture and joinery objects. Geometry is now grouped into approximately 37 batches and remains about 5.7 MB compressed. The fitout module runs before discipline modules. Browser checks cover the new Interiors selection, hover restoration, keyboard reset and mobile rail layout.

## Included

- Registered development, nearest street frontage, garage-side shared driveway and separate pedestrian path.
- Covered front letterbox structure, gate, consolidated bins, lap-and-cap perimeter and garden partitions.
- Private gardens and restrained planting on the opposite side.
- Nearest dwelling reinforced-concrete columns, exact source slab-body geometry and foundations. Superseded timber scene is excluded.
- Transparent window panes and glazed balcony infills with retained frames/rails.
- Electrical street poles/conductors, underground pillar and five DB feeds; 26 lights, 24 double GPOs, five kitchen appliances, 14 switches, 11 circuit groups.
- Separate potable/sanitary/rainwater networks, underground tank/pump, roof drainage, garden reuse and street mains. Fourteen nearest-dwelling fixtures.
- Kitchen hood exhaust, five room extracts and two roof-cavity turbines.

## Viewer

Actual Three.js geometry supports orbit/zoom, seven discipline views, hover preview, click/tap lock, keyboard selection and Escape reset. The close-up button frames the detailed dwelling. Inactive geometry is translucent; ground transparency exposes buried routes. Architecture stays assembled. Rendering occurs on interaction/resize, with no perpetual animation loop.

The model is grouped into 33 material/system batches and Draco-compressed to approximately 5.7 MB, versus 54.9 MB uncompressed. Decoder assets come from the existing Three.js package. No new dependency. Poster image survives unavailable WebGL or model loading failure; unavailable controls remain disabled. The independent landing bundle is built by `pnpm viewer:build`, also run before dev/build.

## Rebuild

Run Blender 5.1.2 in background with `--python Landing/model/coordination/v3/build_integrated.py -- --render --export` from repo root. The three independent modules are assembled once in registered coordinates. `export_web.py` may also run directly to export an existing saved master. Convert the rendered PNG to the public WebP poster, then run `pnpm viewer:build` from frontend.

## Validation

- Site module checks five garage positions, aligned fence centre lines and concrete columns clear of stair voids.
- Electrical checks endpoint continuity, wall mounting and unchanged source transforms.
- Wet-services checks finite continuous routes, independent water networks, roof/wall terminal anchors and unchanged source transforms.
- Browser checks all seven selections, hover restoring a locked choice, Enter selection, Escape reset, close-up and mobile tap. No horizontal overflow at 390px. Model-load failure retains the poster and disables unavailable interactions.
- Typecheck and lint pass. Existing five landing suites: 38 tests pass. Production build and enforced app bundle budgets pass.

## Scope

This is an illustrative coordination model, not consultant design or a surveyed/compliance-checked site. One dwelling has full authored service detail; other dwellings receive site feeds. Utility positions, access dimensions, structural sizing, roof penetrations and non-potable use require project-specific consultant decisions. No clash-free, certified, or resolved-decision counts are claimed. Scroll-driven fly-through and the tablet reveal remain a later composition stage.

Review images: `web-hydraulic.png`, `web-electrical.png`, `web-mobile.png`; rendered overview `../23-integrated-development.png`. Module audit reports sit alongside this file.
