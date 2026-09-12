"""V2 static hero: canonical colours, low perspective, shared cadastral context."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

OUT=Path(__file__).resolve().parent
REPO=OUT.parents[2]
WEB=REPO/'frontend/public/landing-assets/coordination'
draft='--draft' in sys.argv
context_path=OUT/'perspective-context.json'
context=json.loads(context_path.read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/'sitewise-siting-study.blend'))
scene=bpy.context.scene
inventory={r['name']:r for r in json.loads((OUT.parent/'model-inventory.json').read_text())}
source_transforms={o.name:o.matrix_world.copy() for o in scene.objects if o.get('source_name')}

def linear(hex_colour):
    c=[int(hex_colour[i:i+2],16)/255 for i in [1,3,5]]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)
palette={'Petrol':'#12606D','Air':'#93CEDD','Chalk':'#F9F7F3','Ink':'#0F1F22'}
colours={name:linear(value) for name,value in palette.items()}
def material(name,colour,emission=0,roughness=.86):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*colour,1)
    node=m.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*colour,1)
    node.inputs['Roughness'].default_value=roughness
    node.inputs['Emission Color'].default_value=(*colour,1);node.inputs['Emission Strength'].default_value=emission
    return m

petrol=material('Hero v2 | canonical Petrol #12606D',colours['Petrol'])
lot_material=material('Hero v2 | Petrol parcel',tuple(c*1.08 for c in colours['Petrol']))
paving=material('Hero v2 | Petrol Air access',tuple(.91*p+.09*a for p,a in zip(colours['Petrol'],colours['Air'])))
chalk=material('Hero v2 | canonical Chalk #F9F7F3',colours['Chalk'])
glazing=material('Hero v2 | Ink glazing',colours['Ink'],roughness=.35)
white_line=material('Hero v2 | fine white cadastral line',colours['Chalk'],.12)
line_nodes=white_line.node_tree.nodes
line_emission=line_nodes.new('ShaderNodeEmission');line_emission.inputs['Color'].default_value=(*colours['Chalk'],1)
line_emission.inputs['Strength'].default_value=.9
white_line.node_tree.links.new(line_emission.outputs[0],line_nodes.get('Material Output').inputs['Surface'])
warm=material('Hero v2 | selective interior warmth',(.8,.60,.32),.32)
fence_material=material('Hero v2 | Petrol fence',tuple(.75*p+.25*a for p,a in zip(colours['Petrol'],colours['Air'])))
hidden_fence=[];retained_guards=[];warm_glazing=[]
fence_prefixes=('BALUSTER - 001','POST - 001','INNER POST - 001','RAIL - 001','RAIL CONNECTION - 001')
for obj in list(scene.objects):
    if obj.type=='LIGHT':obj.hide_render=True
    if obj.type not in ['MESH','CURVE']:continue
    source_name=obj.get('source_name','')
    original=inventory.get(source_name,{})
    ground_fence=(source_name.startswith(fence_prefixes) and 'Ground FLoor.003' in original.get('parents',[]) and original.get('max',[0,0,99])[2]<2.7)
    if ground_fence:
        obj.hide_render=True;obj.hide_set(True);hidden_fence.append(source_name);continue
    if source_name.startswith(fence_prefixes):retained_guards.append(source_name)
    if obj.hide_render:continue
    if obj.name.startswith(('Illustrative boundary clearance','Source-derived cadastral boundary')) or obj.name=='Selected lot boundary':
        obj.hide_render=True;continue
    mat=None
    if obj.name=='Studio ground | not survey geometry':
        obj.scale=(14,14,14);obj.location.z=-.12;mat=petrol
    elif obj.name=='Selected illustrative parcel | not surveyed':mat=lot_material
    elif obj.get('system')=='01 Site':mat=paving
    elif source_name:
        mat=glazing if 'Glass' in source_name else chalk
        middle=sum((obj.matrix_world@Vector(p) for p in obj.bound_box),Vector())/8
        if source_name.startswith('DOO - 020_Glass') and middle.y<1:
            mat=warm;warm_glazing.append(source_name)
    if mat:
        obj.data=obj.data.copy();obj.data.materials.clear();obj.data.materials.append(mat)

cad_collection=bpy.data.collections.new('HERO v2 | shared source cadastral field')
scene.collection.children.link(cad_collection)
def curves(name,paths,width,z):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=1
    data.bevel_depth=width;data.bevel_resolution=1
    for path in paths:
        spline=data.splines.new('POLY');spline.points.add(len(path)-1)
        for point,(x,y) in zip(spline.points,path):point.co=(x,y,z,1)
    obj=bpy.data.objects.new(name,data);cad_collection.objects.link(obj);data.materials.append(white_line)
    return obj
curves('Distant shared cadastral boundaries',context['context_segments'],.018,-.035)
curves('Selected parcel boundary | continuous',[[*context['lot'],context['lot'][0]]],.028,-.025)

# A replaceable illustrative boundary fence. The original building and balcony guards stay fixed.
fence_collection=bpy.data.collections.new('HERO v2 | fence registered to selected parcel')
scene.collection.children.link(fence_collection)
unit=bpy.data.meshes.new('Perimeter fence | unit box')
unit.from_pydata([(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)],[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
unit.materials.append(fence_material)
fence_runs=[((-12,-22),(-12,22)),((12,-22),(12,22)),((-12,22),(12,22)),((-12,-22),(-10.5,-22)),((-6.5,-22),(12,-22))]
fence_centres=[]
def box(name,center,size):
    obj=bpy.data.objects.new(name,unit);fence_collection.objects.link(obj)
    obj.matrix_world=Matrix.Translation(Vector(center))@Matrix.Diagonal((*size,1))
    obj['provenance']='Illustrative perimeter fence registered to selected lot; specification/access compliance unverified'
    return obj
for ri,(a,b) in enumerate(fence_runs):
    length=math.dist(a,b);count=math.ceil(length/2)
    for i in range(count+1):
        t=i/count;x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
        box(f'Boundary fence {ri+1} post {i+1}',(x,y,.51),(.085,.085,1.1));fence_centres.append((x,y))
    for z in [.26,.88]:
        box(f'Boundary fence {ri+1} rail Z{z}',((a[0]+b[0])/2,(a[1]+b[1])/2,z),
            (length,.055,.075) if a[1]==b[1] else (.055,length,.075))
    # Light pickets keep the low camera's building entrance and ground-floor windows visible.
    pickets=math.floor(length/.32)
    for i in range(1,pickets):
        t=i/pickets;x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
        box(f'Boundary fence {ri+1} picket {i}',(x,y,.56),(.03,.03,.76));fence_centres.append((x,y))

light_collection=bpy.data.collections.new('HERO v2 | neutral light')
scene.collection.children.link(light_collection)
def light(name,position,target,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=(1,1,1)
    o=bpy.data.objects.new(name,d);light_collection.objects.link(o);o.location=position
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
light('Hero v2 daylight',(-24,-35,44),(0,0,3),15000,9)
light('Hero v2 neutral fill',(28,-8,30),(0,0,4),5500,22)
light('Hero v2 roof separation',(-4,40,34),(0,0,4),8500,16)
scene.world.use_nodes=True
nodes=scene.world.node_tree.nodes;nodes.clear()
out=nodes.new('ShaderNodeOutputWorld');mix=nodes.new('ShaderNodeMixShader')
ambient=nodes.new('ShaderNodeBackground');ambient.inputs[0].default_value=(1,1,1,1);ambient.inputs[1].default_value=.15
far_colour=tuple(.70*p+.30*a for p,a in zip(colours['Petrol'],colours['Air']))
sky=nodes.new('ShaderNodeBackground');sky.inputs[1].default_value=.9
direction=nodes.new('ShaderNodeTexCoord');separate=nodes.new('ShaderNodeSeparateXYZ')
absolute=nodes.new('ShaderNodeMath');absolute.operation='ABSOLUTE'
sky_range=nodes.new('ShaderNodeMapRange');sky_range.inputs['From Min'].default_value=0;sky_range.inputs['From Max'].default_value=.45
sky_mix=nodes.new('ShaderNodeMixRGB');sky_mix.inputs[1].default_value=(*far_colour,1);sky_mix.inputs[2].default_value=(*colours['Air'],1)
links=scene.world.node_tree.links
links.new(direction.outputs['Normal'],separate.inputs[0]);links.new(separate.outputs['Z'],absolute.inputs[0]);links.new(absolute.outputs[0],sky_range.inputs[0])
links.new(sky_range.outputs[0],sky_mix.inputs[0]);links.new(sky_mix.outputs[0],sky.inputs[0])
path=nodes.new('ShaderNodeLightPath')
links=scene.world.node_tree.links;links.new(path.outputs['Is Camera Ray'],mix.inputs[0]);links.new(ambient.outputs[0],mix.inputs[1]);links.new(sky.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs[0])

# A distance-based atmospheric blend keeps the level ground and Air sky continuous.
# It adds no terrain or invented topographic geometry and leaves the selected lot unchanged.
nodes=petrol.node_tree.nodes;links=petrol.node_tree.links
view=nodes.new('ShaderNodeCameraData');distance=nodes.new('ShaderNodeMapRange')
distance.interpolation_type='SMOOTHERSTEP';distance.inputs['From Min'].default_value=90;distance.inputs['From Max'].default_value=350
far_surface=nodes.new('ShaderNodeEmission');far_surface.inputs[0].default_value=(*far_colour,1);far_surface.inputs[1].default_value=.9
atmosphere=nodes.new('ShaderNodeMixShader')
links.new(view.outputs['View Distance'],distance.inputs[0]);links.new(distance.outputs[0],atmosphere.inputs[0])
links.new(nodes.get('Principled BSDF').outputs[0],atmosphere.inputs[1]);links.new(far_surface.outputs[0],atmosphere.inputs[2]);links.new(atmosphere.outputs[0],nodes.get('Material Output').inputs[0])

camera=bpy.data.objects['Camera | reverse study'];scene.camera=camera
target=Vector((0,2,2.5));camera.location=(-25,-42,17)
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='PERSP';camera.data.lens=28;camera.data.sensor_width=36;camera.data.dof.use_dof=False
camera.data.clip_end=5000
scene.render.resolution_x=900 if draft else 1200;scene.render.resolution_y=990 if draft else 1320
scene.render.resolution_percentage=100
points=[Vector((x,y,0)) for x,y in context['lot']]
for obj in scene.objects:
    if obj.get('system') in ['04 Walls','06 Roof'] and not obj.hide_render:
        points.extend(obj.matrix_world@Vector(p) for p in obj.bound_box)
bpy.context.view_layer.update()
def projected_bounds():
    uv=[world_to_camera_view(scene,camera,p) for p in points]
    return [min(p.x for p in uv),min(p.y for p in uv),max(p.x for p in uv),max(p.y for p in uv)]
bounds=projected_bounds()
camera.data.lens*=min(.805/(bounds[2]-bounds[0]),.54/(bounds[3]-bounds[1]))
bpy.context.view_layer.update();bounds=projected_bounds()
# Lens shift frames the site without changing its coordinates or the physical viewing angle.
for prop,axis,want in [('shift_x',0,.51),('shift_y',1,.46)]:
    before=projected_bounds();mid=(before[axis]+before[axis+2])/2
    old=getattr(camera.data,prop);setattr(camera.data,prop,old+.01)
    after=projected_bounds();delta=((after[axis]+after[axis+2])/2-mid)/.01
    setattr(camera.data,prop,old+(want-mid)/delta)
forward=Vector((target.x-camera.location.x,target.y-camera.location.y,0)).normalized()
horizon_point=Vector((camera.location.x,camera.location.y,0))+forward*100000
def set_horizon():
    old=camera.data.shift_y
    before=world_to_camera_view(scene,camera,horizon_point).y
    camera.data.shift_y+=.01
    after=world_to_camera_view(scene,camera,horizon_point).y
    camera.data.shift_y=old+(.785-before)/((after-before)/.01)
set_horizon()
for _ in range(8):
    bounds=projected_bounds()
    if bounds[1]>=.205:break
    camera.data.lens*=.985
    set_horizon()
bounds=projected_bounds()
elevation=math.degrees(math.atan2(camera.location.z-target.z,math.hypot(camera.location.x-target.x,camera.location.y-target.y)))

for name,matrix in source_transforms.items():
    assert max(abs(bpy.data.objects[name].matrix_world[i][j]-matrix[i][j]) for i in range(4) for j in range(4))<.00001,name
fence_error=max(min(abs(abs(x)-12),abs(abs(y)-22)) for x,y in fence_centres)
assert fence_error<.00001
manifest=dict(stage='V2 static perspective hero; camera motion deferred',source_scene='sitewise-siting-study.blend',
    shared_context=str(context_path),context_segment_count=len(context['context_segments']),lot=context['lot'],
    palette_srgb=palette,palette_scene_linear=colours,
    camera=dict(type=camera.data.type,position=list(camera.location),target=list(target),lens_mm=camera.data.lens,
        elevation_degrees=elevation,shift_x=camera.data.shift_x,shift_y=camera.data.shift_y,projected_site_bounds=bounds,
        horizon_from_image_top=1-world_to_camera_view(scene,camera,horizon_point).y),
    image_size=[scene.render.resolution_x,scene.render.resolution_y],draft=draft,
    fence=dict(source_suppressed_count=len(hidden_fence),source_suppressed=hidden_fence,
        preserved_guard_family_count=len(retained_guards),runs=fence_runs,centreline_boundary_error=fence_error,
        height=1.1,physical_thickness=.085,opening=dict(edge='Y=-22',x=[-10.5,-6.5],status='Illustrative access gap, not an approved driveway'),
        alignment='All fence centrelines lie on X=+/-12 or Y=+/-22. Half-thickness projects either side of that line.'),
    source_transform_check='Every source object transform remains unchanged; old ground fence visibility is the explicit replacement exception.',
    architectural_geometry='All walls, roofs, floor plates and balcony guards retained; no structural overlay.',
    ground='Level at Z=-.12; expanded plane has no invented topography',
    structural_direction='Reinforced-concrete columns/slabs; not exposed or modelled in this static hero',
    units=context.get('units','Illustrative imported-model units; not verified metres'),
    assets=dict(web='/landing-assets/coordination/sitewise-hero-perspective.webp',render='21-perspective-hero-draft.png' if draft else '22-perspective-hero.png'))
(OUT/'perspective-hero-manifest.json').write_text(json.dumps(manifest,indent=2))
scene.render.engine='CYCLES';scene.cycles.samples=12 if draft else 32;scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene['stage']=manifest['stage'];scene['source_transform_check']=manifest['source_transform_check']
scene['illustrative_fence_note']=manifest['fence']['alignment']
scene.render.filepath=str(OUT/manifest['assets']['render'])
if not draft:bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'sitewise-perspective-hero-v2.blend'))
print('PERSPECTIVE_HERO_READY',json.dumps({k:manifest[k] for k in ['camera','context_segment_count','image_size']}),flush=True)
bpy.ops.render.render(write_still=True)
print('PERSPECTIVE_HERO_RENDER_COMPLETE',flush=True)
