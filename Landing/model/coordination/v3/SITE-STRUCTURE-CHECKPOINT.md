# Site and concrete structure checkpoint

`site_structure.build(scene)` expects the active interior scene already rotated once by `Rz(+atan2(.16053,.98703))`. It checks the actual nearest ground slab against the registered focus `(0.552884, −11.138467, 0)` before creating anything. Returned `suppress_source_names` must be hidden by the integrator: they are scattered bins, the old post-box meshes, and the four exact slab bodies copied into the structure collection. Original ground fences and superseded paving remain the integrator's responsibility.

The module creates 52 civil, 35 landscape and 29 structure meshes. Every mesh has a `V3` prefix, `sw_system` and `sw_label`; separate fence runs are combined to limit browser draw calls. No master scene, source model or landing CSS is saved or changed.

- Five garage connections use measured source door positions, with three thresholds at Z 0.50 and the rear pair at Z 0.20.
- The west shared driveway is X −10.0 to −6.1; the parallel pedestrian path is X −11.6 to −10.3. The street faces Y −22, with sidewalk to −23.5 and roadway to −34.
- Lap-and-cap perimeter fence centrelines remain on X ±12 / Y ±22 with zero measured alignment error. The front pedestrian gate has a letterbox blade and cantilever hood; the separate vehicle opening stays clear.
- Ten supplied bin meshes are regrouped in a screened front store. Private garden divisions and restrained green planting occupy the east side; X 6.0–6.8 remains reserved for services, with the proposed underground tank location at (8, −18) clear.
- Four actual slab-body meshes retain their source topology, offsets and stair voids. Five illustrative concrete column stacks and associated concrete pads/pedestals support the nearest dwelling study. All column footprints pass containment checks against the source ground, living and upper floor triangles.

The model records actual coordination questions: support at the changing western floor edge/stair void; column-to-pitched-roof bearing; and driveway/entry grades and turning. Column sizes, reinforcement, loading, bearing capacity, traffic compliance and dimensions in real-world metres remain unverified. Garden divisions are an illustrative layout based on measured dwelling entry centres.

Run from the repository root:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/coordination/v3/site_structure.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/coordination/v3/review_site_structure.py
```

The first command writes the component-only `site-structure-components.blend` and metadata. The second creates disposable overview/detail studies without saving the source scene. Both images were inspected; they illustrate component placement rather than final hero lighting or animation.
