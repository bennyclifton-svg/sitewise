"""Disposable review cameras; no changes to the garden checkpoint."""
import bpy
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-decks-v9.blend'))
scene=bpy.context.scene
for obj in scene.objects:
    if obj.type=='LIGHT': obj.hide_render=True
    if obj.get('sw_system')=='context': obj.hide_render=True
scene.world.use_nodes=True
world=scene.world.node_tree.nodes.get('Background')
world.inputs['Color'].default_value=(.18,.21,.24,1)
world.inputs['Strength'].default_value=.55

def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size in [('Key',(20,-25,35),15000,12),('Fill',(20,20,20),7000,15)]:
    data=bpy.data.lights.new('Garden Review '+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=loc;aim(obj,(5,0,2))
camdata=bpy.data.cameras.new('Garden Review camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO'
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
for name,pos,target,scale in [('decks-overview',(36,-31,27),(5,0,2),38),('deck-connection',(22,-22,14),(7.5,-11,1.8),13)]:
    cam.location=pos;aim(cam,target);camdata.ortho_scale=scale
    scene.render.filepath=str(HERE/(name+'.png'));bpy.ops.render.render(write_still=True)


