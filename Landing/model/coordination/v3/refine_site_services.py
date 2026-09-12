"""Enlarge and highlight shared stormwater, separate the sewer, close paving gaps."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from replicate_dwellings import bounds
from export_web import export
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-connected-mains-v21.blend'))
scene=bpy.context.scene
audit=dict(stormwater=[],sewer=[],infill=[])
water={o.name:o.matrix_world.copy() for o in scene.objects if str(o.get('sw_route_id','')).startswith('WAT-')}
# Storm meshes are authored as consecutive twelve-vertex rings. Scale only the
# cross section, preserving every centreline and connection point.
for obj in scene.objects:
    if obj.hide_render:continue
    if obj.name.startswith('Storm |'):
        obj['sw_reveal_dwelling']=2
        if obj.get('sw_endpoint_ids') and obj.type=='MESH':
            obj.data=obj.data.copy();vertices=obj.data.vertices;assert len(vertices)%12==0
            ratios=[]
            for start in range(0,len(vertices),12):
                ring=list(vertices[start:start+12]);centre=sum((v.co for v in ring),Vector())/12
                before=(ring[0].co-centre).length
                for v in ring:v.co=centre+(v.co-centre)*2
                ratios.append((ring[0].co-centre).length/before)
            assert all(abs(r-2)<1e-4 for r in ratios)
            audit['stormwater'].append(obj.name)
    route=str(obj.get('sw_route_id',''))
    if route.startswith('SAN-main-'):
        obj.location.y+=1.5;obj.location.z-=1.2;obj['sw_reveal_dwelling']=2;audit['sewer'].append(obj.name)
    elif obj.name=='Development | Shared sanitary collector':
        obj.data=obj.data.copy();inv=obj.matrix_world.inverted()
        for spline in obj.data.splines:
            for p in spline.points:
                v=obj.matrix_world@Vector(p.co[:3]);v.z-=1.2
                if v.y < -22:v.y+=1.5*(-22-v.y)/5.5
                p.co=(* (inv@v),p.co.w)
        audit['sewer'].append(obj.name)
    elif 'Shared sewer collector connection' in obj.name:
        obj.data=obj.data.copy();spline=obj.data.splines[0]
        p=spline.points[-1];v=obj.matrix_world@Vector(p.co[:3]);v.z-=1.2
        p.co=(*(obj.matrix_world.inverted()@v),p.co.w);audit['sewer'].append(obj.name)

# Fill only the open intervals; crossing slabs already cover the other spans.
mat=scene.objects['V3 | Shared driveway'].data.materials[0]
crossings=sorted((bounds(o) for o in scene.objects if o.name.startswith('V3 | Garage pedestrian crossing ')),key=lambda b:b[0].y)
spans=[];cursor=-22
for lo,hi in crossings:
    if lo.y>cursor:spans.append((cursor,min(lo.y,12.25)))
    cursor=max(cursor,hi.y)
if cursor<12.25:spans.append((cursor,12.25))
for i,(ya,yb) in enumerate(spans,1):
    if yb<=ya:continue
    verts=[(x,y,z) for z in (.07,.27) for y in (ya,yb) for x in (-7.7,-7.4)]
    data=bpy.data.meshes.new(f'Driveway infill {i}');data.from_pydata(verts,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]);data.materials.append(mat)
    obj=bpy.data.objects.new(f'Site v22 | Driveway paving infill {i}',data);scene.collection.objects.link(obj)
    obj['sw_system']='civil';obj['sw_civil_surface']=True;audit['infill'].append([ya,yb])
bpy.context.view_layer.update()
assert all(scene.objects[n].matrix_world==m for n,m in water.items())
storm=scene.objects['Storm | Single road stormwater outlet to Road main 24']
sewer=scene.objects['V3 | SAN-main-east']
clearance=bounds(storm)[0].z-bounds(sewer)[1].z
assert clearance>.2,clearance
assert abs(bounds(sewer)[0].y+26.15)<.001
assert len(audit['stormwater'])>20 and len(audit['infill'])>0
audit['main_vertical_clearance_m']=clearance
scene['sw_services_v22']=json.dumps(audit)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-services-v22.blend'))
(HERE/'services-v22-audit.json').write_text(json.dumps(audit,indent=2))
export(scene)
print('SERVICES_V22_PASS',audit['main_vertical_clearance_m'],{k:len(v) for k,v in audit.items() if isinstance(v,list)},flush=True)
