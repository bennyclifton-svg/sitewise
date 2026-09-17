"""Render the current saved options, including the four-bedroom replan."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector

N=int(sys.argv[-1]);HERE=Path(__file__).resolve().parent;folder=HERE/f'option-{N}'
architecture_only='--architecture-only' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(folder/f'terrace-{N}.blend'))
scene=bpy.context.scene;scene.render.resolution_x=1600;scene.render.resolution_y=1000
scene.cycles.samples=20
scene.objects['Street perspective'].data.lens=40
if scene.get('sw_mirrored_dwellings'):
    scene.objects['Dwelling pair detail'].location.x+=49/N
scene.objects['Garden perspective'].location=(-14,52,23)
scene.objects['Garden perspective'].rotation_euler=(Vector((24,10,4))-scene.objects['Garden perspective'].location).to_track_quat('-Z','Y').to_euler()
scene.objects['Garden perspective'].data.lens=40
views={'street':'Street perspective','front':'Front elevation'}
if N==7:
    views.update(detail='Dwelling pair detail',rear='Garden perspective')
    if scene.get('sw_frontage_revision'):
        data=bpy.data.cameras.new('End elevation');cam=bpy.data.objects.new('End elevation',data);scene.collection.objects.link(cam)
        cam.location=(80,7.2,6.7);cam.rotation_euler=(Vector((49,7.2,6.7))-cam.location).to_track_quat('-Z','Y').to_euler()
        data.type='ORTHO';data.ortho_scale=21
        views.update(end='End elevation')
    if not architecture_only:views.update(coordination='Services and structure')
    if scene.get('sw_detail_review'):
        data=bpy.data.cameras.new('Roof frame detail');cam=bpy.data.objects.new('Roof frame detail',data);scene.collection.objects.link(cam)
        cam.location=(19,-17,19);cam.rotation_euler=(Vector((7,6.3,8.2))-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=45
        views.update({'roof-frame':'Roof frame detail'})
selected_views=None
if '--views' in sys.argv:
    selected_views=sys.argv[sys.argv.index('--views')+1].split(',')
    views={k:v for k,v in views.items() if k in selected_views}
for name,cam in views.items():
    scene.camera=scene.objects[cam]
    hidden=[]
    if name=='coordination':
        for s in ('Architecture','Interiors','Landscape','Civil'):bpy.data.collections[s].hide_render=True
    if name=='roof-frame':
        for o in scene.objects:
            if o.type not in {'MESH','CURVE'}:continue
            hidden.append((o,o.hide_render))
            o.hide_render=not (o.get('sw_system')=='structure' and o.get('sw_dwelling') in (1,2) and any(k in o.name for k in ('Roof steel','Raked timber','dormer','Privacy wedge','End window masonry lintel')))
    scene.render.filepath=str(folder/f'{name}.png');bpy.ops.render.render(write_still=True)
    for o,state in hidden:o.hide_render=state
    for s in ('Architecture','Interiors','Landscape','Civil'):bpy.data.collections[s].hide_render=False
if N==7 and (selected_views is None or 'rear-detail' in selected_views):
    light=bpy.data.lights.new('Entry softbox','AREA');light.energy=160;light.size=2
    obj=bpy.data.objects.new('Entry softbox',light);scene.collection.objects.link(obj);obj.location=(4.1,2.5,2.75)
    data=bpy.data.cameras.new('Stair reference detail');cam=bpy.data.objects.new('Stair reference detail',data);scene.collection.objects.link(cam)
    cam.location=(3.98,1.8,1.9);cam.rotation_euler=(Vector((5.2,4.8,1.9))-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=22
    scene.camera=cam;scene.render.filepath=str(folder/'stair-detail.png')
    if not architecture_only and selected_views is None:bpy.ops.render.render(write_still=True)
    obj.hide_render=True
    cam.location=(-5,27,9);cam.rotation_euler=(Vector((3.2,15,3.5))-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=42
    scene.render.filepath=str(folder/'rear-detail.png');bpy.ops.render.render(write_still=True)
