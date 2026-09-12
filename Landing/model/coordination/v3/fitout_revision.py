"""Fit the complete kitchen inside the real room without changing architecture."""
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
KITCHEN_PREFIXES = ('Kitchen source |', 'SW Asset Fridge |', 'SW Asset Oven |',
                    'Microwave |', 'Induction cooktop |', 'Induction zone ', 'Range hood |')
FURNITURE_PREFIXES = ('Coffee Table 04 24 - FU - 056', 'Dining Table Rectangle 24 - FU - 058',
                      'Sofa Bed L-Shape 24 - FU - 056', 'double bed white - FU - 056',
                      'double bed white - FU - 091')


def _system(name):
    if name == 'Kitchen source | Object_8':
        return 'mechanical'
    if name.startswith(('SW Asset Fridge |', 'SW Asset Oven |', 'Induction cooktop |',
                        'Induction zone ', 'Range hood |')):
        return 'electrical'
    if name.startswith('Microwave |') and name != 'Microwave | tower infill':
        return 'electrical'
    return 'interiors'


def _points(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def _bounds(points):
    return ([min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)])


def _bvh(obj):
    return BVHTree.FromPolygons(_points(obj), [list(p.vertices) for p in obj.data.polygons], all_triangles=False)


def build(scene):
    if scene.get('sw_kitchen_revision'):
        raise RuntimeError('Kitchen revision already applied; rebuild from the registered base.')
    kitchen = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render
               and o.name.startswith(KITCHEN_PREFIXES)]
    if len(kitchen) < 30:
        raise RuntimeError('The complete fitted kitchen is required for the room-envelope revision.')
    north = scene.objects.get('SW - 574_Wall white plaster_0.006')
    east = scene.objects.get('SW - 575_Wall white plaster_0.008')
    south = scene.objects.get('SW - 576_Wall white plaster_0.009')
    if not all((north, east, south)):
        raise RuntimeError('The actual living-level room walls are required for the kitchen revision.')
    north_lo, north_hi = _bounds(_points(north))
    east_lo, east_hi = _bounds(_points(east))
    south_lo, south_hi = _bounds(_points(south))
    if abs(north_hi[1] - north_lo[1]) > .2 or abs(east_hi[0] - east_lo[0]) > .2:
        raise RuntimeError('Apply the confirmed source-to-site rotation before the kitchen revision.')
    clearance = .02
    before_points = [p for obj in kitchen for p in _points(obj)]
    before_lo, before_hi = _bounds(before_points)
    delta = Vector((min(0, east_lo[0] - clearance - before_hi[0]),
                    min(0, north_lo[1] - clearance - before_hi[1]), 0))
    transform = Matrix.Translation(delta)
    unchanged = {o: o.matrix_world.copy() for o in scene.objects if o not in kitchen}
    changed = []
    for obj in kitchen:
        before = obj.matrix_world.copy()
        obj.matrix_world = transform @ before
        obj['sw_system'] = _system(obj.name)
        obj['sw_label'] = obj.name
        obj['sw_fitout_revision'] = 'Kitchen assembly fitted inside north/east room faces'
        obj['sw_fitout_delta_world'] = list(delta)
        changed.append({'object': obj.name, 'source_asset': obj.get('source_asset', 'authored or adapted fitting'),
                        'delta_world': list(delta), 'matrix_before': [list(row) for row in before],
                        'matrix_after': [list(row) for row in obj.matrix_world]})
    bpy.context.view_layer.update()
    after_points = [p for obj in kitchen for p in _points(obj)]
    after_lo, after_hi = _bounds(after_points)
    if after_hi[0] > east_lo[0] - clearance + .00001 or after_hi[1] > north_lo[1] - clearance + .00001:
        raise RuntimeError('Kitchen still exceeds the actual north/east room faces.')
    if after_lo[1] < south_hi[1] or after_lo[2] < north_lo[2] - .001 or after_hi[2] > north_hi[2] + .001:
        raise RuntimeError('Kitchen translation does not fit the room floor/ceiling/south envelope.')

    collisions = []
    kitchen_bounds = {o: _bounds(_points(o)) for o in kitchen if len(o.data.vertices)}
    for wall in scene.objects:
        if wall.type != 'MESH' or wall.hide_render or not wall.get('source_name', '').startswith('SW -'):
            continue
        lo, hi = _bounds(_points(wall))
        if any(hi[i] < after_lo[i] or lo[i] > after_hi[i] for i in range(3)):
            continue
        wall_tree = _bvh(wall)
        for obj, (obj_lo, obj_hi) in kitchen_bounds.items():
            if any(obj_hi[i] < lo[i] or obj_lo[i] > hi[i] for i in range(3)):
                continue
            overlaps = _bvh(obj).overlap(wall_tree)
            if overlaps:
                collisions.append({'kitchen_object': obj.name, 'wall_source': wall.get('source_name', wall.name),
                                   'triangle_pairs': len(overlaps)})

    fitted = scene.objects['Kitchen source | Object_54']
    sink_local = [v.co for v in fitted.data.vertices if 2.0 < v.co.x < 2.9 and -.65 < v.co.y < .01 and .72 < v.co.z < 1.4]
    if not sink_local:
        raise RuntimeError('Sink source component was not found after the rigid kitchen move.')
    sink = [fitted.matrix_world @ p for p in sink_local]
    sink_z = min(p.z for p in sink)
    drain_points = [p for p in sink if p.z < sink_z + .015]
    drain_lo, drain_hi = _bounds(drain_points)
    sink_drain = [(drain_lo[0] + drain_hi[0]) / 2, (drain_lo[1] + drain_hi[1]) / 2, drain_lo[2] - .01]
    hood_local = [v.co for v in fitted.data.vertices if .8 < v.co.x < 1.35 and -.25 < v.co.y < .01 and v.co.z > 1.65]
    hood = [fitted.matrix_world @ p for p in hood_local]
    hood_top_z = max(p.z for p in hood)
    hood_top = [p for p in hood if p.z > hood_top_z - .015]
    hood_lo, hood_hi = _bounds(hood_top)
    hood_port = [(hood_lo[0] + hood_hi[0]) / 2, (hood_lo[1] + hood_hi[1]) / 2, hood_hi[2] + .01]
    furnishings = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render and (
        o.name.startswith('SW Curtain |') or o.get('source_name', '').startswith(FURNITURE_PREFIXES))]
    for obj in furnishings:
        obj['sw_system'] = 'interiors'
        obj['sw_label'] = obj.name
    metadata = {'revision': 'Kitchen inside actual room', 'clearance_m': clearance,
                'delta_world': list(delta), 'scale_changed': False,
                'changed_objects': changed, 'bounds_before': {'min': before_lo, 'max': before_hi},
                'bounds_after': {'min': after_lo, 'max': after_hi},
                'room_faces': {'north_y': north_lo[1], 'east_x': east_lo[0], 'south_y': south_hi[1],
                               'floor_z': north_lo[2], 'ceiling_z': north_hi[2]},
                'room_source_ids': [north.name, east.name, south.name],
                'ports': {'sink_drain': sink_drain, 'hood_extract': hood_port},
                'kitchen_placement_matrix': [list(row) for row in fitted.matrix_world],
                'interior_object_names': sorted(o.name for o in [*kitchen, *furnishings] if o.get('sw_system') == 'interiors'),
                'retained_furniture_source_names': sorted(o.get('source_name') for o in furnishings if o.get('source_name')),
                'retained_furniture_object_names': sorted(o.name for o in furnishings if o.get('source_name')),
                'appliance_object_names': sorted(o.name for o in kitchen if o.get('sw_system') == 'electrical'),
                'mechanical_object_names': sorted(o.name for o in kitchen if o.get('sw_system') == 'mechanical'),
                'shared_sink_and_hood_source_objects': ['Kitchen source | Object_54'],
                'audit': {'non_kitchen_transforms_unchanged': all(max(abs(o.matrix_world[i][j] - m[i][j])
                           for i in range(4) for j in range(4)) < .00001 for o, m in unchanged.items()),
                          'north_clearance_m': north_lo[1] - after_hi[1],
                          'east_clearance_m': east_lo[0] - after_hi[0],
                          'wall_geometry_overlaps': collisions,
                          'local_mesh_data_unchanged': True},
                'notes': ['Every imported cabinet/appliance and authored hob, microwave and hood light received one identical translation.',
                          'Existing architecture, ceiling lights and dining pendants remain fixed.',
                          'Service ports follow the current fitted source matrix; no stale placement coordinates are used.']}
    if collisions:
        raise RuntimeError(f'Kitchen intersects actual wall geometry after revision: {collisions[:3]}')
    scene['sw_kitchen_revision'] = 'north/east envelope correction'
    scene['sw_kitchen_delta_world'] = list(delta)
    (HERE / 'fitout-revision-audit.json').write_text(json.dumps(metadata, indent=2))
    return metadata
