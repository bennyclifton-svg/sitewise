"""Coordinate roof drainage, plant openings and bearing supports in the presentation model."""
import bpy
import json
import re
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from replicate_dwellings import bounds, transforms, route
from rebuild_paired_roofs import roof_surface, height
from export_web import export

TARGET = HERE.parent/'sitewise-coordinated-v17.blend'
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-exposed-v16.blend'))
scene = bpy.context.scene
surface = roof_surface(scene)
placements = transforms(scene)
material = scene.objects['Detail | Front roof bearing beam'].data.materials[0]
civil_mat = scene.objects['V3 | West rainwater gutter'].data.materials[0]
audit = dict(drainage=[], removed_entry_ramps=[], turbines=[], restored_members=[], bearings=[], blade_walls=[])

def mesh(name, points, faces, system, mat=material):
    data=bpy.data.meshes.new(name)
    data.from_pydata(points, [], faces); data.update(); data.materials.append(mat)
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj)
    obj['sw_system']=system; obj['sw_illustrative']=True
    return obj

def member(name,a,b,width=.065,depth=.075):
    a,b=Vector(a),Vector(b)
    t=(b-a).normalized()
    ref=Vector((0,1,0)) if abs(t.y)<.95 else Vector((1,0,0))
    u=t.cross(ref).normalized()*depth/2
    v=t.cross(u).normalized()*width/2
    obj=mesh(name,[p+su*u+sv*v for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]],
             [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'structure')
    obj['sw_member_endpoints']=json.dumps([list(a),list(b)])
    return obj

def reshape(obj,lo,hi):
    oldlo,oldhi=bounds(obj); obj.data=obj.data.copy(); inv=obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        p=obj.matrix_world@vertex.co
        vertex.co=inv@Vector([lo[i]+(p[i]-oldlo[i])/(oldhi[i]-oldlo[i])*(hi[i]-lo[i]) for i in range(3)])

# Keep source stair solids; remove only the authored pedestrian ramp wedges.
for obj in list(scene.objects):
    if obj.name.startswith('V3 | Entry link '):
        audit['removed_entry_ramps'].append(obj.name); bpy.data.objects.remove(obj,do_unlink=True)
    elif 'rainwater gutter' in obj.name or 'rear wall rainwater downpipe' in obj.name:
        bpy.data.objects.remove(obj,do_unlink=True)

# Open U-section gutters follow each roof perimeter; outlets share exact pipe endpoints.
def gutter(name,points):
    vertices=[]
    section=[(-.075,.055),(-.075,-.06),(.075,-.06),(.075,.055)]
    for i,p in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])
        n=Vector((-tangent.y,tangent.x,0)).normalized()
        vertices.extend(Vector(p)+n*x+Vector((0,0,z)) for x,z in section)
    faces=[(i*4+j,i*4+j+1,(i+1)*4+j+1,(i+1)*4+j) for i in range(len(points)-1) for j in range(3)]
    return mesh(name,vertices,faces,'civil',civil_mat)

for number,matrix,record in placements:
    lo,hi=bounds(scene.objects[record['slab']])
    # Existing measured eaves extend beyond the facade on both sides.
    xa,xb=-4.85654,5.25968
    ya,yb=lo.y+.04,hi.y-.04
    corners=[(xa,ya),(xb,ya),(xb,yb),(xa,yb),(xa,ya)]
    points=[]
    for a,b in zip(corners,corners[1:]):
        for j in range(41):
            x=a[0]+(b[0]-a[0])*j/40; y=a[1]+(b[1]-a[1])*j/40
            # Sample just inside the roof edge, avoiding the shingle boundary.
            sx=max(xa+.20,min(xb-.20,x)); sy=max(ya+.13,min(yb-.13,y))
            z=height(surface,sx,sy)-.10
            points.append((x,y,z))
    points.append(points[0])
    gutter(f'Coordinated | TH{number:02} perimeter gutter',points)
    for side,x,idx in [('west',xa,0),('east',xb,41)]:
        start=Vector(points[idx]); wallx=-4.84 if side=='west' else 4.82
        # Use the existing relocated pit/network node so the underground route joins it exactly.
        pitname=f'House {number} rear pit' if side=='east' else f'House {number} side west'
        pipes=[o for o in scene.objects if o.get('sw_endpoint_ids') and pitname in json.loads(o['sw_endpoint_ids']) and o.name.startswith('Storm |')]
        assert pipes,pitname
        pipe=pipes[0]; ids=json.loads(pipe['sw_endpoint_ids'])
        drains=json.loads((HERE/'civil-stormwater.json').read_text())
        endpoint=Vector(drains['nodes'][pitname])
        # Rear pits were relocated with the decks; read their current base geometry.
        if side=='east':
            base=scene.objects[f'Storm | {pitname} base']; bl,bh=bounds(base)
            endpoint.x=(bl.x+bh.x)/2;endpoint.y=(bl.y+bh.y)/2
        y=ya+.18
        route_points=[start,(wallx,y,start.z-.18),(wallx,y,.22+matrix.translation.z),
                      (wallx,y,endpoint.z+.06),(endpoint.x,y,endpoint.z+.03),endpoint]
        obj=route(scene,f'Coordinated | TH{number:02} {side} roof to pit',route_points,'civil',.045,civil_mat,number)
        obj['sw_endpoint_ids']=json.dumps([f'TH{number:02}-{side}-gutter',pitname])
        audit['drainage'].append(dict(dwelling=number,side=side,start=list(start),pit=pitname,end=list(endpoint)))

# Seat each turbine on its actual compound roof, discarding the copied flashings.
for number,_,_ in placements:
    prefix='' if number==1 else f'TH{number:02} | '
    for index in (1,2):
        flashing=scene.objects[prefix+f'V3 | Whirlybird {index} roof flashing']
        lo,hi=bounds(flashing); x,y=(lo.x+hi.x)/2,(lo.y+hi.y)/2
        target=height(surface,x,y)
        parts=[o for o in scene.objects if o.name.startswith(prefix+f'V3 | Whirlybird {index} curved vane ')]
        bottom=min(bounds(o)[0].z for o in parts)
        delta=target+.04-bottom
        for obj in parts:
            obj.location.z+=delta
            if obj.get('sw_motion','').startswith('rotor:'):
                motion=obj['sw_motion'].split(':');motion[3]=str(float(motion[3])+delta)
                obj['sw_motion']=':'.join(motion)
        bpy.data.objects.remove(flashing,do_unlink=True)
        necks=[o for o in scene.objects if o.name.startswith(prefix+'V3 | ') and str(o.get('sw_route_id','')).split(':')[-1]==f'MEC-cavity-neck-{index-1}']
        assert len(necks)==1,(number,index,[o.name for o in necks])
        for obj in necks:bpy.data.objects.remove(obj,do_unlink=True)
        route(scene,prefix+f'Coordinated | Turbine {index} seated neck',[(x,y,target-.18),(x,y,target+.26)],'mechanical',.12,civil_mat,number)
        audit['turbines'].append(dict(dwelling=number,turbine=index,vertical_adjustment=delta,roof_height=target))

# Recover the removed trusses from the preceding editable checkpoint, clipping only the plant quarter.
with bpy.data.libraries.load(str(HERE.parent/'sitewise-satin-white-v15.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if re.match(r'Roof v13 \| TH02 \| Truss [56] ',n)]
cut_left=.20289;cut_right=2.42789
for template in dst.objects:
    a,b=map(Vector,json.loads(template['sw_member_endpoints']))
    for suffix,left,right in [('front',-100,cut_left),('rear',cut_right,100)]:
        if abs(b.x-a.x)<1e-6:
            if not left<=a.x<=right:continue
            p,q=a,b
        else:
            t0,t1=sorted(((left-a.x)/(b.x-a.x),(right-a.x)/(b.x-a.x)))
            t0=max(0,t0);t1=min(1,t1)
            if t1-t0<.001:continue
            p,q=a.lerp(b,t0),a.lerp(b,t1)
        obj=member(template.name+' '+suffix,p,q)
        obj['sw_dwelling']=2;obj['sw_component']='roof'
        audit['restored_members'].append(obj.name)
    bpy.data.objects.remove(template,do_unlink=True)
# Trimmers connect the partial ties to the complete adjacent frames.
ties=[scene.objects[f'Roof v13 | TH02 | Truss {i} bottom tie'] for i in (4,7)]
y0,y1=[sum(bounds(o)[j].y for j in (0,1))/2 for o in ties]
for x in (cut_left,cut_right):
    member(f'Coordinated | Plant bay trimmer {x}',(x,y0,8.46),(x,y1,8.46),.09,.09)

for number,_,_ in placements:
    prefix='' if number==1 else f'TH{number:02} | '
    front=scene.objects[prefix+'Detail | Front roof bearing beam']
    c1=scene.objects[prefix+'V3 | RC column 1 level 3'];c2=scene.objects[prefix+'V3 | RC column 2 level 3']
    clo,chi=bounds(c1);dlo,dhi=bounds(c2);lo,hi=bounds(front)
    oldx=(lo.x+hi.x)/2;newx=(clo.x+chi.x)/2
    lo.x=newx-.10;hi.x=newx+.10;lo.y=min(clo.y,dlo.y);hi.y=max(chi.y,dhi.y)
    reshape(front,lo,hi)
    # Extend the existing truss heels to the supported front bearing line.
    candidates=[o for o in scene.objects if not o.hide_render and o.type=='MESH' and o.get('sw_system')=='structure'
                and ('Truss ' in o.name or 'Roof truss ' in o.name) and (o.get('sw_dwelling')==number or (number==1 and o.name.startswith('V3 | Roof truss ')))]
    for obj in candidates:
        obj.data=obj.data.copy();inv=obj.matrix_world.inverted()
        for v in obj.data.vertices:
            p=obj.matrix_world@v.co
            if p.x<oldx+.08:p.x+=newx-oldx;v.co=inv@p
    rear=scene.objects[prefix+'Detail | Rear roof bearing beam']
    rlo,rhi=bounds(rear);rlo.y=lo.y;rhi.y=hi.y;reshape(rear,rlo,rhi)
    audit['bearings'].append(dict(dwelling=number,front_x=newx))
    # The interior stack at three-quarter depth becomes a transverse concrete blade.
    for level in (1,2,3):
        obj=scene.objects[prefix+f'V3 | RC column 6 level {level}']
        lo,hi=bounds(obj);cx=(lo.x+hi.x)/2;lo.x=cx-.50;hi.x=cx+.50
        reshape(obj,lo,hi);obj.name=prefix+f'Coordinated | RC bedroom blade wall level {level}'
        obj['sw_component']='blade_wall';audit['blade_walls'].append(obj.name)

bpy.context.view_layer.update()
# Check actual plant/member intersections, including the new trimmers.
def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
units=[o for o in scene.objects if o.get('sw_coordination_revision')]
roof=[o for o in scene.objects if not o.hide_render and (o.name.startswith('Roof v13 | TH02 | ') or 'Plant bay trimmer' in o.name)]
clashes=[(u.name,r.name) for u in units for r in roof if tree(u).overlap(tree(r))]
assert not clashes,clashes
assert len(audit['drainage'])==10 and len(audit['removed_entry_ramps'])==5 and len(audit['turbines'])==10
assert len(audit['blade_walls'])==15 and audit['restored_members']
audit['unit_roof_clashes']=clashes
scene['sw_coordination_v17']=json.dumps(audit)
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
(HERE/'coordination-v17-audit.json').write_text(json.dumps(audit,indent=2))
export(scene)
print('COORDINATION_V17_PASS', {k:len(v) for k,v in audit.items()},flush=True)
