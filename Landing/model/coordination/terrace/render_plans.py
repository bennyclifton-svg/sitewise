"""Render labelled, uncropped horizontal plan cuts from a saved model."""
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

HERE=Path(__file__).resolve().parent
N=int(sys.argv[-1])
W=49/N
dwelling=int(sys.argv[sys.argv.index('--dwelling')+1]) if '--dwelling' in sys.argv else 1
folder=HERE/f'option-{N}'
bpy.ops.wm.open_mainfile(filepath=str(folder/f'terrace-{N}.blend'))
scene=bpy.context.scene
scene.camera=scene.objects['Plan']
scene.camera.location.x=(dwelling-.5)*W
mirrored=dwelling in scene.get('sw_mirrored_dwellings',[])
reference_plan=bool(scene.get('sw_planning_basis'))
scene.camera.data.ortho_scale=20.5 if reference_plan else 15.5
scene.camera.location.y=7.7 if reference_plan else 6
scene.render.resolution_x=1000
scene.render.resolution_y=1400
scene.cycles.samples=16
originals={}
for level,z in enumerate((.35,3.45,6.55)):
    if '--roof-only' in sys.argv and level!=2:continue
    for obj,data in originals.items():obj.data=data
    originals={}
    for obj in scene.objects:
        if obj.type not in {'MESH','CURVE'}:continue
        points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
        low=min(p.z for p in points);high=max(p.z for p in points)
        obj.hide_render=obj.get('sw_dwelling')!=dwelling or low>z+1.15 or high<z-.24
        if not obj.hide_render and obj.type=='MESH' and high>z+1.15:
            originals[obj]=obj.data
            obj.data=obj.data.copy()
            bm=bmesh.new();bm.from_mesh(obj.data)
            bmesh.ops.transform(bm,matrix=obj.matrix_world,verts=list(bm.verts))
            result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                plane_co=(0,0,z+1.15),plane_no=(0,0,1),clear_outer=True,dist=.00001)
            edges=[e for e in result['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
            if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
            bmesh.ops.transform(bm,matrix=obj.matrix_world.inverted(),verts=list(bm.verts))
            bm.to_mesh(obj.data);bm.free()
        elif not obj.hide_render and obj.type=='CURVE' and high>z+1.15:
            obj.hide_render=True
    positions=[('GARAGE',1.8,3),('ENTRY',W-1.1,1.8),('STAIR',W-1.2,4.7),
        ('GARDEN ROOM',2,9.2),('BATH',W-1.2,8),('LAUNDRY',1.2,7.55)] if level==0 else (
        [('LOGGIA',2.1,.9),('LIVING',2.1,4.2),('DINING',2.1,8.8),('KITCHEN',2.1,10.2),
         ('STAIR',W-1.2,4.7),('BATH',W-1.2,8)] if level==1 else
        [('BEDROOM 1',2.3,2.2),('LANDING',2.4,6.8),('BEDROOM 2',2.3,10.9),('BATH',W-1.2,8)])
    labels=[]
    if reference_plan:
        positions=[('GARAGE',1.8,3),('ENTRY',W-1.1,1.8),('STAIR',W-1.2,4.7),
            ('POWDER',W-1.2,7.5),('KITCHEN',2.25,9),('DINING',4.9,10.7),('LIVING',2.7,12.1)] if level==0 else (
            [('BALCONY',2.1,.9),('BEDROOM 3',2.1,2.4),('BEDROOM 4',2.1,10.8),
             ('LAUNDRY',W-1.2,12.6),('STAIR',W-1.2,4.7),('BATH',W-1.2,8)] if level==1 else
            [('BEDROOM 2',2.1,2.2),('LANDING',2.1,6.8),('MASTER BEDROOM',2.3,11),('WALK-IN ROBE',1.7,10),('BATH',W-1.2,8)])
        if level>0:positions.append(('REAR BALCONY',W/2,15.5))
    positions.extend([(f'TYPICAL HOME / {W:.2f} m frontage',W/2,17.2 if reference_plan else 13),
                      ('STREET',W/2,-.7)])
    for label,x,y in positions:
        data=bpy.data.curves.new('Plan label','FONT');data.body=label;data.size=.18;data.align_x='CENTER'
        obj=bpy.data.objects.new(label,data);scene.collection.objects.link(obj)
        data.materials.append(bpy.data.materials['Bronze charcoal metal'])
        obj.location=((dwelling-1)*W+(W-x if mirrored else x),y,z+1.2);labels.append(obj)
    prefix='plan' if dwelling==1 else f'plan-TH{dwelling:02}'
    scene.render.filepath=str(folder/f'{prefix}-{level}.png')
    bpy.ops.render.render(write_still=True)
    for obj in labels:bpy.data.objects.remove(obj,do_unlink=True)
