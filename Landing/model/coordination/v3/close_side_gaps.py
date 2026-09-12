"""Close exposed ground seams between the pedestrian path and house edges."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from export_web import export

def apply(scene):
    path=scene.objects['V3 | Building-side pedestrian path']
    approach=scene.objects['Detail | Garage approach ground cover']
    east=scene.objects['Detail | East building setback ground cover']
    untouched={o.name:o.matrix_world.copy() for o in scene.objects if o not in (approach,east)}
    # Overlap the wall footprint slightly so rasterisation cannot expose a hairline.
    approach.location.x=(-6.15-4.70)/2
    approach.scale.x=1.45
    approach.location.z=.175
    approach.scale.z=.20
    approach.data.materials.clear()
    approach.data.materials.append(path.data.materials[0])
    approach['sw_system']='civil'
    approach['sw_civil_surface']=True
    approach['sw_label']='Continuous paving infill from footpath to building'
    # Rear ground-floor walls step inward from the upper facade.
    east.location.x=(4.65+6.925)/2
    east.scale.x=6.925-4.65
    # Close the exposed strip below the raised ground-floor cladding.
    for index,(ymin,ymax,top) in enumerate([
        (-13.835,-9.122,.45),(-7.065,-2.352,.45),(-2.38,2.333,.45),
        (4.39,9.103,.15),(9.075,13.788,.15),
    ],1):
        bpy.ops.mesh.primitive_cube_add(size=1,location=(-.06,(ymin+ymax)/2,(top+.02)/2))
        plinth=bpy.context.object
        plinth.name=f'Ground finish | Dwelling {index} base closure'
        plinth.scale=(9.60,ymax-ymin,top-.02)
        plinth.data.materials.append(bpy.data.materials['Facade | Warm limestone'])
        plinth['sw_system']='architecture'
        plinth['sw_label']='Closure below existing ground-floor wall base'
    bpy.context.view_layer.update()
    for name,matrix in untouched.items():
        assert scene.objects[name].matrix_world==matrix,name
    points=[approach.matrix_world@Vector(p) for p in approach.bound_box]
    assert abs(max(p.z for p in points)-.275)<1e-5
    assert max(p.x for p in points)>-4.76
    print('GAP_CHECK_PASS: paving flush at path level; coverage overlaps building; all other transforms retained',flush=True)

if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-facade-v6.blend'))
    scene=bpy.context.scene
    apply(scene)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-facade-v7.blend'))
    export(scene)
