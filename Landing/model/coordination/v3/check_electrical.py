"""Build and audit the electrical module in an isolated copy of the rich scene."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import electrical

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'sitewise-interior-checkpoint.blend'))
scene = bpy.context.scene
original = {o: o.matrix_world.copy() for o in scene.objects}
for obj, world in original.items():
    obj.parent = None
    obj.matrix_world = electrical.ROTATION @ world
bpy.context.view_layer.update()
registered = {o: o.matrix_world.copy() for o in scene.objects}
result = electrical.build(scene)
result['audit']['source_transforms_unchanged'] = all(
    max(abs(obj.matrix_world[i][j] - matrix[i][j]) for i in range(4) for j in range(4)) < .00001
    for obj, matrix in registered.items())
(HERE / 'electrical-audit.json').write_text(json.dumps(result, indent=2))
print('ELECTRICAL_AUDIT', json.dumps(result['audit']), flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'electrical-review.blend'))
