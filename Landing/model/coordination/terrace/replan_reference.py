"""Replan the terrace around the supplied four-bedroom reference floor plan.

Ground living/kitchen/garden; two first-floor bedrooms plus laundry/bath;
two roof bedrooms with dressing space/bath. Geometry remains a concept.
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path
import shutil

import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
N=int(sys.argv[-1]);W=49/N
folder=HERE/f'option-{N}'
source=folder/f'terrace-{N}.blend'
archive=folder/f'terrace-{N}-initial.blend'
if not archive.exists():shutil.copy2(source,archive)
bpy.ops.wm.open_mainfile(filepath=str(archive))
scene=bpy.context.scene
materials=bpy.data.materials
white=materials['Plasterboard ivory'];oak=materials['Oak joinery and framing']
dark=materials['Bronze charcoal metal'];stone=materials['Limestone paving']
fabric=materials['Linen curtains'];concrete=materials['Concrete']
steel=materials['Structural steel'];duct=materials['Galvanised ductwork']
cold=materials['Cold water blue'];hot=materials['Hot water copper']
waste=materials['Sanitary drainage'];power=materials['Electrical conduit amber']
glass=materials['Glazing'];owner=0;routes=[]


def stretch(y):
    if y<=6.6:return y
    if y<12:return 6.6+(y-6.6)*7.8/5.4
    return y+2.4


# Preserve stairs/garage geometry; extend only the rear living and garden side.
for obj in list(scene.objects):
    if obj.type not in {'MESH','CURVE'}:continue
    system=obj.get('sw_system')
    name=obj.name
    if obj.get('sw_dwelling',0)>0:
        keep_interior=any(k in name for k in ('curtain','pleated linen','Stair screen','stair screen',
            'Painted stair','plasterboard lining','Oak floor finish','Stair handrail','Electrical riser plasterboard'))
        if system=='interiors' and not keep_interior:
            bpy.data.objects.remove(obj,do_unlink=True);continue
        if system in {'mechanical','electrical'}:
            bpy.data.objects.remove(obj,do_unlink=True);continue
        if system=='hydraulic' and not any(k in name for k in ('Eaves gutter','Downpipe','Balcony drain')):
            bpy.data.objects.remove(obj,do_unlink=True);continue
        if system=='structure' and any(k in name for k in ('timber stud','timber plate')):
            bpy.data.objects.remove(obj,do_unlink=True);continue
    inv=obj.matrix_world.inverted()
    obj.data=obj.data.copy()
    if obj.type=='MESH':
        for v in obj.data.vertices:
            p=obj.matrix_world@v.co;p.y=stretch(p.y);v.co=inv@p
    else:
        for spl in obj.data.splines:
            for p in spl.points:
                q=obj.matrix_world@Vector(p.co[:3]);q.y=stretch(q.y);p.co=(*list(inv@q),1)


def mesh(name,verts,faces,system,mat):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(f'TH{owner:02} | {name}',data)
    bpy.data.collections[system.title()].objects.link(obj);data.materials.append(mat)
    obj['sw_system']=system;obj['sw_dwelling']=owner;obj['sw_reference_plan']=True
    obj['sw_status']='Reference-plan concept; sizing and detailed coordination provisional'
    return obj


def box(name,lo,hi,system='interiors',mat=white):
    x,y,z=lo;a,b,c=hi
    assert a>x and b>y and c>z,name
    return mesh(name,[(x,y,z),(a,y,z),(a,b,z),(x,b,z),(x,y,c),(a,y,c),(a,b,c),(x,b,c)],
        [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],system,mat)


def pipe(name,points,radius,system,mat):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=radius;data.bevel_resolution=1
    spl=data.splines.new('POLY');spl.points.add(len(points)-1)
    for p,co in zip(spl.points,points):p.co=(*co,1)
    obj=bpy.data.objects.new(f'TH{owner:02} | {name}',data);bpy.data.collections[system.title()].objects.link(obj)
    data.materials.append(mat);obj['sw_system']=system;obj['sw_dwelling']=owner
    routes.append(dict(name=obj.name,system=system,points=points,radius=radius))
    return obj


def partition(name,a,b,y,z,door=None):
    segments=[(a,b)] if door is None else [(a,door),(door+.85,b)]
    for left,right in segments:
        if right-left<.01:continue
        box(name+' drywall',(left,y,z),(right,y+.12,z+2.62))
        for j in range(math.ceil((right-left)/.45)):
            xx=left+j*.45
            box(name+' timber stud',(xx,y+.04,z),(min(xx+.038,right),y+.08,z+2.62),'structure',oak)
    if door is not None:
        box(name+' door head',(door,y,z+2.1),(door+.85,y+.12,z+2.62))
        box(name+' door open',(door,y,z+.02),(door+.035,y+.83,z+2.08),mat=oak)
    box(name+' top plate',(a,y+.04,z+2.58),(b,y+.08,z+2.62),'structure',oak)


def bed(x,y,z,label):
    box(label+' bed',(x,y,z+.12),(x+1.7,y+2,z+.52),mat=fabric)
    box(label+' headboard',(x-.02,y+1.94,z+.03),(x+1.72,y+2.04,z+1.08),mat=oak)
    for dx in (.1,.9):box(label+' pillow',(x+dx,y+1.4,z+.52),(x+dx+.64,y+1.84,z+.63),mat=white)
    for xx in (x-.48,x+1.85):box(label+' bedside',(xx,y+1.5,z),(xx+.38,y+1.93,z+.46),mat=oak)


def wet_room(x,y,z,shower=True):
    box('Bathroom tile',(x,y,z+.01),(x+1.8,y+(2.1 if shower else 1.3),z+.035),mat=stone)
    box('Vanity cabinet',(x+.04,y+.12,z+.1),(x+.54,y+.95,z+.83),mat=oak)
    box('Vanity basin',(x+.02,y+.1,z+.83),(x+.56,y+.68,z+.9),'hydraulic',white)
    box('Vanity mirror',(x+.02,y+.14,z+1.1),(x+.04,y+.91,z+2.02),mat=glass)
    box('WC pan',(x+1.08,y+.12,z+.05),(x+1.5,y+.85,z+.43),'hydraulic',white)
    box('WC cistern',(x+1.07,y+.1,z+.43),(x+1.51,y+.32,z+.8),'hydraulic',white)
    if shower:
        box('Shower tray',(x+.86,y+1.1,z+.02),(x+1.77,y+2,z+.07),'hydraulic',white)
        box('Shower glass',(x+.84,y+1.08,z+.08),(x+.86,y+2.04,z+2.05),mat=glass)
        pipe('Shower mixer and head',[(x+1.5,y+2.02,z+1),(x+1.5,y+2.02,z+2.1),(x+1.5,y+1.78,z+2.1)],.018,'hydraulic',dark)


for i in range(N):
    owner=i+1;x=i*W;rx=x+W-2.25
    # Keep the ground living room open to the rear garden, as in the reference.
    box('Garage side separation',(x+3.63,.8,.35),(x+3.78,6.5,3.25))
    box('Entry timber floor',(x+3.82,1.25,.352),(x+W-.28,2.95,.37),mat=oak)
    box('Passage timber floor',(x+3.82,2.95,.352),(rx-.05,6.5,.37),mat=oak)
    partition('Garage rear separation',x+.25,x+3.78,6.5,.35,x+2.6)
    wet_room(rx,6.9,.35,False)
    partition('Ground powder entry',rx-.1,x+W-.25,6.73,.35,rx+.6)
    partition('Ground powder rear',rx-.1,x+W-.25,8.28,.35)
    box('Ground powder side',(rx-.14,6.85,.35),(rx-.02,8.28,2.97))
    for z in (3.45,6.55):
        wet_room(rx,6.95,z)
        partition('Upper bathroom entry',rx-.1,x+W-.25,6.78,z,rx+.6)
        partition('Upper bathroom rear',rx-.1,x+W-.25,9.12,z)
        box('Upper bathroom side',(rx-.14,6.9,z),(rx-.02,9.12,z+2.62))
    # First floor: Bed 3 and Bed 4, with rear laundry next to Bed 4.
    partition('Bed 3 entry',x+.27,rx-.18,6.35,3.45,x+3.25)
    partition('Bed 4 entry',x+.27,rx-.18,9.85,3.45,x+3.25)
    partition('Laundry entry',rx-.1,x+W-.25,11.15,3.45,rx)
    box('Laundry side',(rx-.14,11.27,3.45),(rx-.02,14.15,6.07))
    box('Laundry bench',(rx+.02,13.45,3.45),(x+W-.3,14.12,4.32),mat=oak)
    box('Laundry sink',(rx+.1,13.6,4.32),(rx+.64,14.02,4.35),'hydraulic',dark)
    box('Washing machine',(rx+.76,13.47,3.5),(rx+1.36,14.06,4.27),'electrical',white)
    # Roof: Bed 2 at front and master at rear with dressing zone.
    partition('Bed 2 entry',x+.27,rx-.18,5.9,6.55,x+3.25)
    partition('Master suite entry',x+.27,rx-.18,9.05,6.55,x+3.25)
    for z in (3.45,6.55):
        box('Front bedroom privacy wall',(rx-.22,1.95,z),(rx-.1,6.35,z+2.62))
        if z<4:
            box('Rear bedroom privacy wall',(rx-.22,9.85,z),(rx-.1,14.15,z+2.62))
        else:
            box('Rear bedroom privacy wall',(rx-.22,9.05,z),(rx-.1,11.4,z+2.62))
            end_height=6.6+3.05*(14.4-14.15)/(2*7.8/5.4)-.1
            mesh('Master sloping privacy lining',[(rx-.22,11.4,z),(rx-.1,11.4,z),(rx-.1,14.15,z),(rx-.22,14.15,z),
                 (rx-.22,11.4,z+2.62),(rx-.1,11.4,z+2.62),(rx-.1,14.15,end_height),(rx-.22,14.15,end_height)],
                 [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'interiors',white)
    for z,front_y,rear_y in ((3.45,3.25,11.4),(6.55,2.7,11.55)):
        bed(x+.9,front_y,z,'Front bedroom')
        bed(x+.9,rear_y,z,'Rear bedroom')
        box('Front bedroom robe',(x+.28,5.35,z),(x+2.6,5.88,z+2.35),mat=oak)
    box('Bed 4 robe',(x+.3,10,3.45),(x+2.6,10.56,5.8),mat=oak)
    for xx in (x+.3,x+2.55):
        box('Master walk-in robe',(xx,9.2,6.55),(xx+.55,10.85,8.85),mat=oak)
    # Ground kitchen: side bench and island, then dining and garden living.
    for j in range(5):
        yy=8.65+j*.6
        box('Kitchen base cabinet',(x+.3,yy,.35),(x+.95,yy+.58,1.21),mat=oak)
    box('Kitchen stone bench',(x+.28,8.62,1.21),(x+.98,11.67,1.25),mat=stone)
    box('Kitchen island',(x+2.1,9.25,.35),(x+3,11.35,1.22),mat=oak)
    box('Island stone top',(x+2.06,9.21,1.22),(x+3.18,11.39,1.26),mat=stone)
    box('Kitchen sink',(x+2.3,10.2,1.262),(x+2.8,10.8,1.28),'hydraulic',dark)
    pipe('Kitchen mixer',[(x+2.85,10.5,1.26),(x+2.85,10.5,1.57),(x+2.62,10.5,1.57)],.015,'hydraulic',dark)
    box('Oven',(x+.33,9.35,.47),(x+.95,9.94,1.05),'electrical',dark)
    box('Induction cooktop',(x+.34,9.3,1.26),(x+.91,10,1.28),'electrical',dark)
    box('Rangehood',(x+.3,9.3,2),(x+.9,10,2.18),'mechanical',dark)
    box('Refrigerator',(x+.3,7.85,.35),(x+1.02,8.55,2.48),'electrical',white)
    box('Dining table',(x+4,9.25,1.08),(x+5.8,10.2,1.15),mat=oak)
    for xx in (x+4.1,x+5.3):
        for yy in (8.65,10.38):
            box('Dining seat',(xx,yy,.75),(xx+.43,yy+.43,.83),mat=fabric)
            box('Dining chair back',(xx,yy+.4,.78),(xx+.43,yy+.45,1.32),mat=oak)
    box('Living sofa',(x+1.5,12.65,.48),(x+4.4,13.5,.84),mat=fabric)
    box('Living sofa back',(x+1.5,13.32,.8),(x+4.4,13.5,1.25),mat=fabric)
    box('Living coffee table',(x+2,11.65,.62),(x+3.4,12.2,.72),mat=oak)
    # Ceiling and plant zones follow the rooms, preserving the stair opening.
    for z in (.35,3.45,6.55):
        for ya,yb in ((2,6.4),(8.4,11.4 if z>6 else 14.15)):
            box('Plasterboard ceiling',(x+.27,ya,z+2.6),(rx-.15,yb,z+2.625))
        if z>6:box('Rear dormer ceiling',(x+.76,11.4,9.18),(x+3.24,14.12,9.205))
        box('Central plant bulkhead',(x+2.7,6.55,z+2.47),(x+4.1,7.85,z+2.5))
        box('Bulkhead closing fascia',(x+2.7,6.5,z+2.47),(x+4.1,6.55,z+2.97))
        box('Plant access hatch',(x+2.85,6.85,z+2.46),(x+3.5,7.45,z+2.47),mat=stone)
    # New rear balconies; screen panels move to the balcony edge and expand to width.
    for obj in list(scene.objects):
        if obj.get('sw_dwelling')!=owner or not any(k in obj.name for k in ('Folded perforated rear','Rear screen side','Rear screen horizontal')):continue
        for v in obj.data.vertices:
            v.co.x=x+.25+(v.co.x-x-.49)*(W-.5)/3.235
            v.co.y+=2.6
        top=obj.copy();top.data=obj.data.copy();top.name=obj.name+' roof balcony'
        bpy.data.collections['Architecture'].objects.link(top)
        for v in top.data.vertices:v.co.z+=3.1
    for z in (3.45,6.55):
        box('Rear balcony structural slab',(x+.15,14.35,z-.2),(x+W-.15,17.1,z),'structure',concrete)
        box('Rear balcony paving',(x+.2,14.4,z+.005),(x+W-.2,17.08,z+.035),'architecture',stone)
        for xx in (x+.13,x+W-.25):
            box('Rear balcony privacy wing',(xx,14.4,z),(xx+.12,17.1,z+1.35),'architecture',white)
        pipe('Rear balcony drainage',[(x+W-.35,16.9,z-.04),(x+W-.35,14.4,z-.1),(x+W-.16,14.4,z-.1)],.025,'hydraulic',cold)
    for xx in (x+.3,x+W-.3):
        box('Rear balcony steel post',(xx-.065,16.85,.05),(xx+.065,16.98,6.55),'structure',steel)
        box('Rear balcony pad foundation',(xx-.4,16.55,-.8),(xx+.4,17.35,-.35),'structure',concrete)
    # Replace home services around the now-stacked wet core and ground kitchen.
    for dx,rad,mat,name in ((0,.018,cold,'Cold riser'),(.09,.014,hot,'Hot riser'),(.23,.055,waste,'Soil and vent stack')):
        pipe(name,[(rx+dx,7.12,-.85),(rx+dx,7.12,9.65)],rad,'hydraulic',mat)
    pipe('Water service',[(x+4.3,-5.1,-.65),(x+4.3,-3.8,-.65),(rx,7.12,-.65)],.018,'hydraulic',cold)
    pipe('Sanitary lateral',[(rx+.23,7.12,-.85),(rx+.23,-5.8,-1.15)],.055,'hydraulic',waste)
    box('Wet service riser lining',(rx-.12,6.9,.35),(rx+.35,7.22,9.3))
    for z in (.35,3.45,6.55):
        for dx,mat,name in ((0,cold,'Cold branch'),(.09,hot,'Hot branch')):
            pipe(name,[(rx+dx,7.12,z-.1),(rx+dx,8.8,z-.1),(x+W-.65,8.8,z-.1)],.012,'hydraulic',mat)
        for yy in (7.55,8.7):
            pipe('Fixture waste branch',[(x+W-.85,yy,z+.04),(rx+.23,yy,z-.13),(rx+.23,7.12,z-.13)],.025,'hydraulic',waste)
        box('Bathroom extract grille',(rx+.8,8,z+2.58),(rx+1.05,8.25,z+2.62),'mechanical',white)
        pipe('Bathroom extract duct',[(rx+.9,8.1,z+2.64),(rx+.65,7.42,z+2.75),(rx+.65,7.42,9.65)],.065,'mechanical',duct)
    for yy,xx,z,label in ((10.5,x+2.55,.35,'Kitchen'),(13.8,rx+.35,3.45,'Laundry')):
        for dx,mat in ((0,cold),(.07,hot)):
            pipe(label+' supply',[(rx+dx,7.12,z-.1),(rx+dx,yy,z-.1),(xx+dx,yy,z-.1),(xx+dx,yy,z+.9)],.012,'hydraulic',mat)
        pipe(label+' waste',[(xx,yy,z+.8),(xx,yy,z-.13),(rx+.23,yy,z-.13),(rx+.23,7.12,z-.13)],.025,'hydraulic',waste)
    box('Heat pump water heater',(x+W-1.05,14.8,.1),(x+W-.35,15.45,1.8),'hydraulic',white)
    pipe('Water heater cold',[(rx,7.12,.65),(rx,15.1,.65),(x+W-.8,15.1,.65)],.018,'hydraulic',cold)
    pipe('Water heater hot',[(x+W-.65,15.1,1.5),(rx+.09,15.1,1.5),(rx+.09,7.12,1.5)],.014,'hydraulic',hot)
    box('AC outdoor condenser',(x+W-2.05,14.8,.2),(x+W-1.2,15.2,1.1),'mechanical',white)
    for j in range(10):box('Condenser grille',(x+W-2.01,15.22,.28+j*.075),(x+W-1.24,15.235,.31+j*.075),'mechanical',dark)
    for z in (.35,3.45,6.55):
        box('Ducted AC indoor unit',(x+2.75,6.8,z+2.55),(x+3.75,7.5,z+2.85),'mechanical',duct)
        pipe('AC refrigerant pair',[(x+W-1.6,15,.7),(rx+.45,15,.7),(rx+.45,7.4,.7),(rx+.45,7.4,z+2.7),(x+3.75,7.2,z+2.7)],.024,'mechanical',hot)
        pipe('AC condensate',[(x+3.2,7.2,z+2.55),(rx+.32,7.2,z+2.5),(rx+.32,7.2,.15),(rx+.32,14.7,.15)],.016,'hydraulic',cold)
        for yy in (3.2,12):
            pipe('Supply air trunk',[(x+3.15,7.2,z+2.72),(x+3.15,yy,z+2.72),(x+2.6,yy,z+2.72),(x+2.6,yy,z+2.6)],.06,'mechanical',duct)
            box('Linear supply grille',(x+1.9,yy,z+2.58),(x+2.7,yy+.08,z+2.62),'mechanical',dark)
        box('Return air grille',(x+2.85,6.55,z+2.48),(x+3.5,6.6,z+2.68),'mechanical',white)
    pipe('Dedicated kitchen exhaust',[(x+.6,9.65,2.18),(x+.6,9.65,2.95),(x+.6,14.6,2.95)],.075,'mechanical',duct)
    bx=x+3.94
    box('Distribution board',(bx,.95,1.1),(bx+.15,1.45,1.75),'electrical',white)
    box('Meter cabinet',(x+W-.55,.02,.65),(x+W-.16,.24,1.55),'electrical',dark)
    pipe('Underground electricity service',[(x+W-.4,-4.65,-.45),(x+W-.4,.3,-.45),(bx,.3,1.4),(bx,1.2,1.4)],.032,'electrical',power)
    pipe('Electrical riser',[(bx,1.2,1.4),(bx,6.62,1.4),(bx,6.62,9.3)],.027,'electrical',power)
    for level,z in enumerate((.35,3.45,6.55)):
        for j,(xx,yy) in enumerate(((1.3,3.2),(3,5.2),(1.3,9.2),(2.4,12.3),(W-1.2,8))):
            box('LED downlight',(x+xx-.06,yy-.06,z+2.58),(x+xx+.06,yy+.06,z+2.62),'electrical',white)
            pipe(f'L{level} lighting circuit {j}',[(bx,6.62,z+2.8),(x+xx,6.62,z+2.8),(x+xx,yy,z+2.8),(x+xx,yy,z+2.6)],.009,'electrical',power)
        for yy in (3.2,9.2,12.3):
            box('Double socket',(x+.255,yy,z+.25),(x+.285,yy+.12,z+.33),'electrical',white)
            pipe(f'L{level} power radial',[(bx,6.62,z+2.83),(x+.32,6.62,z+2.83),(x+.32,yy,z+2.83),(x+.32,yy,z+.3)],.012,'electrical',power)
        box('Switch plate',(rx-.21,6.7,z+1.05),(rx-.17,6.78,z+1.17),'electrical',white)
        box('Smoke alarm',(x+3.65,6.5,z+2.58),(x+3.8,6.65,z+2.62),'electrical',white)
    for label,xx,yy,zz in (('Oven',.6,9.6,.8),('AC',W-1.6,15,.7),('Water heater',W-.6,15,.7),('Washer',W-1.2,13.8,3.9)):
        pipe(label+' dedicated circuit',[(bx,6.62,2.95),(x+xx,6.62,2.95),(x+xx,yy,2.95),(x+xx,yy,zz)],.012,'electrical',power)

scene['sw_planning_basis']='User-supplied four-bedroom terrace plan; ground living and kitchen'
scene['sw_wet_door_clearance']=True
scene['sw_building_depth_m']=14.4
scene['sw_ground_living_zone_depth_m']=6.12
manifest=json.loads((folder/'manifest.json').read_text())
manifest['planning_basis']='Four-bedroom reference supplied during design'
manifest['site_depth_m']=24.3
manifest['count_by_system']=dict(Counter(o.get('sw_system') for o in scene.objects if o.get('sw_system')))
for home in manifest['homes']:
    home.update(depth_m=14.4,bedrooms=4,roof_rooms=2,ground_garden_room=0,
        living_location='Ground floor opening to rear garden',kitchen_location='Ground floor',
        laundry_location='First floor rear',rear_balcony_depth_m=2.7)
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
# Re-read all retained and new curve geometry so the route register matches the model.
routes=[]
for obj in scene.objects:
    if obj.type!='CURVE' or obj.get('sw_system') not in {'electrical','mechanical','hydraulic','civil'}:continue
    for spl in obj.data.splines:
        if not spl.points:continue
        pts=[list(obj.matrix_world@Vector(p.co[:3])) for p in spl.points]
        routes.append(dict(name=obj.name,system=obj.get('sw_system'),points=pts,radius=obj.data.bevel_depth))
(folder/'service-routes.json').write_text(json.dumps(routes,indent=2))
manifest['routes']=len(routes);(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
scene.objects['Plan'].location.y=7.2
scene.objects['Plan'].data.ortho_scale=18
bpy.ops.wm.save_as_mainfile(filepath=str(source))
bpy.ops.export_scene.gltf(filepath=str(folder/f'terrace-{N}.glb'),export_format='GLB',
    export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
print('FOUR_BEDROOM_REPLAN_COMPLETE',N,flush=True)
