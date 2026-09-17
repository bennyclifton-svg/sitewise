"""Longitudinal concept section through TH01, loggia and roof rooms."""
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

HERE=Path(__file__).resolve().parent
folder=HERE/'option-7'
bpy.ops.wm.open_mainfile(filepath=str(folder/'terrace-7.blend'))
scene=bpy.context.scene
for obj in scene.objects:
    if obj.type not in {'MESH','CURVE'}:continue
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    obj.hide_render=obj.get('sw_dwelling')!=1 or min(p.x for p in points)>2.0
    if obj.hide_render:continue
    if obj.type=='MESH':
        obj.data=obj.data.copy()
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.transform(bm,matrix=obj.matrix_world,verts=list(bm.verts))
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
            plane_co=(2.0,0,0),plane_no=(1,0,0),clear_outer=True,dist=.00001)
        bmesh.ops.transform(bm,matrix=obj.matrix_world.inverted(),verts=list(bm.verts))
        bm.to_mesh(obj.data);bm.free()
    elif max(p.x for p in points)>2.0:obj.hide_render=True
data=bpy.data.cameras.new('Longitudinal section')
cam=bpy.data.objects.new('Longitudinal section',data);scene.collection.objects.link(cam)
cam.location=(25,8.2,4.4)
cam.rotation_euler=(Vector((3,8.2,4.4))-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=19.5
scene.camera=cam
scene.render.resolution_x=1400;scene.render.resolution_y=1100
scene.cycles.samples=20
scene.render.filepath=str(folder/'section.png')
bpy.ops.render.render(write_still=True)
