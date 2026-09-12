"""Seat shorter piles below existing strip footings and remove the sample roller door."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from replicate_dwellings import bounds
from export_web import export
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-sample-house-v19.blend'))
scene=bpy.context.scene
audit=dict(removed_caps=[],removed_door=[],piles=[],slabs=[])
slabs=[o for o in scene.objects if not o.hide_render and o.type=='MESH' and 'slab 200mm' in o.name]
original={o.name:[tuple(v.co) for v in o.data.vertices] for o in slabs}
for obj in list(scene.objects):
    if obj.get('sw_component')=='pile_cap':
        audit['removed_caps'].append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)
    elif str(obj.get('sw_motion','')).startswith('door:') or obj.name in ('Detail | Garage roller hood','DOO - 018_Paint - Titanium White_0.002','DOO - 018_Paint - Golden Ochre_0'):
        audit['removed_door'].append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)
for number in range(1,6):
    prefix='' if number==1 else f'TH{number:02} | '
    slab=scene.objects[prefix+'V3 | RC ground slab 200mm'];lo,hi=bounds(slab)
    strips=[o for o in scene.objects if o.name.startswith(prefix+'Detail | Perimeter strip footing ')]
    assert len(strips)==4,(number,len(strips))
    anchors=[(lo.x+(hi.x-lo.x)*i/3,y) for y in (lo.y,hi.y) for i in range(4)]
    anchors += [(x,lo.y+(hi.y-lo.y)*i/3) for x in (lo.x,hi.x) for i in (1,2)]
    piles=sorted((o for o in scene.objects if o.get('sw_component')=='pile' and o.get('sw_dwelling')==number),key=lambda o:o.name)
    assert len(piles)==len(anchors)==12
    for obj,(x,y) in zip(piles,anchors):
        support=next(o for o in strips if bounds(o)[0].x<=x<=bounds(o)[1].x and bounds(o)[0].y<=y<=bounds(o)[1].y)
        top=bounds(support)[0].z+.025
        oldlo,oldhi=bounds(obj);cx=(oldlo.x+oldhi.x)/2;cy=(oldlo.y+oldhi.y)/2
        obj.data=obj.data.copy();inv=obj.matrix_world.inverted()
        for v in obj.data.vertices:
            p=obj.matrix_world@v.co;p.x+=x-cx;p.y+=y-cy
            p.z=top-2.25+(p.z-oldlo.z)/(oldhi.z-oldlo.z)*2.25
            v.co=inv@p
        audit['piles'].append(dict(name=obj.name,depth_m=2.25,strip=support.name,head=[x,y,top]))
for slab in slabs:
    assert original[slab.name]==[tuple(v.co) for v in slab.data.vertices]
    lo,hi=bounds(slab);assert abs(hi.z-lo.z-.2)<1e-4
    for mat in slab.data.materials:
        assert mat.diffuse_color[3]==1
        if mat.use_nodes:
            bsdf=mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:assert bsdf.inputs['Alpha'].default_value==1
    audit['slabs'].append(dict(name=slab.name,thickness_m=hi.z-lo.z,geometry_unchanged=True))
assert len(audit['removed_caps'])==60 and len(audit['piles'])==60 and len(slabs)==15
assert not any(str(o.get('sw_motion','')).startswith('door:') for o in scene.objects)
scene['sw_foundation_v20']=json.dumps(audit)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-solid-foundations-v20.blend'))
(HERE/'solid-foundations-v20-audit.json').write_text(json.dumps(audit,indent=2))
export(scene)
print('SOLID_FOUNDATIONS_PASS: 60 piles at 2.25 m seated under strips; no caps/roller door; 15 solid 200 mm slabs unchanged',flush=True)
