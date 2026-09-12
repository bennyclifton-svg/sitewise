"""Replicate the approved dwelling disciplines using measured source slab/door anchors."""
import bpy
import json
import re
import sys
from collections import Counter
from pathlib import Path
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from export_web import export

SOURCE = HERE.parent / 'sitewise-premium-v11.blend'
TARGET = HERE.parent / 'sitewise-all-dwellings-v12.blend'
SYSTEMS = {'structure', 'electrical', 'mechanical', 'hydraulic'}


def bounds(obj, transform=None):
    matrix = transform if transform is not None else obj.matrix_world
    points = [matrix @ v.co for v in obj.data.vertices] if obj.type == 'MESH' else [matrix @ Vector(p) for p in obj.bound_box]
    return tuple(Vector([fn(p[i] for p in points) for i in range(3)]) for fn in (min, max))


def centre(obj):
    lo, hi = bounds(obj)
    return (lo + hi) / 2


def family(name):
    return re.sub(r'\.\d{3}$', '', name)


def transforms(scene):
    slabs = sorted((o for o in scene.objects if o.name.startswith('SLA - 007_Concrete - Foundation_0')
                    and bounds(o)[1].x - bounds(o)[0].x > 9), key=lambda o: centre(o).y)
    doors = sorted((o for o in scene.objects if o.name.startswith('DOO - 018_Paint - Titanium White')),
                   key=lambda o: centre(o).y)
    assert len(slabs) == len(doors) == 5
    base = centre(slabs[0])
    base_offset = centre(doors[0]).y - base.y
    result = []
    for i, (slab, door) in enumerate(zip(slabs, doors), 1):
        target = centre(slab)
        sign = 1 if (centre(door).y - target.y) * base_offset > 0 else -1
        matrix = Matrix.Translation(target) @ Matrix.Diagonal((1, sign, 1, 1)) @ Matrix.Translation(-base)
        error = (matrix @ centre(doors[0]) - centre(door)).length
        # Source garage openings differ by 150 mm; slabs are the registration anchors.
        assert error < .151, (i, error)
        result.append((i, matrix, dict(dwelling=i, mirrored=sign < 0, slab=slab.name,
                      garage=door.name, anchor_error_m=error, matrix=[list(r) for r in matrix])))
    return result


def local_service(obj):
    if obj.hide_render or obj.type not in ('MESH', 'CURVE') or obj.get('sw_system') not in SYSTEMS:
        return False
    lo, hi = bounds(obj)
    if lo.y < -14.8 or hi.y > -8.7:
        return False
    # Distribution boards and site feeds already exist for every dwelling.
    if re.search(r'Electrical \| DB-01 (?!main vertical)', obj.name):
        return False
    if obj.name.startswith(('V3 | WAT-feed-', 'V3 | WAT-site-', 'V3 | Dwelling ',
                            'V3 | WAT-hose-', 'V3 | Potable side hose')):
        return False
    return True


def route(scene, name, points, system, radius, material, dwelling):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 1
    data.use_fill_caps = True
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for p, xyz in zip(spline.points, points):
        p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    data.materials.append(material)
    obj['sw_system'] = system
    obj['sw_dwelling'] = dwelling
    obj['sw_illustrative'] = True
    return obj


def build():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    placements = transforms(scene)
    originals = list(scene.objects)
    scene.objects['Kitchen source | Object_54']['sw_system'] = 'hydraulic'
    templates = [o for o in originals if local_service(o)]
    # Existing source sanitary fixtures need discipline membership, not duplicate meshes.
    fixture_templates = [o for o in originals if o.type == 'MESH' and not o.hide_render
                         and o.get('sw_system') in ('architecture', 'interiors')
                         and 'SAN-fixture-' in o.get('sw_endpoint_ids', '') and o.get('source_name')]
    suppressed = json.loads((HERE/'site-structure-metadata.json').read_text())['suppress_source_names']
    slab_templates = [scene.objects[n] for n in suppressed if n.startswith('SLA -')]
    records = []
    for number, transform, record in placements:
        if number == 1:
            for obj in templates:
                obj['sw_dwelling'] = number
            record['counts'] = dict(Counter(o['sw_system'] for o in templates))
            records.append(record)
            continue
        group = bpy.data.collections.new(f'Townhouse {number} | Structure and services')
        scene.collection.children.link(group)
        copies = {}
        for src in templates:
            obj = src.copy()
            obj.parent = None
            obj.name = f'TH{number:02} | {src.name}'
            group.objects.link(obj)
            obj.matrix_world = transform @ src.matrix_world
            obj['sw_dwelling'] = number
            obj['sw_replica_source'] = src.name
            for key in ('sw_circuit_id', 'sw_route_id', 'sw_source_endpoint_id'):
                if obj.get(key):
                    obj[key] = f'TH{number:02}:' + obj[key].replace('DB-01', f'DB-{number:02}')
            if obj.get('sw_endpoint_ids'):
                obj['sw_endpoint_ids'] = json.dumps([f'TH{number:02}:{v}' for v in json.loads(obj['sw_endpoint_ids'])])
            motion = obj.get('sw_motion', '')
            if motion.startswith('rotor:'):
                _, axis, x, y, z = motion.split(':')
                pivot = transform @ Vector((float(x), -float(z), float(y)))
                obj['sw_motion'] = f'rotor:{axis}:{pivot.x}:{pivot.z}:{-pivot.y}'
            copies[src.name] = obj
        bpy.context.view_layer.update()
        hidden = []
        for src in slab_templates:
            expected = transform @ centre(src)
            candidates = [o for o in originals if family(o.name) == family(src.name) and o != src]
            match = min(candidates, key=lambda o: (centre(o)-expected).length)
            assert (centre(match)-expected).length < .25, (src.name, match.name)
            match.hide_render = True
            match.hide_set(True)
            hidden.append(match.name)
        tagged = []
        for src in fixture_templates:
            expected = transform @ centre(src)
            candidates = [o for o in originals if family(o.name) == family(src.name) and o != src and not o.hide_render]
            if candidates:
                match = min(candidates, key=lambda o: (centre(o)-expected).length)
                if (centre(match)-expected).length < .15:
                    match['sw_system'] = 'hydraulic'
                    match['sw_dwelling'] = number
                    tagged.append(match.name)
        # Preserve existing feed endpoints and bridge the transformed local riser to them.
        # Site water feeds use fixed civil elevations, whereas the rear dwellings step down.
        garage_y = centre(scene.objects[record['garage']]).y
        local_water = transform @ Vector((4.20, -10.93335, -.45))
        route(scene, f'TH{number:02} | Water feed connection', [(4.20, garage_y, -.45), tuple(local_water)],
              'hydraulic', .03, scene.objects['V3 | WAT-focus-feed'].data.materials[0], number)
        collector = transform @ Vector((6.35, -10.30, -.85))
        main_depth = -1.4 + (collector.y + 22) * .005
        route(scene, f'TH{number:02} | Shared sewer collector connection',
              [tuple(collector), (6.35, collector.y, main_depth)], 'hydraulic', .085,
              scene.objects['V3 | SAN-site-collector'].data.materials[0], number)
        riser = copies['V3 | Electrical | DB-01 main vertical service riser']
        src = scene.objects['V3 | Electrical | DB-01 main vertical service riser']
        local_board = transform @ (src.matrix_world @ Vector(src.data.splines[0].points[0].co[:3]))
        board = scene.objects[f'V3 | Electrical | DB-{number:02} dwelling distribution board']
        board_point = centre(board)
        route(scene, f'TH{number:02} | Board riser connection',
              [tuple(board_point), (board_point.x, board_point.y, local_board.z), tuple(local_board)],
              'electrical', .042, riser.data.materials[0], number)
        record.update(counts=dict(Counter(o['sw_system'] for o in copies.values())),
                      replaced_source_slabs=hidden, existing_fixtures_tagged=tagged)
        records.append(record)
    # One continuous common collector falls towards the existing street sewer.
    material = scene.objects['V3 | SAN-site-collector'].data.materials[0]
    for name in ('V3 | SAN-site-collector', 'V3 | SAN-street-branch'):
        scene.objects[name].hide_render = True
        scene.objects[name].hide_set(True)
    rear_y = max((matrix @ Vector((6.35, -10.30, -.85))).y for _, matrix, _ in placements)
    route(scene, 'Development | Shared sanitary collector',
          [(6.35, rear_y, -1.4 + (rear_y + 22)*.005), (6.35, -22, -1.4), (6.35, -27.5, -1.45)],
          'hydraulic', .085, material, 0)
    route(scene, 'TH01 | Shared sewer collector connection',
          [(6.35, -10.30, -.85), (6.35, -10.30, -1.4 + 11.7*.005)],
          'hydraulic', .085, material, 1)
    scene['sw_model_scope'] = 'Five dwellings with replicated structure, electrical, mechanical and hydraulic detail; shared site services.'
    scene['sw_dwelling_replication'] = json.dumps(records)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    (HERE/'dwelling-replication.json').write_text(json.dumps(records, indent=2))
    if '--export' in sys.argv:
        export(scene)
    print('DWELLING_REPLICATION', json.dumps(records), flush=True)


if __name__ == '__main__':
    build()
