"""Illustrative electrical network anchored to the registered rich dwelling.

Call build(scene) after the original interior has received Rz(+atan2(.16053,
.98703)) once. This creates a service narrative, not a cable-sizing or compliance
design. It preserves every source transform and original fitting mesh.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ROTATION = Matrix.Rotation(math.atan2(.16053, .98703), 4, 'Z')
ORIGIN = ROTATION @ Vector((-1.2423458099365234, -11.08276653289795, 0))
FLOORS = {'G': .5, 'L': 3.22, 'U': 5.94}
CEILINGS = {'G': 2.92, 'L': 5.64, 'U': 8.39}
GARAGE_CENTRES = [-10.93335, -4.01305, -.71860, 7.44200, 10.73645]
SWITCH_GROUPS = [
    ('G-entry', 'Ground entry and stair', ['G01', 'G04'], 'GPO-G01'),
    ('G-multipurpose', 'Ground multipurpose', ['G02', 'G03'], 'GPO-G02'),
    ('G-laundry', 'Laundry', ['G05'], 'GPO-G05'),
    ('G-bedroom', 'Ground bedroom', ['G06', 'G07'], 'GPO-G06'),
    ('G-bathroom', 'Ground bathroom', ['G08', 'G09'], 'GPO-G08'),
    ('L-kitchen', 'Kitchen preparation', ['L01', 'L02'], 'GPO-L05'),
    ('L-living', 'Living room', ['L03', 'L04'], 'GPO-L01'),
    ('L-dining', 'Dining pendants', ['D01', 'D02'], 'GPO-L04'),
    ('L-powder', 'Living powder room', ['L05'], 'GPO-L07'),
    ('U-west-bedroom', 'West bedroom', ['U01', 'U02'], 'GPO-U01'),
    ('U-east-bedroom', 'East bedroom', ['U03', 'U04'], 'GPO-U04'),
    ('U-west-ensuite', 'West ensuite', ['U05', 'U06'], 'GPO-U07'),
    ('U-east-ensuite', 'East ensuite', ['U07', 'U08'], 'GPO-U08'),
    ('U-landing', 'Upper landing and stair', ['U09', 'U10'], 'GPO-U09'),
]


def _material(name, colour, emission=0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    rgb = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    rgb = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*rgb, 1)
    node.inputs['Roughness'].default_value = .72
    node.inputs['Emission Color'].default_value = (*rgb, 1)
    node.inputs['Emission Strength'].default_value = emission
    return mat


def _uv(point):
    return Vector((point[0] - ORIGIN.x, point[1] - ORIGIN.y, point[2]))


def _world(point):
    return Vector((point[0] + ORIGIN.x, point[1] + ORIGIN.y, point[2]))


def _tag(obj, label, circuit='', endpoint='', source=''):
    obj['sw_system'] = 'electrical'
    obj['sw_label'] = label
    obj['sw_status'] = 'Illustrative routing; consultant design and sizing unassigned'
    if circuit:
        obj['sw_circuit_id'] = circuit
    if endpoint:
        obj['sw_source_endpoint_id'] = endpoint
    if source:
        obj['sw_source_object_id'] = source


def build(scene):
    if any(o.name.startswith('V3 | Electrical |') for o in scene.objects):
        raise RuntimeError('Electrical V3 already exists; rebuild from the registered source scene.')
    lights = json.loads((ROOT / 'lighting-checkpoint.json').read_text())['fixtures']
    outlets = json.loads((ROOT / 'gpo-checkpoint.json').read_text())['outlets']
    source = {o.name: o for o in scene.objects}
    source_transforms = {o: o.matrix_world.copy() for o in scene.objects}
    missing = [r['object'] for r in lights if r['object'] not in source]
    missing += [r['root_object'] for r in outlets if r['root_object'] not in source]
    if missing:
        raise RuntimeError(f'Registered rich scene is missing {len(missing)} electrical endpoints: {missing[:4]}')
    # The GPO root is a wall anchor with no fixture geometry offset.
    reference = outlets[0]
    expected = ROTATION @ Vector(reference['world_xyz'])
    if (source[reference['root_object']].matrix_world.translation - expected).length > .01:
        raise RuntimeError('Electrical V3 requires the confirmed single source-to-site rotation.')

    envelope_sources = {
        'G': ('SW - 571_Wall white plaster_0.006', 'SW - 573_Wall white plaster_0.008',
              'SW - 572_Wall white plaster_0.008', 'SW - 571_Wall white plaster_0.008'),
        'L': ('SW - 577_Wall white plaster_0.002', 'SW - 575_Wall white plaster_0.008',
              'SW - 576_Wall white plaster_0.009', 'SW - 574_Wall white plaster_0.006'),
        'U': ('SW - 623_Wall white plaster_0.008', 'SW - 621_Wall white plaster_0.002',
              'SW - 622_Wall white plaster_0.018', 'SW - 620_Wall white plaster_0.002'),
    }
    envelopes = {}
    for level, names in envelope_sources.items():
        boxes = []
        for name in names:
            obj = source[name]
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            boxes.append(([min(p[i] for p in points) for i in range(3)],
                          [max(p[i] for p in points) for i in range(3)]))
        envelopes[level] = {'inner': [boxes[0][1][0], boxes[1][0][0], boxes[2][1][1], boxes[3][0][1]],
                            'outer': [boxes[0][0][0], boxes[1][1][0], boxes[2][0][1], boxes[3][1][1]],
                            'source_walls': names}

    collection = bpy.data.collections.new('V3 | Electrical | network and circuits')
    scene.collection.children.link(collection)
    cable = _material('V3 | Electrical | Citron service trace', '#DEDF88', .12)
    jacket = _material('V3 | Electrical | dark network cable', '#26393E')
    pole_mat = _material('V3 | Electrical | graphite poles', '#536367')
    chalk = _material('V3 | Electrical | chalk equipment', '#F9F7F3')
    detail = _material('V3 | Electrical | equipment detail', '#12606D')
    metadata = {'system': 'electrical', 'scope': 'One dwelling detailed; five individual site feeds',
                'coordinate_contract': 'Original interior rotated once by +atan2(.16053,.98703)',
                'source_rotation_radians': math.atan2(.16053, .98703),
                'focus_origin_world': list(ORIGIN), 'endpoints': [], 'switches': [],
                'circuits': [], 'routes': [], 'boards': [], 'network': {},
                'notes': ['No cable sizes, protective ratings, load diversity or compliance are asserted.',
                          'Ceiling traces represent reserved concealed electrical routes. Exact slab conduits, penetrations and wall cavities require coordinated design.',
                          'Street overhead provision and underground service position are illustrative, not verified utility records.']}

    def mesh_box(name, centre, size, material=chalk, normal=None, circuit='', endpoint='', source_id=''):
        vertices = [(x * size[0] / 2, y * size[1] / 2, z * size[2] / 2)
                    for x, y, z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),
                                    (1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
        mesh = bpy.data.meshes.new('V3 | Electrical | ' + name)
        mesh.from_pydata(vertices, [], [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
        mesh.materials.append(material)
        obj = bpy.data.objects.new(mesh.name, mesh)
        collection.objects.link(obj)
        obj.location = centre
        if normal is not None:
            # Box Y is the face normal; Z remains vertical.
            obj.rotation_euler.z = math.atan2(-normal[0], normal[1])
        _tag(obj, name, circuit, endpoint, source_id)
        return obj

    def route(name, points, radius=.018, material=cable, circuit='', endpoint='', source_id='', category='concealed'):
        clean = []
        for p in points:
            p = Vector(p)
            if not clean or (p - clean[-1]).length > .00001:
                clean.append(p)
        if len(clean) < 2:
            raise RuntimeError(f'Degenerate electrical route {name}')
        data = bpy.data.curves.new('V3 | Electrical | ' + name, 'CURVE')
        data.dimensions = '3D'
        data.resolution_u = 1
        data.bevel_depth = radius
        data.bevel_resolution = 1
        data.resolution_u = 1
        data.use_fill_caps = True
        spline = data.splines.new('POLY')
        spline.points.add(len(clean) - 1)
        for target, p in zip(spline.points, clean):
            target.co = (*p, 1)
        obj = bpy.data.objects.new(data.name, data)
        collection.objects.link(obj)
        data.materials.append(material)
        _tag(obj, name, circuit, endpoint, source_id)
        obj['sw_route_category'] = category
        row = {'object': obj.name, 'circuit': circuit, 'endpoint_id': endpoint,
               'category': category, 'points_world': [list(p) for p in clean],
               'radius_m': radius,
               'length_m': sum((b - a).length for a, b in zip(clean, clean[1:]))}
        metadata['routes'].append(row)
        return obj

    def local_route(name, points, **kwargs):
        return route(name, [_world(p) for p in points], **kwargs)

    walls = [o for o in scene.objects if o.type == 'MESH' and o.get('source_name', '').startswith('SW -') and not o.hide_render]

    def wall_mount(target, direction, limit=.8, preferred=None):
        target, direction = Vector(target), Vector(direction).normalized()
        hits = []
        for wall in ([source[preferred]] if preferred and preferred in source else walls):
            inverse = wall.matrix_world.inverted()
            hit, point, normal, _ = wall.ray_cast(inverse @ target, (inverse.to_3x3() @ direction).normalized())
            if not hit:
                continue
            point = wall.matrix_world @ point
            normal = (wall.matrix_world.to_3x3().inverted().transposed() @ normal).normalized()
            distance = (point - target).length
            if distance <= limit and abs(normal.z) < .02 and abs(normal.dot(direction)) > .98:
                if normal.dot(direction) > 0:
                    normal = -normal
                hits.append((distance, wall, point, normal))
        if not hits:
            raise RuntimeError(f'No source wall for electrical mount near {list(target)}')
        return min(hits, key=lambda row: row[0])[1:]

    def plate_fits(mount, half_width, half_height):
        wall, point, normal = mount
        tangent = Vector((-normal.y, normal.x, 0))
        for x in (-half_width, half_width):
            for z in (-half_height, half_height):
                corner = point + tangent * x + Vector((0, 0, z))
                try:
                    _, hit, _ = wall_mount(corner + normal * .12, -normal, limit=.25, preferred=wall.name)
                except RuntimeError:
                    return False
                if (hit - corner).length > .006:
                    return False
        return True

    # Two street poles support four conductors parallel to the road, with a calm sag.
    for number, x in enumerate((-18, 18), 1):
        route(f'Street pole {number}', [(x, -25, -.05), (x, -25, 7.45)], .13, pole_mat, category='street-pole')
        mesh_box(f'Pole {number} crossarm', (x, -25, 7.35), (.15, 1.22, .12), pole_mat)
        for n, offset in enumerate((-.45, -.15, .15, .45), 1):
            route(f'Pole {number} insulator {n}', [(x, -25 + offset, 7.38), (x, -25 + offset, 7.66)], .055, chalk, category='network-insulator')
    for n, offset in enumerate((-.45, -.15, .15, .45), 1):
        points = []
        for index in range(25):
            t = index / 24
            points.append((-18 + 36 * t, -25 + offset, 7.66 - .62 * 4 * t * (1 - t)))
        route(f'Street conductor {n}', points, .027, jacket, category='overhead')
    route('Pole service cable to protected riser', [(-18, -25.15, 7.66), (-18, -25.15, 6.9), (-17.83, -25, 6.9), (-17.83, -25, .1)], .04, jacket, category='pole-riser')
    route('Protected pole riser', [(-17.83, -25, -.82), (-17.83, -25, 2.8)], .065, pole_mat, category='pole-riser')
    pillar = Vector((-5, -21, .65))
    mesh_box('Site electricity pillar', pillar, (.55, .34, 1.25))
    mesh_box('Site pillar access panel', pillar + Vector((0, -.178, .03)), (.39, .018, .82), detail)
    route('Underground street service to site pillar', [(-17.83, -25, -.82), (-5, -25, -.82), (-5, -21, -.82), (-5, -21, .1)], .054, category='underground')
    metadata['network'] = {'pole_count': 2, 'overhead_conductor_count': 4,
                           'pole_centres': [[-18, -25, 0], [18, -25, 0]],
                           'pillar_world': list(pillar), 'underground_depth_m': .82,
                           'source': 'Illustrative provision, not network survey'}

    # Individual DBs mount on actual garage side walls, avoiding door apertures.
    for i, garage_y in enumerate(GARAGE_CENTRES):
        z = 1.45 if i < 3 else 1.15
        mount = None
        # Paired garages have different returns; test solid side walls instead
        # of placing a board in the source garage-door aperture.
        for x in (-4.1, -3.4, -2.8):
            for sign in (1, -1):
                try:
                    mount = wall_mount((x, garage_y + sign * 1.13, z), (0, sign, 0), limit=.8)
                    if plate_fits(mount, .205, .265):
                        break
                    mount = None
                except RuntimeError:
                    pass
            if mount:
                break
        if not mount:
            raise RuntimeError(f'No garage side-wall mount found for DB-{i + 1:02d}')
        wall, hit, normal = mount
        point = hit + normal * .066
        board_id = f'DB-{i + 1:02d}'
        board = mesh_box(board_id + ' dwelling distribution board', point, (.40, .12, .52), normal=normal)
        for j in range(5):
            mesh_box(f'{board_id} protective device {j + 1}', point + normal * .068 + Vector((-.115 + .058 * j, 0, .08)), (.035, .02, .065), detail, normal=normal)
        mesh_box(board_id + ' diagram plate', point + normal * .071 + Vector((0, 0, -.11)), (.26, .014, .05), detail, normal=normal)
        board['sw_source_object_id'] = wall.get('source_name', wall.name)
        board['sw_board_id'] = board_id
        entry = point - normal * .13
        feeder = [(-5, -21, .1), (-5, -21, -.82), (-5.2, -21, -.82),
                  (-5.2, entry.y, -.82), (entry.x, entry.y, -.82), (entry.x, entry.y, point.z), point]
        route(board_id + ' individual underground feed', feeder, .036, circuit=board_id, category='underground')
        metadata['boards'].append({'id': board_id, 'object': board.name, 'world_xyz': list(point),
                                   'host_wall_source': wall.get('source_name', wall.name),
                                   'host_surface_world': list(hit), 'normal_world': list(normal),
                                   'detail': 'all room endpoints' if i == 0 else 'site feed only'})
    board = _uv(Vector(metadata['boards'][0]['world_xyz']))
    # The living level steps inward on the west. Use the shared interior, not
    # the wider ground/upper footprint or the balcony, for the continuous riser.
    riser = (-2.90 - ORIGIN.x, -9.48 - ORIGIN.y)
    local_route('DB-01 main vertical service riser', [board, (board.x, board.y, 2.97),
                (board.x, riser[1], 2.97), (*riser, 2.97), (*riser, 8.45)], radius=.042, circuit='DB-01')

    circuits = {}
    for level, ceiling in CEILINGS.items():
        west, east, _, north = envelopes[level]['inner']
        for family, setback, z, radius in [('lighting', .14, ceiling + .04, .019), ('power', .21, ceiling + .06, .024)]:
            y = north - setback - ORIGIN.y
            cid = f'DB-01-{level}-' + ('LIGHT' if family == 'lighting' else 'GPO')
            circuits[(level, family)] = (cid, y, z)
            local_route(cid + ' west ceiling distribution', [(*riser, max(z, 2.97)), (*riser, z), (riser[0], y, z), (west + .06 - ORIGIN.x, y, z)], radius=radius, circuit=cid)
            local_route(cid + ' east ceiling distribution', [(riser[0], y, z), (east - .06 - ORIGIN.x, y, z)], radius=radius, circuit=cid)
            metadata['circuits'].append({'id': cid, 'board': 'DB-01', 'family': family,
                                         'level': level, 'endpoint_ids': []})

    circuit_rows = {r['id']: r for r in metadata['circuits']}
    def tee_x(x, level):
        west, east, _, _ = envelopes[level]['inner']
        return max(west + .06 - ORIGIN.x, min(east - .06 - ORIGIN.x, x))
    group_for_light = {light: group[0] for group in SWITCH_GROUPS for light in group[2]}
    for fixture in lights:
        fid = fixture['id']
        level = 'L' if fid.startswith('D') else fid[0]
        cid, y, z = circuits[(level, 'lighting')]
        p = Vector(fixture['local_uvz'])
        local_route(fid + ' luminaire connection', [(tee_x(p.x, level), y, z), (p.x, y, z), (p.x, p.y, z), p], circuit=cid, endpoint=fid, source_id=fixture['object'])
        for obj in scene.objects:
            if obj.name.startswith(fid + ' |') or obj.name == fixture['object'] or (fid.startswith('D') and obj.name.startswith(f'SW Asset Pendant {fid[-1]} |')):
                _tag(obj, fixture['room'] + ' luminaire', cid, fid, fixture['object'])
                obj['sw_switch_group'] = group_for_light[fid]
        circuit_rows[cid]['endpoint_ids'].append(fid)
        metadata['endpoints'].append({'id': fid, 'kind': 'luminaire', 'room': fixture['room'],
                                      'world_xyz': list(_world(p)), 'source_object': fixture['object'],
                                      'circuit': cid, 'switch_group': group_for_light[fid], 'connected': True})

    for outlet in outlets:
        oid = outlet['id']
        level = oid[4]
        cid, y, z = circuits[(level, 'power')]
        p = Vector(outlet['uvz'])
        normal = Vector(outlet['normal_uv'])
        behind = p + normal * .045
        local_route(oid + ' concealed wall drop', [(tee_x(behind.x, level), y, z), (behind.x, y, z), (behind.x, behind.y, z), behind, p], circuit=cid, endpoint=oid, source_id=outlet['host_wall_source'])
        for name in [outlet['root_object'], *outlet['objects']]:
            if name in source:
                _tag(source[name], outlet['room'] + ' double GPO', cid, oid, outlet['host_wall_source'])
        circuit_rows[cid]['endpoint_ids'].append(oid)
        metadata['endpoints'].append({'id': oid, 'kind': 'GPO', 'room': outlet['room'],
                                      'world_xyz': list(_world(p)), 'source_object': outlet['root_object'],
                                      'host_wall_source': outlet['host_wall_source'], 'circuit': cid, 'connected': True})

    by_outlet = {r['id']: r for r in outlets}
    for group_id, room, fixture_ids, host_id in SWITCH_GROUPS:
        outlet = by_outlet[host_id]
        level = group_id[0]
        candidates = [outlet] + [r for r in outlets if r['room'] == outlet['room'] and r['id'] != host_id]
        mount = None
        for host in candidates:
            normal = (ROTATION.to_3x3() @ Vector(host['normal_world'])).normalized()
            tangent = Vector((-normal.y, normal.x, 0))
            for offset in (.16, -.16, .42, -.42, .8, -.8, 1.2, -1.2):
                candidate = _world(host['uvz']) + tangent * offset
                candidate.z = FLOORS[level] + 1.20
                try:
                    mount = wall_mount(candidate + normal * .12, -normal, preferred=host['host_wall_source'], limit=.3)
                    if plate_fits(mount, .039, .059):
                        break
                    mount = None
                except RuntimeError:
                    pass
            if mount:
                break
        if not mount:
            raise RuntimeError(f'No solid source wall for switch group {group_id}')
        wall, hit, normal = mount
        sid = 'SW-' + group_id
        cid, y, z = circuits[(level, 'lighting')]
        point = hit + normal * .008
        mesh_box(sid + ' switch plate', point, (.075, .016, .115), normal=normal, circuit=cid, endpoint=sid, source_id=wall.name)
        mesh_box(sid + ' rocker', point + normal * .012, (.022, .012, .048), detail, normal=normal, circuit=cid, endpoint=sid)
        local = _uv(point)
        behind = local + Vector((normal.x, normal.y, 0)) * .05
        local_route(sid + ' switch leg', [(tee_x(behind.x, level), y, z), (behind.x, y, z), (behind.x, behind.y, z), behind, local], radius=.015, circuit=cid, endpoint=sid, source_id=wall.name)
        metadata['switches'].append({'id': sid, 'room': room, 'fixture_ids': fixture_ids, 'circuit': cid,
                                     'world_xyz': list(point), 'host_wall_source': wall.get('source_name', wall.name),
                                     'host_surface_world': list(hit), 'normal_world': list(normal)})

    # Source-local appliance connection points lie on the back/service face of the fitted assets.
    # This retained source mesh carries the whole fitted-kitchen placement;
    # service ports therefore follow the room-envelope revision automatically.
    placement = source['Kitchen source | Object_54'].matrix_world.copy()
    appliances = [
        ('INDUCTION', 'Induction cooktop', 'Induction cooktop | glass surface', (1.09, -.05, .93)),
        ('OVEN', 'Oven', 'SW Asset Oven | 01 Oven.001_Chrome_0', (.04, -1.54, .78)),
        ('MICROWAVE', 'Microwave', 'Microwave | housing', (.04, -1.54, 1.65)),
        ('FRIDGE', 'Refrigerator', 'SW Asset Fridge | 01 Refrigator.001_Aluminum.001_0', (.04, -2.16, .50)),
        ('HOOD', 'Range hood', 'Kitchen source | Object_8', (1.09, -.05, 1.67)),
    ]
    for index, (aid, label, source_id, point) in enumerate(appliances):
        if source_id not in source:
            raise RuntimeError(f'Missing fitted appliance {source_id}')
        end = placement @ Vector(point)
        p = _uv(end)
        cid = 'DB-01-AP-' + aid
        y = envelopes['L']['inner'][3] - .30 - index * .06 - ORIGIN.y
        z = CEILINGS['L'] + .055
        local_route(aid + ' dedicated appliance circuit', [(*riser, z), (riser[0], y, z),
                    (p.x, y, z), (p.x, p.y, z), p], radius=.021, circuit=cid, endpoint='AP-' + aid, source_id=source_id)
        route(aid + ' connection enclosure', [end - Vector((0, 0, .022)), end + Vector((0, 0, .022))], .037, detail, circuit=cid, endpoint='AP-' + aid, source_id=source_id, category='appliance-connection')
        _tag(source[source_id], label, cid, 'AP-' + aid, source_id)
        if aid == 'HOOD':
            source[source_id]['sw_system'] = 'mechanical'
            source[source_id]['sw_service_systems'] = json.dumps(['mechanical', 'electrical'])
        metadata['circuits'].append({'id': cid, 'board': 'DB-01', 'family': 'dedicated-appliance',
                                     'level': 'L', 'endpoint_ids': ['AP-' + aid]})
        metadata['endpoints'].append({'id': 'AP-' + aid, 'kind': 'appliance', 'room': 'Kitchen',
                                      'label': label, 'world_xyz': list(end), 'source_object': source_id,
                                      'circuit': cid, 'connected': True})

    ids = [r['id'] for r in metadata['endpoints']]
    def touches(a, b):
        for point in a:
            p = Vector(point)
            for start, end in zip(b, b[1:]):
                start, end = Vector(start), Vector(end)
                delta = end - start
                t = max(0, min(1, (p - start).dot(delta) / delta.length_squared))
                if (p - start - delta * t).length < .003:
                    return True
        return False

    main_riser = next(r for r in metadata['routes'] if r['object'].endswith('DB-01 main vertical service riser'))
    disconnected_routes = []
    for circuit in metadata['circuits']:
        pending = [r for r in metadata['routes'] if r['circuit'] == circuit['id']]
        connected = [main_riser]
        while pending:
            joined = [r for r in pending if any(touches(r['points_world'], c['points_world']) or
                       touches(c['points_world'], r['points_world']) for c in connected)]
            if not joined:
                break
            connected.extend(joined)
            pending = [r for r in pending if r not in joined]
        disconnected_routes.extend(r['object'] for r in pending)
    endpoint_error = {}
    for endpoint in metadata['endpoints']:
        route_ends = [Vector(r['points_world'][-1]) for r in metadata['routes']
                      if r['endpoint_id'] == endpoint['id'] and r['category'] == 'concealed']
        endpoint_error[endpoint['id']] = min((p - Vector(endpoint['world_xyz'])).length for p in route_ends)
    circuit_levels = {r['id']: r['level'] for r in metadata['circuits']}
    envelope_violations = []
    checked_routes = 0
    void_overruns = []
    for route_row in metadata['routes']:
        if route_row['category'] not in ('concealed', 'appliance-connection'):
            continue
        checked_routes += 1
        points, radius = route_row['points_world'], route_row['radius_m']
        for segment, (a, b) in enumerate(zip(points, points[1:])):
            for n in range(11):
                p = Vector(a).lerp(Vector(b), n / 10)
                level = circuit_levels.get(route_row['circuit'])
                if level is None:
                    level = 'U' if p.z >= 5.94 else 'L' if p.z >= 3.22 else 'G'
                # Only the final short termination may occupy its existing wall
                # lining; all distribution/riser/drop bodies stay inside faces.
                terminal = bool(route_row['endpoint_id']) and segment == len(points) - 2
                bounds = envelopes[level]['outer' if terminal else 'inner']
                west, east, south, north = bounds
                overrun = max(west - (p.x - radius), p.x + radius - east,
                              south - (p.y - radius), p.y + radius - north)
                if overrun > .001:
                    envelope_violations.append({'object': route_row['object'], 'level': level,
                        'point': list(p), 'radius_m': radius, 'overrun_m': overrun})
                    break
            level = circuit_levels.get(route_row['circuit'])
            if level in ('G', 'L') and abs(a[2] - b[2]) < .0001 and a[2] >= CEILINGS[level]:
                if a[2] + radius > CEILINGS[level] + .1 + .001:
                    void_overruns.append(route_row['object'])
    metadata['audit'] = {'luminaire_count': sum(r['kind'] == 'luminaire' for r in metadata['endpoints']),
                         'gpo_count': sum(r['kind'] == 'GPO' for r in metadata['endpoints']),
                         'dedicated_appliance_count': sum(r['kind'] == 'appliance' for r in metadata['endpoints']),
                         'switch_count': len(metadata['switches']), 'board_count': len(metadata['boards']),
                         'circuit_count': len(metadata['circuits']), 'route_count': len(metadata['routes']),
                         'duplicate_endpoint_ids': sorted({i for i in ids if ids.count(i) > 1}),
                         'unconnected_endpoints': [r['id'] for r in metadata['endpoints'] if not r['connected']],
                         'unswitched_lights': [r['id'] for r in lights if r['id'] not in group_for_light],
                         'created_object_count': len(collection.objects),
                         'missing_source_objects': [],
                         'disconnected_circuit_routes': disconnected_routes,
                         'maximum_endpoint_connection_error_m': max(endpoint_error.values()),
                         'source_transforms_unchanged': all(max(abs(o.matrix_world[i][j] - m[i][j])
                            for i in range(4) for j in range(4)) < .00001 for o, m in source_transforms.items()),
                         'wall_mount_corner_checks_passed': len(metadata['boards']) + len(metadata['switches']),
                         'floor_envelopes': envelopes,
                         'radius_checked_internal_route_count': checked_routes,
                         'radius_aware_envelope_violations': envelope_violations,
                         'ceiling_service_void_overruns': void_overruns,
                         'continuity_method': 'Each circuit route must touch its own connected distribution paths and the DB main riser; all 55 endpoint ends compared with their registered anchors.'}
    if metadata['audit']['luminaire_count'] != 26 or metadata['audit']['gpo_count'] != 24:
        raise RuntimeError('Electrical endpoint coverage changed unexpectedly.')
    if disconnected_routes or metadata['audit']['maximum_endpoint_connection_error_m'] > .003:
        raise RuntimeError(f'Electrical route continuity failed: {disconnected_routes}')
    if envelope_violations or void_overruns:
        raise RuntimeError(f'Electrical envelope failed: {envelope_violations[:4]}; void={void_overruns}')
    (HERE / 'electrical-audit.json').write_text(json.dumps(metadata, indent=2))
    scene['sw_electrical_status'] = 'Illustrative full nearest dwelling routes; electrical design unverified'
    return metadata
