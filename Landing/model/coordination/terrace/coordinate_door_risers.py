"""Move wet-room door openings clear of the service riser in saved studies."""
from pathlib import Path
import sys
import bpy

N=int(sys.argv[-1]);W=49/N
folder=Path(__file__).resolve().parent/f'option-{N}'
bpy.ops.wm.open_mainfile(filepath=str(folder/f'terrace-{N}.blend'))
scene=bpy.context.scene
if not scene.get('sw_wet_door_clearance'):
    for obj in list(scene.objects):
        if obj.type!='MESH' or not any(s in obj.name for s in ('Ground powder entry','Upper bathroom entry')):continue
        rx=(obj.get('sw_dwelling')-1)*W+W-2.25
        if 'door head' in obj.name or 'door open' in obj.name:
            for v in obj.data.vertices:v.co.x+=.6
        elif 'drywall' in obj.name:
            lo=min(v.co.x for v in obj.data.vertices);hi=max(v.co.x for v in obj.data.vertices)
            if abs(hi-rx)<.001:
                for v in obj.data.vertices:
                    if abs(v.co.x-hi)<.001:v.co.x+=.6
            elif abs(lo-(rx+.85))<.001:
                for v in obj.data.vertices:
                    if abs(v.co.x-lo)<.001:v.co.x+=.6
        elif 'timber stud' in obj.name:
            centre=sum(v.co.x for v in obj.data.vertices)/len(obj.data.vertices)
            if rx+.6<centre<rx+1.45:
                target=rx+(.35 if centre<rx+1 else .56)
                for v in obj.data.vertices:v.co.x+=target-centre
    scene['sw_wet_door_clearance']=True
bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'terrace-{N}.blend'))
bpy.ops.export_scene.gltf(filepath=str(folder/f'terrace-{N}.glb'),export_format='GLB',
    export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
