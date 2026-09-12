"""Import and inspect the supplied kitchen asset without modifying it."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination/asset-audit'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'kitchen.glb'))
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type=='MESH']
records=[]
points=[]
for o in meshes:
    corners=[o.matrix_world@Vector(c) for c in o.bound_box]
    points+=corners
    o.data.calc_loop_triangles()
    records.append({'name':o.name,'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),
        'min':[min(p[i] for p in corners) for i in range(3)],
        'max':[max(p[i] for p in corners) for i in range(3)],
        'materials':[m.name for m in o.data.materials if m]})
lo=Vector([min(p[i] for p in points) for i in range(3)])
hi=Vector([max(p[i] for p in points) for i in range(3)])
center=(hi+lo)/2
span=max(hi-lo)
scene.world=bpy.data.worlds.new('Audit studio')
scene.world.color=(.78,.78,.76)
scene.render.engine='BLENDER_WORKBENCH'
shade=scene.display.shading
shade.light='STUDIO'
shade.color_type='MATERIAL'
shade.show_shadows=True
shade.show_cavity=True
shade.cavity_type='BOTH'
shade.background_type='WORLD'
scene.render.resolution_x=1400
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
camera_data=bpy.data.cameras.new('Audit camera')
camera=bpy.data.objects.new('Audit camera',camera_data)
scene.collection.objects.link(camera)
scene.camera=camera
camera_data.type='ORTHO'
camera_data.clip_end=span*20
camera_data.ortho_scale=span*1.3
for n,vec in [('a',(1,-1,.65)),('b',(-1,1,.65))]:
    camera.location=center+Vector(vec)*span*2
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'kitchen-{n}.png')
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'kitchen-source.blend'))
(OUT/'kitchen-inventory.json').write_text(json.dumps({'bounds_min':list(lo),'bounds_max':list(hi),
    'dimensions':list(hi-lo),'objects':records,'triangles':sum(r['triangles'] for r in records)},indent=2))
print('KITCHEN_AUDIT_COMPLETE',len(records),'meshes; bounds',list(hi-lo),flush=True)
