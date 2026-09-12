"""Prepare independent rotors and relocate the condenser clear of the window."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from export_web import export

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'sitewise-detail-v4.blend'))
scene = bpy.context.scene
for obj in scene.objects:
    if obj.name.startswith(('Detail | Outdoor condenser', 'Detail | Condenser')):
        obj.location.x -= 2.8
    if obj.name.startswith('Detail | Insulated refrigerant '):
        for spline in obj.data.splines:
            for point in list(spline.points)[:3]:
                point.co.x -= 2.8
    if obj.name.startswith('Detail | Condenser fan blade'):
        # glTF uses Y-up: Blender (x,y,z) becomes (x,z,-y).
        obj['sw_motion'] = 'rotor:z:0:0.72:14.59'
    if 'Whirlybird 1 curved vane' in obj.name:
        obj['sw_motion'] = 'rotor:y:-2.55:9.3:12.1'
    if 'Whirlybird 2 curved vane' in obj.name:
        obj['sw_motion'] = 'rotor:y:2.75:9.3:11.2'
bpy.context.view_layer.update()
cabinet = scene.objects['Detail | Outdoor condenser cabinet']
corners = [cabinet.matrix_world @ Vector(c) for c in cabinet.bound_box]
assert max(p.x for p in corners) < 2.06, 'Condenser still overlaps the window'
assert min(p.x for p in corners) > -1.61, 'Condenser overlaps the left window'
assert sum(str(o.get('sw_motion', '')).startswith('rotor:') for o in scene.objects) == 33
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent / 'sitewise-detail-v5.blend'))
export(scene)
