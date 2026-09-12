"""Editable illustrative wet-area study derived from the approved Camera B scene.

Original architecture is retained in hidden collections. Section geometry is a
presentation derivative; services are illustrative and never engineering evidence.
"""
import bpy
import bmesh
import json
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-camera-review.blend'))
scene = bpy.context.scene
SOURCE_CENTER = Vector((-24.757655, -11.917233, 0))
FOCUS_SOURCE = Vector((-26, -23, 0))
FOCUS = FOCUS_SOURCE - SOURCE_CENTER
U = Vector((0.98703, -0.16053, 0)).normalized()
V = Vector((0.16053, 0.98703, 0)).normalized()
LEVELS = [(0.0, 2.92), (2.92, 5.64), (5.64, 8.36), (8.36, 10.5)]
GAP = 3.0

def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

cut = [collection(f'STUDY | {name}') for name in ['Ground', 'Living', 'Bedrooms', 'Roof']]
services = collection('STUDY | Illustrative hydraulic routes')
annotations = collection('STUDY | Presentation marks')

def material(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    node = m.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*rgb, 1)
    node.inputs['Roughness'].default_value = .75
    return m

pipe_mat = material('Study | hydraulic mineral', (.065, .13, .14))
fixture_mat = material('Study | fixture mineral', (.40, .53, .52))
question_mat = material('Study | open decision amber', (.90, .31, .055))
line_mat = material('Study | registration graphite', (.36, .39, .37))

def trim(bm, point, normal, clear_outer=True):
    if not bm.verts:
        return
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
        plane_co=point, plane_no=normal, dist=0.0001,
        clear_outer=clear_outer, clear_inner=not clear_outer)

census = json.loads((OUT / 'source-census.json').read_text())
fixtures = []
fixture_meshes = set()
for kind in ['toilets', 'basins', 'showers', 'kitchen_sinks', 'laundry_sinks']:
    for fixture in census['assemblies'][kind]:
        point = Vector(fixture['center_blender_world']) - SOURCE_CENTER
        if point.dot(V) < -8:
            fixtures.append(dict(fixture, kind=kind))
            fixture_meshes.update(fixture['source_meshes'])

sources = [o for o in list(scene.objects) if o.type == 'MESH'
           and 'source_name' in o and not o.hide_render]
sections = []
for obj in sources:
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    spans = [p.dot(V) for p in corners]
    obj.hide_render = True
    obj.hide_set(True)
    if min(spans) >= -8 or max(spans) < -15.5:
        continue
    # The close-up omits site fences and landscaping; foundation slabs remain.
    if obj.get('system') == '01 Site':
        continue
    zmin = min(p.z for p in corners)
    zmax = max(p.z for p in corners)
    name = obj['source_name']
    is_wall = obj.get('system') in ['04 Walls', '05 Envelope']
    is_fixture = name in fixture_meshes
    for level, (base, top) in enumerate(LEVELS):
        if zmin >= top or zmax < base:
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        trim(bm, V * -8, V)
        trim(bm, V * -15.5, -V)
        trim(bm, Vector((0, 0, base)), Vector((0, 0, -1)))
        trim(bm, Vector((0, 0, top)), Vector((0, 0, 1)))
        if is_wall and level < 3:
            trim(bm, Vector((0, 0, base + .85)), Vector((0, 0, 1)))
        # Tall shower screens obscure the retained pans and adjacent fixtures.
        if 'Shower Cabin' in name:
            trim(bm, Vector((0, 0, base + .70)), Vector((0, 0, 1)))
        if not bm.faces:
            bm.free()
            continue
        mesh = bpy.data.meshes.new(f'Section L{level} | {name}')
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        copy = bpy.data.objects.new(mesh.name, mesh)
        cut[level].objects.link(copy)
        for m in obj.data.materials:
            copy.data.materials.append(fixture_mat if is_fixture else m)
        copy.location = -FOCUS + Vector((0, 0, level * GAP))
        if level == 3:
            copy.location += U * 5.5
            copy.hide_render = True
            copy.hide_set(True)
        copy['source_name'] = name
        copy['study_level'] = level
        copy['provenance'] = 'Presentation section of source architecture; not a design change'
        sections.append({'object': copy.name, 'source_mesh': name, 'level': level})

def pipe(name, points, radius=.045, mat=pipe_mat, target=services, source=None):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.use_fill_caps = True
    spline = curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for p, xyz in zip(spline.points, points):
        p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    target.objects.link(obj)
    curve.materials.append(mat)
    obj['provenance'] = 'Illustrative coordination route; not surveyed or engineered'
    obj['decision_id'] = 'HYD-01'
    if source:
        obj['source_fixture'] = source
    return obj

def uv_point(u, v, z):
    p = U*u+V*v
    p.z = z
    return p

STACK_U, STACK_V = 2.65, .4
routes = []
for fixture in fixtures:
    source_point = Vector(fixture['center_blender_world']) - FOCUS_SOURCE
    level = min(2, max(0, int((fixture['bounds_min'][2]-.15)/2.72)))
    base = LEVELS[level][0]
    rise = level*GAP
    u, v = source_point.dot(U), source_point.dot(V)
    # Diagrammatic collection below the floor keeps the interface legible.
    branch_z = base - .18 + rise
    endpoint_z = fixture['bounds_min'][2] + .12 + rise
    points = [uv_point(u,v,endpoint_z), uv_point(u,v,branch_z),
              uv_point(STACK_U,v,branch_z), uv_point(STACK_U,STACK_V,branch_z-.06)]
    pipe('Illustrative waste | '+fixture['source_assembly'], points,
         radius=.045 if fixture['kind']=='toilets' else .03,
         source=fixture['source_assembly'])
    routes.append({'source_fixture': fixture['source_assembly'], 'kind': fixture['kind'],
                   'level': level, 'path': [list(p) for p in points]})

for level, (base, top) in enumerate(LEVELS[:3]):
    rise = level*GAP
    pipe(f'Illustrative riser | level {level}',
         [uv_point(STACK_U,STACK_V,base-.35+rise), uv_point(STACK_U,STACK_V,top-.35+rise)], .065)
    if level < 2:
        start, end = top-.35+rise, top-.35+(level+1)*GAP
        z = start+.10
        while z < end:
            pipe('Riser registration | exploded-view guide',
                 [uv_point(STACK_U,STACK_V,z), uv_point(STACK_U,STACK_V,min(z+.10,end))],
                 .013, line_mat, annotations)
            z += .25

# A single amber ring marks the example penetration decision, not a detected clash.
decision = uv_point(STACK_U, STACK_V, LEVELS[1][0]+GAP)
bpy.ops.mesh.primitive_torus_add(major_radius=.22, minor_radius=.035, location=decision)
ring = bpy.context.object
ring.name = 'HYD-01 | floor penetration responsibility — illustrative question'
for c in list(ring.users_collection):
    c.objects.unlink(ring)
annotations.objects.link(ring)
ring.data.materials.append(question_mat)
ring['decision_id'] = 'HYD-01'
ring['status'] = 'Illustrative open question; no project approval represented'

camera = bpy.data.objects['Camera | reverse study']
scene.camera = camera
target = Vector((0, 0, 7))
camera.location = target + Vector((-40, -55, 58))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale = 24
camera['direction'] = 'Approved Camera B azimuth; steeper cutaway pitch'
scene.render.resolution_x = 1500
scene.render.resolution_y = 1500
scene.cycles.samples = 32
scene['stage'] = '04 First hydraulic cutaway study; awaiting review before motion'
scene['cutaway_note'] = 'Walls sectioned to 850 mm above level for visibility; floor gaps are display offsets'
scene['hydraulic_note'] = 'Waste route study only. Diameters, falls, venting, capacity, penetrations and fire strategy are unverified.'
scene.render.filepath = str(OUT / '05-hydraulic-cutaway-b.png')
bpy.ops.render.render(write_still=True)

# An explicit services-focus view reveals connections hidden by the floor plates.
# This is a drawing convention; it does not change the underlying architecture.
ghost = bpy.data.materials.new('Study | architecture ghost for services focus')
ghost.use_nodes = True
nodes = ghost.node_tree.nodes
nodes.clear()
output = nodes.new('ShaderNodeOutputMaterial')
mix = nodes.new('ShaderNodeMixShader')
mix.inputs[0].default_value = .13
transparent = nodes.new('ShaderNodeBsdfTransparent')
diffuse = nodes.new('ShaderNodeBsdfDiffuse')
diffuse.inputs['Color'].default_value = (.72,.73,.69,1)
ghost.node_tree.links.new(transparent.outputs[0],mix.inputs[1])
ghost.node_tree.links.new(diffuse.outputs[0],mix.inputs[2])
ghost.node_tree.links.new(mix.outputs[0],output.inputs['Surface'])
for coll in cut[:3]:
    for obj in coll.objects:
        if obj['source_name'] not in fixture_meshes:
            for slot in obj.material_slots:
                slot.material = ghost
scene.cycles.transparent_max_bounces = 24
scene.render.filepath = str(OUT / '06-hydraulic-focus-b.png')
bpy.ops.render.render(write_still=True)

# The file opens in solid material mode so inspection does not start another render.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
            area.spaces.active.shading.type = 'SOLID'
            area.spaces.active.shading.color_type = 'MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'sitewise-hydraulic-study.blend'))
(OUT / 'hydraulic-study.json').write_text(json.dumps({
    'decision_id': 'HYD-01', 'camera': 'B', 'status': 'Illustrative concept for review',
    'question': 'Agree the wet-area riser and floor penetration responsibility',
    'disciplines': ['Architecture', 'Hydraulics', 'Structure'],
    'proposed_scope_outcome': 'Record route, reserved zone and penetration responsibility in consultant and trade scope',
    'source_origin': list(FOCUS_SOURCE), 'display_level_gap': GAP,
    'routes': routes, 'sections': sections,
    'limitations': ['Not a clash result or engineered hydraulic design',
                    'Cutaway and floor offsets are presentation only',
                    'Review fixture connection points and room boundaries before further detailing']
}, indent=2))
print('HYDRAULIC_STUDY_COMPLETE', len(sections), 'sections;',len(routes),'fixture routes', flush=True)
