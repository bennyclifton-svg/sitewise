"""Room lighting and one curtain set in the approved focus dwelling."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
AUDIT = OUT / 'asset-audit'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-kitchen-checkpoint.blend'))
scene = bpy.context.scene
focus = Vector((-26, -23, 0)) - Vector((-24.757655, -11.917233, 0))
U = Vector((.98703, -.16053, 0)).normalized()
V = Vector((.16053, .98703, 0)).normalized()
source_transforms = {o.name: o.matrix_world.copy() for o in scene.objects if o.get('source_name')}


def world(u, v, z):
    return focus + U*u + V*v + Vector((0, 0, z))


def collection(name):
    result = bpy.data.collections.new(name)
    scene.collection.children.link(result)
    return result


def material(name, color, emission=0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1)
    result.use_nodes = True
    shader = result.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = .8
    shader.inputs['Emission Color'].default_value = (*color, 1)
    shader.inputs['Emission Strength'].default_value = emission
    return result


fixtures = collection('CHECKPOINT 02 | Luminaires and electrical endpoints')
illumination = collection('CHECKPOINT 02 | Light sources for presentation')
furnishings = collection('CHECKPOINT 02 | Restrained furnishings')
chalk = material('Lighting | chalk trim', (.67, .68, .65))
opal = material('Lighting | warm opal diffuser', (1, .83, .61), 3)
linen = material('Furnishing | mineral linen', (.53, .57, .56))
fabric = material('Furnishing | soft chalk textile', (.70, .69, .65))
manifest = []


def move(obj, target):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)


def area_light(name, position, power, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    data.color = (1, .87, .72)
    obj = bpy.data.objects.new(name, data)
    illumination.objects.link(obj)
    obj.location = position
    obj['purpose'] = 'Presentation illumination, not a photometric design'
    return obj


def register(obj, fixture_id, room, uvz, source):
    obj['fixture_id'] = fixture_id
    obj['room'] = room
    obj['system'] = 'Electrical lighting'
    obj['service_scope'] = 'Power endpoint; circuit and switching routes pending'
    obj['provenance'] = source
    manifest.append({'id': fixture_id, 'object': obj.name, 'room': room,
                     'local_uvz': list(uvz), 'world_xyz': list(world(*uvz)),
                     'source': source, 'status': 'Illustrative luminaire placement; circuit unassigned'})


def downlight(fixture_id, room, u, v, ceiling, power=24):
    z = ceiling - .009
    p = world(u, v, z)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.070, depth=.018, location=p)
    trim = bpy.context.object
    trim.name = f'{fixture_id} | {room} | recessed trim'
    move(trim, fixtures)
    trim.data.materials.append(chalk)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.055, depth=.006,
                                      location=p - Vector((0, 0, .012)))
    diffuser = bpy.context.object
    diffuser.name = f'{fixture_id} | warm diffuser'
    move(diffuser, fixtures)
    diffuser.data.materials.append(opal)
    area_light(f'{fixture_id} | downlight illumination', p-Vector((0, 0, .025)), power, .11)
    register(trim, fixture_id, room, (u, v, ceiling), 'Authored repeatable illustrative downlight')


# Replace the initial four temporary lights with mounted fixtures and the dining pendants.
# The kitchen fitting, appliances, camera fill and task strip remain in place.
for obj in list(scene.objects):
    if obj.name.startswith(('Kitchen ceiling light', 'Kitchen downlight')):
        bpy.data.objects.remove(obj, do_unlink=True)

schedule = [
    ('G01', 'Ground entry', -4.65, -1.9, 2.92),
    ('G02', 'Ground multipurpose room', -3.35, .2, 2.92),
    ('G03', 'Ground multipurpose room', -1.6, .2, 2.92),
    ('G04', 'Ground stair approach', -.15, -1.05, 2.92),
    ('G05', 'Laundry', .47, 1.1, 2.92),
    ('G06', 'Ground bedroom', 1.85, -.8, 2.92),
    ('G07', 'Ground bedroom', 3.3, -.8, 2.92),
    ('G08', 'Ground bathroom', 1.55, 1.35, 2.92),
    ('G09', 'Ground bathroom', 3.12, 1.35, 2.92),
    ('L01', 'Kitchen preparation', 2.65, -.8, 5.64),
    ('L02', 'Kitchen preparation', 2.65, 1.25, 5.64),
    ('L03', 'Living room', -2.65, .8, 5.64),
    ('L04', 'Living room', -2.65, -.85, 5.64),
    ('L05', 'Living powder room', 3.5, -2.08, 5.64),
    ('U01', 'West bedroom', -3.7, .2, 8.39),
    ('U02', 'West bedroom', -2.5, -1.9, 8.39),
    ('U03', 'East bedroom', 2.0, -.8, 8.39),
    ('U04', 'East bedroom', 3.75, -.8, 8.39),
    ('U05', 'West ensuite', -1.5, .55, 8.39),
    ('U06', 'West ensuite', -.55, 1.35, 8.39),
    ('U07', 'East ensuite', 1.7, 1.35, 8.39),
    ('U08', 'East ensuite', 3.45, 1.35, 8.39),
    ('U09', 'Upper landing', .55, .2, 8.39),
    ('U10', 'Upper stair', .55, -1.75, 8.39),
]
for fixture_id, room, u, v, ceiling in schedule:
    downlight(fixture_id, room, u, v, ceiling,
              18 if 'bath' in room or 'ensuite' in room or 'powder' in room else 24)

library = json.loads((AUDIT / 'appliance-library.json').read_text())
for number, u in [(1, .30), (2, 1.18)]:
    asset = next(a for a in library['assets'] if a['name'] == f'SW Asset Pendant {number}')
    base_z = 4.63
    transform = Matrix.Translation(world(u, .73, base_z))
    pendant_objects = list(bpy.data.collections[asset['collection']].objects)
    for obj in pendant_objects:
        obj.matrix_world = transform
        obj.hide_render = False
        obj.hide_set(False)
        move(obj, fixtures)
        obj.data = obj.data.copy()
        # Shorten the suspension above the globe, preserving the globe's shape.
        for vertex in obj.data.vertices:
            if vertex.co.z > .40:
                vertex.co.z = .40 + (vertex.co.z-.40) * (5.64-base_z-.40)/(asset['dimensions'][2]-.40)
        obj.data.materials.clear()
        obj.data.materials.append(opal if 'Glass_' in obj.name or 'White1_' in obj.name else chalk)
    register(pendant_objects[0], f'D{number:02}', 'Dining pendants', (u, .73, 5.64),
             'interior-design.glb / DiningTable.001 pendant extract / Visthétique / CC-BY-4.0; drop adjusted')
    area_light(f'D{number:02} | dining illumination', world(u, .73, base_z-.025), 16, .24)

# A curtain pair at the actual west-bedroom window; the source sheer stays hidden.
curtain_meta = json.loads((AUDIT / 'curtain-library.json').read_text())
with bpy.data.libraries.load(str(AUDIT / 'curtain-library.blend'), link=False) as (src, dst):
    dst.collections = [name for name in src.collections if name.startswith('SW Asset Curtain')]
for col in dst.collections:
    scene.collection.children.link(col)

# The extraction manifest is read rather than inferring a size from the original apartment.
curtain_dims = curtain_meta['dimensions']
orientation = Matrix(((V.x, -U.x, 0, 0), (V.y, -U.y, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
curtain_transform = Matrix.Translation(world(-5.08, .055, 5.99)) @ orientation @ Matrix.Diagonal((2.64/curtain_dims[0], 1, 2.24/curtain_dims[2], 1))
curtain_objects = []
for col in dst.collections:
    for obj in list(col.all_objects):
        if obj.type != 'MESH':
            continue
        obj.matrix_world = curtain_transform
        is_sheer = 'sheer' in obj.name.lower() or obj.get('curtain_role') == 'sheer'
        obj.hide_render = is_sheer
        obj.hide_set(is_sheer)
        if not is_sheer:
            obj.data.materials.clear()
            obj.data.materials.append(linen if 'rail' not in obj.name.lower() else chalk)
        obj['fitted_opening'] = 'WD - 006_Paint - Glossy White_0.035'
        obj['modification'] = 'Width/drop fitted to source west-bedroom window; no opening changed'
        curtain_objects.append(obj.name)

for obj in scene.objects:
    if not obj.get('source_name') or obj.type != 'MESH':
        continue
    if not obj['source_name'].startswith(('double bed white', 'Sofa Bed L-Shape')):
        continue
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    center = sum(points, Vector())/8
    if not -2.7 < (center-focus).dot(V) < 1.95:
        continue
    if 'Metal' in obj['source_name']:
        continue
    obj.data = obj.data.copy()
    obj.data.materials.clear()
    obj.data.materials.append(fabric)
    obj['material_note'] = 'Existing source soft furnishing retained; chalk textile for lighting contrast'

assert all(bpy.data.objects[name].matrix_world == matrix for name, matrix in source_transforms.items())
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1500
scene.render.resolution_y = 1125
scene.render.resolution_percentage = 100
scene['stage'] = 'Checkpoint 02 — focus dwelling lighting and restrained interior detail'
scene['lighting_scope'] = 'Illustrative luminaire placement, not engineered illuminance/circuit design'
scene['structural_assumption'] = 'Latest user correction: reinforced-concrete columns and slabs; prior timber study superseded; structural rebuild deferred'


def camera(name, position, target, lens=23):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = world(*position)
    target_point = world(*target)
    obj.rotation_euler = (target_point-obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'PERSP'
    data.lens = lens
    data.clip_start = .03
    data.clip_end = 200
    data.dof.use_dof = True
    data.dof.focus_distance = (target_point-obj.location).length
    data.dof.aperture_fstop = 5.6
    return obj


living_camera = camera('Camera | dining lighting checkpoint', (-3.5, -1.6, 4.94), (1.05, .6, 4.40), 24)
bedroom_camera = camera('Camera | bedroom lighting checkpoint', (-2.30, -1.24, 7.40), (-3.80, .6, 6.90), 22)
scene.camera = living_camera
(OUT / 'lighting-checkpoint.json').write_text(json.dumps({
    'stage': '02 lighting and restrained furnishings',
    'base_scene': 'sitewise-kitchen-checkpoint.blend',
    'fixtures': manifest,
    'curtain_objects': curtain_objects,
    'curtain_target_opening': 'WD - 006_Paint - Glossy White_0.035',
    'source_transforms_unchanged': len(source_transforms),
    'floor_levels': [.50, 3.22, 5.94], 'ceiling_levels': [2.92, 5.64, 8.39],
    'retained_furnishings': 'Original duplex beds, sofa and dining; no full apartment import',
    'status': 'Placement study; electrical routes, switching and photometric design unassigned',
}, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'sitewise-lighting-checkpoint.blend'))
for cam, filename in ([] if '--no-render' in sys.argv else [(living_camera, '13-dining-lighting.png'), (bedroom_camera, '14-bedroom-lighting.png')]):
    scene.camera = cam
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)
print('LIGHTING_CHECKPOINT_COMPLETE', flush=True)
