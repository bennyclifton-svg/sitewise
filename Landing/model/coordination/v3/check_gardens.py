"""Check that the garden addition preserves the existing model and serves all five homes."""
import bpy
import hashlib
from array import array
from pathlib import Path
HERE=Path(__file__).resolve().parent

def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    result={}
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or obj.name.startswith(('Garden |','V3 | Shrub ')): continue
        points=array('f',[0.0])*(len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co',points)
        result[obj.name]=(hashlib.sha256(points.tobytes()).hexdigest(),tuple(tuple(row) for row in obj.matrix_world),tuple(m.name for m in obj.data.materials if m))
    return result

before=snapshot(HERE.parent/'sitewise-facade-v7.blend')
after=snapshot(HERE.parent/'sitewise-gardens-v8.blend')
assert before==after,'Existing geometry, placement or materials changed'
scene=bpy.context.scene
assert not any(o.name.startswith('V3 | Shrub ') for o in scene.objects)
for i in range(1,6):
    prefix=f'Garden | Townhouse {i}'
    parts=[o for o in scene.objects if o.name.startswith(prefix)]
    assert sum('awning post' in o.name for o in parts)==2
    assert sum('tree trunk' in o.name for o in parts)==1
    assert sum('breakfast table slat' in o.name for o in parts)==7
    assert sum('chair ' in o.name and ' seat ' in o.name for o in parts)==10
    assert all(o.get('sw_service_systems')=='["landscape"]' for o in parts if 'awning' in o.name)
print(f'PASS: {len(before)} existing meshes preserve geometry, transforms and materials; five pergolas, five breakfast settings, five trees; shrub proxies removed.')
