"""First fitted kitchen checkpoint. Original GLBs and approved scenes remain intact."""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'coordination'
AUDIT=OUT/'asset-audit'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'sitewise-camera-review.blend'))
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1500
scene.render.resolution_y=1125
source_center=Vector((-24.757655,-11.917233,0))
focus=Vector((-26,-23,0))-source_center
U=Vector((.98703,-.16053,0)).normalized()
V=Vector((.16053,.98703,0)).normalized()
floor_z=3.22
anchor=focus+U*4.47+V*2.33+Vector((0,0,floor_z))
orientation=Matrix(((-V.x,U.x,0,0),(-V.y,U.y,0,0),(0,0,1,0),(0,0,0,1)))
placement=Matrix.Translation(anchor)@orientation

def mat(name,color,emission=0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    node=m.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value=(*color,1)
    node.inputs['Roughness'].default_value=.72
    node.inputs['Emission Color'].default_value=(*color,1)
    node.inputs['Emission Strength'].default_value=emission
    return m

chalk=mat('Kitchen | chalk joinery',(.77,.77,.73))
stone=mat('Kitchen | pale countertop',(.65,.67,.66))
graphite=mat('Kitchen | appliance glass and hob',(.035,.049,.057))
metal=mat('Kitchen | brushed mineral',(.28,.34,.35))
warm=mat('Kitchen | warm light',(.95,.75,.44),5)
screen=mat('Kitchen | appliance display',(.10,.24,.32),.3)
fitout=bpy.data.collections.new('CHECKPOINT 01 | Kitchen fit-out')
scene.collection.children.link(fitout)
lighting=bpy.data.collections.new('CHECKPOINT 01 | Kitchen lighting')
scene.collection.children.link(lighting)
manifest=[]

# The original kitchen cabinetry is two complete source meshes in this dwelling.
replaced=['SLA - 012_Wood - Oak Light_0.010','SLA - 012_Stone - Marble Black_0.010']
for obj in scene.objects:
    if obj.type!='MESH' or not obj.get('source_name'):
        continue
    name=obj['source_name']
    corners=[obj.matrix_world@Vector(c) for c in obj.bound_box]
    center=sum(corners,Vector())/8
    in_dwelling=(center-focus).dot(V)<3 and (center-focus).dot(V)>-3
    if name in replaced or (in_dwelling and name.startswith(('Sink General','Cooktop'))
                           and 3.2<center.z<4.7):
        obj.hide_render=True
        obj.hide_set(True)
        obj['replacement_note']='Retained original; replaced for kitchen checkpoint'

# Load the supplied kitchen and normalize its millimetre-like source scale.
with bpy.data.libraries.load(str(AUDIT/'kitchen-source.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n!='Audit camera']
loaded=[o for o in dst.objects if o]
for obj in loaded:
    fitout.objects.link(obj)
bpy.context.view_layer.update()
millimetres=Matrix.Diagonal((.001,.001,.001,1))
skip={2,3,4,9,11,12,5,*range(19,25),26,*range(27,35),*range(38,54),*range(55,59)}
for obj in loaded:
    if obj.type!='MESH':
        continue
    number=int(obj.name.split('_')[1].split('.')[0])
    if number in skip:
        bpy.data.objects.remove(obj,do_unlink=True)
        continue
    world=obj.matrix_world.copy()
    obj.parent=None
    obj.data=obj.data.copy()
    obj.data.transform(millimetres@world)
    # Open the two appliance bays while retaining the supplied cabinet carcass.
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    discard=[f for f in bm.faces if .50<f.calc_center_median().x<.65
             and -2.47<f.calc_center_median().y<-1.23
             and .15<f.calc_center_median().z<1.98]
    bmesh.ops.delete(bm,geom=discard,context='FACES')
    # Imported overhead storage crosses the dwelling's existing kitchen window.
    above_window=[f for f in bm.faces if f.calc_center_median().x>1.5
                  and f.calc_center_median().z>1.36]
    bmesh.ops.delete(bm,geom=above_window,context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    obj.matrix_world=placement
    obj.data.materials.clear()
    obj.data.materials.append(graphite if number in [8,24] else metal if number in [19,20,21,22,23,54] else stone if number==59 else chalk)
    obj.name=f'Kitchen source | Object_{number}'
    obj['source_asset']='kitchen.glb'
    obj['source_object']=f'Object_{number}'
    obj['provenance']='baldoVReal / CC BY 4.0; scale normalized; decor removed; appliance openings adjusted'
    manifest.append({'object':obj.name,'source':'kitchen.glb','source_object':f'Object_{number}'})
for obj in loaded:
    try:
        if obj.type=='EMPTY':
            bpy.data.objects.remove(obj,do_unlink=True)
    except ReferenceError:
        pass

library=json.loads((AUDIT/'appliance-library.json').read_text())
with bpy.data.libraries.load(str(AUDIT/'appliance-library.blend'),link=False) as (src,dst):
    dst.collections=[a['collection'] for a in library['assets']]
for c in dst.collections:
    scene.collection.children.link(c)
for asset in library['assets']:
    objects=bpy.data.collections[asset['collection']].objects
    dimensions=asset['dimensions']
    if 'Fridge' in asset['name']:
        transform=placement@Matrix.Translation((.29,-2.16,.15))@Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Diagonal((.59/dimensions[0],.59/dimensions[1],1,1))
        service='Electrical; optional water connection unassigned'
    elif 'Oven' in asset['name']:
        transform=placement@Matrix.Translation((.30,-1.54,.47))@Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Diagonal((.57/dimensions[0],.55/dimensions[1],.88/dimensions[2],1))
        service='Electrical; appliance load and circuit unassigned'
    else:
        # Keep extracted pendants ready for the furnishing/lighting checkpoint.
        for obj in objects:
            obj.hide_render=True
            obj.hide_set(True)
        continue
    for obj in objects:
        obj.matrix_world=transform
        obj['service_scope']=service
        manifest.append({'object':obj.name,'source':'interior-design.glb','service':service})

def box(name,center,size,material):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj=bpy.context.object
    obj.name=name
    obj.data.transform(Matrix.Diagonal((*size,1)))
    obj.matrix_world=placement@Matrix.Translation(center)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    fitout.objects.link(obj)
    obj.data.materials.append(material)
    bevel=obj.modifiers.new('Soft manufactured edges','BEVEL')
    bevel.width=.004
    bevel.segments=2
    obj['provenance']='Authored illustrative fitting; no manufacturer specification'
    return obj

box('Microwave | housing',(.30,-1.54,1.65),(.56,.57,.33),chalk)
box('Microwave | glazed door',(.586,-1.58,1.65),(.012,.42,.26),graphite)
box('Microwave | display',(.596,-1.295,1.705),(.014,.063,.056),screen)
box('Microwave | handle',(.62,-1.376,1.645),(.03,.016,.21),metal)
box('Microwave | lower control',(.596,-1.295,1.596),(.014,.045,.035),metal)
box('Microwave | tower infill',(.30,-1.54,1.405),(.56,.57,.08),chalk)
box('Induction cooktop | glass surface',(1.09,-.30,.955),(.76,.51,.025),graphite)
for i,(x,y) in enumerate([(.88,-.18),(1.30,-.18),(.88,-.41),(1.30,-.41)]):
    bpy.ops.mesh.primitive_torus_add(major_radius=.083,minor_radius=.0018,major_segments=40,minor_segments=6)
    ring=bpy.context.object
    ring.name=f'Induction zone {i+1} | geometric marking'
    ring.matrix_world=placement@Matrix.Translation((x,y,.969))
    for c in list(ring.users_collection):
        c.objects.unlink(ring)
    fitout.objects.link(ring)
    ring.data.materials.append(metal)
box('Induction cooktop | touch controls',(1.09,-.53,.97),(.15,.012,.002),screen)
box('Range hood | task light',(1.09,-.25,1.588),(.54,.025,.008),warm)
manifest.append({'object':'Microwave assembly','source':'Authored','service':'Electrical; circuit/load unassigned'})
manifest.append({'object':'Induction cooktop','source':'Authored; gas-specific source geometry removed','service':'Electrical; circuit/load unassigned'})

def light(name,position,power,size,target):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=power
    data.shape='DISK'
    data.size=size
    data.color=(1,.85,.66)
    obj=bpy.data.objects.new(name,data)
    lighting.objects.link(obj)
    obj.location=position
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj

for i,(u,v) in enumerate([(2.65,-.8),(2.65,1.25),(1.2,-.8),(1.2,1.25)]):
    p=focus+U*u+V*v+Vector((0,0,5.58))
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.065,depth=.022,location=p)
    obj=bpy.context.object
    obj.name=f'Kitchen ceiling light {i+1} | illustrative'
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    lighting.objects.link(obj)
    obj.data.materials.append(warm)
    light(f'Kitchen downlight {i+1}',p-Vector((0,0,.04)),35,.22,p-Vector((0,0,2)))
light('Kitchen soft camera fill',focus+U*1+V*-1+Vector((0,0,5.2)),65,1.8,anchor+Vector((0,0,1)))

camera=bpy.data.objects['Camera | reverse study']
scene.camera=camera
camera.data.type='PERSP'
camera.data.lens=23
camera.data.clip_start=.03
target=placement@Vector((1.55,-.85,1.25))
camera.location=focus+U*.30-V*1.75+Vector((0,0,5.05))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.dof.use_dof=True
camera.data.dof.focus_distance=(target-camera.location).length
camera.data.dof.aperture_fstop=6.3
scene['stage']='Checkpoint 01 — fitted kitchen and initial kitchen lights; other systems pending'
scene['fitout_provenance']='Adapted supplied assets plus authored microwave/lights; illustrative fit requiring review'
scene['structural_assumption']='Timber studs and roof framing/trusses; concrete slabs/foundations; not yet modelled'
scene.render.filepath=str(OUT/'11-fitted-kitchen.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'sitewise-kitchen-checkpoint.blend'))

# Review-only overhead view checks the kitchen in its existing room and circulation.
# The saved scene above keeps the entire architecture assembled for the fly-through.
for obj in list(scene.objects):
    if obj.type!='MESH' or not obj.get('source_name') or obj.hide_render:
        continue
    corners=[obj.matrix_world@Vector(c) for c in obj.bound_box]
    midpoint=sum(corners,Vector())/8
    v=(midpoint-focus).dot(V)
    if max(p.z for p in corners)<3.2 or min(p.z for p in corners)>5.6 or v<-3.5 or v>3.2:
        obj.hide_render=True
camera.data.type='ORTHO'
camera.data.ortho_scale=10.5
camera.data.dof.use_dof=False
target=focus+U*1.2+Vector((0,0,3.7))
camera.location=target-U*9-V*9+Vector((0,0,15))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'12-kitchen-placement-review.png')
bpy.ops.render.render(write_still=True)
(OUT/'kitchen-checkpoint.json').write_text(json.dumps({'stage':'Kitchen first fit for review',
    'source_floor':floor_z,'placement_matrix':[list(r) for r in placement],
    'objects':manifest,'existing_kitchen_replaced':replaced,
    'service_endpoints':{'sink':'Water and waste; former route must be re-anchored to new fitting',
        'induction_hob':'User-approved all-electric kitchen; electrical circuit/load unassigned',
        'hood':'Electrical and extract route; terminal unassigned',
        'fridge':'Electrical','oven':'Electrical','microwave':'Electrical','lights':'Electrical'},
    'status':'No circuits, duct sizing or structural engineering inferred',
    'pending':['Fit/clearance review','Lighting throughout dwelling','Curtains/soft furnishings',
        'Timber frame/roof/slabs/foundations','MEP routes','Car/traffic','Unified site scene and motion']},indent=2))
print('KITCHEN_CHECKPOINT_COMPLETE',flush=True)
