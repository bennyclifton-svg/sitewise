"""Restore a chalk study palette without altering the latest model geometry."""
import bpy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from build_integrated import linear
from export_web import export
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-decks-v9.blend'))
scene=bpy.context.scene
for mat in bpy.data.materials:
    if not (mat.name.startswith('Facade |') or 'Default chalk' in mat.name or mat.name.startswith('Detail | Chalk')):
        continue
    colour='#E7E3DD' if mat.name=='Facade | Balcony oak' else '#F7F7F4'
    rgb=linear(colour)
    mat.diffuse_color=(*rgb,1)
    shader=mat.node_tree.nodes.get('Principled BSDF') if mat.use_nodes else None
    if shader:
        shader.inputs['Base Color'].default_value=(*rgb,1)
        shader.inputs['Metallic'].default_value=0
        shader.inputs['Roughness'].default_value=.88
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-chalk-v10.blend'))
export(scene)
