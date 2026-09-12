"""Reproducible SiteWise art-direction scene; source GLB remains untouched."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'source-import.blend'))
scene = bpy.context.scene
inventory = json.loads((ROOT / 'model-inventory.json').read_text())
rows = {r['name']: r for r in inventory}

def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = 0.82
    return mat

chalk = material('Chalk | architectural fabric', (0.79, 0.80, 0.77))
glass = material('Mineral grey | glazing', (0.32, 0.39, 0.40))
ground = material('Paper | site', (0.63, 0.65, 0.62))
graphite = material('Graphite | drawing lines', (0.24, 0.29, 0.29))
amber = material('Amber | coordination question', (0.85, 0.32, 0.055))

def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

collections = {k: collection(k) for k in ['01 Site', '02 Substructure', '03 Floor plates',
    '04 Walls', '05 Envelope', '06 Roof', '07 Fit-out', '08 Hydraulic fixtures',
    '09 Context — hidden', '10 Drawing field', '11 Hydraulic — illustrative',
    '12 Electrical — illustrative', '13 Mechanical — illustrative', '14 Decisions — illustrative']}

def group_for(r):
    n = r['name'].lower()
    mats = ' '.join(r['materials']).lower()
    if any(s in n for s in ['grass model', 'tree model', 'palmtree', 'girl', 'guy ', 'telsa', 'jeep', 'car ford', 'hedge model']):
        return '09 Context — hidden'
    if any(s in n for s in ['basin ', 'wc 24', 'sink ', 'shower ', 'roof_downpipe', 'washingmachine']):
        return '08 Hydraulic fixtures'
    if 'roof covering' in n or n.startswith('rt -'):
        return '06 Roof'
    if 'concrete_-_foundation' in mats:
        return '02 Substructure'
    if any(s in mats for s in ['earth_', 'grass_', 'pavement_']) or '0 SITE' in r['parents']:
        return '01 Site'
    if n.startswith('sla -'):
        return '03 Floor plates' if r['max'][0]-r['min'][0] > 2 and r['max'][1]-r['min'][1] > 2 else '07 Fit-out'
    if n.startswith('sw -'):
        return '04 Walls'
    if n.startswith(('wd -', 'doo -', 'polygonal')) or 'wall covering' in n:
        return '05 Envelope'
    return '07 Fit-out'

core = [r for r in inventory if group_for(r) in ['04 Walls', '06 Roof']]
low = Vector(tuple(min(r['min'][i] for r in core) for i in range(3)))
high = Vector(tuple(max(r['max'][i] for r in core) for i in range(3)))
center = (low + high) / 2
center.z = 0
print('CORE_BOUNDS', list(low), list(high), flush=True)
for obj in list(scene.objects):
    if obj.type != 'MESH':
        continue
    r = rows[obj.name]
    matrix = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = matrix
    obj.location -= center
    key = group_for(r)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collections[key].objects.link(obj)
    obj['source_name'] = r['name']
    obj['provenance'] = 'Supplied architectural GLB; classification inferred from names/materials'
    obj['system'] = key
    obj.data.materials.clear()
    obj.data.materials.append(glass if any('Glass' in m for m in r['materials']) else ground if key == '01 Site' else chalk)
    if key == '09 Context — hidden':
        obj.hide_render = True
        obj.hide_set(True)
for obj in list(scene.objects):
    if obj.type == 'EMPTY':
        bpy.data.objects.remove(obj, do_unlink=True)

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world = bpy.data.worlds.new('Warm studio')
scene.world.color = (0.8, 0.8, 0.8)
shade = scene.display.shading
shade.light = 'STUDIO'
shade.studiolight_rotate_z = 0.4
shade.color_type = 'MATERIAL'
shade.show_shadows = True
shade.show_cavity = True
shade.cavity_type = 'BOTH'
shade.curvature_ridge_factor = 1.2
shade.curvature_valley_factor = 1.0
shade.show_object_outline = False
shade.background_type = 'WORLD'
scene.world.color = (0.87, 0.87, 0.84)
scene.view_settings.view_transform = 'Standard'

def camera(name, direction, scale):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    target = Vector((0, 0, 3))
    obj.location = target + Vector(direction)
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'
    data.ortho_scale = scale
    return obj

span = max(high.x-low.x, high.y-low.y)
scene.camera = camera('Camera | coordination hero', (40, -55, 42), span*1.35)
scene.render.filepath = str(OUT / '01-camera-a.png')
bpy.ops.render.render(write_still=True)
scene.camera = camera('Camera | reverse study', (-40, -55, 42), span*1.35)
scene.render.filepath = str(OUT / '02-camera-b.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'sitewise-coordination.blend'))
