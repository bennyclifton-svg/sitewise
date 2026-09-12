"""Read-only geometry inventory for the facade revision."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'sitewise-chalk-v10.blend'))
records = []
for o in bpy.context.scene.objects:
    if o.hide_render or o.type != 'MESH':
        continue
    if not (o.name.startswith(('WD -', 'DOO -', 'CI Tools Wall', 'SLA -', 'Facade |', 'Ground finish', 'Detail | Garage', 'V3 | Building-side')) or any(s in o.name.lower() for s in ('door', 'planter', 'step'))):
        continue
    p = [o.matrix_world @ v.co for v in o.data.vertices]
    records.append(dict(name=o.name, lo=[round(min(v[i] for v in p),4) for i in range(3)], hi=[round(max(v[i] for v in p),4) for i in range(3)], glass=bool(o.get('sw_glass')), materials=[m.name for m in o.data.materials], vertices=len(o.data.vertices), source=o.get('source_name','')))
(HERE/'premium-source-inventory.json').write_text(json.dumps(records,indent=2))
print('INVENTORY',len(records))
