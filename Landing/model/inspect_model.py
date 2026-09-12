"""Inspect the supplied GLB without modifying it. Run with Blender --background."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'duplex.glb'))
rows = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    chain = []
    parent = obj.parent
    while parent:
        chain.append(parent.name)
        parent = parent.parent
    rows.append(dict(name=obj.name, parents=chain,
                     min=[min(p[i] for p in corners) for i in range(3)],
                     max=[max(p[i] for p in corners) for i in range(3)],
                     vertices=len(obj.data.vertices),
                     materials=[m.name for m in obj.data.materials if m]))
(ROOT / 'model-inventory.json').write_text(json.dumps(rows, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'source-import.blend'))
print('INVENTORY_COMPLETE', len(rows), flush=True)
