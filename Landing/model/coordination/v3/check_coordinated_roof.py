"""Verify the saved coordination checkpoint independently of its builder."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from replicate_dwellings import bounds
from rebuild_paired_roofs import roof_surface,height
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-coordinated-v17.blend'))
scene=bpy.context.scene
audit=json.loads(scene['sw_coordination_v17'])
assert not any(o.name.startswith('V3 | Entry link ') for o in scene.objects)
prior=json.loads((HERE/'exposed-dwelling-audit.json').read_text())
assert all(scene.objects.get(n) and scene.objects[n].get('sw_component')=='stair' for n in prior['structural_stairs'])

def overlap(a,b):
 al,ah=bounds(a);bl,bh=bounds(b)
 return all(min(ah[i],bh[i])-max(al[i],bl[i])>0 for i in range(3))

for n in range(1,6):
 prefix='' if n==1 else f'TH{n:02} | '
 for side,columns in [('Front',(1,2)),('Rear',(3,4))]:
  beam=scene.objects[prefix+f'Detail | {side} roof bearing beam']
  assert all(overlap(beam,scene.objects[prefix+f'V3 | RC column {i} level 3']) for i in columns),(n,side)
 for level in (1,2,3):
  lo,hi=bounds(scene.objects[prefix+f'Coordinated | RC bedroom blade wall level {level}'])
  assert abs(hi.x-lo.x-1)<1e-5
 assert not any(o.name.startswith(prefix+'V3 | Whirlybird ') and 'flashing' in o.name for o in scene.objects)
 for side in ('west','east'):
  obj=scene.objects[f'Coordinated | TH{n:02} {side} roof to pit']
  assert obj['sw_system']=='civil'
  points=[Vector(p.co[:3]) for p in obj.data.splines[0].points]
  record=next(r for r in audit['drainage'] if r['dwelling']==n and r['side']==side)
  assert (points[0]-Vector(record['start'])).length<1e-5
  assert (points[-1]-Vector(record['end'])).length<1e-5
  assert all(b.z<=a.z+.001 for a,b in zip(points,points[1:]))
assert not any('MEC-cavity-neck' in str(o.get('sw_route_id','')) for o in scene.objects)

def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
units=[o for o in scene.objects if o.get('sw_coordination_revision')]
roof=[o for o in scene.objects if not o.hide_render and (o.name.startswith('Roof v13 | TH02 | ') or 'Plant bay trimmer' in o.name)]
assert not [(u.name,r.name) for u in units for r in roof if tree(u).overlap(tree(r))]
print('SAVED_COORDINATION_PASS: 10 connected graded drops; 20 column/bearing contacts; 15 blade-wall segments; stairs preserved; no plant/roof clashes',flush=True)
