"""Plan review of the corrected kitchen within the source room walls."""
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'fitout-revision-review.blend'))
scene = bpy.context.scene
for obj in scene.objects:
    if obj.type == 'LIGHT':
        obj.hide_render = True
    if obj.type not in ('MESH', 'CURVE') or obj.hide_render:
        continue
    if obj.name.startswith('V3 | Electrical |'):
        obj.hide_render = True
        continue
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    centre = sum(points, Vector()) / 8
    if centre.y < -14.5 or centre.y > -7.8 or min(p.z for p in points) >= 5.60 or max(p.z for p in points) < 3.15:
        obj.hide_render = True
for name, location, energy in [('Ceiling wash', (3, -10, 11), 1000), ('Soft fill', (-2, -15, 9), 700)]:
    data = bpy.data.lights.new('Kitchen revision ' + name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = 5
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((3.5, -11.2, 3.4)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value = (.15, .21, .22, 1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value = .35
camera = scene.camera
camera.location = (3.3, -11.2, 16)
camera.rotation_euler = (Vector((3.3, -11.2, 3.4)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 6.5
camera.data.dof.use_dof = False
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.filepath = str(HERE / 'fitout-revision-plan.png')
bpy.ops.render.render(write_still=True)
