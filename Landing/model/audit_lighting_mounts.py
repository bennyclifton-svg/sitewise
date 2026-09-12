"""Read-only geometry checks of the lighting checkpoint; no renders or scene saves."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-lighting-checkpoint.blend'))
manifest = json.loads((OUT / 'lighting-checkpoint.json').read_text())
focus = Vector((-26, -23, 0)) - Vector((-24.757655, -11.917233, 0))
U = Vector((.98703, -.16053, 0)).normalized()
V = Vector((.16053, .98703, 0)).normalized()


def uvz(point):
    delta = point-focus
    return Vector((delta.dot(U), delta.dot(V), point.z))


def world(u,v,z):
    return focus+U*u+V*v+Vector((0,0,z))


def bounds(obj):
    points = [uvz(obj.matrix_world@Vector(p)) for p in obj.bound_box]
    return (Vector(tuple(min(p[i] for p in points) for i in range(3))),
            Vector(tuple(max(p[i] for p in points) for i in range(3))))


source = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or not obj.get('source_name'):
        continue
    low, high = bounds(obj)
    if high.x < -6 or low.x > 5 or high.y < -3 or low.y > 2.2:
        continue
    source.append((obj,low,high,obj.matrix_world.inverted()))


def above(u,v,z,limit=3.1):
    origin=world(u,v,z)
    hits=[]
    for obj,low,high,inverse in source:
        if not low.x-.001 <= u <= high.x+.001 or not low.y-.001 <= v <= high.y+.001:
            continue
        if high.z < z or low.z > z+limit:
            continue
        local_origin=inverse@origin
        direction=(inverse.to_3x3()@Vector((0,0,1))).normalized()
        hit,point,normal,index=obj.ray_cast(local_origin,direction)
        if not hit:
            continue
        point=obj.matrix_world@point
        if point.z > z+limit:
            continue
        normal=(obj.matrix_world.to_3x3()@normal).normalized()
        hits.append(dict(source=obj['source_name'], z=point.z, normal_z=normal.z))
    return sorted(hits,key=lambda h:h['z'])


rows=[]
for fixture in manifest['fixtures']:
    u,v,ceiling=fixture['local_uvz']
    ring=[]
    for dx,dy in [(0,0)]+[(.067*math.cos(i*math.tau/8),.067*math.sin(i*math.tau/8)) for i in range(8)]:
        hits=above(u+dx,v+dy,ceiling-.08)
        first=hits[0] if hits else None
        ring.append(dict(offset=[dx,dy],first=first,
                         at_expected_ceiling=bool(first and abs(first['z']-ceiling)<.012)))
    row=dict(id=fixture['id'], room=fixture['room'], uvz=fixture['local_uvz'],
             mount_coverage=sum(s['at_expected_ceiling'] for s in ring), samples=ring)
    rows.append(row)

curtains=[obj for obj in bpy.context.scene.objects if obj.name.startswith('SW Curtain |')]
curtain_rows=[]
for curtain in curtains:
    low,high=bounds(curtain)
    tree=BVHTree.FromPolygons([curtain.matrix_world@v.co for v in curtain.data.vertices],
                             [p.vertices[:] for p in curtain.data.polygons])
    intersections=[]
    for obj,slo,shi,inverse in source:
        if any(low[i]>shi[i] or high[i]<slo[i] for i in range(3)):
            continue
        target=BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                                   [p.vertices[:] for p in obj.data.polygons])
        overlaps=tree.overlap(target)
        if overlaps:
            intersections.append(dict(source=obj['source_name'], triangle_overlap_pairs=len(overlaps),
                                      min=list(slo),max=list(shi)))
    curtain_rows.append(dict(object=curtain.name,min=list(low),max=list(high),bvh_overlaps=intersections))

table=[(obj,lo,hi) for obj,lo,hi,_ in source if obj['source_name'].startswith('Dining Table Rectangle')]
pendants=[obj for obj in bpy.context.scene.objects if obj.name.startswith('SW Asset Pendant') and not obj.hide_render and obj.type=='MESH']
pendant_bounds=[dict(object=obj.name,min=list(bounds(obj)[0]),max=list(bounds(obj)[1])) for obj in pendants]
offset_trials=[]
for offset in [.05,.08,.10,.12,.15,.20]:
    overlaps_by_object=[]
    for curtain in curtains:
        low,high=bounds(curtain)
        low.x+=offset
        high.x+=offset
        tree=BVHTree.FromPolygons([curtain.matrix_world@v.co+U*offset for v in curtain.data.vertices],
                                 [p.vertices[:] for p in curtain.data.polygons])
        hits=[]
        for obj,slo,shi,_ in source:
            if any(low[i]>shi[i] or high[i]<slo[i] for i in range(3)):
                continue
            target=BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                                       [p.vertices[:] for p in obj.data.polygons])
            pairs=tree.overlap(target)
            if pairs:
                hits.append(dict(source=obj['source_name'],pairs=len(pairs)))
        overlaps_by_object.append(dict(object=curtain.name,overlaps=hits))
    offset_trials.append(dict(positive_u_offset=offset,objects=overlaps_by_object))
result=dict(scene='sitewise-lighting-checkpoint.blend', method='Source-mesh ray casts: center and eight trim-edge samples; world-space curtain/source BVH overlap check.',
            mounts=rows, curtain_checks=curtain_rows, pendant_mesh_bounds=pendant_bounds,
            curtain_inward_offset_trials=offset_trials,
            source_dining_table=[dict(object=obj['source_name'],min=list(lo),max=list(hi)) for obj,lo,hi in table])
(OUT/'lighting-mount-audit.json').write_text(json.dumps(result,indent=2))
print('LIGHTING_MOUNT_QA',json.dumps(dict(mounts=[{k:r[k] for k in ['id','room','mount_coverage']} for r in rows], curtains=curtain_rows)),flush=True)
