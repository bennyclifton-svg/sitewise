"""Render disposable review views from the saved facade checkpoint."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-premium-v11.blend'))
scene=bpy.context.scene
for obj in scene.objects:
    if obj.type=='LIGHT' or obj.get('sw_system')=='context':
        obj.hide_render=True
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value=(.32,.38,.48,1)
bg.inputs['Strength'].default_value=.35

def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

for name,loc,power,size in [('Key',(-18,-20,30),10000,10),('Fill',(-10,22,20),4500,12),('Rear',(20,-12,25),7000,14)]:
    data=bpy.data.lights.new('Premium Review '+name,'AREA')
    data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj)
    obj.location=loc;aim(obj,(0,0,4))
camdata=bpy.data.cameras.new('Premium review camera')
cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO'
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
views=[('premium-overview',(-34,-31,22),(-.4,0,4),34),
       ('premium-front-detail',(-23,-22,14),(-3,-10.9,4.4),14),
       ('premium-rear',(30,25,20),(2,1,4),34),
       ('premium-window-detail',(-14,-16,10),(-4.8,-11.08,7.35),4.3)]
if '--draft' in sys.argv:
    views=views[:2];scene.cycles.samples=12
    scene.render.resolution_percentage=70
for name,pos,target,scale in views:
    cam.location=pos;aim(cam,target);camdata.ortho_scale=scale
    scene.render.filepath=str(HERE/(name+'.png'))
    bpy.ops.render.render(write_still=True)
