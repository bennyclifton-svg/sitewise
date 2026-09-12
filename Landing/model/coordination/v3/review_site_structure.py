"""Read-only source load and disposable visual review; no master scene saves."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import site_structure

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-interior-checkpoint.blend'))
scene=bpy.data.scenes['01 | Assembled interior'];bpy.context.window.scene=scene
original=[o for o in scene.objects if not o.hide_render]
transforms={o:o.matrix_world.copy() for o in original}
rotation=Matrix.Rotation(site_structure.ANGLE,4,'Z')
for obj,matrix in transforms.items():
    if obj.type not in ('LIGHT','CAMERA'):
        obj.parent=None;obj.matrix_world=rotation@matrix
bpy.context.view_layer.update()
metadata=site_structure.build(scene)
inventory={r['name']:r for r in json.loads((HERE.parents[1]/'model-inventory.json').read_text())}
for obj in original:
    source=obj.get('source_name','')
    row=inventory.get(source,{})
    external=source.startswith(('BALUSTER - 001','POST - 001','INNER POST - 001','RAIL - 001','RAIL CONNECTION - 001')) and 'Ground FLoor.003' in row.get('parents',[]) and row.get('max',[0,0,99])[2]<2.7
    if source in metadata['suppress_source_names'] or external or obj.get('system')=='01 Site' or obj.type=='LIGHT':
        obj.hide_render=True
scene.world.use_nodes=True
background=scene.world.node_tree.nodes.get('Background')
if background:
    background.inputs['Color'].default_value=(.7,.8,.83,1);background.inputs['Strength'].default_value=.45
def aim(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for name,loc,energy,size in [('Key',(-20,-30,45),18000,15),('Fill',(25,-10,25),8000,20)]:
    light=bpy.data.lights.new('V3 Review '+name,'AREA');light.energy=energy;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=loc;aim(obj,(0,-4,3))
camera=bpy.data.cameras.new('V3 Review camera')
cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam);scene.camera=cam
cam.location=(-36,-57,40);aim(cam,(0,-3,2));camera.type='PERSP';camera.lens=38
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.render.filepath=str(HERE/'site-structure-overview.png')
bpy.ops.render.render(write_still=True)

# Focus structure review: ghosts keep the source rooms recognisable without concealing columns.
ghost=bpy.data.materials.new('V3 Review architectural ghost');ghost.use_nodes=True
nodes=ghost.node_tree.nodes;links=ghost.node_tree.links
shader=nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.6,.7,.72,1)
transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.10
links.new(transparent.outputs[0],mix.inputs[1]);links.new(shader.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],nodes.get('Material Output').inputs['Surface'])
focus=site_structure.FOCUS
for obj in original:
    if obj.type!='MESH' or obj.hide_render:continue
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    centre=sum(points,Vector())/8
    if abs(centre.y-focus.y)>2.6 or abs(centre.x-focus.x)>6.1:
        if obj.get('source_name'):obj.hide_render=True
    elif obj.get('source_name'):
        obj.data=obj.data.copy();obj.data.materials.clear();obj.data.materials.append(ghost)
for group in ('civil','landscape'):
    for obj in bpy.data.collections[metadata['collections'][group]].objects: obj.hide_render=True
cam.location=(-15,-24,14);aim(cam,focus+Vector((0,0,4)));camera.lens=45
scene.render.filepath=str(HERE/'site-structure-focus.png')
bpy.ops.render.render(write_still=True)
print('SITE_STRUCTURE_REVIEW_COMPLETE',flush=True)
