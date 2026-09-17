"""Build the landing asset without modifying the editable architectural master.

Run with Blender --background --python export_web.py from the repository root.
"""
from pathlib import Path
from collections import defaultdict
import json
import bpy

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).parent / 'option-7' / 'terrace-7.glb'
OUTPUT = ROOT / 'frontend/public/landing-assets/coordination/terrace-7.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
groups = defaultdict(list)
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH':
        continue
    # Keep facade groups separate for the next partial-envelope cutaway.
    component = 'facade' if any(word in obj.name.lower() for word in (
        'street wall', 'glazing', 'garage', 'loggia', 'entry', 'front',
    )) else 'body'
    key = (obj.get('sw_system', 'architecture'), obj.get('sw_dwelling', 0),
           tuple(slot.material.name if slot.material else '' for slot in obj.material_slots), component)
    groups[key].append(obj)

for (system, dwelling, materials, component), objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = f'TH{dwelling:02} | {system} | {component} | {materials[0] if materials else "unpainted"}'
    obj['sw_system'] = system
    obj['sw_dwelling'] = dwelling
    obj['sw_component'] = component

# Procedural brick courses are supplied by the viewer; retain the authored palette.
for i, colour in enumerate(('BC9376', 'C4A184', 'AE8167'), 1):
    material = bpy.data.materials.get(f'Warm brick {i}')
    if material:
        rgb = [int(colour[j:j+2], 16) / 255 for j in (0, 2, 4)]
        linear = tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb)
        material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (*linear, 1)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format='GLB', export_extras=True,
    export_cameras=False, export_lights=False, export_animations=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
print(json.dumps({'output': str(OUTPUT), 'groups': len(groups), 'bytes': OUTPUT.stat().st_size}))
