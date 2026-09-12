"""Extract selected supplied apartment assets into a small reusable Blender library."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination' / 'asset-audit'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'interior-design.glb'))
bpy.context.view_layer.update()
originals = list(bpy.data.objects)


def material(name, color, roughness=0.65):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return mat


chalk = material('SW | Chalk appliance enamel', (0.76, 0.75, 0.70))
graphite = material('SW | Graphite appliance glass', (0.10, 0.13, 0.15), 0.38)
metal = material('SW | Mineral metal', (0.38, 0.40, 0.40), 0.45)
opal = material('SW | Opal globe', (0.88, 0.85, 0.77), 0.5)


def components(obj):
    adjacency = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    unseen = set(range(len(adjacency)))
    while unseen:
        start = unseen.pop()
        component = {start}
        stack = [start]
        while stack:
            for other in adjacency[stack.pop()]:
                if other in unseen:
                    unseen.remove(other)
                    component.add(other)
                    stack.append(other)
        yield component


def derived_mesh(source, name, selected_vertices=None):
    indices = set(range(len(source.data.vertices))) if selected_vertices is None else selected_vertices
    ordered = sorted(indices)
    mapping = {old: new for new, old in enumerate(ordered)}
    points = [source.matrix_world @ source.data.vertices[index].co for index in ordered]
    source_faces = [poly for poly in source.data.polygons if all(index in indices for index in poly.vertices)]
    faces = [tuple(mapping[index] for index in poly.vertices) for poly in source_faces]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    for poly, source_poly in zip(mesh.polygons, source_faces):
        poly.use_smooth = source_poly.use_smooth
    obj = bpy.data.objects.new(name, mesh)
    obj['source_object'] = source.name
    obj['source_file'] = 'interior-design.glb'
    obj['source_author'] = 'Visthétique'
    obj['source_license'] = 'CC-BY-4.0'
    return obj


records = []
collections = []


def make_asset(name, selections, is_pendant=False):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    collections.append(collection)
    objects = []
    for number, (source, indices) in enumerate(selections, 1):
        obj = derived_mesh(source, f'{name} | {number:02} {source.name}', indices)
        collection.objects.link(obj)
        source_name = source.name.lower()
        assigned = opal if is_pendant and 'white' in source_name else chalk
        if any(s in source_name for s in ['frontblack', '_black_', 'frontpanel', 'frontdown', 'fronttop']):
            assigned = graphite
        elif 'chrome' in source_name or 'aluminum' in source_name or 'gold' in source_name:
            assigned = metal
        elif is_pendant and 'glass' in source_name:
            assigned = opal
        obj.data.materials.append(assigned)
        objects.append(obj)
    coords = [vertex.co for obj in objects for vertex in obj.data.vertices]
    low = Vector(tuple(min(p[i] for p in coords) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in coords) for i in range(3)))
    pivot = Vector(((low.x+high.x)/2, (low.y+high.y)/2, low.z))
    for obj in objects:
        for vertex in obj.data.vertices:
            vertex.co -= pivot
        obj['asset_name'] = name
        obj['pivot'] = 'Footprint center at base; +Z up; source forward retained'
    records.append(dict(name=name, collection=name, objects=[obj.name for obj in objects],
                        source_pivot=list(pivot), dimensions=list(high-low),
                        forward=[0, -1, 0] if not is_pendant else None,
                        target_positive_x_rotation_z_degrees=90 if not is_pendant else None,
                        triangles=sum(sum(len(p.vertices)-2 for p in obj.data.polygons) for obj in objects)))


for name, prefix in [('SW Asset Fridge', 'Refrigator.001_'), ('SW Asset Oven', 'Oven.001_')]:
    make_asset(name, [(obj, None) for obj in originals if obj.type == 'MESH' and obj.name.startswith(prefix)])

pendants = [[], []]
for source in originals:
    if source.type != 'MESH' or not source.name.startswith('DiningTable.001_'):
        continue
    selected = [set(), set()]
    world = [source.matrix_world @ v.co for v in source.data.vertices]
    for part in components(source):
        # Dining furniture is below 1.0 m; the pendants start above 1.7 m.
        if min(world[i].z for i in part) < 1.45:
            continue
        center_x = sum(world[i].x for i in part) / len(part)
        selected[0 if center_x < 0.15 else 1].update(part)
    for index, selection in enumerate(selected):
        if selection:
            pendants[index].append((source, selection))
for index, selections in enumerate(pendants, 1):
    if not selections:
        raise RuntimeError(f'Pendant {index} did not extract')
    make_asset(f'SW Asset Pendant {index}', selections, is_pendant=True)

for obj in originals:
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.outliner.orphans_purge(do_recursive=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'
metadata = dict(source='interior-design.glb', author='Visthétique', license='CC-BY-4.0',
                source_url='https://sketchfab.com/3d-models/modern-apartment-1fbb649cd6624f2bb7b7d6e30c6533a5',
                modifications='Selected geometry extracted, source world transforms baked, pivots centered at base, texture-free chalk/graphite materials applied. No new appliance engineering details asserted.',
                assets=records)
(OUT / 'appliance-library.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
scene['source_attribution'] = json.dumps(metadata, ensure_ascii=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'appliance-library.blend'))

# Arrange only the audit preview; saved library assets remain centered at origin.
offsets = [Vector((-1.2, 0, 0)), Vector((0, 0, 0)), Vector((1.15, 0, 1.0)), Vector((1.85, 0, 1.0))]
for collection, offset in zip(collections, offsets):
    for obj in collection.objects:
        obj.location = offset
camera_data = bpy.data.cameras.new('Library audit camera')
camera = bpy.data.objects.new('Library audit camera', camera_data)
scene.collection.objects.link(camera)
center = Vector((0.25, 0, 1.0))
camera.location = center + Vector((4, -6, 3))
camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 4.8
scene.camera = camera
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1440
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.world = bpy.data.worlds.new('Audit backdrop')
scene.world.color = (0.75, 0.77, 0.80)
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(OUT / 'appliance-library-preview.png')
bpy.ops.render.render(write_still=True)
print('APPLIANCE_LIBRARY_COMPLETE', json.dumps(records), flush=True)
