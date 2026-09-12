"""Extract one complete source window curtain set, leaving source files unchanged."""
import json
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination' / 'asset-audit'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'interior-design.glb'))
bpy.context.view_layer.update()
originals = list(bpy.data.objects)


def material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = 0.84
    return mat


chalk = material('SW | Curtain chalk fabric', (0.80, 0.78, 0.73))
rail_mat = material('SW | Curtain mineral rail', (0.26, 0.30, 0.32))
collection = bpy.data.collections.new('SW Asset Curtain Pair')
bpy.context.scene.collection.children.link(collection)
derived = []
records = []


def in_window(point):
    return 9.75 < point.x < 13.30 and 1.1 < point.y < 1.6


def outer_panels(mesh):
    """Remove disconnected sheer-edge scraps and keep the two complete drapes."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # GLB splits vertices at texture/normal seams; join coincident coordinates
    # only to identify complete cloth components in the texture-free copy.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
    unseen = set(bm.verts)
    components = []
    while unseen:
        start = unseen.pop()
        stack, component = [start], {start}
        while stack:
            current = stack.pop()
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other in unseen:
                    unseen.remove(other)
                    component.add(other)
                    stack.append(other)
        components.append(component)
    largest = sorted(components, key=len, reverse=True)[:2]
    largest.sort(key=lambda group: sum(v.co.x for v in group)/len(group))
    result = []
    for side, group in zip(('left panel', 'right panel'), largest):
        vertices = list(group)
        index = {vertex: i for i, vertex in enumerate(vertices)}
        faces = [face for face in bm.faces if all(v in group for v in face.verts)]
        panel = bpy.data.meshes.new(f'SW Curtain | {side}')
        panel.from_pydata([v.co.copy() for v in vertices], [],
                         [tuple(index[v] for v in face.verts) for face in faces])
        panel.update()
        for face, source in zip(panel.polygons, faces):
            face.use_smooth = source.smooth
        result.append((f'SW Curtain | {side}', panel))
    bm.free()
    return result


for source in originals:
    # Keep the opaque outer drapes and rail. The central sheer would conceal
    # the window in a chalk render and is deliberately excluded.
    if source.type != 'MESH' or source.name not in ('Curtatins_Black_0', 'Curtatins_White1_0'):
        continue
    points = [source.matrix_world @ v.co for v in source.data.vertices]
    inside = {i for i, point in enumerate(points) if in_window(point)}
    if not inside:
        continue
    crossing_faces = [poly for poly in source.data.polygons
                      if any(i in inside for i in poly.vertices)
                      and not all(i in inside for i in poly.vertices)]
    if crossing_faces:
        raise RuntimeError(f'Window region crosses {len(crossing_faces)} faces in {source.name}')
    faces = [poly for poly in source.data.polygons if all(i in inside for i in poly.vertices)]
    used = sorted({i for poly in faces for i in poly.vertices})
    remap = {old: new for new, old in enumerate(used)}
    name = 'SW Curtain | rail' if '_Black_' in source.name else 'SW Curtain | outer pair'
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([points[i] for i in used], [],
                     [tuple(remap[i] for i in p.vertices) for p in faces])
    mesh.update()
    for poly, original in zip(mesh.polygons, faces):
        poly.use_smooth = original.use_smooth
    parts = [(name, mesh)] if '_Black_' in source.name else outer_panels(mesh)
    for name, part in parts:
        obj = bpy.data.objects.new(name, part)
        collection.objects.link(obj)
        obj.data.materials.append(rail_mat if '_Black_' in source.name else chalk)
        obj['source_file'] = 'interior-design.glb'
        obj['source_object'] = source.name
        obj['source_parent'] = 'Curtatins'
        obj['source_author'] = 'Visthétique'
        obj['source_license'] = 'CC-BY-4.0'
        obj['extraction'] = 'One complete window set; no faces cut; disconnected sheer-edge scraps excluded'
        derived.append(obj)
        records.append(dict(object=name, source_object=source.name,
                            source_vertex_count=len(source.data.vertices),
                            selected_vertices=len(part.vertices), selected_triangles=sum(len(p.vertices)-2 for p in part.polygons),
                            crossing_faces=0))

coords = [vertex.co for obj in derived for vertex in obj.data.vertices]
low = Vector(tuple(min(p[i] for p in coords) for i in range(3)))
high = Vector(tuple(max(p[i] for p in coords) for i in range(3)))
pivot = Vector(((low.x + high.x)/2, (low.y + high.y)/2, low.z))
for obj in derived:
    for vertex in obj.data.vertices:
        vertex.co -= pivot
    obj['pivot'] = 'Window width/depth center at fabric base'
for obj in originals:
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.outliner.orphans_purge(do_recursive=True)

metadata = dict(collection=collection.name, source_file='interior-design.glb',
                source_author='Visthétique', source_license='CC-BY-4.0',
                source_url='https://sketchfab.com/3d-models/modern-apartment-1fbb649cd6624f2bb7b7d6e30c6533a5',
                modifications='One complete window outer curtain pair and rail extracted; central sheer and disconnected sheer-edge scraps omitted; coincident seam vertices merged for component separation; transforms baked, base-center pivot, texture-free fabric/rail materials; geometry not decimated.',
                source_pivot=list(pivot), dimensions=list(high-low), width_axis='+X',
                depth_axis='+Y', up_axis='+Z', room_facing_direction=[0,-1,0],
                hanging_direction=[0,0,-1], rail_height=(high-low).z,
                ceiling_attachment_local=[0,0,(high-low).z],
                objects=records)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'
scene['source_attribution'] = json.dumps(metadata, ensure_ascii=False)
(OUT / 'curtain-library.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'curtain-library.blend'))

camera_data = bpy.data.cameras.new('Curtain audit camera')
camera = bpy.data.objects.new('Curtain audit camera', camera_data)
scene.collection.objects.link(camera)
center = Vector((0, 0, (high-low).z/2))
camera.location = center + Vector((1.0, -8.0, 0.5))
camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = max(high-low)*1.25
scene.camera = camera
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1300
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'MATERIAL'
shading.show_cavity = True
shading.cavity_type = 'BOTH'
shading.show_shadows = True
shading.background_type = 'WORLD'
scene.world = bpy.data.worlds.new('Curtain audit background')
scene.world.color = (0.68, 0.71, 0.73)
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(OUT / 'curtain-library-preview.png')
bpy.ops.render.render(write_still=True)
print('CURTAIN_LIBRARY_COMPLETE', json.dumps(metadata), flush=True)
