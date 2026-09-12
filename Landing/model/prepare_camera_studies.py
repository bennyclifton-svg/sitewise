"""Stage 2: clean studio camera studies, with no invented building systems."""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-coordination.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 1500
scene.render.resolution_y = 1125
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.90, 0.92, 0.95, 1)
background.inputs['Strength'].default_value = 0.35

for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    shader = mat.node_tree.nodes.get('Principled BSDF')
    if shader is None:
        continue
    color = None
    if mat.name.startswith('Chalk'):
        color = (0.82, 0.81, 0.77, 1)
    elif mat.name.startswith('Paper'):
        color = (0.73, 0.73, 0.70, 1)
    elif mat.name.startswith('Mineral'):
        color = (0.36, 0.41, 0.42, 1)
    if color:
        shader.inputs['Base Color'].default_value = color
        mat.diffuse_color = color

# Large surroundings obscure the project's silhouette and are not the site boundary.
hidden_context = []
for obj in list(scene.objects):
    if obj.type != 'MESH' or obj.hide_render:
        continue
    corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    width = max(p.x for p in corners)-min(p.x for p in corners)
    depth = max(p.y for p in corners)-min(p.y for p in corners)
    midpoint = sum(corners, Vector()) / len(corners)
    outside_fragment = obj.name.startswith(('SLA -', 'TR -')) and abs(midpoint.y) > 17.5
    if width > 38 or depth > 45 or outside_fragment:
        obj.hide_render = True
        obj.hide_set(True)
        hidden_context.append(obj.name)

studio = bpy.data.collections.new('00 Studio | art direction only')
scene.collection.children.link(studio)
mat = bpy.data.materials.new('Studio | warm paper')
mat.use_nodes = True
mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0.87, 0.85, 0.81, 1)
mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = 1
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -1.13))
plane = bpy.context.object
plane.name = 'Studio ground | not survey geometry'
plane.data.materials.append(mat)
for c in list(plane.users_collection):
    c.objects.unlink(plane)
studio.objects.link(plane)

def area(name, position, power, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    studio.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector((0, 0, 3)) - obj.location).to_track_quat('-Z', 'Y').to_euler()

area('Key | broad north light', (3, -20, 32), 11000, 14)
area('Fill | soft reflected light', (-24, 0, 18), 3500, 20)
area('Rim | roof separation', (10, 22, 26), 8000, 18)

def render(name, camera_name):
    scene.camera = bpy.data.objects[camera_name]
    scene.camera.data.ortho_scale = 45
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)

scene['stage'] = '02 Camera and material review; no services added'
scene['source_credit'] = 'MyStudioNZ / Sketchfab / CC BY 4.0; materials and presentation modified'
scene['hidden_oversized_context'] = ', '.join(hidden_context)
render('03-chalk-a.png', 'Camera | coordination hero')
render('04-chalk-b.png', 'Camera | reverse study')
scene.camera = bpy.data.objects['Camera | coordination hero']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
            area.spaces.active.shading.type = 'MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'sitewise-camera-review.blend'))
print('CAMERA_STUDIES_COMPLETE', flush=True)
