"""White enclosed entries, clear garage approaches, articulated roof and end gardens."""
import json, math, shutil, sys
from pathlib import Path
from collections import Counter
import bpy
from mathutils import Vector

N=int(sys.argv[-1]); W=49/N
folder=Path(__file__).resolve().parent/f'option-{N}'
master=folder/f'terrace-{N}.blend'; baseline=folder/f'terrace-{N}-before-frontage-revision.blend'
if not baseline.exists():shutil.copy2(master,baseline)
bpy.ops.wm.open_mainfile(filepath=str(baseline)); scene=bpy.context.scene
dark=bpy.data.materials['Bronze charcoal metal']; glass=bpy.data.materials['Glazing']
white=bpy.data.materials.new('Pure white exterior render');white.diffuse_color=(1,1,1,1)
white.use_nodes=True; bs=white.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(1,1,1,1);bs.inputs['Roughness'].default_value=.72
grass=bpy.data.materials['Garden groundcover']
def mesh(name,v,f,mat=white,system='architecture',owner=0):
    d=bpy.data.meshes.new(name);d.from_pydata(v,[],f);d.update()
    o=bpy.data.objects.new(f'TH{owner:02} | {name}',d);bpy.data.collections[system.title()].objects.link(o)
    d.materials.append(mat);o['sw_system']=system;o['sw_dwelling']=owner;return o
def box(name,a,b,mat=white,system='architecture',owner=0):
    x,y,z=a;X,Y,Z=b
    return mesh(name,[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,system,owner)
def bounds(o):
    p=[o.matrix_world@Vector(v) for v in o.bound_box]
    return [min(v[i] for v in p) for i in range(3)],[max(v[i] for v in p) for i in range(3)]
def remove(o):bpy.data.objects.remove(o,do_unlink=True)
def recolor(o,m):o.data.materials.clear();o.data.materials.append(m)
def pipe(name,pts,r,mat=dark,system='architecture',owner=0):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=1
    s=d.splines.new('POLY');s.points.add(len(pts)-1)
    for p,v in zip(s.points,pts):p.co=(*v,1)
    o=bpy.data.objects.new(f'TH{owner:02} | {name}',d);bpy.data.collections[system.title()].objects.link(o);d.materials.append(mat)
    o['sw_system']=system;o['sw_dwelling']=owner;return o

entries=[]
for i in range(N):
    x=i*W;owner=i+1;sx=x+W-2.25
    left=sx-.05;right=left+.95;sl=left-.42
    for o in list(scene.objects):
        if o.get('sw_dwelling')!=owner:continue
        if any(k in o.name for k in ('Ground frontage','Recessed entry door','Entry pull')):remove(o);continue
        if any(k in o.name for k in ('Garage sectional door','Garage horizontal joint','Bin enclosure','Front vertical fence','Fence gate')):recolor(o,white)
        if 'Wheelie bin' in o.name or 'Bin enclosure' in o.name:
            inv=o.matrix_world.inverted()
            for v in o.data.vertices:
                p=o.matrix_world@v.co
                v.co=inv@Vector((x+W-1.15+(p.y+1.82),-3.35+(p.x-x-.27),p.z))
        if 'Entry walk' in o.name:
            lo,hi=bounds(o)
            for v in o.data.vertices:
                if v.co.x>(lo[0]+hi[0])/2:v.co.x=max(x+5.2,right+.08)
    opens=[(x+.4,x+3.5,.35,2.65),(sl,right,.35,2.75)]
    cuts=sorted({x,x+W,*[a for p in opens for a in p[:2]]})
    for a,b in zip(cuts,cuts[1:]):
        intervals=[p for p in opens if p[0]<=a and p[1]>=b];bottom=.35
        for _,_,s,h in intervals:
            if s>bottom:box('White ground frontage',(a,.55,bottom),(b,.83,s),owner=owner)
            bottom=h
        if bottom<3.45:box('White ground frontage',(a,.55,bottom),(b,.83,3.45),owner=owner)
    box('White single entry door',(left+.035,.71,.38),(right-.035,.78,2.7),owner=owner)
    box('Entry full-height sidelight',(sl+.045,.735,.41),(left-.045,.76,2.69),glass,owner=owner)
    for a in (sl,left-.022,right-.04):box('White entry frame',(a,.68,.35),(a+.04,.82,2.75),owner=owner)
    for z in (.35,2.71):box('White entry frame',(sl,.68,z),(right,.82,z+.04),owner=owner)
    box('Entry handle',(right-.14,.655,1.22),(right-.115,.69,1.65),dark,owner=owner)
    box('White entry threshold',(sl,.5,.34),(right,.86,.38),owner=owner)
    box('White ground-floor fascia',(x,.36,3.00),(x+W,.53,3.45),owner=owner)
    box('White balcony-drain cover',(x+3.65,.29,.35),(x+3.75,.43,3.45),owner=owner)
    box('White downpipe cover',(x+W-.215,-.065,.35),(x+W-.105,.065,3.4),owner=owner)
    entries.append(dict(dwelling=owner,door_x=[left-x,right-x],stair_start_x=sx-x))
for j in range(N+1):
    x=j*W
    a,b=(x-.02,x+.28) if j<N else (48.72,49.02)
    box('White ground pier facing',(a,.205,.35),(b,.565,3.45))
for a,b in ((-.045,-.025),(49.025,49.045)):
    box('White end entry return',(a,.205,.35),(b,1.2,3.45))
for o in scene.objects:
    if 'Shared front garden blade' in o.name:recolor(o,white)

# Keep the steep front slope; articulate the rear with a shallower pitched roof.
ridge_y=7.8; ridge_z=10.3; eave_y=14.6; eave_z=8.95
def rz(y):
    if y<=2:return 6.6+3.05*y/2
    if y<=ridge_y:return 9.65+(ridge_z-9.65)*(y-2)/(ridge_y-2)
    return ridge_z+(eave_z-ridge_z)*(y-ridge_y)/(eave_y-ridge_y)
join_y=ridge_y+(9.38-ridge_z)*(eave_y-ridge_y)/(eave_z-ridge_z)
for i in range(N):
    x=i*W;owner=i+1;a=x+.05;b=x+W-.05;dl=x+.65;dr=x+6.05
    for o in list(scene.objects):
        if o.get('sw_dwelling')!=owner:continue
        if any(k in o.name for k in ('Roof sides and top','Rear roof left','Rear roof right','Rear dormer upper flashing','Rear standing seam')):remove(o)
    for ya,yb in ((2,ridge_y),(ridge_y,join_y)):
        mesh('Shallow pitched main roof',[(a,ya,rz(ya)),(b,ya,rz(ya)),(b,yb,rz(yb)),(a,yb,rz(yb))],[(0,1,2,3)],dark,owner=owner)
    for aa,bb in ((a,dl),(dr,b)):
        mesh('Shallow rear roof beside dormer',[(aa,join_y,9.38),(bb,join_y,9.38),(bb,eave_y,eave_z),(aa,eave_y,eave_z)],[(0,1,2,3)],dark,owner=owner)
        box('Rear roof metal infill',(aa,14.39,6.6),(bb,14.46,rz(14.4)),dark,owner=owner)
    for j in range(math.ceil((b-a)/.32)):
        xx=a+j*.32;end=join_y if dl<xx<dr else eave_y
        pipe('Shallow roof standing seam',[(xx,2,9.67),(xx,ridge_y,ridge_z+.02),(xx,end,rz(end)+.02)],.012,owner=owner)
    pipe('Main roof ridge',[(a,ridge_y,ridge_z+.015),(b,ridge_y,ridge_z+.015)],.045,owner=owner)

windows=[(8.6,9.4,1.0,2.1),(5.25,6.0,4.1,5.4),(10.15,10.95,7.35,8.8)]
if '--detail-review' in sys.argv:
    windows=[(8.5,9.5,.9,2.35),(5.125,6.125,3.85,5.65),(10.05,11.05,7.05,9.05)]
def side_wall(name,xa,xb,ya,yb,z0,top,openings,mat,system,owner):
    cuts=sorted({ya,yb,*[v for o in openings for v in o[:2] if ya<v<yb],*[v for v in (2,ridge_y) if ya<v<yb]})
    for a,b in zip(cuts,cuts[1:]):
        bottom=z0
        for _,_,s,h in sorted([o for o in openings if o[0]<=a and o[1]>=b],key=lambda o:o[2]):
            if s>bottom:box(name,(xa,a,bottom),(xb,b,s),mat,system,owner)
            bottom=max(bottom,h)
        ta,tb=top(a),top(b)
        if min(ta,tb)>bottom:
            mesh(name,[(xa,a,bottom),(xb,a,bottom),(xb,b,bottom),(xa,b,bottom),(xa,a,ta),(xb,a,ta),(xb,b,tb),(xa,b,tb)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,system,owner)
for owner,edge,sign in ((1,0,-1),(N,49,1)):
    brick=next(o.data.materials[0] for o in scene.objects if o.get('sw_dwelling')==owner and 'Brick street wall' in o.name)
    for o in list(scene.objects):
        if o.get('sw_dwelling')!=owner or not any(k in o.name for k in ('Masonry bearing wall','Internal wall plasterboard lining')):continue
        lo,hi=bounds(o)
        if abs((lo[0]+hi[0])/2-edge)>.3:continue
        mat=o.data.materials[0];system=o['sw_system'];remove(o)
        name='Masonry bearing wall end openings' if system=='structure' else 'Internal wall plasterboard lining end openings'
        side_wall(name,lo[0],hi[0],lo[1],hi[1],lo[2],lambda y:hi[2],windows[:2],mat,system,owner)
    xa,xb=(edge,edge+.24) if sign<0 else (edge-.24,edge)
    side_wall('Brick end gable',xa,xb,0,14.4,6.55,rz,[windows[2]],brick,'architecture',owner)
    for ya,yb,s,h in windows:
        plane=edge+sign*.025
        box('End window glass',(plane-.012,ya+.045,s+.045),(plane+.012,yb-.045,h-.045),glass,owner=owner)
        for yy in (ya,yb-.045):box('End window jamb',(plane-.065,yy,s),(plane+.065,yy+.045,h),dark,owner=owner)
        for zz in (s,h-.045):box('End window sill and head',(plane-.065,ya,zz),(plane+.065,yb,zz+.045),dark,owner=owner)
        xx=sorted((edge+sign*.02,edge+sign*.19))
        box('End window hood',(xx[0],ya-.025,h),(xx[1],yb+.025,h+.04),dark,owner=owner)
        pipe('End window curtain track',[(edge-sign*.2,ya,h-.04),(edge-sign*.2,yb,h-.04)],.012,owner=owner,system='interiors')
        for yy in (ya+.05,yb-.2):box('End window curtain',(edge-sign*.18-.015,yy,s+.05),(edge-sign*.18+.015,yy+.15,h-.07),white,'interiors',owner)
    pipe('End gable verge',[(edge,0,6.62),(edge,2,9.67),(edge,ridge_y,ridge_z+.02),(edge,eave_y,eave_z+.02)],.045,owner=owner)

for o in list(scene.objects):
    if 'End boundary wall' in o.name:remove(o)
    elif 'Site ground' in o.name:
        for v in o.data.vertices:
            if v.co.x<0:v.co.x=-2.3
            elif v.co.x>49:v.co.x=51.3
def fence(axis,start,end,fixed):
    def b(name,a,c,z0,z1,thick):
        lo,hi=((a,fixed-thick/2,z0),(c,fixed+thick/2,z1)) if axis=='x' else ((fixed-thick/2,a,z0),(fixed+thick/2,c,z1))
        return box(name,lo,hi,white,'landscape')
    b('Rendered block dwarf wall',start,end,.02,.5,.19);b('Dwarf wall cap',start,end,.5,.54,.23)
    for j in range(math.ceil((end-start)/.105)):
        a=start+j*.105;b('Side return white picket',a,min(a+.04,end),.54,1.65,.04)
    for z in (.7,1.45):b('Side return fence rail',start,end,z,z+.045,.055)
    for j in range(math.ceil((end-start)/1.8)+1):
        a=min(start+j*1.8,end);b('Side return fence post',a-.035,a+.035,.52,1.72,.07)
for edge,outer in ((0,-2.2),(49,51.2)):
    a,b=sorted((edge,outer));fence('x',a,b,-3.81);fence('y',-3.81,20.4,outer)
    box('Side yard lawn',(a+.12,.1,.015),(b-.12,20.3,.045),grass,'landscape')
    fence('x',a,b,20.4)

bpy.context.view_layer.update()
for i in range(N):
    bins=[o for o in scene.objects if o.get('sw_dwelling')==i+1 and 'Wheelie bin' in o.name]
    assert len(bins)==2
    assert all(bounds(o)[0][0]>i*W+3.6 for o in bins),'Bin obstructs garage approach'
    assert all(bounds(o)[0][0]>i*W+W-1.27 for o in bins),'Bin obstructs entry approach'
assert len([o for o in scene.objects if 'End window glass' in o.name])==6
assert len([o for o in scene.objects if 'White single entry door' in o.name])==N
audit=dict(status='pass',entries=entries,end_windows=6,side_yard_m=2.2,roof_ridge_m=10.3,
    roof_profile_yz=[[0,6.6],[2,9.65],[7.8,10.3],[14.6,8.95]],bins_clear_of_garages=True,
    scope='Architecture and landscape; end masonry/lining openings and bin/entry-walk positions updated. Roof structure and drainage require next coordination review.')
(folder/'frontage-revision-audit.json').write_text(json.dumps(audit,indent=2))
manifest=json.loads((folder/'manifest.json').read_text());manifest['frontage_revision']=audit
manifest['count_by_system']=dict(Counter(o.get('sw_system') for o in scene.objects if o.get('sw_system')))
for h in manifest['homes']:h['roof_peak_m']=10.3
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
scene['sw_frontage_revision']='White enclosed entries; relocated bins; shallow rear roof; end windows; side gardens'
if '--defer-save' not in sys.argv:
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    bpy.ops.export_scene.gltf(filepath=str(folder/f'terrace-{N}.glb'),export_format='GLB',export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
print('FRONTAGE_REVISION_PASS',N,flush=True)
