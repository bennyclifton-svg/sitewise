"""Illustrative wet services and ventilation in the registered site coordinates.

Root applies the interior's registration rotation once before build(scene).
Geometry dimensions communicate routes; they are not engineered pipe/duct sizes.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector, Matrix


HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROTATION = Matrix.Rotation(math.atan2(.16053, .98703), 4, 'Z')
FOCUS = ROTATION @ Vector((-1.2423458099365234, -11.08276653289795, 0))


def _vertices(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def _bounds(points):
    return [min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]


def _tube(points, radius, sides=10):
    points = [Vector(p) for p in points]
    vertices, faces = [], []
    for i, point in enumerate(points):
        tangent = (points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]).normalized()
        reference = Vector((0, 0, 1)) if abs(tangent.z) < .95 else Vector((0, 1, 0))
        u = tangent.cross(reference).normalized()
        v = tangent.cross(u).normalized()
        vertices.extend(point + radius * (u * math.cos(j * math.tau / sides) + v * math.sin(j * math.tau / sides)) for j in range(sides))
        if i:
            for j in range(sides):
                faces.append(((i - 1) * sides + j, (i - 1) * sides + (j + 1) % sides,
                              i * sides + (j + 1) % sides, i * sides + j))
    faces.extend([tuple(reversed(range(sides))), tuple(range((len(points) - 1) * sides, len(points) * sides))])
    return vertices, faces


def build(scene):
    for obj in list(scene.objects):
        if obj.get('sw_owner') == 'wet_services':
            bpy.data.objects.remove(obj, do_unlink=True)
    palette = json.loads((OUT.parents[1] / 'design/colour-system/sitewise-colours.json').read_text(encoding='utf-8'))['primitives']
    collections, materials = {}, {}
    for subsystem, colour in [('sanitary', 'cyan-800'), ('potable', 'cyan-700'), ('rainwater', 'cyan-600'), ('ventilation', 'neutral-500'), ('exterior-chalk', 'neutral-50')]:
        name = 'V3 | Wet services | ' + subsystem
        collection = bpy.data.collections.get(name) or bpy.data.collections.new(name)
        if collection.name not in scene.collection.children:
            scene.collection.children.link(collection)
        collections[subsystem] = collection
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        rgb = [int(palette[colour]['hex'][i:i + 2], 16) / 255 for i in (1, 3, 5)]
        rgb = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
        mat.use_nodes = True
        mat.diffuse_color = (*rgb, 1)
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*rgb, 1)
        shader.inputs['Roughness'].default_value = .68
        materials[subsystem] = mat

    nodes, routes, objects, equipment, source_links = {}, [], [], [], {}

    def mesh(label, verts, faces, subsystem):
        name = 'V3 | ' + label
        data = bpy.data.meshes.new(name)
        data.from_pydata(verts, [], faces)
        data.update()
        obj = bpy.data.objects.new(name, data)
        collections[subsystem].objects.link(obj)
        data.materials.append(materials[subsystem])
        obj['sw_owner'] = 'wet_services'
        obj['sw_system'] = 'mechanical' if subsystem == 'ventilation' else 'hydraulic'
        obj['sw_subsystem'] = subsystem
        obj['sw_label'] = label
        obj['sw_illustrative'] = True
        obj['sw_underground'] = max(Vector(p).z for p in verts) < .05
        objects.append(obj.name)
        return obj

    def tube(label, points, radius, subsystem):
        verts, faces = _tube(points, radius)
        obj = mesh(label, verts, faces, subsystem)
        for polygon in obj.data.polygons:
            polygon.use_smooth = len(polygon.vertices) == 4
        return obj

    def box(label, center, size, subsystem):
        x, y, z = center
        a, b, c = [s / 2 for s in size]
        verts = [(x + dx * a, y + dy * b, z + dz * c) for dz in (-1, 1) for dy in (-1, 1) for dx in (-1, 1)]
        return mesh(label, verts, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)], subsystem)

    def node(identifier, point, subsystem, label, sources=(), role='junction'):
        point = [float(v) for v in point]
        if identifier in nodes:
            assert math.dist(nodes[identifier]['point'], point) < 1e-6
            return identifier
        names = [obj.name for obj in sources]
        nodes[identifier] = dict(id=identifier, point=point, subsystem=subsystem, label=label, role=role, source_objects=names)
        for obj in sources:
            previous = json.loads(obj.get('sw_endpoint_ids', '[]'))
            if identifier not in previous:
                previous.append(identifier)
            obj['sw_endpoint_ids'] = json.dumps(previous)
            source_links.setdefault(obj.name, []).append(identifier)
        return identifier

    def route(identifier, start, end, via=(), radius=.025, label=None, network=None):
        assert nodes[start]['subsystem'] == nodes[end]['subsystem']
        subsystem = nodes[start]['subsystem']
        points = [nodes[start]['point'], *[list(p) for p in via], nodes[end]['point']]
        points = [p for i, p in enumerate(points) if not i or math.dist(p, points[i - 1]) > 1e-7]
        assert len(points) >= 2 and all(math.isfinite(v) for p in points for v in p)
        obj = tube(label or identifier, points, radius, subsystem)
        obj['sw_route_id'] = identifier
        obj['sw_endpoint_ids'] = json.dumps([start, end])
        routes.append(dict(id=identifier, object=obj.name, label=label or identifier, subsystem=subsystem,
                           network=network or subsystem, start=start, end=end, points=points,
                           length=sum(math.dist(a, b) for a, b in zip(points, points[1:])),
                           display_radius=radius, status='Illustrative route and connection; sizing and coordination unverified'))
        return obj

    def fitting(label, point, subsystem, radius=.05):
        p = Vector(point)
        return tube(label, [p - Vector((0, 0, .045)), p + Vector((0, 0, .045))], radius, subsystem)

    sources = {obj.get('source_name', obj.name): obj for obj in scene.objects
               if obj.type == 'MESH' and not obj.hide_render and obj.get('sw_owner') != 'wet_services'}
    kitchen = scene.objects.get('Kitchen source | Object_54')
    if kitchen is None:
        raise ValueError('The fitted kitchen checkpoint is required for wet-services anchoring.')
    # Component windows are in the unchanged source mesh, so ports follow the
    # complete kitchen's fitted transform instead of its obsolete world position.
    sink_points = [kitchen.matrix_world @ v.co for v in kitchen.data.vertices
                   if 2.0 < v.co.x < 2.9 and -.65 < v.co.y < .01 and .72 < v.co.z < 1.4]
    if len(sink_points) < 100:
        raise ValueError('The fitted kitchen sink source component is missing.')
    bowl_bottom = [p for p in sink_points if p.z < min(q.z for q in sink_points) + .015]
    lo, hi = _bounds(bowl_bottom)
    sink_drain = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] - .01]
    census = json.loads((OUT / 'source-census.json').read_text(encoding='utf-8'))
    retained_downpipes = []
    for entry in census['assemblies']['named_downpipes']:
        for name in entry['source_meshes']:
            if name not in sources:
                continue
            obj = sources[name]
            obj['sw_system'] = 'hydraulic'
            obj['sw_subsystem'] = 'rainwater'
            obj['sw_label'] = 'Retained original-model rainwater downpipe'
            lo, hi = _bounds(_vertices(obj))
            retained_downpipes.append(dict(object=obj.name, bounds=[lo, hi], reused_in_place=True,
                                           nearest_dwelling=-14 < (lo[1] + hi[1]) / 2 < -8.8))
    fixtures = []
    for kind in ['toilets', 'basins', 'showers', 'laundry_sinks', 'washing_machines']:
        for entry in census['assemblies'][kind]:
            members = [sources[name] for name in entry['source_meshes'] if name in sources]
            if not members:
                continue
            ceramic = [o for o in members if 'Ceramic' in o.get('source_name', '')]
            lo, hi = _bounds([p for o in ceramic or members for p in _vertices(o)])
            center = [(lo[i] + hi[i]) / 2 for i in range(3)]
            if not -14 < center[1] < -8.8:
                continue
            level = 0 if lo[2] < 2 else 1 if lo[2] < 5 else 2
            drain = [center[0], center[1], lo[2] + .02]
            if kind == 'washing_machines':
                drain = [hi[0] - .04, hi[1], lo[2] + .62]
            water = [center[0] + .10, hi[1] - .04, lo[2] + (.95 if kind == 'showers' else .30)]
            fixtures.append(dict(id=entry['source_assembly'], kind=kind, level=level, drain=drain, water=water, sources=members))
    tap_points = [kitchen.matrix_world @ v.co for v in kitchen.data.vertices
                  if 2.0 < v.co.x < 2.9 and -.65 < v.co.y < .01 and 1.15 < v.co.z < 1.4]
    tap_lo, tap_hi = _bounds(tap_points)
    sink_water = [(tap_lo[0] + tap_hi[0]) / 2, (tap_lo[1] + tap_hi[1]) / 2, sink_drain[2] + .14]
    fixtures.append(dict(id='Fitted kitchen sink', kind='kitchen_sinks', level=1, drain=sink_drain,
                         water=sink_water, sources=[kitchen]))
    assert len(fixtures) == 14, f'Expected 14 focus wet fixtures including washer; found {len(fixtures)}'

    # The rear internal service zone fits inside every storey's measured envelope.
    # Floor branches need designed recesses/sleeves: these are routing intent,
    # not a claim that an unmodified reinforced slab accommodates pipework.
    shaft_x, shaft_y = 4.40, -9.42
    stack = [node('SAN-stack-' + str(i), (shaft_x, shaft_y, z), 'sanitary', 'Internal soil stack level connection')
             for i, z in enumerate([-.30, 3.04, 5.76])]
    for index, fixture in enumerate(fixtures):
        port = node(f'SAN-fixture-{index:02}', fixture['drain'], 'sanitary', fixture['id'] + ' waste outlet', fixture['sources'], 'fixture')
        x, y, z = fixture['drain']
        branch_z = [-.14, 3.12, 5.84][fixture['level']]
        route(f'SAN-branch-{index:02}', port, stack[fixture['level']],
              [(x, y, branch_z), (shaft_x, y, branch_z - .04)],
              .048 if fixture['kind'] == 'toilets' else .027, fixture['id'] + ' sanitary branch')
    route('SAN-stack-upper', stack[2], stack[1], radius=.055, label='Concealed upper soil stack')
    route('SAN-stack-lower', stack[1], stack[0], radius=.055, label='Concealed lower soil stack')
    collector = node('SAN-collector', (6.35, -10.30, -.85), 'sanitary', 'Underground side collector')
    boundary = node('SAN-boundary', (6.35, -22, -1.12), 'sanitary', 'Sanitary connection at front boundary', role='site-boundary')
    tie = node('SAN-street-tie', (6.35, -27.5, -1.45), 'sanitary', 'Illustrative sewer connection in street', role='street-network')
    route('SAN-stack-to-collector', stack[0], collector, [(shaft_x, shaft_y, -.85), (6.35, shaft_y, -.85)], .055)
    route('SAN-site-collector', collector, boundary, radius=.085)
    route('SAN-street-branch', boundary, tie, radius=.085)
    for side, x in [('west', -24), ('east', 24)]:
        end = node('SAN-street-' + side, (x, -27.5, -1.45), 'sanitary', 'Illustrative street sewer ' + side, role='network-extent')
        route('SAN-main-' + side, end if side == 'west' else tie, tie if side == 'west' else end, radius=.15)
    for z in [.25, 3.1, 5.85]:
        fitting('Internal soil stack access collar', (shaft_x, shaft_y, z), 'sanitary', .069)

    # Potable supplies are independent of the rainwater system, including the heater.
    water_tie = node('WAT-street-tie', (6.55, -32, -.90), 'potable', 'Illustrative potable street connection', role='street-network')
    for side, x in [('west', -24), ('east', 24)]:
        end = node('WAT-street-' + side, (x, -32, -.90), 'potable', 'Illustrative potable main ' + side, role='network-extent')
        route('WAT-main-' + side, end if side == 'west' else water_tie, water_tie if side == 'west' else end, radius=.10)
    meter_in = node('WAT-meter-in', (6.55, -21.8, .28), 'potable', 'Potable meter inlet')
    meter_out = node('WAT-meter-out', (6.55, -21.4, .28), 'potable', 'Potable meter outlet')
    boundary_water = node('WAT-boundary', (6.55, -22, -.60), 'potable', 'Potable boundary connection', role='site-boundary')
    route('WAT-street-to-boundary', water_tie, boundary_water, radius=.055)
    route('WAT-meter-entry', boundary_water, meter_in, [(6.55, -21.8, -.60)], .035)
    route('WAT-meter', meter_in, meter_out, radius=.060, label='Potable meter and isolation assembly')
    box('Potable meter enclosure', (6.55, -21.6, .29), (.30, .24, .24), 'potable')
    previous = meter_out
    dwelling_feeds = []
    for index, y in enumerate([-10.93335, -4.01305, -.71860, 7.44200, 10.73645]):
        header = node(f'WAT-site-header-{index}', (6.55, y, -.55), 'potable', f'Dwelling {index + 1} distribution junction')
        via = [(6.55, -21.4, -.55)] if index == 0 else []
        route(f'WAT-site-main-{index}', previous, header, via, .04)
        feed = node(f'WAT-dwelling-{index}', (4.20, y, -.45), 'potable', f'Dwelling {index + 1} underground water feed', role='dwelling-feed')
        route(f'WAT-feed-{index}', header, feed, [(4.20, y, -.55)], .025)
        fitting(f'Dwelling {index + 1} isolation valve', nodes[feed]['point'], 'potable')
        dwelling_feeds.append(feed)
        previous = header
    cold = [node(f'WAT-cold-level-{i}', (4.20, shaft_y, z), 'potable', 'Internal cold water floor distribution') for i, z in enumerate([-.04, 3.16, 5.88])]
    hot = [node(f'WAT-hot-level-{i}', (4.08, shaft_y, z), 'potable', 'Internal hot water floor distribution') for i, z in enumerate([.02, 3.19, 5.91])]
    route('WAT-focus-feed', dwelling_feeds[0], cold[0], [(4.20, shaft_y, -.45)], .03)
    for i in (1, 2):
        route(f'WAT-cold-riser-{i}', cold[i - 1], cold[i], radius=.03)
        route(f'WAT-hot-riser-{i}', hot[i - 1], hot[i], radius=.026)
    # The garage north-wall utility corner is clear of the actual door, wet
    # fixtures and DB-01. Equipment sits above the floor; both feeds run below it.
    garage_wall_lo, garage_wall_hi = _bounds(_vertices(sources['SW - 571_Wall white plaster_0.008']))
    heater_x, heater_y = -3.25, garage_wall_lo[1] - .42
    floor_z = garage_wall_lo[2]
    heater_bottom, heater_top = floor_z + .04, floor_z + 1.44
    heater_in = node('WAT-heater-in', (heater_x, heater_y, floor_z + .10), 'potable', 'Garage electric water heater inlet')
    heater_out = node('WAT-heater-out', (heater_x, heater_y, floor_z + 1.35), 'potable', 'Garage electric water heater outlet')
    route('WAT-heater-cold', dwelling_feeds[0], heater_in, [(4.20, heater_y, -.45), (heater_x, heater_y, -.45)], .025)
    route('WAT-heater-internal', heater_in, heater_out, radius=.12, label='Water heater storage vessel connection')
    heater_vessel = tube('Garage compact electric water heater vessel', [(heater_x, heater_y, heater_bottom), (heater_x, heater_y, heater_top)], .27, 'potable')
    heater_vessel.data.materials[0] = materials['exterior-chalk']
    heater_vessel['sw_default_material'] = 'chalk'
    heater_power = [heater_x + .28, heater_y, floor_z + .76]
    compartment = box('Garage water heater electrical service compartment', heater_power, (.12, .25, .33), 'potable')
    compartment.data.materials[0] = materials['exterior-chalk']
    heater_lo = [heater_x - .27, heater_y - .27, heater_bottom]
    heater_hi = [heater_x + .34, heater_y + .27, heater_top]
    fixture_objects = {obj for fixture in fixtures for obj in fixture['sources']}
    heater_obstacles = []
    for obj in sources.values():
        if not obj.get('source_name', '').startswith(('SW -', 'DOO -')) and obj not in fixture_objects:
            continue
        lo, hi = _bounds(_vertices(obj))
        if all(hi[i] > heater_lo[i] and lo[i] < heater_hi[i] for i in range(3)):
            heater_obstacles.append(dict(object=obj.name, bounds=[lo, hi]))
    assert not heater_obstacles, f'Garage heater intersects source wall/door/fixture bounds: {heater_obstacles}'
    route('WAT-heater-hot', heater_out, hot[0],
          [(heater_x + .28, heater_y, floor_z + 1.35), (heater_x + .28, heater_y, -.36),
           (4.08, heater_y, -.36), (4.08, shaft_y, -.36)], .026)
    equipment.append(dict(id='electric-water-heater', subsystem='potable', ports=[heater_in, heater_out], electrical_endpoint=heater_power,
                          location='Ground-floor garage north-wall utility corner',
                          vessel_bounds=[[heater_x - .27, heater_y - .27, heater_bottom], [heater_x + .27, heater_y + .27, heater_top]],
                          checked_wall_door_fixture_overlaps=heater_obstacles,
                          source_wall='SW - 571_Wall white plaster_0.008'))
    for index, fixture in enumerate(fixtures):
        for temperature, risers, dx in [('cold', cold, 0), ('hot', hot, -.075)]:
            if temperature == 'hot' and fixture['kind'] in ['toilets', 'washing_machines']:
                continue
            x, y, z = fixture['water']
            port = node(f'WAT-{temperature}-fixture-{index:02}', (x + dx, y, z), 'potable', fixture['id'] + ' ' + temperature + ' water', fixture['sources'], 'fixture')
            supply = risers[fixture['level']]
            sx, sy, sz = nodes[supply]['point']
            route(f'WAT-{temperature}-branch-{index:02}', supply, port, [(sx, y, sz), (x + dx, y, sz)], .013)
    for identifier, p, supply in [('side', (4.72, -10.50, .72), dwelling_feeds[0]), ('rear', (6.55, 15.0, .72), previous)]:
        tap = node('WAT-hose-' + identifier, p, 'potable', 'Potable ' + identifier + ' hose tap', role='hose-tap')
        route('WAT-hose-feed-' + identifier, supply, tap, [(nodes[supply]['point'][0], p[1], -.45), (p[0], p[1], -.45)], .018)
        box('Potable ' + identifier + ' hose tap handle', (p[0], p[1], p[2] + .06), (.16, .04, .035), 'potable')
        if identifier == 'rear':
            support = box('Rear hose tap mounting post', (p[0] + .06, p[1], .43), (.07, .09, .86), 'potable')
            support.data.materials[0] = materials['exterior-chalk']

    roof_objects = [o for o in sources.values() if o.get('source_name', '').startswith('RT - 024_')]

    def roof_height(x, y):
        hits = []
        for obj in roof_objects:
            inverse = obj.matrix_world.inverted()
            origin = inverse @ Vector((x, y, 15))
            direction = (inverse.to_3x3() @ Vector((0, 0, -1))).normalized()
            hit, point, normal, face = obj.ray_cast(origin, direction)
            if hit:
                hits.append((obj.matrix_world @ point).z)
        if not hits:
            raise ValueError(f'No actual roof below service outlet {(x, y)}')
        return max(hits)

    # Gutters discharge at the rear. Drops follow solid wall sections and step
    # with the west wall at the upper floor, avoiding the balcony and glazing.
    roof_points = [p for o in roof_objects for p in _vertices(o) if -14.0 < p.y < -9.0]
    low, high = _bounds(roof_points)
    front_y, back_y = low[1], high[1]
    rain_collect = node('RWT-collector', (6.22, -14.70, -.58), 'rainwater', 'Rainwater-only underground collector')
    for side, x in [('west', low[0] - .045), ('east', high[0] + .045)]:
        inside_x = x + .12 if side == 'west' else x - .12
        eave_z = roof_height(inside_x, (front_y + back_y) / 2) - .10
        far = node('RWT-gutter-' + side + '-front', (x, front_y, eave_z), 'rainwater', side + ' roof gutter front')
        outlet = node('RWT-gutter-' + side + '-rear', (x, back_y, eave_z - .025), 'rainwater', side + ' rear gutter downpipe outlet')
        obj = route('RWT-gutter-' + side, far, outlet, radius=.065, label=side.title() + ' rainwater gutter')
        # Open U-profile replaces the display tube; its centreline stays in route metadata.
        section = [(-.075, .04), (-.06, -.055), (.06, -.055), (.075, .04)]
        verts = [(x + dx, y, z + dz) for y, z in [(front_y, eave_z), (back_y, eave_z - .025)] for dx, dz in section]
        data = bpy.data.meshes.new(obj.name + ' open trough')
        data.from_pydata(verts, [], [(i, i + 1, i + 5, i + 4) for i in range(3)])
        data.materials.append(materials['exterior-chalk'])
        obj.data = data
        obj['sw_default_material'] = 'chalk'
        wall_y = FOCUS.y + 1.9451 + .048
        upper_x, lower_x = (-4.63, -3.30) if side == 'west' else (4.50, 4.50)
        bottom = node('RWT-downpipe-' + side, (lower_x, wall_y, -.42), 'rainwater', side + ' wall-mounted downpipe below ground')
        path = [(upper_x, wall_y, eave_z - .07), (upper_x, wall_y, 5.80), (lower_x, wall_y, 5.80)]
        downpipe = route('RWT-downpipe-route-' + side, outlet, bottom, path, .035,
                         label=side.title() + ' rear wall rainwater downpipe')
        downpipe.data.materials[0] = materials['exterior-chalk']
        downpipe['sw_default_material'] = 'chalk'
        downpipe['sw_mounting'] = 'Solid rear wall, 13 mm illustrative face clearance; window openings avoided'
        for z in [.85, 2.50, 4.2, 5.5, 6.75, 8.05]:
            clip_x = upper_x if z > 5.80 else lower_x
            clip = box(side.title() + ' rainwater wall clip', (clip_x, wall_y - .025, z), (.10, .065, .035), 'rainwater')
            clip.data.materials[0] = materials['exterior-chalk']
        route('RWT-downpipe-collector-' + side, bottom, rain_collect,
              [(lower_x, wall_y, -.58), (6.22, wall_y, -.58)], .045)
    filter_in = node('RWT-filter-in', (7.20, -16.9, -.64), 'rainwater', 'Rainwater pre-tank filter inlet')
    filter_out = node('RWT-filter-out', (7.48, -17.1, -.72), 'rainwater', 'Rainwater filter outlet')
    tank_in = node('RWT-tank-in', (7.60, -17.35, -.86), 'rainwater', 'Underground rainwater tank inlet')
    tank_out = node('RWT-tank-out', (8.55, -18.30, -1.82), 'rainwater', 'Rainwater tank pump suction')
    overflow = node('RWT-tank-overflow', (8.72, -17.30, -.89), 'rainwater', 'Rainwater tank high-level overflow')
    route('RWT-collector-to-filter', rain_collect, filter_in, [(6.22, -16.9, -.63)], .055)
    route('RWT-filter-link', filter_in, filter_out, radius=.065)
    route('RWT-filter-to-tank', filter_out, tank_in, radius=.055)
    box('Underground rainwater tank - separate from potable supply', (8, -18, -1.62), (2.40, 2.05, 1.65), 'rainwater')
    box('Rainwater pre-tank filter chamber', (7.35, -17.0, -.67), (.42, .42, .45), 'rainwater')
    tube('Rainwater tank maintenance access', [(8, -18, -.82), (8, -18, .045)], .23, 'rainwater')
    pump_in = node('RWT-pump-in', (9.42, -18.0, .13), 'rainwater', 'Rainwater pump inlet')
    pump_out = node('RWT-pump-out', (9.70, -18.0, .20), 'rainwater', 'Rainwater pump non-potable outlet')
    route('RWT-tank-pump', tank_out, pump_in, [(9.42, -18.30, -1.82), (9.42, -18, -1.82)], .026)
    route('RWT-pump-through', pump_in, pump_out, radius=.07)
    box('Non-potable rainwater garden pump', (9.55, -18, .18), (.40, .32, .28), 'rainwater')
    equipment.extend([dict(id='rainwater-tank', subsystem='rainwater', ports=[tank_in, tank_out, overflow]),
                      dict(id='rainwater-filter', subsystem='rainwater', ports=[filter_in, filter_out]),
                      dict(id='rainwater-pump', subsystem='rainwater', ports=[pump_in, pump_out], electrical_endpoint=[9.55, -18, .32])])
    garden_header = node('RWT-garden-header', (10.60, -16, -.34), 'rainwater', 'Non-potable garden distribution')
    route('RWT-pump-garden-header', pump_out, garden_header, [(9.70, -18, -.34), (10.60, -18, -.34)], .022)
    for identifier, y in [('near', -15.8), ('rear', 17.0)]:
        tap = node('RWT-garden-tap-' + identifier, (10.60, y, .67), 'rainwater', 'Non-potable rainwater garden tap ' + identifier, role='non-potable-tap')
        route('RWT-garden-feed-' + identifier, garden_header, tap, [(10.60, y, -.34)], .018)
        box('Rainwater-only garden tap ' + identifier, (10.60, y, .71), (.16, .045, .05), 'rainwater')
        support = box('Rainwater garden tap mounting post ' + identifier, (10.66, y, .40), (.07, .09, .80), 'rainwater')
        support.data.materials[0] = materials['exterior-chalk']
    storm_boundary = node('RWT-boundary-overflow', (7.2, -22, -1.02), 'rainwater', 'Rainwater overflow at front boundary', role='site-boundary')
    storm_tie = node('RWT-street-tie', (7.2, -25, -1.18), 'rainwater', 'Illustrative stormwater street connection', role='street-network')
    route('RWT-overflow-to-boundary', overflow, storm_boundary, [(7.2, -17.30, -.92)], .065)
    route('RWT-overflow-street-branch', storm_boundary, storm_tie, radius=.065)
    for side, x in [('west', -24), ('east', 24)]:
        end = node('RWT-street-' + side, (x, -25, -1.18), 'rainwater', 'Illustrative stormwater main ' + side, role='network-extent')
        route('RWT-street-main-' + side, end if side == 'west' else storm_tie, storm_tie if side == 'west' else end, radius=.12)

    # Room extraction terminates at actual blank wall bands above window heads.
    wall_runs = json.loads((OUT / 'structure-audit-summary.json').read_text(encoding='utf-8'))['wall_runs']
    room_specs = [
        ('ground-bath', (3.5, -10.0), 2.92, 'SW - 573_Wall white plaster_0.008', -9.95, 2.72),
        ('laundry', (1.10, -9.65), 2.92, 'SW - 571_Wall white plaster_0.008', 1.10, 2.72),
        ('living-powder', (4.25, -13.15), 5.64, 'SW - 576_Wall white plaster_0.009', 4.35, 5.43),
        ('upper-west-ensuite', (-.05, -10.1), 8.395, 'SW - 620_Wall white plaster_0.002', -.10, 8.18),
        ('upper-east-ensuite', (3.50, -10.1), 8.395, 'SW - 621_Wall white plaster_0.002', -9.95, 8.18),
    ]
    for identifier, (x, y), ceiling, wall_name, along, terminal_z in room_specs:
        wall = next(r for r in wall_runs if r['source'] == wall_name)
        normal_sign = 1 if wall['at'] > 0 else -1
        plane = wall['at'] + normal_sign * (wall['thickness'] / 2 + .035)
        terminal = (FOCUS.x + plane, along, terminal_z) if wall['axis'] == 'V' else (along, FOCUS.y + plane, terminal_z)
        port = node('MEC-room-' + identifier, (x, y, ceiling - .06), 'ventilation', identifier + ' ceiling extract', role='room-extract')
        end = node('MEC-wall-' + identifier, terminal, 'ventilation', identifier + ' exterior extract grille', [sources[wall_name]] if wall_name in sources else [], 'exterior-terminal')
        route('MEC-extract-' + identifier, port, end, [(x, y, terminal_z)], .060, network='room-extract-' + identifier)
        fitting(identifier + ' ceiling extract face', nodes[port]['point'], 'ventilation', .105)
        width = (.055, .34, .25) if wall['axis'] == 'V' else (.34, .055, .25)
        box(identifier + ' exterior grille frame', terminal, width, 'ventilation')
        for i in range(5):
            p = list(terminal)
            p[2] += -.085 + i * .0425
            p[0 if wall['axis'] == 'V' else 1] += normal_sign * .035
            size = (.04, .29, .010) if wall['axis'] == 'V' else (.29, .04, .010)
            box(identifier + f' grille louvre {i + 1}', p, size, 'ventilation')
        equipment.append(dict(id='extract-fan-' + identifier, subsystem='ventilation', ports=[port, end], electrical_endpoint=nodes[port]['point'], wall_source=wall_name))

    hood_points = [kitchen.matrix_world @ v.co for v in kitchen.data.vertices
                   if .8 < v.co.x < 1.35 and -.25 < v.co.y < .01 and v.co.z > 1.65]
    hood_top = max(p.z for p in hood_points)
    hlo, hhi = _bounds([p for p in hood_points if p.z > hood_top - .015])
    hood_port = [(hlo[0] + hhi[0]) / 2, (hlo[1] + hhi[1]) / 2, hhi[2] + .01]
    hood_sources = [kitchen]
    if scene.objects.get('Kitchen source | Object_8'):
        hood_sources.append(scene.objects['Kitchen source | Object_8'])
    hood_source = node('MEC-hood-port', hood_port, 'ventilation', 'Fitted range hood extract connection', hood_sources, 'appliance')
    hx, hy = 4.73, -9.42
    hz = roof_height(hx, hy)
    hood_exit = node('MEC-hood-roof', (hx, hy, hz + .30), 'ventilation', 'Range hood roof weather terminal', role='exterior-terminal')
    route('MEC-range-hood', hood_source, hood_exit,
          [(hood_port[0], hood_port[1], 5.52), (hx, hood_port[1], 5.52), (hx, hy, 5.52)], .065,
          label='Range hood concealed ceiling duct and internal riser', network='kitchen-extract')
    tube('Range hood weather cap', [(hx, hy, hz + .27), (hx, hy, hz + .31)], .13, 'ventilation')
    vent_x, vent_y = shaft_x, shaft_y
    vent_height = roof_height(vent_x, vent_y)
    soil_air = node('SAN-roof-vent', (vent_x, vent_y, vent_height + .30), 'sanitary', 'Soil stack roof vent - separate from room ventilation', role='air-terminal')
    route('SAN-vent', stack[2], soil_air, radius=.05)

    # Roof turbines ventilate the cavity only; they have no room-duct connection.
    for index, (x, y) in enumerate([(-2.55, -12.1), (2.75, -11.2)]):
        z = roof_height(x, y)
        inlet = node(f'MEC-cavity-{index}', (x, y, z - .28), 'ventilation', 'Roof cavity ventilation inlet', role='roof-cavity')
        outlet = node(f'MEC-turbine-{index}', (x, y, z + .42), 'ventilation', 'Roof cavity whirlybird outlet', role='exterior-terminal')
        route(f'MEC-cavity-neck-{index}', inlet, outlet, radius=.12, network=f'roof-cavity-{index}')
        flashing = [(x + dx, y + dy, roof_height(x + dx, y + dy) + .015) for dx, dy in [(-.25, -.25), (.25, -.25), (.25, .25), (-.25, .25)]]
        mesh(f'Whirlybird {index + 1} roof flashing', flashing, [(0, 1, 2, 3)], 'ventilation')
        for blade in range(14):
            angle = blade * math.tau / 14
            points = [(x + radius * math.cos(angle + twist), y + radius * math.sin(angle + twist), z + height)
                      for radius, twist, height in [(.13, 0, .12), (.235, .28, .24), (.19, .50, .40), (.055, .70, .47)]]
            tube(f'Whirlybird {index + 1} curved vane {blade + 1}', points, .020, 'ventilation')
        equipment.append(dict(id=f'roof-cavity-turbine-{index}', subsystem='ventilation', ports=[inlet, outlet], connection='Roof cavity only; no room extract connection'))

    for record in routes:
        assert record['points'][0] == nodes[record['start']]['point']
        assert record['points'][-1] == nodes[record['end']]['point']
        assert record['length'] > 0

    # Check pipe thickness against actual room-face bounds, including the
    # changing west/east alignment. Slab-zone branches use that floor's outline.
    envelopes = []
    for name, underside, walls in [
        ('ground', .30, ['SW - 571_Wall white plaster_0.006', 'SW - 573_Wall white plaster_0.008',
                        'SW - 572_Wall white plaster_0.008', 'SW - 571_Wall white plaster_0.008']),
        ('living', 3.02, ['SW - 577_Wall white plaster_0.002', 'SW - 575_Wall white plaster_0.008',
                         'SW - 576_Wall white plaster_0.009', 'SW - 574_Wall white plaster_0.006']),
        ('upper', 5.74, ['SW - 623_Wall white plaster_0.008', 'SW - 621_Wall white plaster_0.002',
                        'SW - 622_Wall white plaster_0.018', 'SW - 620_Wall white plaster_0.002'])]:
        bounds = [_bounds(_vertices(sources[w])) for w in walls]
        envelopes.append(dict(level=name, underside_z=underside,
                              inside=[bounds[0][1][0], bounds[1][0][0], bounds[2][1][1], bounds[3][0][1]],
                              wall_sources=walls))
    internal_ids = ('SAN-branch-', 'SAN-stack-upper', 'SAN-stack-lower', 'SAN-vent',
                    'WAT-cold-', 'WAT-hot-', 'WAT-focus-feed', 'WAT-heater-', 'MEC-range-hood')
    interior_samples = 0
    for record in routes:
        if not record['id'].startswith(internal_ids):
            continue
        scene.objects[record['object']]['sw_concealed'] = True
        record['placement'] = 'Within measured building outline; floor/shaft interfaces require design'
        radius = record['display_radius']
        for a, b in zip(record['points'], record['points'][1:]):
            count = max(1, math.ceil(math.dist(a, b) / .10))
            for i in range(count + 1):
                p = Vector(a).lerp(Vector(b), i / count)
                if p.z < .30:
                    continue
                envelope = next(e for e in reversed(envelopes) if p.z >= e['underside_z'])
                left, right, front, rear = envelope['inside']
                assert left + radius < p.x < right - radius and front + radius < p.y < rear - radius, \
                    f"{record['id']} outside {envelope['level']} room outline at {list(p)}"
                interior_samples += 1

    rear_wall_samples = 0
    for record in routes:
        if not record['id'].startswith('RWT-downpipe-route-'):
            continue
        for a, b in zip(record['points'][1:], record['points'][2:]):
            count = max(1, math.ceil(math.dist(a, b) / .15))
            for i in range(count + 1):
                p = Vector(a).lerp(Vector(b), i / count)
                level = next((j for j, (lo, hi) in enumerate([(.50, 2.92), (3.22, 5.64), (5.94, 8.335)])
                              if lo + .05 < p.z < hi - .05), None)
                if level is None:
                    continue
                wall = sources[envelopes[level]['wall_sources'][3]]
                inverse = wall.matrix_world.inverted()
                hit, point, normal, face = wall.ray_cast(inverse @ p,
                                                        (inverse.to_3x3() @ Vector((0, -1, 0))).normalized())
                assert hit and .03 < (wall.matrix_world @ point - p).length < .09, \
                    f"{record['id']} lacks a close solid rear wall at {list(p)}"
                rear_wall_samples += 1
    return dict(module='wet_services', coordinate_contract='Registered site XY; no module rotation',
                status='Illustrative coordination geometry; no sizing, falls, capacity or compliance certification',
                units='Imported model coordinate units; not verified metres', objects=objects,
                endpoints=list(nodes.values()), routes=routes, equipment=equipment,
                source_fixture_endpoints=source_links,
                retained_source_downpipes=retained_downpipes,
                routing_revision='Concealed internal service shafts; fitted kitchen ports; rear-wall chalk rainwater drops',
                measured_floor_envelopes=envelopes,
                fixture_count=len(fixtures), dwelling_feeds=dwelling_feeds,
                validation=dict(continuous_routes=len(routes), endpoints=len(nodes), separate_subsystems=True,
                                base_fixture_transforms_changed=0, roof_outlets_anchored_by_raycast=True,
                                internal_envelope_samples=interior_samples, rear_wall_raycast_samples=rear_wall_samples,
                                kitchen_ports_follow_current_source_transform=True,
                                garage_heater_wall_door_fixture_bounds_clear=True,
                                retained_source_downpipe_count=len(retained_downpipes)),
                pending=['Consultant verification of capacity, gradients, routes and access.',
                         'Resolve floor branch recesses, sleeves, internal shaft linings and structural interfaces.',
                         'Verify water-heater and pump electrical provisions, rainwater treatment and overflow approval.',
                         'Street network positions and connection permissions require investigation.'])
