"""Fit the four replicated roof frames to the source compound roof surfaces."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from replicate_dwellings import bounds
from export_web import export

SOURCE = HERE.parent/'sitewise-all-dwellings-v12.blend'
TARGET = HERE.parent/'sitewise-roof-frames-v13.blend'


def roof_surface(scene):
    vertices, faces = [], []
    for obj in scene.objects:
        if obj.hide_render or not obj.name.startswith('CI Tools Roof Covering - _Roof - Asphalt Shingle Gray'):
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
    return BVHTree.FromPolygons(vertices, faces)


def height(surface, x, y):
    hit = surface.ray_cast(Vector((x,y,20)), Vector((0,0,-1)))[0]
    if hit is not None:
        return hit.z
    # Rays can land precisely in the modelled shingle joints. Resolve only
    # millimetre-scale gaps, conservatively using the lowest adjacent surface.
    for radius in (.002,.005,.01):
        neighbours=[surface.ray_cast(Vector((x+dx,y+dy,20)),Vector((0,0,-1)))[0]
                    for dx,dy in [(radius,0),(-radius,0),(0,radius),(0,-radius)]]
        heights=[p.z for p in neighbours if p is not None]
        if heights:
            return min(heights)
    raise AssertionError(('No roof surface',x,y))


def simplify(points, tolerance=.025):
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    distances = [(p-a).cross(b-a).length/(b-a).length for p in points[1:-1]]
    furthest = max(range(len(distances)), key=distances.__getitem__)
    if distances[furthest] <= tolerance:
        return [a,b]
    i = furthest+1
    return simplify(points[:i+1],tolerance)[:-1]+simplify(points[i:],tolerance)


def build():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    surface = roof_surface(scene)
    records = json.loads(scene['sw_dwelling_replication'])
    material = scene.objects['V3 | Roof ridge member'].data.materials[0]
    audit = []
    for record in records[1:]:
        number = record['dwelling']
        prefix = f'TH{number:02} | '
        old = [o for o in scene.objects if o.name.startswith(prefix) and o.get('sw_component') == 'roof']
        assert len(old) > 40
        chord = scene.objects[prefix+'V3 | Roof truss 1 bottom chord']
        lo, hi = bounds(chord)
        xmin, xmax, bottom = lo.x, hi.x, (lo.z+hi.z)/2
        slab_lo, slab_hi = bounds(scene.objects[record['slab']])
        # The paired roofs descend at the outer ends. Set back the first and last
        # full trusses so their ties and webs fit above the existing bearing level.
        start, end = slab_lo.y+.48, slab_hi.y-.48
        group = bpy.data.collections.new(f'Compound roof | Internal dwelling {number}')
        scene.collection.children.link(group)
        created = []

        def member(label, a, b, width=.065, depth=.065):
            a,b = Vector(a),Vector(b)
            if (b-a).length < .025:
                return
            tangent = (b-a).normalized()
            reference = Vector((0,1,0)) if abs(tangent.y)<.95 else Vector((1,0,0))
            u = tangent.cross(reference).normalized()*depth/2
            v = tangent.cross(u).normalized()*width/2
            points = [p+su*u+sv*v for p in (a,b) for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
            mesh = bpy.data.meshes.new(label)
            mesh.from_pydata(points,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
            mesh.materials.append(material)
            obj = bpy.data.objects.new(f'Roof v13 | TH{number:02} | {label}',mesh)
            group.objects.link(obj)
            obj['sw_system']='structure';obj['sw_component']='roof'
            obj['sw_dwelling']=number;obj['sw_roof_revision']='compound-v13'
            obj['sw_member_endpoints']=json.dumps([list(a),list(b)])
            obj['sw_status']='Illustrative roof framing fitted to source roof; member design unverified'
            created.append(obj)

        profiles=[]
        for index in range(8):
            y=start+(end-start)*index/7
            samples=[Vector((x,y,height(surface,x,y)-.16))
                     for x in [xmin+(xmax-xmin)*j/100 for j in range(101)]]
            profile=simplify(samples)
            # A simplified top chord must remain below every sampled tile course.
            for a,b in zip(profile,profile[1:]):
                for j in range(21):
                    p=a.lerp(b,j/20)
                    assert p.z+.045 < height(surface,p.x,p.y)
            member(f'Truss {index+1} bottom tie',(xmin,y,bottom),(xmax,y,bottom),depth=.075)
            for j,(a,b) in enumerate(zip(profile,profile[1:])):
                member(f'Truss {index+1} compound top chord {j+1}',a,b)
            panel_x=[xmin+(xmax-xmin)*j/6 for j in range(7)]
            for j,x in enumerate(panel_x):
                top=Vector((x,y,height(surface,x,y)-.19))
                foot=Vector((x,y,bottom))
                if top.z>bottom+.055:
                    member(f'Truss {index+1} vertical {j}',foot,top,width=.045,depth=.045)
                if j and top.z>bottom+.08:
                    member(f'Truss {index+1} diagonal {j}',(panel_x[j-1],y,bottom),top,width=.045,depth=.045)
            profiles.append([list(p) for p in profile])
        # Longitudinal jack/hip support follows the change in roof pitch between
        # transverse frames, rather than carrying the old constant-height ridge.
        for k,x in enumerate([xmin, xmin+(xmax-xmin)*.25, (xmin+xmax)/2, xmin+(xmax-xmin)*.75, xmax]):
            path=simplify([Vector((x,y,height(surface,x,y)-.225))
                           for y in [start+(end-start)*j/80 for j in range(81)]])
            for j,(a,b) in enumerate(zip(path,path[1:])):
                member(f'Longitudinal pitch support {k+1}.{j+1}',a,b,width=.06,depth=.08)
        # Existing side bearing beams remain at the approved column support level.
        for obj in old:
            if 'roof bearing beam' in obj.name:
                continue
            obj.hide_render=True;obj.hide_set(True)
        audit.append(dict(internal_dwelling=number, user_townhouse=6-number,
                          source_slab=record['slab'], trusses=8, members=len(created),
                          hidden_copied_members=[o.name for o in old if o.hide_render],profiles=profiles))
    scene['sw_roof_revision']=json.dumps(audit)
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    (HERE/'compound-roof-frames.json').write_text(json.dumps(audit,indent=2))
    if '--export' in sys.argv:
        export(scene)
    print('COMPOUND_ROOFS',[(r['user_townhouse'],r['members']) for r in audit],flush=True)


if __name__=='__main__':
    build()
