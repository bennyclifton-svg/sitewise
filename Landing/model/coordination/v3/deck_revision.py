"""Low-polygon rear decks, supported pergola rafters and relocated garden pits."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from garden_revision import bounds
from build_integrated import material
from wet_services import _tube
from export_web import export


def apply(scene):
    timber=[material('Garden | Deck board '+str(i),colour,.75) for i,colour in enumerate(('#A18A70','#AA9379','#A58D73'))]
    frame=bpy.data.materials['Garden | Weathered oak']
    additions=[]
    def box(name,lo,hi,mat):
        verts=[(x,y,z) for z in (lo[2],hi[2]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])]
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
        mesh.materials.append(mat);mesh.update()
        obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
        obj['sw_system']='landscape';obj['sw_service_systems']='[]'
        obj['sw_label']=name;additions.append(obj)
        return obj
    def reshape(obj,lo,hi):
        oldlo,oldhi=bounds(obj)
        inv=obj.matrix_world.inverted()
        for v in obj.data.vertices:
            p=obj.matrix_world@v.co
            for axis in range(3):p[axis]=lo[axis]+(p[axis]-oldlo[axis])/(oldhi[axis]-oldlo[axis])*(hi[axis]-lo[axis])
            v.co=inv@p
        obj.data.update()
    lawns=sorted((o for o in scene.objects if o.name.startswith('V3 | Private lawn ')),key=lambda o:bounds(o)[0].y)
    patios=sorted((o for o in scene.objects if o.name.startswith('SLA - 011_Floorboards - 03')),key=lambda o:bounds(o)[0].y)
    assert len(lawns)==len(patios)==5
    drains=json.loads((HERE/'civil-stormwater.json').read_text())
    moved={};records=[]
    for i,(lawn,patio) in enumerate(zip(lawns,patios),1):
        gl,gh=bounds(lawn);pl,ph=bounds(patio)
        floor=max(ph.z,.12)
        prefix=f'Garden | Townhouse {i}'
        objects=[o for o in scene.objects if o.name.startswith(prefix)]
        ledger=next(o for o in objects if 'awning wall ledger' in o.name)
        ll,lh=bounds(ledger)
        posts=[o for o in objects if 'awning post' in o.name]
        edge=max(bounds(o)[1].x for o in posts)+.18
        # Ground-floor cladding is recessed from the upper facade.
        wall=4.7482
        xa=wall-.015
        ya=max(gl.y+.06,min(pl.y,ll.y-.18));yb=min(gh.y-.06,max(ph.y,lh.y+.18))
        patio.hide_render=True
        count=math.ceil((edge-xa)/.145)
        pitch=(edge-xa)/count
        for k in range(count):
            box(prefix+f' deck board {k+1}',(xa+k*pitch+.003,ya,floor-.028),(xa+(k+1)*pitch-.003,yb,floor),timber[k%3])
        box(prefix+' deck outer fascia',(edge-.03,ya,floor-.14),(edge,yb,floor-.029),frame)
        for y in (ya,yb-.025):
            box(prefix+' deck side fascia',(xa,y,floor-.14),(edge,y+.025,floor-.029),frame)
        # Keep furniture grounded when the northern decks are lifted clear of the lawn.
        for obj in objects:
            if any(label in obj.name for label in ('breakfast table','table leg','chair ')):
                obj.location.z+=floor-ph.z
        roof=ph.z+2.54
        cy=(ll.y+lh.y)/2
        reshape(ledger,Vector((wall-.015,ll.y,roof-.10)),Vector((wall+.105,lh.y,roof)))
        ledger['sw_label']='100 mm wall-mounted trimmer supporting rafters'
        for obj in objects:
            lo,hi=bounds(obj)
            if 'awning slat' in obj.name:
                lo.x=wall-.005;lo.z=roof;hi.z=roof+.11
                reshape(obj,lo,hi)
            elif 'awning outer beam' in obj.name:
                lo.z=roof-.20;hi.z=roof;reshape(obj,lo,hi)
            elif 'awning post' in obj.name:
                lo.z=floor;hi.z=roof-.20;reshape(obj,lo,hi)
        key=f'House {i} rear pit'
        old=Vector(drains['nodes'][key])
        new=Vector(((edge+gh.x)/2,(gl.y+gh.y)/2,old.z))
        moved[key]=(old,new)
        drains['nodes'][key]=list(new)
        for obj in scene.objects:
            if obj.name.startswith('Storm | '+key) and not obj.get('sw_endpoint_ids'):
                obj.location.x+=new.x-old.x;obj.location.y+=new.y-old.y
                # Grate tops finish flush with the lawn; retain the invert and pipe grades.
                for v in obj.data.vertices:
                    if 'grate' in obj.name:v.co.z-=.0725
                    elif 'chamber' in obj.name and v.co.z>.10:v.co.z=.0475
        bpy.context.view_layer.update()
        assert edge>max(bounds(o)[1].x for o in posts)
        assert new.x-.253>edge and new.x+.253<gh.x
        assert abs(bounds(ledger)[1].z-roof)<.00001
        assert abs((bounds(ledger)[1].z-bounds(ledger)[0].z)-.10)<.00001
        records.append(dict(dwelling=i,boards=count,deck_top=round(floor,3),deck_bounds=[xa,edge,ya,yb],wall_x=wall,trimmer_depth=.10,rafter_seat=roof,drain=list(new)))
    changed_routes=0
    for route in drains['routes']:
        if route['start'] not in moved and route['end'] not in moved:continue
        points=route['points']
        if route['start'] in moved:points[0]=drains['nodes'][route['start']]
        if route['end'] in moved:points[-1]=drains['nodes'][route['end']]
        matches=[o for o in scene.objects if o.get('sw_endpoint_ids') and json.loads(o['sw_endpoint_ids'])==[route['start'],route['end']]]
        assert len(matches)==1,(route['start'],route['end'])
        obj=matches[0];oldmesh=obj.data
        verts,faces=_tube(points,route['radius'],12)
        mesh=bpy.data.meshes.new(oldmesh.name+' garden route');mesh.from_pydata(verts,[],faces);mesh.update()
        for mat in oldmesh.materials:mesh.materials.append(mat)
        obj.data=mesh;changed_routes+=1
    bpy.context.view_layer.update()
    for route in drains['routes']:
        assert (Vector(route['points'][0])-Vector(drains['nodes'][route['start']])).length<.00001
        assert (Vector(route['points'][-1])-Vector(drains['nodes'][route['end']])).length<.00001
    polygon_count=sum(len(o.data.polygons) for o in additions)
    assert polygon_count<1000
    (HERE/'civil-stormwater-decks.json').write_text(json.dumps(drains,indent=2))
    result=dict(source='sitewise-gardens-v8.blend',checkpoint='sitewise-decks-v9.blend',decks=records,added_deck_polygons=polygon_count,rerouted_connections=changed_routes,trees_unchanged=True)
    (HERE/'deck-revision.json').write_text(json.dumps(result,indent=2))
    print('DECK_CHECK_PASS',json.dumps(result),flush=True)

if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-gardens-v8.blend'))
    apply(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-decks-v9.blend'))
    export(bpy.context.scene)
