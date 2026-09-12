"""Apply an achromatic chalk finish to the complete coordinated model."""
import bpy
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from export_web import export

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-roof-frames-v13.blend'))
scene=bpy.context.scene
before={o.name: (o.matrix_world.copy(),o.hide_render) for o in scene.objects}
white=((.98+.055)/1.055)**2.4
glass_materials={m for o in scene.objects if o.get('sw_glass') and o.type=='MESH' for m in o.data.materials if m}
changed=[]
for mat in bpy.data.materials:
    glass=mat in glass_materials
    alpha=.20 if glass else 1
    mat.diffuse_color=(white,white,white,alpha)
    if mat.use_nodes:
        shader=mat.node_tree.nodes.get('Principled BSDF')
        if shader:
            for name in ('Base Color','Emission Color','Metallic','Roughness','Alpha','Emission Strength','Transmission Weight'):
                for link in list(shader.inputs[name].links):mat.node_tree.links.remove(link)
            shader.inputs['Base Color'].default_value=(white,white,white,1)
            shader.inputs['Emission Color'].default_value=(1,1,1,1)
            shader.inputs['Emission Strength'].default_value=0
            shader.inputs['Metallic'].default_value=0
            shader.inputs['Roughness'].default_value=.32 if glass else .86
            shader.inputs['Alpha'].default_value=alpha
            shader.inputs['Transmission Weight'].default_value=0
    changed.append(mat.name)
for obj in scene.objects:
    if obj.type=='LIGHT':obj.data.color=(1,1,1)
    assert (obj.matrix_world,obj.hide_render)==before[obj.name]
scene.world.use_nodes=True
background=scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value=(.22,.22,.22,1)
background.inputs['Strength'].default_value=.45
scene['sw_palette']='Bright neutral chalk white; all disciplines and site elements achromatic'
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-bright-chalk-v14.blend'))
(HERE/'bright-chalk-audit.json').write_text(json.dumps({'materials_whitened':len(changed),
    'objects_preserved':len(before),'glass_materials':len(glass_materials),'materials':changed},indent=2))
if '--export' in sys.argv:export(scene)
if '--render' in sys.argv:
    from mathutils import Vector
    for obj in scene.objects:
        if obj.type=='LIGHT' or obj.get('sw_system')=='context':obj.hide_render=True
    def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    for name,loc,power,size in [('Key',(-20,-20,30),13000,8),('Fill',(20,15,25),4500,12)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc;aim(obj,(0,0,4))
    data=bpy.data.cameras.new('Bright chalk review');data.type='ORTHO';data.ortho_scale=34
    camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera)
    camera.location=(-30,-29,27);aim(camera,(0,0,4));scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(HERE/'bright-chalk-overview.png')
    bpy.ops.render.render(write_still=True)
