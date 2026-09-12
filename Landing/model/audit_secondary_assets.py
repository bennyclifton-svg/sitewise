"""Read supplied apartment/car assets and write audit evidence, never originals.

Run with Blender --background --python audit_secondary_assets.py.
"""
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination' / 'asset-audit'
OUT.mkdir(exist_ok=True, parents=True)


def read_glb(path):
    raw = path.read_bytes()
    length, kind = struct.unpack_from('<II', raw, 12)
    assert raw[:4] == b'glTF' and kind == 0x4e4f534a
    data = json.loads(raw[20:20 + length])
    triangles = 0
    vertices = 0
    primitives = 0
    for mesh in data.get('meshes', []):
        for primitive in mesh['primitives']:
            primitives += 1
            vertices += data['accessors'][primitive['attributes']['POSITION']]['count']
            count = data['accessors'][primitive['indices']]['count'] if 'indices' in primitive else data['accessors'][primitive['attributes']['POSITION']]['count']
            mode = primitive.get('mode', 4)
            triangles += count // 3 if mode == 4 else max(0, count - 2) if mode in (5, 6) else 0
    image_bytes = sum(data['bufferViews'][im['bufferView']]['byteLength'] for im in data.get('images', []) if 'bufferView' in im)
    return dict(file=path.name, bytes=len(raw), asset=data.get('asset'),
                counts={key:len(data.get(key, [])) for key in ['nodes', 'meshes', 'materials', 'images', 'animations']},
                primitives=primitives, triangles=triangles, vertices=vertices,
                embedded_image_bytes=image_bytes,
                extensions=data.get('extensionsUsed', []),
                punctual_lights=len(data.get('extensions', {}).get('KHR_lights_punctual', {}).get('lights', [])),
                nodes=[dict(index=i, **node) for i, node in enumerate(data.get('nodes', []))])


def bounds(objects):
    points = [obj.matrix_world @ Vector(p) for obj in objects for p in obj.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return low, high


def render(objects, filename, direction):
    scene = bpy.context.scene
    for obj in scene.objects:
        if obj.type == 'MESH':
            obj.hide_render = obj not in objects
    low, high = bounds(objects)
    center = (low + high) / 2
    span = max(high - low)
    camera_data = bpy.data.cameras.new('Audit camera')
    camera = bpy.data.objects.new('Audit camera', camera_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector(direction).normalized() * span * 3
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = span * 1.35
    camera_data.clip_end = span * 20
    scene.camera = camera
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.color_type = 'MATERIAL'
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = 'BOTH'
    shading.show_specular_highlight = True
    shading.show_object_outline = False
    shading.background_type = 'WORLD'
    if scene.world is None:
        scene.world = bpy.data.worlds.new('Audit background')
    scene.world.color = (0.75, 0.77, 0.80)
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)


sources = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['interior-design.glb', 'car.glb']
for source in sources:
    audit = read_glb(ROOT / source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / source))
    bpy.context.view_layer.update()
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    low, high = bounds(meshes)
    audit['blender_bounds_m'] = dict(min=list(low), max=list(high), dimensions=list(high-low))
    audit['blender_objects'] = []
    groups = defaultdict(list)
    for obj in meshes:
        lo, hi = bounds([obj])
        parents = []
        parent = obj.parent
        while parent:
            parents.append(parent.name)
            parent = parent.parent
        row = dict(name=obj.name, parents=parents, min=list(lo), max=list(hi), dimensions=list(hi-lo),
                   vertices=len(obj.data.vertices), triangles=sum(len(poly.vertices)-2 for poly in obj.data.polygons),
                   materials=[mat.name for mat in obj.data.materials if mat])
        audit['blender_objects'].append(row)
        groups[parents[0] if parents else obj.name].append(obj)
    audit['groups'] = []
    for name, objects in groups.items():
        lo, hi = bounds(objects)
        audit['groups'].append(dict(name=name, mesh_objects=len(objects), dimensions=list(hi-lo), min=list(lo), max=list(hi),
                                    triangles=sum(sum(len(poly.vertices)-2 for poly in obj.data.polygons) for obj in objects)))
    output = OUT / (source.removesuffix('.glb') + '-audit.json')
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print('AUDIT', source, json.dumps({k:v for k,v in audit.items() if k not in ['nodes', 'blender_objects', 'groups']}), flush=True)
    if source == 'interior-design.glb':
        # Large architectural shell hides the extractable furnishing groups.
        furnishing = [obj for obj in meshes if not obj.name.startswith(('Plane.002', 'Windows', 'Door.001', 'EnteranceDoor', 'Baseboard'))]
        render(furnishing, 'interior-furnishings-overview.png', (1, -1.6, 1.5))
        appliances = [obj for obj in meshes if obj.name.startswith(('Hood_', 'Hobs.', 'Oven.', 'Refrigator.', 'Sink_', 'Dishwasher.'))]
        render(appliances, 'interior-kitchen-appliances.png', (1, -1.4, 1.1))
        dining = [obj for obj in meshes if obj.name.startswith('DiningTable.001_')]
        render(dining, 'interior-dining-pendants.png', (1, -1.4, 0.7))
    else:
        # Two orphaned source components sit approximately 100 m away.
        car = [obj for obj in meshes if obj.name not in ['Object_291', 'Object_292']]
        lo, hi = bounds(car)
        audit['car_main_cluster_bounds_m'] = dict(min=list(lo), max=list(hi), dimensions=list(hi-lo))
        audit['excluded_remote_objects'] = ['Object_291', 'Object_292']
        output.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
        render(car, 'car-overview.png', (1.2, -1.6, 0.9))

print('SECONDARY_ASSET_AUDIT_COMPLETE', flush=True)
