"""Assemble isolated v3 discipline modules into one registered, editable scene."""
import bpy
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
REPO = OUT.parents[2]
WEB = REPO / 'frontend/public/landing-assets/coordination'
ANGLE = math.atan2(.16053, .98703)
ROTATE = Matrix.Rotation(ANGLE, 4, 'Z')


def linear(colour):
    values = [int(colour[i:i+2], 16)/255 for i in (1, 3, 5)]
    return [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]


def material(name, colour, alpha=1, emission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    rgb = linear(colour)
    m.diffuse_color = (*rgb, alpha)
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = .74
    shader.inputs['Alpha'].default_value = alpha
    shader.inputs['Emission Color'].default_value = (*rgb, 1)
    shader.inputs['Emission Strength'].default_value = emission
    if alpha < 1:
        m.surface_render_method = 'DITHERED'
        shader.inputs['Roughness'].default_value = .12
    return m


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_scene():
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-interior-checkpoint.blend'))
    scene = bpy.data.scenes['01 | Assembled interior']
    bpy.context.window.scene = scene
    keep = [o for o in scene.objects if o.visible_get() and not o.hide_render and o.type in ('MESH', 'CURVE')
            and not any(c.name.startswith(('00 Studio', 'ARCHIVE', 'STRUCTURE')) for c in o.users_collection)]
    worlds = {o: o.matrix_world.copy() for o in scene.objects}
    for obj in scene.objects:
        obj.parent = None
        obj.matrix_world = ROTATE @ worlds[obj]
    inventory = {r['name']: r for r in json.loads((OUT.parent / 'model-inventory.json').read_text())}
    chalk = material('V3 | Chalk architecture', '#F9F7F3')
    glass = material('V3 | Clear glazing', '#BAE1EC', .20)
    metal = material('V3 | Mineral metal', '#A8A8A8')
    appliance = material('V3 | Appliance face', '#3A3A3A')
    light = material('V3 | Luminaire face', '#F9F7F3', emission=.6)
    counts = defaultdict(int)
    for obj in list(scene.objects):
        if obj not in keep:
            obj.hide_render = True
            continue
        source = obj.get('source_name', '')
        original = inventory.get(source, {})
        ground_fence = source.startswith(('BALUSTER - 001','POST - 001','INNER POST - 001','RAIL - 001','RAIL CONNECTION - 001')) and 'Ground FLoor.003' in original.get('parents', []) and original.get('max', [0,0,99])[2] < 2.7
        if ground_fence or obj.get('system') == '01 Site' or source.startswith(('Post-Box', 'Rubish Bin')):
            obj.hide_render = True
            obj.hide_set(True)
            counts['suppressed_site_objects'] += 1
            continue
        obj['sw_system'] = 'architecture'
        obj['sw_label'] = source or obj.name
        mat = chalk
        if 'Glass' in source or 'glass-material' in source:
            mat = glass
            obj['sw_glass'] = True
            counts['clear_glazing_meshes'] += 1
        elif 'Metal - Stainless' in source:
            mat = metal
        if any(c.name.startswith(('CHECKPOINT 02 | Luminaires', 'CHECKPOINT 03 | General power')) for c in obj.users_collection) or obj.name.startswith(('GPO-', 'G01 |', 'G02 |')):
            obj['sw_system'] = 'electrical'
        if obj.name.startswith(('SW Asset Fridge', 'SW Asset Oven', 'Microwave', 'Induction')):
            obj['sw_system'] = 'electrical'
            mat = appliance if any(t in obj.name.lower() for t in ('black','glass','display','hob')) else chalk
        if any(t in obj.name.lower() for t in ('emitter','diffuser','task strip')):
            mat = light
        obj.data = obj.data.copy()
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        if obj.type == 'MESH':
            for face in obj.data.polygons:
                face.material_index = 0
        counts['retained_base_objects'] += 1
    scene['v3_coordinate_contract'] = 'Registered XY: Rz(atan2(.16053,.98703)) applied once to the rich interior. Front Y=-22.'
    bpy.context.view_layer.update()
    return scene, dict(counts)


def finish_materials(scene):
    chalk = material('V3 | Default chalk', '#F9F7F3')
    glazing = material('V3 | Default clear glazing', '#F9F7F3', .20)
    luminous = material('V3 | Default luminous chalk', '#F9F7F3', emission=.6)
    for obj in scene.objects:
        if obj.hide_render or obj.type not in ('MESH', 'CURVE') or not obj.get('sw_system'):
            continue
        mat = glazing if obj.get('sw_glass') else luminous if any(t in obj.name.lower() for t in ('emitter','diffuser','task strip')) else chalk
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        if obj.type == 'MESH':
            for face in obj.data.polygons:
                face.material_index = 0


def setup_scene(scene):
    ground = material('V3 | Petrol ground', '#12606D')
    bpy.ops.mesh.primitive_plane_add(size=4000, location=(0,0,-.14))
    plane = bpy.context.object
    plane.name = 'V3 | Context earth plane'
    plane.data.materials.append(ground)
    plane['sw_system'] = 'context'
    context = json.loads((OUT / 'perspective-context.json').read_text())
    data = bpy.data.curves.new('V3 | Cadastral field', 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = .016
    data.bevel_resolution = 0
    for a, b in context['context_segments']:
        spline = data.splines.new('POLY')
        spline.points.add(1)
        for point, (x,y) in zip(spline.points, (a,b)):
            point.co = (x,y,-.09,1)
    lines = bpy.data.objects.new('V3 | Shared cadastral boundaries', data)
    scene.collection.objects.link(lines)
    lines['sw_system'] = 'context'
    data.materials.append(material('V3 | White map lines', '#F9F7F3', emission=.5))
    for name, position, power, size in [('key',(-25,-35,42),19000,12),('fill',(25,-5,25),10000,20),('rear',(-10,35,30),11000,16)]:
        light = bpy.data.lights.new('V3 | '+name, 'AREA')
        light.energy = power
        light.shape = 'DISK'
        light.size = size
        obj = bpy.data.objects.new(light.name, light)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (Vector((0,-2,3))-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs[0].default_value = (*linear('#93CEDD'),1)
        bg.inputs[1].default_value = .5
    camera_data = bpy.data.cameras.new('V3 | Front and garage perspective')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = (-49,-39,23)
    target = Vector((0,-3,2))
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.lens = 32
    camera_data.clip_end = 1500
    scene.camera = camera
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1320
    scene.render.resolution_percentage = 100
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    return {'position': list(camera.location), 'target': list(target), 'lens': camera_data.lens}


def main():
    scene, base_counts = base_scene()
    reports = {}
    for name in ('fitout_revision', 'site_structure', 'wet_services', 'electrical'):
        print('V3_BUILD_MODULE', name, flush=True)
        reports[name] = load_module(name).build(scene)
        suppression = set(reports[name].get('suppress_source_names', []))
        for obj in scene.objects:
            if obj.get('source_name') in suppression and not obj.name.startswith('V3'):
                obj.hide_render = True
                obj.hide_set(True)
    finish_materials(scene)
    camera = setup_scene(scene)
    scene['scope'] = 'Illustrative coordination: one detailed dwelling, shared site and street services. Not an engineered design.'
    report = {'base':base_counts,'modules':reports,'camera':camera,'rotation_radians':ANGLE,'scope':scene['scope']}
    (HERE/'integration.json').write_text(json.dumps(report, indent=2, default=str))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'sitewise-integrated-v3.blend'))
    print('V3_MASTER_READY', flush=True)
    if '--render' in sys.argv:
        scene.render.filepath = str(OUT/'23-integrated-development.png')
        bpy.ops.render.render(write_still=True)
    if '--export' in sys.argv:
        load_module('export_web').export(scene)


if __name__ == '__main__':
    main()
