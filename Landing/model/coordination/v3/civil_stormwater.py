"""Shared civil stormwater collection, outside the five dwelling footprints."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def build(scene):
    from wet_services import _tube
    site = json.loads((HERE/'site-structure-metadata.json').read_text())
    houses = next(v['dwelling_bounds'] for v in site.values() if isinstance(v, dict) and 'dwelling_bounds' in v)
    replaced = ('RWT-downpipe-collector-', 'RWT-collector-to-filter', 'RWT-filter-link',
                'RWT-filter-to-tank', 'RWT-overflow-', 'RWT-street-main-')
    downpipes = []
    for obj in list(scene.objects):
        if obj.name.startswith('Storm |') or str(obj.get('sw_route_id', '')).startswith(replaced) or obj.name == 'V3 | Rainwater pre-tank filter chamber':
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        if obj.get('sw_subsystem') == 'rainwater':
            obj['sw_system'] = 'civil'
            obj['sw_service_systems'] = '[]'
            if 'downpipe' in str(obj.get('sw_label', '')).lower() and obj.type == 'MESH':
                vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
                low = min(p.z for p in vertices)
                bottom = [p for p in vertices if p.z < low+.035]
                downpipes.append((obj.name, sum(bottom, Vector())/len(bottom)))
        if obj.get('sw_system') == 'civil' and obj.get('sw_subsystem') != 'rainwater' and not obj.get('sw_motion'):
            obj['sw_civil_surface'] = True
    mat = bpy.data.materials.get('Civil stormwater infrastructure') or bpy.data.materials.new('Civil stormwater infrastructure')
    mat.diffuse_color = (.26,.39,.43,1)
    nodes, routes, pits = {}, [], []

    def mesh(label, vertices, faces):
        data = bpy.data.meshes.new('Storm | '+label)
        data.from_pydata(vertices, [], faces)
        data.materials.append(mat)
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj['sw_system'] = 'civil'
        obj['sw_subsystem'] = 'stormwater'
        return obj

    def box(label, center, size):
        c, s = Vector(center), Vector(size)/2
        vertices = [c+Vector((x*s.x,y*s.y,z*s.z)) for z in (-1,1) for y in (-1,1) for x in (-1,1)]
        return mesh(label, vertices, [(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)])

    def node(name, point):
        nodes[name] = list(point)
        return name

    def route(a, b, via=(), radius=.065):
        points = [nodes[a], *map(list, via), nodes[b]]
        points = [p for i,p in enumerate(points) if i == 0 or (Vector(p)-Vector(points[i-1])).length > .00001]
        obj = mesh(a+' to '+b, *_tube(points, radius, 12))
        obj['sw_endpoint_ids'] = json.dumps([a,b])
        routes.append(dict(start=a,end=b,points=points,radius=radius))

    def pit(name, x, y, invert, surface=.27, width=.62):
        node(name, (x,y,invert))
        bottom = invert-.12
        for dx,dy,sx,sy in [(-width/2,0,.055,width),(width/2,0,.055,width),(0,-width/2,width,.055),(0,width/2,width,.055)]:
            box(name+' chamber', (x+dx,y+dy,(bottom+surface)/2), (sx,sy,surface-bottom))
        box(name+' base', (x,y,bottom), (width,width,.055))
        for i in range(8):
            box(name+' grate', (x-width*.44+i*width*.88/7,y,surface), (.025,width,.035))
        pits.append(name)
        return name

    def trunk_z(y):
        return -.78-(16-y)*.009

    # One trunk under the driveway, with four surface inlets and five house tees.
    trunk = []
    for i,y in enumerate([14,5,-4,-13]):
        name = pit('Driveway pit '+str(i+1), -9.65,y,trunk_z(y))
        trunk.append((y,name))
    house_nodes = []
    for i,house in enumerate(houses):
        lo,hi = house['min'],house['max']
        side_y = (houses[i-1]['max'][1]+lo[1])/2 if i and lo[1]-houses[i-1]['max'][1] < .5 else lo[1]-.45
        depth = trunk_z(side_y)+.10
        rear = pit('House '+str(i+1)+' rear pit',5.3,(lo[1]+hi[1])/2,depth+.07,.12,.45)
        corner = node('House '+str(i+1)+' side east',(5.3,side_y,depth+.04))
        west = node('House '+str(i+1)+' side west',(-5.15,side_y,depth))
        tee = node('House '+str(i+1)+' driveway tee',(-9.65,side_y,trunk_z(side_y)))
        route(rear,corner)
        # Narrow joined-building gaps get a small collector below the slab level.
        route(corner,west,radius=.045)
        route(west,tee)
        trunk.append((side_y,tee))
        house_nodes.append((rear,west,side_y))
    for label,base in downpipes:
        index = min(range(5), key=lambda i: abs(base.y-(houses[i]['min'][1]+houses[i]['max'][1])/2))
        rear,west,side_y = house_nodes[index]
        start = node('Downpipe '+str(len([n for n in nodes if n.startswith('Downpipe ')]))+': '+label,base)
        target = west if base.x < 0 else rear
        exterior_x = -5.15 if base.x < 0 else 5.3
        # Exit the wall at the downpipe base before dropping below ground.
        route(start,target,[(exterior_x,base.y,base.z),(exterior_x,base.y,nodes[target][2]+.025)],.04)
    bin_pit = pit('Bin room pit',-1.9,-19.85,-1.16,.105,.50)
    tank_in = node('Detention inlet',(7.60,-17.35,-1.25))
    tank_out = node('Detention controlled outlet',(8.72,-17.30,-1.62))
    collector = node('Front collection junction',(-9.65,-16.4,trunk_z(-16.4)))
    trunk.append((-16.4,collector))
    trunk.sort(reverse=True)
    for (_,a),(_,b) in zip(trunk,trunk[1:]):
        route(a,b,radius=.10)
    route(collector,tank_in,[(-9.65,-17.35,-1.12)],.10)
    route(bin_pit,tank_in,[(-1.9,-17.35,-1.20)],.065)
    road = node('Single road stormwater outlet',(-9.65,-25,-1.95))
    route(tank_out,road,[(8.72,-21,-1.70),(-9.65,-21,-1.80)],.09)
    for x in (-24,24):
        end = node('Road main '+str(x),(x,-25,-1.95))
        route(road,end,radius=.15)
    # Equipment links describe flow through the retained tank, not a bypass pipe.
    links = [(r['start'],r['end']) for r in routes]+[(tank_in,tank_out)]
    reachable = {road}
    while True:
        updated = reachable | {a for a,b in links if b in reachable}
        if updated == reachable:
            break
        reachable = updated
    assert all(p in reachable for p in pits)
    assert all(n in reachable for n in nodes if n.startswith('Downpipe '))
    assert len(pits) == 10 and len(house_nodes) == 5
    assert not any(o.get('sw_system')=='hydraulic' and o.get('sw_subsystem')=='rainwater' for o in scene.objects)
    # Side runs must remain outside every slab footprint in plan.
    for r in routes:
        if 'side east' not in r['start']:
            continue
        y = r['points'][0][1]
        assert all(not h['min'][1] < y < h['max'][1] for h in houses)
    (HERE/'civil-stormwater.json').write_text(json.dumps(dict(nodes=nodes,routes=routes,pits=pits,
        tank_flow_link=[tank_in,tank_out],validation=dict(houses=5,driveway_pits=4,rear_pits=5,bin_pits=1,
        connected_downpipes=len(downpipes),road_outlets=1,all_pits_connected=True,side_runs_outside_slabs=True)),indent=2))
    bpy.context.view_layer.update()
    print('CIVIL_STORMWATER_COMPLETE',len(pits),'pits;',len(downpipes),'downpipes; one outlet',flush=True)


if __name__ == '__main__':
    from export_web import export
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-detail-v4.blend'))
    build(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    export(bpy.context.scene)
