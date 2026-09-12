import bpy
from pathlib import Path
from mathutils.bvhtree import BVHTree

bpy.ops.wm.open_mainfile(filepath=str(Path(__file__).resolve().parent.parent/'sitewise-exposed-v16.blend'))
scene=bpy.context.scene
def tree(o):
    return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices], [list(p.vertices) for p in o.data.polygons])
units=[o for o in scene.objects if o.get('sw_coordination_revision')]
roof=[o for o in scene.objects if o.name.startswith('Roof v13 | TH02 | ') and not o.hide_render]
clashes=[(u.name,r.name) for u in units for r in roof if tree(u).overlap(tree(r))]
print('UNIT_ROOF_CLASHES',clashes,flush=True)
for r in roof:
    if 'Longitudinal pitch support 4.' in r.name:
        print('SUPPORT',r.get('sw_member_endpoints'),flush=True)
assert not clashes
