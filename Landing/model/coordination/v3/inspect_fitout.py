"""Measure the supplied fitted kitchen against the real registered room walls."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'sitewise-interior-checkpoint.blend'))
rotation = Matrix.Rotation(math.atan2(.16053, .98703), 4, 'Z')
names = ['SW - 574_Wall white plaster_0.006', 'SW - 575_Wall white plaster_0.008',
         'SW - 576_Wall white plaster_0.009', 'SW - 574_Wall white plaster_0.008']
rows = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or obj.hide_render:
        continue
    if obj.name not in names and not obj.name.startswith(('Kitchen source |', 'SW Asset Fridge |',
        'SW Asset Oven |', 'Microwave |', 'Induction cooktop |', 'Induction zone ', 'Range hood |')):
        continue
    points = [rotation @ obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if not points:
        continue
    rows.append({'name': obj.name, 'source_name': obj.get('source_name'), 'vertices': len(points),
                 'min': [min(p[i] for p in points) for i in range(3)],
                 'max': [max(p[i] for p in points) for i in range(3)]})
(HERE / 'fitout-source-audit.json').write_text(json.dumps(rows, indent=2))
for row in rows:
    print(row['name'], [round(v, 4) for v in row['min']], [round(v, 4) for v in row['max']])
