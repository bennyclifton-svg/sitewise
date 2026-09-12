"""Combine the reviewed interior, GPO and structural libraries in editable scenes."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-lighting-checkpoint.blend'))
interior = bpy.context.scene
interior.name = '01 | Assembled interior'
source_transforms = {o.name: o.matrix_world.copy() for o in interior.objects if o.get('source_name')}
focus = Vector((-26, -23, 0)) - Vector((-24.757655, -11.917233, 0))
U = Vector((.98703, -.16053, 0)).normalized()
V = Vector((.16053, .98703, 0)).normalized()


def world(u, v, z):
    return focus + U*u + V*v + Vector((0, 0, z))


def append_collections(path, predicate, parent):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.collections = [name for name in src.collections if predicate(name)]
    if not dst.collections:
        raise RuntimeError(f'No expected collections found in {path.name}')
    for col in dst.collections:
        parent.children.link(col)
    return dst.collections


gpo_manifest = json.loads((OUT / 'gpo-checkpoint.json').read_text())
gpo_collections = append_collections(OUT / 'sitewise-gpo-library.blend',
                                   lambda name: name == gpo_manifest['collection'], interior.collection)
structure = bpy.data.collections.new('ARCHIVE | Superseded timber structural study')
interior.collection.children.link(structure)
structural_collections = append_collections(OUT / 'sitewise-structure-library.blend',
                                          lambda name: name.startswith('STRUCTURE'), structure)
bpy.context.view_layer.update()
interior.view_layers[0].name = 'Architecture and fitted interior'
interior.view_layers[0].layer_collection.children[structure.name].exclude = True

# Separate scene makes the frame immediately inspectable without altering source materials.
frame = bpy.data.scenes.new('ARCHIVE | Superseded timber study')
frame.world = interior.world
frame.collection.children.link(structure)
frame.collection.children.link(bpy.data.collections['00 Studio | art direction only'])
review = bpy.data.collections.new('REVIEW | Ground slab and frame camera')
frame.collection.children.link(review)
slab = next(o for o in interior.objects if o.get('source_name') == 'SLA - 007_Concrete - Foundation_0.029')
slab_copy = slab.copy()
slab_copy.name = 'Frame context | original ground slab'
slab_copy.hide_render = False
review.objects.link(slab_copy)
slab_copy['presentation_note'] = 'Linked copy of original ground slab for frame review; not a new slab'
cam_data = bpy.data.cameras.new('Camera | complete structural frame')
cam = bpy.data.objects.new('Camera | complete structural frame', cam_data)
review.objects.link(cam)
cam.location = world(-17, -19, 16)
cam.rotation_euler = (world(-.3, -.3, 4.4)-cam.location).to_track_quat('-Z', 'Y').to_euler()
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 16.2
frame.camera = cam
frame.render.engine = 'CYCLES'
frame.cycles.samples = 24
frame.cycles.use_denoising = True
frame.render.resolution_x = 1450
frame.render.resolution_y = 1150
frame.view_settings.view_transform = 'AgX'
frame.view_settings.look = 'AgX - Medium High Contrast'
frame['scope'] = 'Superseded timber study retained at user request; current direction is reinforced-concrete columns and slabs'

# Move the bedroom viewpoint inside the doorway to reveal the bed and curtain pair clearly.
bedroom_cam = bpy.data.objects['Camera | bedroom lighting checkpoint']
bedroom_cam.location = world(-2.30, -1.24, 7.40)
bedroom_target = world(-3.80, .6, 6.90)
bedroom_cam.rotation_euler = (bedroom_target-bedroom_cam.location).to_track_quat('-Z', 'Y').to_euler()
bedroom_cam.data.dof.focus_distance = (bedroom_target-bedroom_cam.location).length
interior.camera = bpy.data.objects['Camera | dining lighting checkpoint']
interior['stage'] = 'Lighting, restrained interior detail and general power checkpoint'
interior['structural_assumption'] = 'Reinforced-concrete columns and slabs; earlier timber study superseded and retained for now at user request'
interior['pending'] = 'Services/circuits, deferred reinforced-concrete structural study, unified cadastral scene, vehicle and full fly-through'
assert all(bpy.data.objects[name].matrix_world == matrix for name, matrix in source_transforms.items())

structure_manifest = json.loads((OUT / 'structure-checkpoint.json').read_text())
lighting_manifest = json.loads((OUT / 'lighting-checkpoint.json').read_text())
(OUT / 'interior-checkpoint.json').write_text(json.dumps({
    'scene': 'sitewise-interior-checkpoint.blend',
    'scenes': [interior.name, frame.name],
    'source_transforms_unchanged': len(source_transforms),
    'lighting_fixture_count': len(lighting_manifest['fixtures']),
    'gpo_count': gpo_manifest['count'],
    'gpo_collections': [c.name for c in gpo_collections],
    'structure_collections': [c.name for c in structural_collections],
    'structure_member_counts': structure_manifest['counts'],
    'structure_status': 'Superseded timber geometry retained only in an archived scene; hidden in the assembled interior',
    'current_structural_direction': 'Reinforced-concrete columns and reinforced-concrete slabs; rebuild deferred at user direction',
    'archived_roof_geometry_check': structure_manifest['roof_geometry_check'],
    'unresolved_interfaces': structure_manifest['unresolved_interfaces'],
    'detailed_manifests': ['lighting-checkpoint.json', 'gpo-checkpoint.json', 'structure-checkpoint.json'],
    'scope': 'Focus dwelling enriched within full supplied development; original source GLBs unchanged',
    'pending': ['Electrical circuits and appliance services', 'Hydraulic/mechanical routing',
                'Reinforced-concrete structural study when revisited', 'Site/utility integration',
                'Car/access study', 'Unified fly-through and website integration'],
}, indent=2))
bpy.context.window.scene = interior
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'sitewise-interior-checkpoint.blend'))
print('COMBINED_CHECKPOINT_SAVED', flush=True)
if '--no-render' not in sys.argv:
    for selected_scene, camera_name, filename in [
        (interior, 'Camera | dining lighting checkpoint', '13-dining-lighting.png'),
        (interior, bedroom_cam.name, '14-bedroom-lighting.png'),
    ]:
        bpy.context.window.scene = selected_scene
        selected_scene.camera = bpy.data.objects[camera_name]
        selected_scene.render.filepath = str(OUT / filename)
        bpy.ops.render.render(write_still=True, scene=selected_scene.name)
print('COMBINED_CHECKPOINT_COMPLETE', flush=True)
