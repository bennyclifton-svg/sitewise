"""Camera approach and in-situ reveal. Full architectural geometry stays assembled."""
import bpy
import bmesh
import json
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-camera-review.blend'))
scene = bpy.context.scene
study = json.loads((OUT / 'hydraulic-study.json').read_text())
center = Vector((-24.757655, -11.917233, 0))
focus = Vector(study['source_origin']) - center
source_names = {x['source_mesh'] for x in study['sections']}
census = json.loads((OUT / 'source-census.json').read_text())
fixture_names = {name for group in census['assemblies'].values() for f in group
                 if any(r['source_fixture'] == f['source_assembly'] for r in study['routes'])
                 for name in f['source_meshes']}

def reveal_material(name, color, opacity=1, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    surface = nodes.new('ShaderNodeBsdfPrincipled')
    surface.inputs['Base Color'].default_value = (*color, 1)
    surface.inputs['Roughness'].default_value = .78
    surface.inputs['Emission Color'].default_value = (*color, 1)
    surface.inputs['Emission Strength'].default_value = emission
    transparent = nodes.new('ShaderNodeBsdfTransparent')
    mix = nodes.new('ShaderNodeMixShader')
    mix.name = 'Reveal opacity'
    mix.inputs[0].default_value = opacity
    mat.node_tree.links.new(transparent.outputs[0], mix.inputs[1])
    mat.node_tree.links.new(surface.outputs[0], mix.inputs[2])
    mat.node_tree.links.new(mix.outputs[0], output.inputs['Surface'])
    return mat, mix.inputs[0]

architecture, arch_opacity = reveal_material('In situ | translucent chalk', (.77,.77,.73), .11)
roof, roof_opacity = reveal_material('In situ | translucent roof', (.77,.77,.73), .24)
blue, blue_opacity = reveal_material('In situ | provisional deep blue service accent', (.008,.035,.30), 1, .3)
amber, amber_opacity = reveal_material('In situ | open decision amber', (.95,.40,.015), 1, .3)

source_transforms = {}
edge_sources = []
axis = Vector((.16053,.98703,0)).normalized()
for obj in list(scene.objects):
    if obj.type != 'MESH' or obj.hide_render or not obj.get('source_name'):
        continue
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    span = [p.dot(axis) for p in corners]
    if min(span) >= -8 or max(span) < -15.5 or max(p.z for p in corners) < .15:
        continue
    source_transforms[obj.name] = [list(row) for row in obj.matrix_world]
    # Mesh copies prevent material changes leaking to other source instances.
    obj.data = obj.data.copy()
    mat = blue if obj['source_name'] in fixture_names else roof if obj.get('system') == '06 Roof' else architecture
    for slot in obj.material_slots:
        slot.material = mat
    obj['presentation'] = 'In situ: original mesh and transform; animated material only'
    if obj.get('system') in ['04 Walls','05 Envelope','06 Roof'] and not obj.name.startswith('CI Tools Wall'):
        edge_sources.append(obj)

services = bpy.data.collections.new('IN SITU | Illustrative hydraulic system')
scene.collection.children.link(services)
edges_collection = bpy.data.collections.new('IN SITU | Architectural feature edges')
scene.collection.children.link(edges_collection)
edge_mat, edge_opacity = reveal_material('In situ | architectural edge graphite', (.18,.23,.26))
edge_data = bpy.data.curves.new('Architecture feature edges | no triangulation','CURVE')
edge_data.dimensions = '3D'
edge_data.bevel_depth = .007
edge_data.bevel_resolution = 0
for obj in edge_sources:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.link_faces[0].normal.dot(e.link_faces[1].normal) > .8:
            continue
        if e.calc_length() < .15:
            continue
        spline = edge_data.splines.new('POLY')
        spline.points.add(1)
        for p,v in zip(spline.points,e.verts):
            p.co = (*(obj.matrix_world @ v.co),1)
    bm.free()
edge_obj=bpy.data.objects.new(edge_data.name,edge_data)
edges_collection.objects.link(edge_obj)
edge_data.materials.append(edge_mat)

def pipe(name, points, radius, mat=blue, fixture=None):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 3
    data.use_fill_caps = True
    line = data.splines.new('POLY')
    line.points.add(len(points)-1)
    for p, xyz in zip(line.points, points):
        p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    services.objects.link(obj)
    data.materials.append(mat)
    obj['provenance'] = 'Illustrative service layout; source architecture unchanged'
    obj['decision_id'] = 'HYD-01'
    if fixture:
        obj['source_fixture'] = fixture
    return obj

route_records = []
for route in study['routes']:
    points = [Vector(p)+focus-Vector((0,0,route['level']*study['display_level_gap'])) for p in route['path']]
    pipe('Waste | '+route['source_fixture'], points, .045 if route['kind']=='toilets' else .03,
         fixture=route['source_fixture'])
    route_records.append({'source_fixture': route['source_fixture'], 'points': [list(p) for p in points]})
stack = Vector(route_records[0]['points'][-1])
pipe('Riser | continuous in-situ alignment', [(stack.x,stack.y,-.35),(stack.x,stack.y,8.01)], .065)
bpy.ops.mesh.primitive_torus_add(major_radius=.26, minor_radius=.045, location=(stack.x,stack.y,2.92))
ring = bpy.context.object
ring.name = 'HYD-01 | illustrative penetration decision'
for c in list(ring.users_collection):
    c.objects.unlink(ring)
services.objects.link(ring)
ring.data.materials.append(amber)

def key_opacity(socket, values):
    for frame, value in values:
        socket.default_value = value
        socket.keyframe_insert('default_value', frame=frame)

key_opacity(arch_opacity, [(1,1),(100,1),(150,.11),(240,.11)])
key_opacity(roof_opacity, [(1,1),(100,1),(150,.08),(240,.08)])
key_opacity(edge_opacity, [(1,0),(100,0),(150,.4),(240,.4)])
key_opacity(blue_opacity, [(1,0),(100,0),(150,1),(240,1)])
key_opacity(amber_opacity, [(1,0),(160,0),(180,1),(240,1)])

# Source fixtures remain visible as chalk before the service highlight appears.
fixture_material, fixture_opacity = reveal_material('In situ | source fixtures', (.80,.80,.76))
fixture_shader = fixture_material.node_tree.nodes.get('Principled BSDF')
for obj in scene.objects:
    if obj.type == 'MESH' and obj.get('source_name') in fixture_names and not obj.hide_render:
        for slot in obj.material_slots:
            slot.material = fixture_material
for frame, color in [(1,(.80,.80,.76,1)), (100,(.80,.80,.76,1)), (150,(.008,.035,.30,1)), (240,(.008,.035,.30,1))]:
    fixture_shader.inputs['Base Color'].default_value = color
    fixture_shader.inputs['Base Color'].keyframe_insert('default_value',frame=frame)

camera = bpy.data.objects['Camera | reverse study']
scene.camera = camera
camera.data.type = 'PERSP'
camera.data.lens = 52
poses = [
    (1, Vector((-40,-55,45)), Vector((0,0,3))),
    (72, focus+Vector((-24,-32,23)), focus+Vector((0,0,4))),
    (120, focus+Vector((-14,-19,14)), focus+Vector((0,0,4.2))),
    (240, focus+Vector((-14,-19,14)), focus+Vector((0,0,4.2)))
]
for frame, position, target in poses:
    camera.location = position
    camera.rotation_euler = (target-position).to_track_quat('-Z','Y').to_euler()
    camera.keyframe_insert('location', frame=frame)
    camera.keyframe_insert('rotation_euler', frame=frame)
scene.frame_start = 1
scene.frame_end = 240
scene.render.fps = 24
for frame, name in [(1,'01 Establish | Camera B'), (72,'02 Approach dwelling'),
                    (120,'03 Reveal begins'), (180,'04 Coordination question'), (240,'05 Hold')]:
    scene.timeline_markers.new(name, frame=frame)
scene.render.resolution_x = 1500
scene.render.resolution_y = 1125
scene.cycles.samples = 24
scene.cycles.transparent_max_bounces = 32
scene['direction'] = 'Scroll-led perspective approach with in-situ system reveals; no exploded geometry'
scene['palette_status'] = 'Deep blue provisional; colour assessment pending'
scene['motion_status'] = 'Keyframed approach study; continuous-motion review still required'
scene['source_credit'] = 'MyStudioNZ / Sketchfab / CC BY 4.0; modified materials, illustrative services'
if '--focus-only' not in sys.argv:
    scene.frame_set(96)
    scene.render.filepath = str(OUT / '07-in-situ-approach.png')
    bpy.ops.render.render(write_still=True)
scene.frame_set(200)
scene.render.filepath = str(OUT / '08-in-situ-hydraulics.png')
bpy.ops.render.render(write_still=True)

for name, transform in source_transforms.items():
    actual = bpy.data.objects[name].matrix_world
    assert all(abs(actual[r][c]-transform[r][c]) < 1e-6 for r in range(4) for c in range(4)), name
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'sitewise-in-situ-study.blend'))
(OUT / 'in-situ-study.json').write_text(json.dumps({
    'status': 'Illustrative camera/material study, not engineered design',
    'camera': 'B as opening position; perspective approach into nearest dwelling',
    'architecture_opacity': .11, 'roof_opacity': .08, 'feature_edge_opacity': .4,
    'source_transforms_verified_unchanged': len(source_transforms),
    'routes': route_records, 'animation_frames': [1,240], 'fps': 24,
    'motion_review': 'Key poses rendered; full flight not yet rendered or reviewed'
}, indent=2))
print('IN_SITU_COMPLETE',len(source_transforms),'source transforms unchanged',flush=True)
