"""Build the approved warm-brick facade on v10, preserving source openings.

Brick faces are clipped to the actual covering polygons, not wall bounding boxes.
Window screens reference glazing objects; access checks use exact world vertices.
"""
import bpy
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_integrated import linear


def bounds(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def signature(obj):
    return hashlib.sha256(repr((tuple(tuple(r) for r in obj.matrix_world),
        [tuple(v.co) for v in obj.data.vertices], [tuple(p.vertices) for p in obj.data.polygons])).encode()).hexdigest()


def material(name, colour, roughness=.72, metallic=0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    rgb = (*linear(colour), 1)
    mat.diffuse_color = rgb
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = rgb
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Alpha'].default_value = 1
    return mat


def finish(obj, mat):
    obj.data = obj.data.copy()
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.material_index = 0


def clip(poly, axis, limit, greater):
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        inside_a = a[axis] >= limit if greater else a[axis] <= limit
        inside_b = b[axis] >= limit if greater else b[axis] <= limit
        if inside_a:
            out.append(a)
        if inside_a != inside_b:
            t = (limit-a[axis])/(b[axis]-a[axis])
            out.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(2)))
    return out


def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2


def intersects(a, b, margin=0):
    return all(a[1][i] > b[0][i]-margin and a[0][i] < b[1][i]+margin for i in range(3))


def covering_regions(source, axis, sign):
    """Union projected overlapping weatherboards into disjoint wall rectangles.

    A horizontal sweep keeps source opening boundaries while removing the lap
    overlap that would otherwise create coplanar flicker in the brick skin.
    """
    tangent=1-axis
    polys=[]
    normal_matrix=source.matrix_world.to_3x3().inverted().transposed()
    for face in source.data.polygons:
        normal=(normal_matrix@face.normal).normalized()
        if normal[axis]*sign < .1:
            continue
        poly=[(round((source.matrix_world@source.data.vertices[i].co)[tangent],4),
               round((source.matrix_world@source.data.vertices[i].co).z,4)) for i in face.vertices]
        if area(poly)>.000001:
            polys.append(poly)
    levels=sorted({p[1] for poly in polys for p in poly})
    rectangles=[]
    active={}
    for z0,z1 in zip(levels,levels[1:]):
        if z1-z0 < .00001:
            continue
        z=(z0+z1)/2
        spans=[]
        for poly in polys:
            cuts=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                if min(a[1],b[1])<=z<max(a[1],b[1]):
                    cuts.append(a[0]+(z-a[1])*(b[0]-a[0])/(b[1]-a[1]))
            if len(cuts)>=2:
                spans.append((min(cuts),max(cuts)))
        merged=[]
        for a,b in sorted(spans):
            if merged and a<=merged[-1][1]+.0003:
                merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else:
                merged.append((a,b))
        next_active={}
        for a,b in merged:
            key=(round(a,4),round(b,4))
            if key in active:
                rect=active.pop(key);rect[3]=z1
            else:
                rect=[key[0],key[1],z0,z1]
            next_active[key]=rect
        rectangles.extend(active.values());active=next_active
    rectangles.extend(active.values())
    return [[(a,z0),(b,z0),(b,z1),(a,z1)] for a,b,z0,z1 in rectangles]


def apply(scene):
    original = {o.name: signature(o) for o in scene.objects if o.type == 'MESH'}
    visible = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render]
    group = bpy.data.collections.new('Facade | Premium v11')
    scene.collection.children.link(group)
    bronze = material('Facade | Satin bronze', '#776550', .42, .55)
    timber = material('Facade | Balcony oak', '#AA8D68', .76)
    mineral = material('Facade | Mineral inset', '#C8BEAF')
    white = material('Facade | Warm limestone', '#E9E3D7')
    roof = material('Facade | Warm grey roof', '#BEBBB3', .86)
    mortar = material('Facade | Recessed lime mortar', '#CDC3B2', .95)
    bricks = [material('Facade | Sand brick '+str(i+1), c, .88) for i,c in enumerate(
        ['#D7C8B0','#DDCFBA','#D3C3AA','#E0D2BF','#D9CBB7'])]
    soil = material('Garden | Planter soil', '#4C493D', .95)
    green = bpy.data.materials['Garden | Olive foliage']
    added = []
    hidden = []
    records = dict(screens=[], brick_panels=[], balcony_bands=[], planters=[], access=[], source='sitewise-chalk-v10.blend')

    def mesh(name, verts, faces, mat, indices=None):
        data = bpy.data.meshes.new('Premium | '+name)
        data.from_pydata(verts, [], faces)
        data.update()
        obj = bpy.data.objects.new(data.name, data)
        group.objects.link(obj)
        for m in mat if isinstance(mat,list) else [mat]:
            data.materials.append(m)
        if indices:
            for p, index in zip(data.polygons, indices):
                p.material_index = index
        obj['sw_system'] = 'architecture'
        obj['sw_label'] = name
        obj['sw_provenance'] = 'Approved facade concept, 10 September 2026'
        added.append(obj)
        return obj

    def box(name, lo, hi, mat):
        verts = [(x,y,z) for z in (lo[2],hi[2]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])]
        return mesh(name, verts, [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)], mat)

    def hide(obj):
        obj.hide_render = True
        obj.hide_set(True)
        obj['premium_replaced_by'] = 'Facade | Premium v11'
        hidden.append(obj.name)

    # Retain the actual materials in both Blender and the texture-free web export.
    for obj in visible:
        name = obj.name
        if name.startswith('CI Tools Roof Covering') or name.startswith('RT -'):
            finish(obj, roof)
        elif name.startswith('DOO - 018') or name.startswith('Detail | Garage roller'):
            finish(obj, bronze)
        elif name.startswith('DOO - 019_Wood - Walnut'):
            finish(obj, timber)
        elif name.startswith('DOO - 020') and not obj.get('sw_glass'):
            finish(obj, bronze)
        elif name.startswith(('TOPRAIL','BALUSTER','POST -','RAIL -','INNER POST','PANEL -')) and not obj.get('sw_glass'):
            finish(obj, bronze)

    # Ground walls and middle-level side walls receive brick. Upper boards and
    # sheltered balcony/rear vertical cladding retain their lighter finishes.
    for source in visible:
        if not source.name.startswith('CI Tools Wall Covering'):
            continue
        lo, hi = bounds(source)
        axis = 0 if hi.x-lo.x < hi.y-lo.y else 1
        tangent = 1-axis
        height = hi.z-lo.z
        is_brick = height > 1 and (hi.z < 3.0 or (axis == 1 and hi.z < 5.7))
        if not is_brick:
            continue
        # Small companion end caps retain their existing geometry.
        if len(source.data.vertices) < 300:
            finish(source, bricks[1])
            continue
        sign = (1 if (lo.x+hi.x)/2 > 0 else -1) if axis == 0 else (
            -1 if any(abs((lo.y+hi.y)/2-y)<.2 for y in [-13.81,-7.04,4.42]) else 1)
        plane = (hi[axis] if sign > 0 else lo[axis]) + sign*.003
        verts, faces, indices = [], [], []
        base_verts, base_faces = [], []
        def point(u,z,offset):
            p=[0.,0.,z]; p[axis]=plane+sign*offset;p[tangent]=u
            return tuple(p)
        source.data.update()
        for poly in covering_regions(source,axis,sign):
            # (u,z) winding faces +X for Y-tangent, -Y for X-tangent.
            if (axis==0 and sign<0) or (axis==1 and sign>0):
                poly=list(reversed(poly))
            start=len(base_verts)
            base_verts.extend(point(u,z,0) for u,z in poly)
            base_faces.append(tuple(range(start,start+len(poly))))
            u0,u1=min(p[0] for p in poly),max(p[0] for p in poly)
            z0,z1=min(p[1] for p in poly),max(p[1] for p in poly)
            for row in range(math.floor(z0/.075),math.floor(z1/.075)+1):
                shift=(row%2)*.12
                for col in range(math.floor((u0-shift)/.24),math.floor((u1-shift)/.24)+1):
                    part=poly[:]
                    for dim,limit,greater in [(0,col*.24+shift+.004,True),(0,(col+1)*.24+shift-.004,False),
                                               (1,row*.075+.004,True),(1,(row+1)*.075-.004,False)]:
                        part=clip(part,dim,limit,greater)
                        if len(part)<3:
                            break
                    if len(part)<3 or area(part)<.000001:
                        continue
                    start=len(verts)
                    verts.extend(point(u,z,.007) for u,z in part)
                    faces.append(tuple(range(start,start+len(part))))
                    indices.append((row*17+col*13)%len(bricks))
        assert faces, source.name
        base=mesh('Mortar bed '+source.name,base_verts,base_faces,mortar)
        brick=mesh('Brick skin '+source.name,verts,faces,bricks,indices)
        for obj in (base,brick):
            obj['source_surface']=source.name
        records['brick_panels'].append(dict(source=source.name,faces=len(faces),axis=axis,plane=plane))
        hide(source)

    windows = [o for o in visible if o.name.startswith('WD -') and o.get('sw_glass')]
    doors = [o for o in visible if o.name.startswith('DOO -')]
    fronts = sorted((o for o in windows if bounds(o)[1].x < -4 and bounds(o)[0].z > 6),key=lambda o:bounds(o)[0].y)
    assert len(fronts)==5
    # Five front fixed centre panes plus selected tall side windows. No balcony
    # door is used as a screen host; every blade stays within its glazing bounds.
    sides = [o for o in windows if .7 < (bounds(o)[0].x+bounds(o)[1].x)/2 < 1.7
             and bounds(o)[0].z > 3 and bounds(o)[1].z-bounds(o)[0].z > 1.5]
    for index, window in enumerate(fronts+sides,1):
        lo,hi=bounds(window); centre=(lo+hi)/2
        axis=0 if hi.x-lo.x<.3 else 1; tangent=1-axis
        direction=(1 if centre.x>0 else -1) if axis==0 else (
            -1 if any(abs(centre.y-y)<.25 for y in [-13.81,-7.04,4.42]) else 1)
        width=min(.92 if window in fronts else .53,(hi[tangent]-lo[tangent])-.14)
        a,b=centre[tangent]-width/2,centre[tangent]+width/2
        bottom,top=lo.z+.025,hi.z-.025
        outer=hi[axis] if direction>0 else lo[axis]
        normal=outer+direction*.32
        glass_tree=BVHTree.FromPolygons([window.matrix_world@v.co for v in window.data.vertices],
            [tuple(p.vertices) for p in window.data.polygons])
        ray_direction=Vector((0,0,0));ray_direction[axis]=-direction
        pieces=[]
        def screen_box(label,u0,u1,z0,z1,n0,n1):
            p=[0.,0.,z0];q=[0.,0.,z1]
            p[tangent],q[tangent]=u0,u1
            p[axis],q[axis]=sorted([n0,n1])
            obj=box(f'Window {index:02d} '+label,p,q,bronze)
            obj['host_window']=window.name
            pieces.append(obj)
            return obj
        count=max(4,round(width/.10))
        blade_positions=[]
        for j in range(count):
            nominal=a+.018+j*(width-.036)/(count-1)
            candidates=[nominal]+[nominal+delta*sign for delta in (.01,.02,.03,.04,.05,.06) for sign in (-1,1)]
            u=None
            for candidate in candidates:
                if not a+.012<=candidate<=b-.012 or any(abs(candidate-prior)<.055 for prior in blade_positions):
                    continue
                hits=0
                for fraction in (.2,.4,.6,.8):
                    origin=Vector((0,0,bottom+(top-bottom)*fraction))
                    origin[axis]=normal;origin[tangent]=candidate
                    if glass_tree.ray_cast(origin,ray_direction,1)[0] is not None:hits+=1
                if hits>=2:
                    u=candidate;break
            assert u is not None, f'No glazing-backed blade location for {window.name}'
            blade_positions.append(u)
            screen_box(f'vertical louvre {j+1}',u-.012,u+.012,bottom,top,normal-direction*.065,normal+direction*.065)
        for z,label in [(bottom,'bottom carrier'),(top,'top carrier')]:
            screen_box(label,a-.015,b+.015,z-.014,z+.014,normal-direction*.065,normal+direction*.065)
        # Four stand-offs return to the solid head/sill frame outside the glass.
        for u in (a+.025,b-.025):
            for z in (lo.z-.08,hi.z+.08):
                screen_box('frame standoff',u-.016,u+.016,z-.016,z+.016,outer-direction*.07,normal)
                screen_box('carrier ear',u-.016,u+.016,min(z,bottom if z<bottom else top),max(z,bottom if z<bottom else top),normal-.015,normal+.015)
        for obj in pieces:
            if 'vertical louvre' not in obj.name:
                continue
            bl,bh=bounds(obj)
            assert bl[tangent]>=lo[tangent] and bh[tangent]<=hi[tangent]
            assert bl.z>=lo.z and bh.z<=hi.z
            assert not any(intersects((bl,bh),bounds(d),.02) for d in doors)
        records['screens'].append(dict(window=window.name,blades=count,glazing_bounds=[list(lo),list(hi)],
            screen_width_m=width,clearance_to_existing_glass_m=.255,parts=[o.name for o in pieces]))

    # Rounded mineral surrounds replace the five earlier rectangular front trims.
    for window in fronts:
        lo,hi=bounds(window);cy=(lo.y+hi.y)/2;cz=(lo.z+hi.z)/2
        for o in visible:
            if not o.name.startswith('Facade |') or 'shallow surround' not in o.name:
                continue
            ol,oh=bounds(o)
            if abs((ol.y+oh.y)/2-cy)<1.2 and abs((ol.z+oh.z)/2-cz)<1.0:
                hide(o)
        paths=[]
        for extra,r in [(.15,.10),(.085,.035)]:
            ya,yb=lo.y-extra,hi.y+extra;za,zb=lo.z-extra,hi.z+extra
            path=[]
            for y,z,start in [(yb-r,zb-r,0),(ya+r,zb-r,90),(ya+r,za+r,180),(yb-r,za+r,270)]:
                for j in range(7):
                    angle=math.radians(start+j*90/6)
                    path.append((y+r*math.cos(angle),z+r*math.sin(angle)))
            paths.append(path)
        n=len(paths[0]);verts=[]
        for x in (-5.075,-4.775):
            for path in paths:
                verts.extend((x,y,z) for y,z in path)
        faces=[]
        for j in range(n):
            k=(j+1)%n
            faces.extend([(j,k,n+k,n+j),(2*n+j,3*n+j,3*n+k,2*n+k),
                          (j,2*n+j,2*n+k,k),(n+j,n+k,3*n+k,3*n+j)])
        mesh('Soft window surround '+window.name,verts,faces,white)

    # Three continuous rounded cladding bands follow the single and paired blocks.
    # The 260 mm wrap sits outside the existing slab, with original glass rails inset.
    for idx,(ya,yb,z) in enumerate([(-13.82,-9.14,3.22),(-7.05,2.32,3.22),(4.405,13.775,2.92)],1):
        radius=.26;xf=-5.445;rear=-3.49
        path=[(rear,ya-radius),(xf,ya-radius)]
        for j in range(1,13):
            angle=-math.pi/2-j*math.pi/24
            path.append((xf+radius*math.cos(angle),ya+radius*math.sin(angle)))
        path.append((xf-radius,yb))
        for j in range(1,13):
            angle=math.pi-j*math.pi/24
            path.append((xf+radius*math.cos(angle),yb+radius*math.sin(angle)))
        path.append((rear,yb+radius))
        lengths=[0.]
        for a,b in zip(path,path[1:]):lengths.append(lengths[-1]+math.dist(a,b))
        def at(s):
            for i in range(len(path)-1):
                if s<=lengths[i+1]+1e-7:
                    t=(s-lengths[i])/(lengths[i+1]-lengths[i])
                    return tuple(path[i][k]+t*(path[i+1][k]-path[i][k]) for k in range(2))
            return path[-1]
        verts=[];faces=[];indices=[]
        for row in range(4):
            for col in range(-1,math.ceil(lengths[-1]/.24)+1):
                a=max(0,col*.24+(row%2)*.12+.004);b=min(lengths[-1],(col+1)*.24+(row%2)*.12-.004)
                if b<=a:continue
                stops=[a]+[s for s in lengths if a<s<b]+[b]
                for sa,sb in zip(stops,stops[1:]):
                    pa,pb=at(sa),at(sb);start=len(verts)
                    za=z-.3+row*.075+.004;zb=za+.067
                    verts.extend([(pa[0],pa[1],za),(pb[0],pb[1],za),(pb[0],pb[1],zb),(pa[0],pa[1],zb)])
                    faces.append(tuple(range(start,start+4)));indices.append((row+col)%5)
        mesh(f'Block {idx} curved brick fascia',verts,faces,bricks,indices)
        # Closed top/bottom return connects the wrap to the existing straight edge.
        inner=[(max(x,xf+.015),min(yb-.015,max(ya+.015,y))) for x,y in path]
        verts=[(x,y,h) for h in (z-.30,z+.015) for ring in (path,inner) for x,y in ring]
        n=len(path);faces=[]
        for j in range(n-1):
            faces.extend([(j,j+1,n+j+1,n+j),(2*n+j,3*n+j,3*n+j+1,2*n+j+1),
                          (j,2*n+j,2*n+j+1,j+1)])
        core=mesh(f'Block {idx} curved fascia backing and coping',verts,faces,mortar)
        # Offset outer backing inward so mortar is recessed behind brick faces.
        for v in core.data.vertices:
            if v.co.x < xf: v.co.x+=.008
            if v.co.y < ya: v.co.y+=.008
            if v.co.y > yb: v.co.y-=.008
        records['balcony_bands'].append(dict(block=idx,y=[ya,yb],slab_top=z,radius_m=radius))

    balcony_doors=sorted([o for o in visible if o.name.startswith('DOO - 020_Metal - Aluminium') and bounds(o)[0].x < -3],key=lambda o:bounds(o)[0].y)
    front_doors=sorted([o for o in visible if o.name.startswith('DOO - 019_Wood - Walnut')],key=lambda o:bounds(o)[0].y)
    assert len(front_doors)==len(balcony_doors)==5
    bays=[(-13.78,-9.17,3.22),(-7.01,-2.40,3.22),(-2.33,2.28,3.22),(4.44,9.05,2.92),(9.13,13.74,2.92)]
    rng=random.Random(911)
    for i,((ya,yb,floor),door,entry) in enumerate(zip(bays,balcony_doors,front_doors),1):
        dl,dh=bounds(door)
        cy=ya+.40 if dl.y-ya>yb-dh.y else yb-.40
        xa,xb=-5.32,-4.85;pa,pb=cy-.29,cy+.29;top=floor+.46
        parts=[]
        for label,lo,hi in [('base',(xa,pa,floor),(xb,pb,floor+.045)),
            ('front',(xa,pa,floor),(xa+.045,pb,top)),('back',(xb-.045,pa,floor),(xb,pb,top)),
            ('left',(xa,pa,floor),(xb,pa+.045,top)),('right',(xa,pb-.045,floor),(xb,pb,top))]:
            parts.append(box(f'Balcony {i} planter '+label,lo,hi,white))
        parts.append(box(f'Balcony {i} soil',(xa+.05,pa+.05,top-.09),(xb-.05,pb-.05,top-.07),soil))
        verts=[];faces=[]
        for j in range(85):
            x=rng.uniform(xa+.07,xb-.07);y=rng.uniform(pa+.06,pb-.06)
            angle=rng.uniform(0,math.tau);h=rng.uniform(.12,.30)
            dx,dy=.055*math.cos(angle),.055*math.sin(angle);s=len(verts)
            verts.extend([(x-.015,y,top-.07),(x+.015,y,top-.07),(x+dx,y+dy,top+h)])
            faces.append((s,s+1,s+2))
        parts.append(mesh(f'Balcony {i} fine planting',verts,faces,green))
        for obj in parts:
            obj['sw_service_systems']='["landscape"]'
            assert not any(intersects(bounds(obj),bounds(d),.10) for d in doors),obj.name
        records['planters'].append(dict(dwelling=i,footprint=[xa,xb,pa,pb],clear_depth_to_balcony_door_m=round(dl.x-xb,3)))
        # Wall fixtures sit beside the existing entry frame, outside its aperture.
        el,eh=bounds(entry)
        ey=eh.y+.10 if eh.y+.18<yb else el.y-.10
        lamp=box(f'Entry {i} bronze sconce',(-4.965,ey-.025,1.77),(-4.87,ey+.025,2.13),bronze)
        assert not intersects(bounds(lamp),bounds(entry),.025)
        records['access'].append(dict(door=entry.name,unchanged=True,new_ground_planters=0))

    bpy.context.view_layer.update()
    for name,digest in original.items():
        assert signature(scene.objects[name])==digest,'Source geometry changed: '+name
    records['preserved_source_meshes']=len(original)
    records['hidden_replaced_coverings_and_trims']=hidden
    records['new_objects']=len(added)
    records['new_ground_planters']=0
    records['checks']=['All source mesh vertices, topology and transforms unchanged',
        'Every louvre blade lies within a named window glazing projection',
        'Every louvre blade has at least 255 mm clearance to existing glazing envelope',
        'No new louvre blade or planter intersects a door bounding volume',
        'No garden beds added to ground-level entries, garage aprons or steps']
    scene['premium_facade_audit']='v3/premium-facade-audit.json'
    (HERE/'premium-facade-audit.json').write_text(json.dumps(records,indent=2))
    print('PREMIUM_VERIFIED',len(records['brick_panels']),'brick panels;',len(records['screens']),
          'window screens;',len(records['planters']),'planters;',len(original),'source meshes preserved',flush=True)


if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-chalk-v10.blend'))
    apply(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-premium-v11.blend'))
    if '--export' in sys.argv:
        from export_web import export
        export(bpy.context.scene)
