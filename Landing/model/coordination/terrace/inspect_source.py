"""Read the existing master without modifying it; record measured model bounds."""
import json
from collections import Counter
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'sitewise-entry-bikes-v23.blend'))
records = []
for obj in bpy.context.scene.objects:
    if obj.type not in {'MESH', 'CURVE'} or obj.hide_render:
        continue
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    records.append(dict(name=obj.name, system=obj.get('sw_system', 'architecture'),
                        dwelling=obj.get('sw_dwelling'),
                        min=[min(p[i] for p in points) for i in range(3)],
                        max=[max(p[i] for p in points) for i in range(3)]))
summary = dict(source='sitewise-entry-bikes-v23.blend',
               units=bpy.context.scene.unit_settings.system,
               scale=bpy.context.scene.unit_settings.scale_length,
               counts=dict(Counter(r['system'] for r in records)),
               anchors=[r for r in records if any(k in r['name'] for k in
                   ('Shared driveway', 'pedestrian path', 'Public footpath',
                    'SLA - 007_Concrete - Foundation_0', 'boundary', 'Boundary'))])
(HERE / 'source-inventory.json').write_text(json.dumps(records, indent=2))
(HERE / 'source-audit.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
