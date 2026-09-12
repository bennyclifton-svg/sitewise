"""Verify planted geometry, deck/post extents, rafter bearing and relocated grates."""
import bpy
import hashlib
from array import array
from pathlib import Path
from mathutils import Vector
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from garden_revision import bounds

def planting():
    result={}
    for o in bpy.context.scene.objects:
        if o.type!='MESH' or not o.name.startswith('Garden |') or not any(n in o.name for n in ('tree ','grass ','shrub ')):continue
        points=array('f',[0])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',points)
        result[o.name]=(hashlib.sha256(points.tobytes()).hexdigest(),tuple(tuple(row) for row in o.matrix_world))
    return result
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-gardens-v8.blend'))
before=planting()
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-decks-v9.blend'))
assert before==planting()
scene=bpy.context.scene
for i in range(1,6):
    parts=[o for o in scene.objects if o.name.startswith(f'Garden | Townhouse {i} ')]
    boards=[o for o in parts if 'deck board' in o.name]
    posts=[o for o in parts if 'awning post' in o.name]
    ledger=next(o for o in parts if 'awning wall ledger' in o.name)
    ll,lh=bounds(ledger)
    for rafter in [o for o in parts if 'awning slat' in o.name]:
        lo,hi=bounds(rafter)
        assert lo.x<lh.x and hi.x>ll.x
        assert abs(lo.z-lh.z)<1e-5
    for post in posts:
        pl,ph=bounds(post)
        assert max(bounds(b)[1].x for b in boards)>ph.x
        assert min(bounds(b)[0].y for b in boards)<pl.y and max(bounds(b)[1].y for b in boards)>ph.y
        assert abs(pl.z-max(bounds(b)[1].z for b in boards))<1e-5
    grates=[o for o in scene.objects if o.name.startswith(f'Storm | House {i} rear pit grate')]
    assert len(grates)==8
    assert min(bounds(g)[0].x for g in grates)>max(bounds(b)[1].x for b in boards)
    assert all(abs(bounds(g)[1].z-.065)<1e-5 for g in grates)
print(f'PASS: {len(before)} planting meshes unchanged; all five decks support posts; rafters bear on wall trimmers; five grates outside decks at lawn level.')
