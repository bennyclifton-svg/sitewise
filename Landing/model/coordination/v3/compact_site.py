"""Tighten the presentation site while preserving its street/bin assembly."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from replicate_dwellings import bounds
from export_web import export
SOURCE=HERE.parent/'sitewise-coordinated-v17.blend'
TARGET=HERE.parent/'sitewise-compact-site-v18.blend'
SHIFT=-2.5
BACK=17.5
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
material=scene.objects['V3 | Shared driveway'].data.materials[0]
grass=scene.objects['Detail | Rear garden infill'].data.materials[0]
protected_prefixes=('V3 | Front bin store','V3 | Bin store','V3 | Relocated bin','V3 | Public footpath','V3 | Kerb','V3 | Driveway crossover','V3 | Pedestrian entry crossing','V3 | Pedestrian front gate','V3 | Letterbox','V3 | Cantilever entry hood')
protected={o.name:[o.matrix_world.copy(),o.data.copy()] for o in scene.objects if o.name.startswith(protected_prefixes)}
old_roofs={o.name:[bounds(o),o.matrix_world.copy()] for o in scene.objects if not o.hide_render and o.type=='MESH' and o.name.startswith('CI Tools Roof Covering - _Roof - Asphalt Shingle Gray')}
audit=dict(front_group_translation_m=SHIFT,old_site_depth_m=44,new_site_depth_m=39.5,rear_boundary_y=BACK,visitor_bays=[],protected=list(protected))

def map_y(y):
    if y<=-18.86:return y
    if y < -14.8:return y+SHIFT*(y+18.86)/4.06
    if y<=15.1:return y+SHIFT
    return 12.6+(y-15.1)*(BACK-12.6)/(22-15.1)

def move_point(obj,p):
    q=obj.matrix_world@Vector(p[:3]);q.y=map_y(q.y)
    return obj.matrix_world.inverted()@q

for obj in list(scene.objects):
    if obj.type not in ('MESH','CURVE') or obj.name in protected or obj.get('sw_system')=='context':continue
    if obj.type=='MESH' and not obj.data.vertices:continue
    lo,hi=bounds(obj)
    if hi.y<=-18.86:continue
    if lo.y>=-14.8 and hi.y<=15.1:
        obj.location.y+=SHIFT
    else:
        obj.data=obj.data.copy()
        if obj.type=='MESH':
            for v in obj.data.vertices:v.co=move_point(obj,v.co)
        else:
            for spline in obj.data.splines:
                for p in spline.points:p.co=(*move_point(obj,p.co),p.co.w)
                for p in spline.bezier_points:
                    p.handle_left=move_point(obj,p.handle_left);p.handle_right=move_point(obj,p.handle_right);p.co=move_point(obj,p.co)
    if obj.get('sw_motion','').startswith('rotor:'):
        motion=obj['sw_motion'].split(':');motion[4]=str(-map_y(-float(motion[4])));obj['sw_motion']=':'.join(motion)
    if obj.get('sw_member_endpoints'):
        points=json.loads(obj['sw_member_endpoints'])
        for p in points:p[1]=map_y(p[1])
        obj['sw_member_endpoints']=json.dumps(points)

bpy.context.view_layer.update()

def box(name,lo,hi,mat=material,system='civil'):
    points=[(x,y,z) for z in (lo[2],hi[2]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])]
    data=bpy.data.meshes.new(name);data.from_pydata(points,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]);data.materials.append(mat)
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj['sw_system']=system
    obj['sw_civil_surface']=system=='civil';obj['sw_illustrative']=True
    return obj

def set_y_end(obj,new_y):
    lo,hi=bounds(obj);oldend=hi.y;inv=obj.matrix_world.inverted();obj.data=obj.data.copy()
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co;p.y=lo.y+(p.y-lo.y)*(new_y-lo.y)/(oldend-lo.y);v.co=inv@p

# Continuous driving surface meets the rear court; no strip of missing pavement.
set_y_end(scene.objects['V3 | Shared driveway'],17.44)
set_y_end(scene.objects['V3 | Building-side pedestrian path'],12.25)
set_y_end(scene.objects['Detail | Garage approach ground cover'],12.25)
for obj in list(scene.objects):
    if obj.name in ('V3 | Driveway rear turning apron', 'CSG - 010_Wood - Pine Grained Vertical_0', 'CSG - 010_Wood - Pine Grained Vertical_0.001') or obj.name.startswith(('Detail | Rear garden infill','V3 | Rear landscape strip')):
        bpy.data.objects.remove(obj,do_unlink=True)
box('Compact site | Rear visitor court',(-7.7,12.25,.07),(-.2,17.44,.27))
box('Compact site | Rear garden',(-.20,12.25,-.10),(6.90,17.44,.05),grass,'landscape')
# The continuous ground layer sits below the individual lawns/infill patches.
# Coplanar overlapping faces otherwise produce black patches in the site view.
scene.objects['Detail | Continuous garden ground cover'].location.z-=.01
# Two 2.5 x 5.4 m bays face the six-metre-wide rear manoeuvring aisle.
paint=bpy.data.materials.new('Compact site | Parking marking charcoal');paint.diffuse_color=(.12,.12,.12,1)
paint.use_nodes=True;bsdf=paint.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.12,.12,.12,1);bsdf.inputs['Roughness'].default_value=.8
for y in (12.25,14.75,17.25):
    box(f'Compact site | Visitor bay line {y}',(-5.6,y-.025,.273),(-.2,y+.025,.281),paint)
box('Compact site | Visitor bay head line',(-.25,12.25,.273),(-.20,17.25,.281),paint)
for i,ya in enumerate((12.25,14.75),1):
    box(f'Compact site | Visitor wheel stop {i}',(-.80,ya+.35,.28),(-.63,ya+2.15,.38))
    data=bpy.data.curves.new(f'Visitor {i} label','FONT');data.body='VISITOR';data.align_x='CENTER';data.align_y='CENTER';data.size=.32;data.extrude=.001;data.materials.append(paint)
    obj=bpy.data.objects.new(f'Compact site | Visitor {i} pavement label',data);scene.collection.objects.link(obj)
    obj.location=(-3.0,ya+1.25,.282);obj.rotation_euler.z=1.57079632679
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.convert(target='MESH');obj.select_set(False)
    obj['sw_system']='civil';obj['sw_civil_surface']=True
    audit['visitor_bays'].append(dict(bay=i,bounds=[[-5.6,ya,.27],[-.2,ya+2.5,.27]],width_m=2.5,length_m=5.4,aisle_width_m=6.0))

# Export metadata moves reveal masks with the houses, preserving discipline ownership.
scene['sw_dwelling_y_offset']=SHIFT
scene['sw_compact_site']=json.dumps(audit)
bpy.context.view_layer.update()
for name,(old_bounds,matrix) in old_roofs.items():
    lo,hi=bounds(scene.objects[name]);before_lo,before_hi=old_bounds
    assert (lo-before_lo-Vector((0,SHIFT,0))).length<1e-4,name
    assert (hi-before_hi-Vector((0,SHIFT,0))).length<1e-4,name
for name,(matrix,data) in protected.items():
    obj=scene.objects[name];assert obj.matrix_world==matrix,name
    if obj.type=='MESH':assert all(a.co==b.co for a,b in zip(obj.data.vertices,data.vertices)),name
assert abs(bounds(scene.objects['V3 | Perimeter 3'])[0].y-(BACK-.06))<.025
assert bounds(scene.objects['V3 | Shared driveway'])[1].y>=17.24
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
(HERE/'compact-site-v18-audit.json').write_text(json.dumps(audit,indent=2))
export(scene)
print('COMPACT_SITE_PASS: two visitor bays; depth 44 -> 39.5 m; frontage intact; buildings translated rigidly',flush=True)
