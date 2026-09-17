"""Verify authored coordination invariants; not an engineering clash certificate."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
count=int(sys.argv[-1])
folder=HERE/f'option-{count}'
bpy.ops.wm.open_mainfile(filepath=str(folder/f'terrace-{count}.blend'))
scene=bpy.context.scene
manifest=json.loads((folder/'manifest.json').read_text())
assert manifest['frontage_m']==49
assert len(manifest['homes'])==count
expected={'architecture','structure','electrical','mechanical','hydraulic','interiors','civil','landscape'}
assert set(manifest['count_by_system'])==expected
checks=[]
for dwelling in range(1,count+1):
    objects=[o for o in scene.objects if o.get('sw_dwelling')==dwelling]
    names='\n'.join(o.name for o in objects)
    roof_family='Raked timber roof rafter' if scene.get('sw_detail_review') else 'Timber flat roof'
    for required in ('Strip footing','Floor slab','Masonry bearing wall','Roof steel',roof_family,
         'plasterboard','curtain','Distribution board','lighting circuit','power radial','condenser',
         'refrigerant','Soil and vent','Water service','Kitchen supply','standing seam','Balcony drain'):
        assert required in names,(dwelling,required)
    assert manifest['homes'][dwelling-1]['ground_passage_clear_m']>=.9
    # Nothing may cap the U-stair void at either upper slab level.
    x=(dwelling-1)*49/count
    sx=x+49/count-2.25
    test=Vector((sx+1,4.5,3.35))
    if manifest['homes'][dwelling-1].get('mirrored'):test.x=2*x+49/count-test.x
    for obj in objects:
        if 'Floor slab' not in obj.name:continue
        pts=[obj.matrix_world@Vector(p) for p in obj.bound_box]
        lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)))
        hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
        for height in (3.35,6.45):
            test.z=height
            assert not all(lo[i]<test[i]<hi[i] for i in range(3)),obj.name
    checks.append(f'TH{dwelling:02}: systems, component families, passage and stair void verified')
    if scene.get('sw_planning_basis'):
        assert manifest['homes'][dwelling-1]['bedrooms']==4
        assert len([o for o in objects if 'bedside' not in o.name and ('Front bedroom bed' in o.name or 'Rear bedroom bed' in o.name)])==4
        assert 'Rear balcony structural slab' in names
        def limits(obj):
            pts=[obj.matrix_world@Vector(p) for p in obj.bound_box]
            return ([min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)])
        chases=[o for o in objects if 'Wet service riser lining' in o.name]
        doors=[o for o in objects if 'door open' in o.name and ('powder' in o.name or 'bathroom' in o.name)]
        for door in doors:
            a,b=limits(door)
            for chase in chases:
                c,d=limits(chase)
                assert not all(a[i]<d[i] and b[i]>c[i] for i in range(3)),door.name
        checks.append(f'TH{dwelling:02}: four beds and rear balcony slabs verified')
for obj in scene.objects:
    if obj.type=='MESH':
        assert all(math.isfinite(v) for p in obj.data.vertices for v in p.co),obj.name
if scene.get('sw_detail_review'):
    for dwelling in range(1,count):
        side_a='left' if manifest['homes'][dwelling-1].get('mirrored') else 'right'
        side_b='right' if manifest['homes'][dwelling].get('mirrored') else 'left'
        a=next(o for o in scene.objects if o.get('sw_dwelling')==dwelling and 'Roof front '+side_a in o.name)
        b=next(o for o in scene.objects if o.get('sw_dwelling')==dwelling+1 and 'Roof front '+side_b in o.name)
        assert abs(limits(a)[1][0]-limits(b)[0][0])<.0001,'Open roof joint'
    assert not any('Timber flat roof joist' in o.name for o in scene.objects)
    checks.append('Roof sheets meet at each party boundary; superseded flat roof joists removed')
routes=json.loads((folder/'service-routes.json').read_text())
for route in routes:
    assert route['radius']>0
    assert all(math.dist(a,b)>0 for a,b in zip(route['points'],route['points'][1:])),route['name']
result=dict(status='pass',checks=checks,objects=sum(manifest['count_by_system'].values()),
    routes_checked=len(routes),scope='Presence, finite geometry, stair openings, passage allowance and nonzero routes',
    exclusions=['No engineering sizing','No exhaustive inter-service or structural clash detection',
                'No swept path, solar, acoustic, fire or planning assessment'])
(folder/'validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
