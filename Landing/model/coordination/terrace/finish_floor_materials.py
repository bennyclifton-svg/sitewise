"""Apply the ground-floor finish boundary to an already rendered concept."""
import sys
from pathlib import Path
import bpy

count=int(sys.argv[-1])
folder=Path(__file__).resolve().parent/f'option-{count}'
bpy.ops.wm.open_mainfile(filepath=str(folder/f'terrace-{count}.blend'))
for obj in bpy.context.scene.objects:
    if 'Oak floor finish' in obj.name and max(v.co.z for v in obj.data.vertices)<1:
        for v in obj.data.vertices:
            if v.co.y<6.65:v.co.y=6.65
bpy.context.scene.objects['Plan'].data.ortho_scale=15.5
bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'terrace-{count}.blend'))
bpy.ops.export_scene.gltf(filepath=str(folder/f'terrace-{count}.glb'),export_format='GLB',
    export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
