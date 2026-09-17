"""Apply the first architectural review without changing structure or services.

Run after the four-bedroom replan. A pre-review master is retained for a
repeatable architectural delta and for geometry-preservation checks.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys
from collections import Counter

import bpy
from mathutils import Vector

N=int(sys.argv[-1]);W=49/N
HERE=Path(__file__).resolve().parent;folder=HERE/f'option-{N}'
master=folder/f'terrace-{N}.blend'
baseline=folder/f'terrace-{N}-before-architecture-feedback.blend'
if not baseline.exists():shutil.copy2(master,baseline)
bpy.ops.wm.open_mainfile(filepath=str(baseline))
scene=bpy.context.scene
white=bpy.data.materials['Warm lime render']
metal=bpy.data.materials['Bronze charcoal metal']
pale_metal=bpy.data.materials['Plasterboard ivory']
timber=bpy.data.materials['Oak joinery and framing']
glass=bpy.data.materials['Glazing']
protected={'structure','electrical','mechanical','hydraulic','civil'}


def fingerprint():
    result={}
    for obj in scene.objects:
        if obj.get('sw_system') not in protected:continue
        h=hashlib.sha256()
        for row in obj.matrix_world:h.update(struct.pack('<4d',*row))
        if obj.type=='MESH':
            for v in obj.data.vertices:h.update(struct.pack('<3d',*v.co))
        elif obj.type=='CURVE':
            for spline in obj.data.splines:
                for p in spline.points:h.update(struct.pack('<4d',*p.co))
        result[obj.name]=h.hexdigest()
    return result


before=fingerprint()


def mesh(name,verts,faces,system,material,owner=0):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(f'TH{owner:02} | {name}',data)
    bpy.data.collections[system.title()].objects.link(obj);data.materials.append(material)
    obj['sw_system']=system;obj['sw_dwelling']=owner
    obj['sw_architecture_feedback']=True
    return obj


def box(name,lo,hi,system,material,owner=0):
    x,y,z=lo;a,b,c=hi
    return mesh(name,[(x,y,z),(a,y,z),(a,b,z),(x,b,z),(x,y,c),(a,y,c),(a,b,c),(x,b,c)],
        [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],system,material,owner)


def bounds(obj):
    pts=[obj.matrix_world@Vector(v) for v in obj.bound_box]
    return ([min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)])


# Remove the old entry blades and the fins from the adjacent normal windows.
for obj in list(scene.objects):
    if 'Expressed entrance blade' in obj.name or 'Integrated bronze privacy fin' in obj.name:
        bpy.data.objects.remove(obj,do_unlink=True)

for j in range(1,N):
    x=j*W
    mesh('Shared front garden blade',[(x-.08,-3.81,.12),(x+.08,-3.81,.12),(x+.08,.55,.12),(x-.08,.55,.12),
         (x-.08,-3.81,1.25),(x+.08,-3.81,1.25),(x+.08,.55,3.45),(x-.08,.55,3.45)],
         [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'architecture',white)

for i in range(N):
    owner=i+1;x=i*W
    face=next(o for o in scene.objects if o.get('sw_dwelling')==owner and 'Brick street wall' in o.name)
    brick=face.data.materials[0]
    # 200 mm to each jamb, 150 mm to head and sill. The room and sliding door
    # remain behind the deeper reveal rather than being stretched with the facade.
    for a,b in ((x+.55,x+.75),(x+3.65,x+3.85)):
        box('Loggia narrower brick jamb',(a,0,3.65),(b,1.9,5.95),'architecture',brick,owner)
    for a,b in ((3.65,3.8),(5.8,5.95)):
        box('Loggia reduced head or sill',(x+.75,0,a),(x+3.65,1.9,b),'architecture',brick,owner)
    for obj in scene.objects:
        if obj.get('sw_dwelling')!=owner or obj.type!='CURVE':continue
        if not any(k in obj.name for k in ('Loggia vertical baluster','Loggia handrail','Loggia bottom rail')):continue
        for spl in obj.data.splines:
            for p in spl.points:
                p.co.x=x+.75+(p.co.x-x-.55)*2.9/3.3
                p.co.z=3.8+(p.co.z-3.65)*.85

    # Double the overall rear dormer width, anchored at its existing left jamb.
    rear_names=('Rear dormer cheek','Rear dormer cap','Rear roof dormer','Rear dormer ceiling')
    for obj in scene.objects:
        if obj.get('sw_dwelling')!=owner or not any(k in obj.name for k in rear_names):continue
        if obj.type=='MESH':
            lo,hi=bounds(obj)
            if 'cheek' in obj.name:
                if lo[0]-x>2:
                    for v in obj.data.vertices:v.co.x+=2.7
            elif 'cap' in obj.name or 'ceiling' in obj.name:
                for v in obj.data.vertices:
                    if v.co.x>(lo[0]+hi[0])/2:v.co.x+=2.7
            elif 'pleated linen' in obj.name:
                if lo[0]-x>2:
                    for v in obj.data.vertices:v.co.x+=2.7
            elif 'stile' in obj.name:
                delta=2.7 if lo[0]-x>2.5 else (1.35 if lo[0]-x>1.5 else 0)
                for v in obj.data.vertices:v.co.x+=delta
            else:
                # Rails and glass retain their section dimensions at the jambs.
                for v in obj.data.vertices:
                    if v.co.x>(lo[0]+hi[0])/2:v.co.x+=2.7
        elif obj.type=='CURVE':
            for spl in obj.data.splines:
                for p in spl.points:
                    if p.co.x>x+2:p.co.x+=2.7

    # Widen the actual roof aperture as well as the dormer box. Trim the seams
    # so they do not run through the expanded window or cheek geometry.
    for obj in scene.objects:
        if obj.get('sw_dwelling')!=owner or obj.type!='MESH':continue
        if 'Rear roof right' in obj.name:
            for v in obj.data.vertices:
                if abs(v.co.x-(x+3.35))<.001:v.co.x=x+6.05
        elif 'Rear dormer upper flashing' in obj.name:
            for v in obj.data.vertices:
                if abs(v.co.x-(x+3.35))<.001:v.co.x=x+6.05
    for obj in list(scene.objects):
        if obj.get('sw_dwelling')!=owner or 'Rear standing seam' not in obj.name:continue
        lo,hi=bounds(obj)
        if x+.62<(lo[0]+hi[0])/2<x+6.08:bpy.data.objects.remove(obj,do_unlink=True)

# Replace the paired internal balcony wing walls with one uninterrupted wall.
for obj in list(scene.objects):
    if 'Rear balcony privacy wing' not in obj.name:continue
    lo,hi=bounds(obj);mid=(lo[0]+hi[0])/2
    if .5<mid<48.5:bpy.data.objects.remove(obj,do_unlink=True)
for j in range(1,N):
    x=j*W
    box('Shared full-height rear privacy wall',(x-.15,14.35,3.45),(x+.15,17.12,9.38),'architecture',white)

# Flat, regular perforations: 20 mm pitch / 14 mm clear square holes. One mesh
# is shared by every screen in an option to keep the GLB efficient.
for obj in list(scene.objects):
    if 'Folded perforated rear metal screen' in obj.name:bpy.data.objects.remove(obj,do_unlink=True)
verts=[];faces=[]
width=W-.54;height=1.05;pitch=.02;rib=.006
def quad(x0,x1,z0,z1):
    k=len(verts);verts.extend([(x0,0,z0),(x1,0,z0),(x1,0,z1),(x0,0,z1)])
    faces.append((k,k+1,k+2,k+3))
for c in range(math.ceil(width/pitch)):
    a=c*pitch;b=min(a+rib,width)
    quad(a,b,0,height)
    if a+rib>=width:continue
    for r in range(math.ceil(height/pitch)):
        z=r*pitch
        quad(a+rib,min(a+pitch,width),z,min(z+rib,height))
panel=mesh('Flat fine-perforated rear balustrade',verts,faces,'architecture',pale_metal,1)
for i in range(N):
    for level,z in enumerate((3.6,6.7)):
        if i==0 and level==0:obj=panel
        else:
            obj=panel.copy();bpy.data.collections['Architecture'].objects.link(obj)
        obj.name=f'TH{i+1:02} | Flat fine-perforated rear balustrade L{level+1}'
        obj['sw_dwelling']=i+1;obj.location=(i*W+.27,17.09,z)

# Timber paling fences replace the broad flat fence sheets at the rear and along
# garden boundaries. The pale terrace privacy walls retain their separate role.
fence_runs=[]
for obj in list(scene.objects):
    if not any(k in obj.name for k in ('Rear boundary fence','Garden dividing fence')):continue
    lo,hi=bounds(obj);owner=obj.get('sw_dwelling',0)
    if 'Rear boundary fence' in obj.name:
        fence_runs.append(('x',lo[0],hi[0],(lo[1]+hi[1])/2,0,1.8,0))
    else:
        centre=(lo[0]+hi[0])/2
        # Adjacent old paired fences become one fence on each dwelling seam.
        boundary=round(centre/W)*W
        fence_runs.append(('y',16.8,hi[1],boundary,.05,1.75,owner))
    bpy.data.objects.remove(obj,do_unlink=True)
seen=set()
for axis,start,end,fixed,bottom,height,owner in fence_runs:
    key=(axis,round(fixed,3),round(start,3),round(end,3))
    if key in seen:continue
    seen.add(key)
    vv=[];ff=[]
    def timber_box(a,b):
        xx,yy,zz=a;aa,bb,cc=b;k=len(vv)
        vv.extend([(xx,yy,zz),(aa,yy,zz),(aa,bb,zz),(xx,bb,zz),(xx,yy,cc),(aa,yy,cc),(aa,bb,cc),(xx,bb,cc)])
        ff.extend(tuple(k+j for j in f) for f in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)))
    for j in range(math.ceil((end-start)/.1)):
        a=start+j*.1;b=min(a+.09,end)
        if axis=='x':timber_box((a,fixed-.012,bottom),(b,fixed+.012,bottom+height))
        else:timber_box((fixed-.012,a,bottom),(fixed+.012,b,bottom+height))
    for j in range(math.ceil((end-start)/1.8)+1):
        a=min(start+j*1.8,end)
        if axis=='x':timber_box((a-.045,fixed+.015,bottom),(a+.045,fixed+.105,bottom+height+.03))
        else:timber_box((fixed+.015,a-.045,bottom),(fixed+.105,a+.045,bottom+height+.03))
    for z in (bottom+.3,bottom+height-.3):
        if axis=='x':timber_box((start,fixed+.013,z),(end,fixed+.048,z+.08))
        else:timber_box((fixed+.013,start,z),(fixed+.048,end,z+.08))
    mesh('Rear timber paling fence',vv,ff,'landscape',timber,owner)

bpy.context.view_layer.update()
assert before==fingerprint(),'Architecture review changed protected discipline geometry'
assert len([o for o in scene.objects if 'Shared front garden blade' in o.name])==N-1
assert len([o for o in scene.objects if 'Shared full-height rear privacy wall' in o.name])==N-1
assert len([o for o in scene.objects if 'Flat fine-perforated rear balustrade L' in o.name])==N*2
assert not any('Integrated bronze privacy fin' in o.name or 'Expressed entrance blade' in o.name for o in scene.objects)
for owner in range(1,N+1):
    cap=next(o for o in scene.objects if o.get('sw_dwelling')==owner and 'Rear dormer cap' in o.name)
    lo,hi=bounds(cap);assert abs((hi[0]-lo[0])-5.4)<.001

audit=dict(status='pass',front_blades=N-1,front_blade_heights_m=[1.25,3.45],
    loggia_opening_m=[2.9,2.0],rear_dormer_width_m=5.4,rear_privacy_walls=N-1,
    rear_privacy_wall_vertical_extent_m=[3.45,9.38],perforation_pitch_m=.02,
    perforation_clear_hole_m=.014,protected_objects_verified=len(before),
    protected_systems=sorted(protected),upper_balcony_size_changed=False)
(folder/'architecture-feedback-audit.json').write_text(json.dumps(audit,indent=2))
manifest=json.loads((folder/'manifest.json').read_text())
manifest['count_by_system']=dict(Counter(o.get('sw_system') for o in scene.objects if o.get('sw_system')))
manifest['architecture_feedback']=audit
for home in manifest['homes']:home['loggia_clear_m']=[2.9,1.6]
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
scene['sw_architecture_feedback']='Shared blades; reduced loggias; plain windows; wider rear dormers; flat perforations; paling fences'
bpy.ops.wm.save_as_mainfile(filepath=str(master))
bpy.ops.export_scene.gltf(filepath=str(folder/f'terrace-{N}.glb'),export_format='GLB',
    export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
print('ARCHITECTURE_FEEDBACK_PASS',N,audit,flush=True)
