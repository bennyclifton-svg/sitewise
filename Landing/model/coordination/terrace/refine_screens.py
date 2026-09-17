"""Apply the user's stair/rear references to both saved terrace concepts.

Full-height painted stair battens, folded open metal mesh, pale garden privacy
walls and a curved brick seat are separate named components, not image overlays.
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
N=int(sys.argv[-1])
W=49/N
folder=HERE/f'option-{N}'
bpy.ops.wm.open_mainfile(filepath=str(folder/f'terrace-{N}.blend'))
scene=bpy.context.scene
white=bpy.data.materials['Plasterboard ivory']
timber=bpy.data.materials['Oak joinery and framing']
brick=bpy.data.materials['Warm brick 1']
for obj in list(scene.objects):
    if obj.get('sw_reference_refinement'):bpy.data.objects.remove(obj,do_unlink=True)


def mesh(name,verts,faces,system,material,owner):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(f'TH{owner:02} | {name}',data)
    bpy.data.collections[system.title()].objects.link(obj)
    data.materials.append(material)
    obj['sw_system']=system;obj['sw_dwelling']=owner
    obj['sw_reference_refinement']=True
    obj['sw_status']='Reference-inspired concept; fixings and guarding to be resolved'
    return obj


def box(name,lo,hi,system,material,owner):
    x,y,z=lo;a,b,c=hi
    return mesh(name,[(x,y,z),(a,y,z),(a,b,z),(x,b,z),(x,y,c),(a,y,c),(a,b,c),(x,b,c)],
        [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],system,material,owner)


for i in range(N):
    owner=i+1;x=i*W;sx=x+W-2.25
    box('Electrical riser plasterboard enclosure',(x+3.855,6.53,.35),(x+4.025,6.72,9.32),'interiors',white,owner)
    # Reposition the garage lining slightly to preserve the circulation allowance.
    for obj in scene.objects:
        if obj.get('sw_dwelling')==owner and 'Garage side separation' in obj.name:
            for v in obj.data.vertices:
                v.co.x=x+(3.63 if v.co.x-x<3.775 else 3.78)
    for base in (.35,3.45,6.55):
        box('Service bulkhead closing fascia',(x+2.7,6.6,base+2.48),(x+4.08,6.65,base+2.96),'interiors',white,owner)
        for j in range(32):
            yy=3+j*.105
            box('Painted stair screen batten',(sx-.03,yy,base+.055),(sx+.03,yy+.03,base+2.7),'interiors',white,owner)
        for zz in (base+.03,base+2.7):
            box('Stair screen frame',(sx-.04,2.99,zz),(sx+.04,6.33,zz+.045),'interiors',white,owner)
        box('Stair screen timber handrail',(sx+.06,3,base+.98),(sx+.10,5.2,base+1.025),'interiors',timber,owner)
    # Folded perforated rear guard: actual open grid geometry, not a texture.
    # Each rectangular cell has thin perimeter ribs on a shallow diamond fold.
    verts=[];faces=[]
    width=3.2;height=1.05;columns=92;rows=30
    def point(u,v):
        panel=(u*4)%1
        fold=max(0,1-abs(2*panel-1)-abs(2*v-1))
        return (x+.5+u*width,12.09+.14*fold,3.6+v*height)
    def quad(u0,u1,v0,v1):
        k=len(verts);verts.extend([point(u0,v0),point(u1,v0),point(u1,v1),point(u0,v1)])
        faces.append((k,k+1,k+2,k+3))
    rib=.005
    for a in range(columns):
        for b in range(rows):
            u=a/columns;v=b/rows
            quad(u,u+rib/width,v,(b+1)/rows)
            quad(u,(a+1)/columns,v,v+rib/height)
    mesh('Folded perforated rear metal screen',verts,faces,'architecture',white,owner)
    for xx in (x+.49,x+3.7):
        box('Rear screen side frame',(xx,12.06,3.58),(xx+.025,12.11,4.69),'architecture',white,owner)
    for zz in (3.58,4.66):
        box('Rear screen horizontal frame',(x+.49,12.055,zz),(x+3.725,12.1,zz+.025),'architecture',white,owner)
    # Front portion of the garden boundary becomes a solid pale privacy wall.
    box('Pale rear terrace privacy wall',(x+.1,12,.1),(x+.24,14.4,1.85),'landscape',white,owner)
    # Curved seat / planting edge in the garden, built from individual brick units.
    cx=x+2.05;cy=15.3
    for course in range(5):
        for j in range(17):
            a=math.radians(25+j*7+(3.5 if course%2 else 0))
            b=a+math.radians(6.55)
            r0,r1=1.15,1.48
            z=.05+course*.077
            v=[(cx+r*math.cos(t),cy+r*math.sin(t),h) for h in (z,z+.07) for r,t in ((r0,a),(r1,a),(r1,b),(r0,b))]
            mesh('Curved garden seat brick',v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'landscape',brick,owner)
    for j in range(22):
        a=math.radians(25+j*5.45);b=a+math.radians(5.0)
        v=[(cx+r*math.cos(t),cy+r*math.sin(t),h) for h in (.435,.5) for r,t in ((1.13,a),(1.5,a),(1.5,b),(1.13,b))]
        mesh('Curved seat brick coping',v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'landscape',brick,owner)

manifest=json.loads((folder/'manifest.json').read_text())
manifest['count_by_system']=dict(Counter(o.get('sw_system') for o in scene.objects if o.get('sw_system')))
manifest['reference_refinements']=['Painted stair batten screens','Folded perforated rear screens','Pale garden privacy walls','Curved brick garden seats']
for home in manifest['homes']:home['ground_passage_clear_m']=round(W-2.25-.04-3.78,3)
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'terrace-{N}.blend'))
bpy.ops.export_scene.gltf(filepath=str(folder/f'terrace-{N}.glb'),export_format='GLB',
    export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
if N==7:
    data=bpy.data.cameras.new('Stair screen interior');cam=bpy.data.objects.new('Stair screen interior',data)
    scene.collection.objects.link(cam);cam.location=(1.1,2.8,4.9)
    cam.rotation_euler=(Vector((4.85,4.75,4.9))-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=24
    light=bpy.data.lights.new('Interior softbox','AREA');light.energy=180;light.size=3
    obj=bpy.data.objects.new('Interior softbox',light);scene.collection.objects.link(obj);obj.location=(2,4,5.9)
    scene.camera=cam;scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.cycles.samples=32
    scene.render.filepath=str(folder/'stair-detail.png');bpy.ops.render.render(write_still=True)
    if '--stair-only' in sys.argv:sys.exit(0)
    obj.hide_render=True
    scene.camera=scene.objects['Garden perspective']
    scene.render.resolution_x=1600;scene.render.resolution_y=1000
    scene.render.filepath=str(folder/'rear.png');bpy.ops.render.render(write_still=True)
    data=bpy.data.cameras.new('Garden screen detail');cam=bpy.data.objects.new('Garden screen detail',data)
    scene.collection.objects.link(cam);cam.location=(-4,22,7)
    cam.rotation_euler=(Vector((3.2,12.8,3.2))-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=42
    scene.camera=cam;scene.render.filepath=str(folder/'rear-detail.png');bpy.ops.render.render(write_still=True)
