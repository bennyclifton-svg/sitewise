"""Read the existing fitted electrical endpoints without changing the scene."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'sitewise-interior-checkpoint.blend'))
scene = bpy.context.scene
rows = []
for obj in scene.objects:
    if obj.type != 'MESH':
        continue
    if not obj.name.startswith(('Kitchen source', 'SW Asset Fridge', 'SW Asset Oven',
                                'Microwave |', 'Induction cooktop', 'Range hood')):
        continue
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    rows.append({'name': obj.name, 'visible': not obj.hide_render,
                 'min': [min(p[i] for p in points) for i in range(3)],
                 'max': [max(p[i] for p in points) for i in range(3)],
                 'matrix_world': [list(row) for row in obj.matrix_world]})
(HERE / 'electrical-source-audit.json').write_text(json.dumps(rows, indent=2))
print('ELECTRICAL_SOURCE_AUDIT', len(rows))
