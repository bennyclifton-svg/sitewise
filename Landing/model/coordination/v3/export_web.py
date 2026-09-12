"""Bake visible geometry into material/system batches; leave the editable master intact."""
import bpy
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE.parents[3] / 'frontend/public/landing-assets/coordination'


def export(source):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    batches = defaultdict(list)
    for obj in source.objects:
        if obj.hide_render or obj.type not in ('MESH', 'CURVE') or not obj.get('sw_system'):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if not mesh:
            continue
        system = obj['sw_system']
        if obj.name.startswith(('V3 | Perimeter ', 'V3 | Pedestrian front gate',
                                'V3 | Front bin store', 'V3 | Bin store ', 'V3 | Relocated bin ')):
            system = 'landscape'
            obj['sw_system'] = system
        endpoint_ids = json.loads(obj.get('sw_endpoint_ids', '[]'))
        if system in ('architecture', 'interiors'):
            if any(identifier.startswith('SAN-fixture-') for identifier in endpoint_ids):
                system = 'hydraulic'
            elif obj.name.startswith('Kitchen source') and 'MEC-hood-port' in endpoint_ids:
                system = 'mechanical'
        slots = list(mesh.materials)
        for index, mat in enumerate(slots or [None]):
            faces = [p for p in mesh.polygons if p.material_index == index]
            if not faces:
                continue
            memberships = tuple(json.loads(obj.get('sw_service_systems', '[]')))
            night_window = bool(obj.get('sw_glass')) and obj.name.startswith('WD -')
            key = (system, mat.name if mat else 'Default', bool(obj.get('sw_glass')), memberships, obj.get('sw_motion', ''), bool(obj.get('sw_civil_surface')), night_window, int(obj.get('sw_landscape_dwelling', 0)), int(obj.get('sw_reveal_dwelling', 0)), bool(obj.get('sw_underground')))
            vertices = [tuple(obj.matrix_world @ v.co) for v in mesh.vertices]
            mirrored = obj.matrix_world.to_3x3().determinant() < 0
            batches[key].append((vertices, [tuple(reversed(p.vertices)) if mirrored else tuple(p.vertices) for p in faces], mat))
        evaluated.to_mesh_clear()
    scene = bpy.data.scenes.new('WEB EXPORT | System batches')
    bpy.context.window.scene = scene
    counts = {}
    for (system, label, glass, memberships, motion, civil_surface, night_window, landscape_dwelling, reveal_dwelling, underground), parts in batches.items():
        vertices, faces = [], []
        for points, polygons, _ in parts:
            offset = len(vertices)
            vertices.extend(points)
            faces.extend(tuple(i + offset for i in face) for face in polygons)
        mesh = bpy.data.meshes.new(system + ' | ' + label)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(obj)
        obj['sw_system'] = system
        obj['sw_glass'] = glass
        obj['sw_civil_surface'] = civil_surface
        obj['sw_night_window'] = night_window
        obj['sw_landscape_dwelling'] = landscape_dwelling
        obj['sw_dwelling_y_offset'] = source.get('sw_dwelling_y_offset', 0)
        obj['sw_reveal_dwelling'] = reveal_dwelling
        obj['sw_underground'] = underground
        obj['sw_service_systems'] = json.dumps(list(memberships))
        if motion:
            obj['sw_motion'] = motion
            if motion == 'car':
                obj['sw_car_origin'] = json.loads(source['sw_car_origin'])
        if parts[0][2]:
            mesh.materials.append(parts[0][2])
        obj.select_set(True)
        counts[system] = counts.get(system, 0) + len(faces)
    WEB.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(WEB/'sitewise-coordination.glb'), export_format='GLB',
        use_selection=True, use_active_scene=True, export_extras=True, export_cameras=False, export_lights=False,
        export_animations=False, export_texcoords=False, export_normals=True,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_draco_position_quantization=16, export_draco_normal_quantization=10,
        export_materials='EXPORT', export_image_format='NONE')
    (WEB/'model-manifest.json').write_text(json.dumps({'systems': counts, 'batches':len(batches),
        'scope':source.get('sw_model_scope', 'One detailed dwelling; illustrative shared site and street services.')}, indent=2))
    bpy.context.window.scene = source
    print('V3_WEB_EXPORTED', dict(counts), flush=True)


if __name__ == '__main__':
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-entry-bikes-v23.blend'))
    export(bpy.context.scene)
