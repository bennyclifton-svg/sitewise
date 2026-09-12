"""A temporary in-situ electrical review render; does not overwrite the blend."""
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'electrical-review.blend'))
scene = bpy.context.scene
ghost = bpy.data.materials.new('Electrical review only | architectural context')
ghost.use_nodes = True
nodes = ghost.node_tree.nodes
surface = nodes.get('Principled BSDF')
surface.inputs['Base Color'].default_value = (.66, .72, .73, 1)
surface.inputs['Roughness'].default_value = .85
transparent = nodes.new('ShaderNodeBsdfTransparent')
mix = nodes.new('ShaderNodeMixShader')
mix.inputs[0].default_value = .13
ghost.node_tree.links.new(transparent.outputs[0], mix.inputs[1])
ghost.node_tree.links.new(surface.outputs[0], mix.inputs[2])
ghost.node_tree.links.new(mix.outputs[0], nodes.get('Material Output').inputs[0])
for obj in scene.objects:
    if obj.type == 'LIGHT':
        obj.hide_render = True
    if obj.type not in ('MESH', 'CURVE') or obj.hide_render:
        continue
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    centre = sum(points, Vector()) / 8
    near = -7 < centre.x < 6.8 and -15.5 < centre.y < -7.8
    if obj.name.startswith('V3 | Electrical |'):
        if not near:
            obj.hide_render = True
    elif obj.get('sw_system') == 'electrical':
        pass
    elif not near:
        obj.hide_render = True
    elif obj.get('source_name'):
        obj.data = obj.data.copy()
        obj.data.materials.clear()
        obj.data.materials.append(ghost)

scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value = (.035, .09, .10, 1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value = .6
for name, position, power, size in [('Key', (-9, -21, 17), 1900, 8), ('Fill', (8, -9, 13), 1400, 6)]:
    light = bpy.data.lights.new('Electrical review ' + name, 'AREA')
    light.energy = power
    light.shape = 'DISK'
    light.size = size
    obj = bpy.data.objects.new(light.name, light)
    scene.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector((0, -11, 4)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
camera = scene.camera
camera.location = (-13, -23, 13)
camera.rotation_euler = (Vector((-.3, -11.2, 4.2)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 17.0
camera.data.dof.use_dof = False
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.transparent_max_bounces = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.filepath = str(HERE / 'electrical-in-situ-review.png')
bpy.ops.render.render(write_still=True)
