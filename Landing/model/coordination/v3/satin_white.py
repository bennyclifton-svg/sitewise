"""Neutral satin-white material master; neon selection is applied in the viewer."""
import bpy
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from export_web import export
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-bright-chalk-v14.blend'))
scene=bpy.context.scene
glass={m for o in scene.objects if o.type=='MESH' and o.get('sw_glass') for m in o.data.materials if m}
for mat in bpy.data.materials:
    mat.diffuse_color=(1,1,1,mat.diffuse_color[3])
    shader=mat.node_tree.nodes.get('Principled BSDF') if mat.use_nodes else None
    if shader:
        shader.inputs['Base Color'].default_value=(1,1,1,1)
        shader.inputs['Roughness'].default_value=.16 if mat in glass else .38
scene['sw_palette']='Pure satin white; shared neon-blue discipline highlighting in web viewer'
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-satin-white-v15.blend'))
if '--export' in sys.argv:export(scene)
