"""Independently verify the saved replication and render a discipline overview."""
import bpy
import json
import sys
from pathlib import Path
from collections import Counter
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-all-dwellings-v12.blend'))
scene = bpy.context.scene
records = json.loads(scene['sw_dwelling_replication'])
assert len(records) == 5
checked = 0
for record in records[1:]:
    number = record['dwelling']
    matrix = Matrix(record['matrix'])
    copies = [o for o in scene.objects if o.get('sw_dwelling') == number and o.get('sw_replica_source')]
    assert dict(Counter(o['sw_system'] for o in copies)) == records[0]['counts']
    for obj in copies:
        original = scene.objects[obj['sw_replica_source']]
        expected = matrix @ original.matrix_world
        assert max(abs(a-b) for row_a,row_b in zip(expected,obj.matrix_world) for a,b in zip(row_a,row_b)) < .0001
        assert obj.data == original.data, obj.name
        assert not obj.hide_render
        checked += 1
    assert all(scene.objects[n].hide_render for n in record['replaced_source_slabs'])
assert [r['dwelling'] for r in records if r['mirrored']] == [3,5]
assert sum('dwelling distribution board' in o.name and not o.hide_render for o in scene.objects) == 5
assert sum(o.name == 'Development | Shared sanitary collector' for o in scene.objects) == 1
report = {'copied_objects_checked':checked, 'dwelling_count':5,
          'mirrored_dwellings':[3,5], 'per_dwelling_counts':records[0]['counts'],
          'checks':['Saved transforms match source placement matrices', 'Mesh and curve data preserved',
                    'Replaced source slabs hidden', 'Five existing distribution boards preserved']}
(HERE/'dwelling-replication-check.json').write_text(json.dumps(report,indent=2))
print('PASS_DWELLINGS',report,flush=True)
if '--render' not in sys.argv:
    sys.exit(0)
for obj in scene.objects:
    if obj.type == 'LIGHT' or obj.get('sw_system') not in ('structure','electrical','mechanical','hydraulic'):
        obj.hide_render = True
    if obj.get('sw_dwelling') is None:
        obj.hide_render = True
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (.20,.24,.28,1)
bg.inputs['Strength'].default_value = .5
def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for name, position, energy in [('Key',(-20,-20,30),12000),('Fill',(20,15,25),9000)]:
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.shape='DISK';data.size=15
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=position;aim(obj,(0,0,4))
data=bpy.data.cameras.new('All dwellings review');data.type='ORTHO';data.ortho_scale=35
camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera)
camera.location=(-30,-29,25);aim(camera,(0,0,3.7));scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(HERE/'all-dwellings-services.png')
bpy.ops.render.render(write_still=True)
