"""Rear pergolas, breakfast settings and varied planting on the preserved v7 facade."""
import bpy
import json
import math
import random
import sys
from pathlib import Path
from mathutils import Vector, Euler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_integrated import material
from export_web import export


def bounds(obj):
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    return Vector([min(p[i] for p in points) for i in range(3)]), Vector([max(p[i] for p in points) for i in range(3)])


def apply(scene):
    rng = random.Random(1709)
    group = bpy.data.collections.new('Garden | Rear living')
    scene.collection.children.link(group)
    timber = material('Garden | Weathered oak', '#A68B6C', .68)
    bark = material('Garden | Bark', '#776B5A', .9)
    foliage = [material('Garden | '+name, colour, .86) for name, colour in
               [('Olive foliage', '#75846A'), ('Silver foliage', '#96A28B'), ('Deep foliage', '#586D5D')]]
    created = []

    def mesh(name, verts, faces, mat, system='landscape'):
        data = bpy.data.meshes.new('Garden | '+name)
        data.from_pydata(verts, [], faces); data.update()
        obj = bpy.data.objects.new(data.name, data); group.objects.link(obj)
        obj.data.materials.append(mat)
        obj['sw_system'] = system
        obj['sw_label'] = name
        obj['sw_provenance'] = 'Illustrative rear garden and outdoor living arrangement'
        created.append(obj)
        return obj

    def box(name, pos, size, mat=timber, system='landscape'):
        verts = [(pos[0]+x*size[0]/2, pos[1]+y*size[1]/2, pos[2]+z*size[2]/2)
                 for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        obj = mesh(name, verts, [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)], mat, system)
        bevel = obj.modifiers.new('Soft timber edges', 'BEVEL'); bevel.width=.007; bevel.segments=2
        return obj

    def branch(name, a, b, radius, mat=bark, end_radius=None):
        a,b = Vector(a),Vector(b)
        rotation = (b-a).to_track_quat('Z','Y')
        verts=[]
        for centre,r in [(a,radius),(b,end_radius if end_radius is not None else radius*.58)]:
            verts.extend(tuple(centre+rotation@Vector((r*math.cos(k*math.tau/8),r*math.sin(k*math.tau/8),0))) for k in range(8))
        faces=[tuple(reversed(range(8))),tuple(range(8,16))]+[(k,(k+1)%8,(k+1)%8+8,k+8) for k in range(8)]
        obj=mesh(name,verts,faces,mat)
        for p in obj.data.polygons[2:]: p.use_smooth=True
        return obj

    def leaves(name, centre, radii, count, mat, leaf_length=.24):
        verts=[];faces=[]
        for _ in range(count):
            # Discrete gently folded leaves create an open crown, without spherical proxy meshes.
            direction=Vector((rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-1,1)))
            if direction.length < .01: direction=Vector((1,0,0))
            direction.normalize(); direction*=rng.random()**.45
            c=Vector(centre)+Vector([direction[i]*radii[i] for i in range(3)])
            length=leaf_length*rng.uniform(.75,1.3); width=length*.32
            rotation=Euler((rng.uniform(-.8,.8),rng.uniform(-.8,.8),rng.uniform(0,math.tau))).to_matrix()
            shape=[(-length/2,0,0),(0,-width/2,0),(length/2,0,0),(0,width/2,0),(0,0,width*.2)]
            offset=len(verts);verts.extend(tuple(c+rotation@Vector(p)) for p in shape)
            faces.extend(tuple(offset+i for i in f) for f in [(0,1,4),(1,2,4),(2,3,4),(3,0,4)])
        return mesh(name,verts,faces,mat)

    def grass(name,x,y,height,mat):
        verts=[];faces=[]
        for k in range(15):
            angle=k*2.4; reach=rng.uniform(.16,.36); h=height*rng.uniform(.7,1.1)
            side=Vector((math.cos(angle+math.pi/2),math.sin(angle+math.pi/2),0))*.026
            a=Vector((x,y,.10));b=a+Vector((math.cos(angle)*reach*.35,math.sin(angle)*reach*.35,h*.65));c=a+Vector((math.cos(angle)*reach,math.sin(angle)*reach,h))
            n=len(verts);verts.extend(tuple(p) for p in [a-side,a+side,b-side*.65,b+side*.65,c])
            faces.extend([(n,n+1,n+3,n+2),(n+2,n+3,n+4)])
        mesh(name,verts,faces,mat)

    lawns=sorted((o for o in scene.objects if o.name.startswith('V3 | Private lawn ')),key=lambda o:bounds(o)[0].y)
    patios=sorted((o for o in scene.objects if o.name.startswith('SLA - 011_Floorboards - 03')),key=lambda o:bounds(o)[0].y)
    assert len(lawns)==len(patios)==5
    removed=[]
    for obj in list(scene.objects):
        if obj.name.startswith('V3 | Shrub '):
            removed.append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)
    records=[]
    shapes=[('spreading',3.6,1.02),('upright',4.15,.72),('multi-stem',3.25,1.08),('layered',3.85,.95),('open-vase',4.0,.88)]
    for i,(lawn,patio) in enumerate(zip(lawns,patios)):
        lo,hi=bounds(lawn);pl,ph=bounds(patio)
        cy=max(lo.y+1.95,min(hi.y-1.95,(pl.y+ph.y)/2))
        floor=ph.z
        width=min(3.65,hi.y-lo.y-.7)
        xa,xb=5.52,ph.x-.12
        top=floor+2.60
        prefix=f'Townhouse {i+1}'
        ledger=box(prefix+' awning wall ledger',(xa,cy,top-.10),(.10,width,.20),system='architecture')
        beam=box(prefix+' awning outer beam',(xb,cy,top-.10),(.14,width+.12,.20),system='architecture')
        for side in (-1,1):
            box(prefix+f' awning post {side}',(xb,cy+side*(width/2-.12),(floor+top-.20)/2),(.12,.12,top-.20-floor),system='architecture')
        slats=round(width/.22)+1
        for k in range(slats):
            box(prefix+f' awning slat {k+1}',((xa+xb)/2,cy-width/2+k*width/(slats-1),top+.055),(xb-xa+.28,.075,.11),system='architecture')
        # Pergolas belong to the envelope and are also visible in the landscape view.
        for obj in created:
            if obj.name.startswith('Garden | '+prefix+' awning'): obj['sw_service_systems']='["landscape"]'
        tx=(xa+xb)/2
        for k in range(7):
            box(prefix+f' breakfast table slat {k+1}',(tx-.39+k*.13,cy,floor+.745),(.115,.82,.045))
        for dx in (-.30,.30):
            for dy in (-.28,.28):
                box(prefix+' table leg',(tx+dx,cy+dy,floor+.35),(.055,.055,.70))
        for side in (-1,1):
            chair_y=cy+side*.87
            for k in range(5):
                box(prefix+f' chair {side} seat {k}',(tx-.20+k*.10,chair_y,floor+.45),(.085,.46,.035))
            for dx in (-.19,.19):
                for dy in (-.18,.18):
                    box(prefix+' chair leg',(tx+dx,chair_y+dy,floor+.22),(.04,.04,.44))
                box(prefix+' chair back upright',(tx+dx,chair_y+side*.20,floor+.64),(.04,.04,.40))
            for k in range(3):
                box(prefix+' chair back slat',(tx,chair_y+side*.20,floor+.59+k*.09),(.46,.035,.065))
        silhouette,height,spread=shapes[i]
        tree_x=10.35
        tree_y=cy+(.65 if i%2 else -.55)
        base=Vector((tree_x,tree_y,.10))
        fork=base+Vector((.10*(-1 if i%2 else 1),.08,height*.43))
        branch(prefix+' tree trunk',base,fork,.065,end_radius=.04)
        for k in range(8):
            angle=k*2.4+i*.6
            reach=spread*(.5 if k==7 else .8)
            z=height*(.66+.25*(k%3)/2)
            if silhouette=='upright': z=height*(.50+.45*k/7)
            end=Vector((tree_x+math.cos(angle)*reach,tree_y+math.sin(angle)*reach,z))
            origin=base+Vector((0,0,.12)) if silhouette=='multi-stem' and k<3 else fork
            branch(prefix+f' tree branch {k}',origin,end,.022,end_radius=.006)
            leaves(prefix+f' tree foliage {k}',end,(spread*.53,spread*.50,.48 if silhouette!='upright' else .58),75,foliage[(i+k)%3],.27)
        for k in range(7):
            gy=lo.y+.55+(hi.y-lo.y-1.1)*k/6
            grass(prefix+f' border grass {k}',11.35+(.1 if k%2 else -.12),gy,.38+.15*(k%3),foliage[(i+k)%3])
        for k in range(2):
            sy=max(lo.y+.55,min(hi.y-.55,cy+(-1 if k==0 else 1)*1.75))
            leaves(prefix+f' low spreading shrub {k}',(10.05,sy,.52),(.50,.45,.38),110,foliage[(i+k)%3],.19)
        records.append(dict(dwelling=i+1,patio_elevation=round(floor,3),awning_width=width,projection=round(xb-xa,3),posts=2,slats=slats,table=1,chairs=2,tree_shape=silhouette,tree_height=height,garden_y=[lo.y,hi.y]))
    bpy.context.view_layer.update()
    for obj in created:
        lo,hi=bounds(obj)
        assert lo.x>5.35 and hi.x<12, f'Garden object outside rear garden: {obj.name}'
    result=dict(source='sitewise-facade-v7.blend',checkpoint='sitewise-gardens-v8.blend',gardens=records,removed_ball_shrubs=len(removed),added_objects=len(created))
    (HERE/'garden-revision.json').write_text(json.dumps(result,indent=2))
    print('GARDENS_VERIFIED',json.dumps(result),flush=True)

if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-facade-v7.blend'))
    apply(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-gardens-v8.blend'))
    export(bpy.context.scene)

