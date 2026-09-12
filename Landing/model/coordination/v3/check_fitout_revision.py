"""Audit the kitchen correction on an isolated registered source scene."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fitout_revision
import electrical

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'sitewise-interior-checkpoint.blend'))
scene = bpy.context.scene
rotation = Matrix.Rotation(math.atan2(.16053, .98703), 4, 'Z')
original = {o: o.matrix_world.copy() for o in scene.objects}
for obj, matrix in original.items():
    obj.parent = None
    obj.matrix_world = rotation @ matrix
bpy.context.view_layer.update()
result = fitout_revision.build(scene)
print('FITOUT_REVISION', json.dumps({k: result[k] for k in ['delta_world', 'bounds_before', 'bounds_after', 'ports', 'audit']}), flush=True)
power = electrical.build(scene)
print('ELECTRICAL_AFTER_FITOUT', json.dumps(power['audit']), flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'fitout-revision-review.blend'))
