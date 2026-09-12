"""Check roof clearance independently in the saved master and render review views."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from rebuild_paired_roofs import roof_surface, height, SOURCE, TARGET

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
original={o.name: (o.matrix_world.copy(),o.hide_render,len(o.data.vertices) if o.type=='MESH' else 0)
          for o in bpy.context.scene.objects}
bpy.ops.wm.open_mainfile(filepath=str(TARGET))
scene=bpy.context.scene
surface=roof_surface(scene)
audit=json.loads(scene['sw_roof_revision'])
hidden={name for row in audit for name in row['hidden_copied_members']}
for name,(matrix,was_hidden,count) in original.items():
    obj=scene.objects[name]
    assert obj.matrix_world==matrix, name
    assert obj.hide_render==(True if name in hidden else was_hidden),name
    if obj.type=='MESH':
        assert len(obj.data.vertices)==count,name
minimum=99
checks=0
for obj in scene.objects:
    if obj.get('sw_roof_revision')!='compound-v13':continue
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co
        gap=height(surface,p.x,p.y)-p.z
        assert gap>.035,(obj.name,gap)
        minimum=min(minimum,gap);checks+=1
    a,b=[Vector(p) for p in json.loads(obj['sw_member_endpoints'])]
    for j in range(21):
        p=a.lerp(b,j/20)
        assert height(surface,p.x,p.y)-p.z>.06,(obj.name,p)
        checks+=1
assert len(audit)==4 and all(row['trusses']==8 for row in audit)
report=dict(rebuilt_user_townhouses=[1,2,3,4], original_user_townhouse_5_unchanged=True,
            surface_checks=checks, minimum_vertex_clearance_to_tiles_m=minimum,
            preserved_original_objects=len(original), new_roof_members=sum(r['members'] for r in audit))
(HERE/'compound-roof-check.json').write_text(json.dumps(report,indent=2))
print('PASS_ROOFS',report,flush=True)
if '--render' not in sys.argv:sys.exit(0)
for obj in scene.objects:
    if obj.type=='LIGHT' or obj.get('sw_system')=='context':obj.hide_render=True
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.24,.28,.34,1);bg.inputs['Strength'].default_value=.5
def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for name,loc in [('Key',(-20,-20,30)),('Fill',(20,15,25))]:
    data=bpy.data.lights.new(name,'AREA');data.energy=11000;data.shape='DISK';data.size=12
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc;aim(obj,(0,0,4))
data=bpy.data.cameras.new('Compound roof review');data.type='ORTHO';data.ortho_scale=34
camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera)
camera.location=(-30,-29,27);aim(camera,(0,0,4));scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(HERE/'compound-roofs-envelope.png');bpy.ops.render.render(write_still=True)
for obj in scene.objects:
    if obj.type in ('MESH','CURVE') and obj.get('sw_component')!='roof':obj.hide_render=True
camera.location=(-25,-28,30);aim(camera,(0,0,8.6));data.ortho_scale=32
scene.render.filepath=str(HERE/'compound-roofs-frame.png');bpy.ops.render.render(write_still=True)
