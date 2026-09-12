"""Place the condenser at the side gable and conceal its riser inside the wall."""
import bpy
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

def build(scene):
    if scene.get('sw_condenser_side_placement'):
        return
    old=Vector((5.83,-12,0))
    new=Vector((2.8,-14.35,0))
    transform=Matrix.Translation(new)@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Translation(-old)
    names=('Detail | Outdoor condenser','Detail | Condenser vibration',
           'Detail | Condenser circular','Detail | Condenser radial',
           'Detail | Condenser fan','Detail | Condenser intake')
    for obj in scene.objects:
        if obj.name.startswith(names):
            obj.matrix_world=transform@obj.matrix_world
        elif obj.name.startswith('Detail | Condenser service isolator'):
            obj.location=(3.65,-13.88,1.3)
            obj.rotation_euler.z=-math.pi/2
    pipes=sorted((o for o in scene.objects if o.name.startswith('Detail | Insulated refrigerant ')),key=lambda o:o.name)
    assert len(pipes)==2
    for i,obj in enumerate(pipes):
        # Both risers stay in the side wall; the horizontal run is below the roof void.
        x=3.28+i*.11
        points=[(x,-14.18,.5),(x,-13.73,.5),(x,-13.73,8.30),
                (.3+i*.11,-13.73,8.30),(.3+i*.11,-11.4,8.30),(.3,-11.4,8.8)]
        obj.data.splines.clear()
        spline=obj.data.splines.new('POLY');spline.points.add(len(points)-1)
        for point,xyz in zip(spline.points,points):point.co=(*xyz,1)
        obj.matrix_world=Matrix.Identity(4)
    scene['sw_condenser_side_placement']=True
    bpy.context.view_layer.update()
    print('CONDENSER_SIDE_PLACEMENT',list(new),'wall riser Y=-13.73; ceiling route Z=8.30',flush=True)

if __name__=='__main__':
    from export_web import export
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-detail-v4.blend'))
    build(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    export(bpy.context.scene)
