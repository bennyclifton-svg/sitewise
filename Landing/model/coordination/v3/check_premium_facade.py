"""Independently check saved geometry, glazing hosts, access and exported assets."""
import bpy
import json
import sys
import struct
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from premium_facade import bounds, intersects

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-premium-v11.blend'))
scene=bpy.context.scene
audit=json.loads((HERE/'premium-facade-audit.json').read_text())
visible=[o for o in scene.objects if o.type=='MESH' and not o.hide_render]
doors=[o for o in visible if o.name.startswith('DOO -')]
results=[]
for record in audit['screens']:
    host=scene.objects[record['window']]
    lo,hi=bounds(host)
    axis=0 if hi.x-lo.x<.3 else 1
    tree=BVHTree.FromPolygons([host.matrix_world@v.co for v in host.data.vertices],
                             [tuple(p.vertices) for p in host.data.polygons])
    counts=[]
    for name in record['parts']:
        obj=scene.objects[name]
        if 'vertical louvre' not in name:continue
        a,b=bounds(obj);c=(a+b)/2
        direction=Vector((0,0,0));direction[axis]=1 if (lo[axis]+hi[axis])/2>c[axis] else -1
        hits=0
        for fraction in (.2,.4,.6,.8):
            origin=c.copy();origin.z=a.z+(b.z-a.z)*fraction
            if tree.ray_cast(origin,direction,1)[0] is not None:hits+=1
        assert hits>=2, f'Louvre not over actual glazing: {name}, {hits}/4 rays'
        assert not any(intersects((a,b),bounds(d),.02) for d in doors)
        counts.append(hits)
    results.append(dict(window=host.name,blades=len(counts),minimum_glass_hits_per_blade=min(counts),samples_per_blade=4))

# Test every new brick skin against the original opening centres on the same plane.
skins=[o for o in visible if o.name.startswith('Premium | Brick skin')]
openings=[o for o in visible if (o.name.startswith('WD -') and o.get('sw_glass'))
          or o.name.startswith(('DOO - 019_Wood - Walnut','DOO - 020_Metal - Aluminium','DOO - 018_Paint - Titanium'))]
opening_checks=0
for skin in skins:
    a,b=bounds(skin);axis=0 if b.x-a.x<b.y-a.y else 1;tangent=1-axis
    tree=BVHTree.FromPolygons([skin.matrix_world@v.co for v in skin.data.vertices],[tuple(p.vertices) for p in skin.data.polygons])
    for opening in openings:
        lo,hi=bounds(opening);c=(lo+hi)/2
        if abs(c[axis]-(a[axis]+b[axis])/2)>.35 or not (a[tangent]<c[tangent]<b[tangent] and a.z<c.z<b.z):continue
        direction=Vector((0,0,0));direction[axis]=1
        for fu in (.25,.5,.75):
            for fz in (.25,.5,.75):
                p=c.copy();p[tangent]=lo[tangent]+fu*(hi[tangent]-lo[tangent]);p.z=lo.z+fz*(hi.z-lo.z)
                p[axis]=a[axis]-.5
                assert tree.ray_cast(p,direction,1)[0] is None,f'Brick obstructs {opening.name}'
                opening_checks+=1

planters=[o for o in visible if o.name.startswith('Premium | Balcony')]
for obj in planters:
    assert not any(intersects(bounds(obj),bounds(d),.10) for d in doors),obj.name
assert len(audit['planters'])==5 and audit['new_ground_planters']==0
assert min(r['clear_depth_to_balcony_door_m'] for r in audit['planters'])>1.2

web=HERE.parents[3]/'frontend/public/landing-assets/coordination/sitewise-coordination.glb'
with web.open('rb') as stream:
    stream.seek(12);length,_=struct.unpack('<II',stream.read(8));data=json.loads(stream.read(length))
names={m['name'] for m in data['materials']}
assert 'Facade | Sand brick 1' in names and 'Facade | Satin bronze' in names
assert {n.get('extras',{}).get('sw_system') for n in data['nodes']} >= {
    'architecture','interiors','landscape','structure','civil','electrical','mechanical','hydraulic'}
assert any(n.get('extras',{}).get('sw_motion')=='car' for n in data['nodes'])
assert any(str(n.get('extras',{}).get('sw_motion','')).startswith('rotor:') for n in data['nodes'])
result=dict(screens=results,opening_clearance_rays=opening_checks,new_planter_parts_checked=len(planters),
            minimum_balcony_clear_depth_m=min(r['clear_depth_to_balcony_door_m'] for r in audit['planters']),
            export_bytes=web.stat().st_size,export_batches=len(data['nodes']))
(HERE/'premium-clearance-check.json').write_text(json.dumps(result,indent=2))
print('PASS',json.dumps(result),flush=True)
