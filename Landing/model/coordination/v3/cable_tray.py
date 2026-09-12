"""Limited ladder tray at the board/riser, with clipped roof circuit departures."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def build(scene):
    from electrical_circuits import build as circuits, cable_points
    # Recreate the unmodified circuit paths so this operation is repeatable.
    circuits(scene)
    for obj in list(scene.objects):
        if obj.name.startswith('Tray |'):
            bpy.data.objects.remove(obj, do_unlink=True)
    metal = bpy.data.materials.get('Electrical tray galvanized') or bpy.data.materials.new('Electrical tray galvanized')
    metal.diffuse_color = (.38, .43, .46, 1)
    metal.use_nodes = True
    shader = metal.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = metal.diffuse_color
    shader.inputs['Metallic'].default_value = .55
    shader.inputs['Roughness'].default_value = .48
    count = 0

    def member(label, a, b, width, depth, normal=None):
        nonlocal count
        a, b = Vector(a), Vector(b)
        direction = b-a
        rotation = direction.to_track_quat('Z', 'Y')
        axis_x = Vector(normal).cross(direction.normalized()) if normal is not None else rotation @ Vector((1,0,0))
        axis_y = Vector(normal) if normal is not None else rotation @ Vector((0,1,0))
        verts = [axis_x*x*width/2+axis_y*y*depth/2+direction*z/2+(a+b)/2
                 for x, y, z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        mesh = bpy.data.meshes.new('Tray | '+label)
        mesh.from_pydata(verts, [], [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        mesh.materials.append(metal)
        obj = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(obj)
        obj['sw_system'] = 'electrical'
        obj['sw_component'] = 'cable-tray' if 'clip' not in label else 'cable-clip'
        count += 1

    def tray(a, b, across, label):
        a, b, across = Vector(a), Vector(b), Vector(across)
        opening = (b-a).normalized().cross(across)
        # The open ladder leaves the cable bundle visible between its side rails.
        for sign in (-1, 1):
            offset = across*.105*sign+opening*.035
            member(label+' rail', a+offset, b+offset, .018, .090, opening)
        steps = max(1, math.ceil((b-a).length/.24))
        for i in range(steps+1):
            center = a.lerp(b, i/steps)
            member(label+' rung', center-across*.105, center+across*.105, .018, .018)

    # Main riser stays on the existing service route and retains all floor taps.
    tray((-4.1,-9.40,1.45), (-4.1,-9.40,2.97), (1,0,0), 'board rise')
    tray((-4.1,-9.34935,2.92), (-4.1,-9.48,2.92), (1,0,0), 'board offset')
    tray((-4.1,-9.48,2.92), (-2.9,-9.48,2.92), (0,1,0), 'garage transfer')
    tray((-2.9,-9.53,2.97), (-2.9,-9.53,8.58), (1,0,0), 'vertical backbone')
    tray((-2.9,-9.48,8.53), (-2.9,-11.76418,8.53), (1,0,0), 'roof header')
    riser = scene.objects['V3 | Electrical | DB-01 main vertical service riser']
    riser.data.splines[0].points[-1].co.z = 8.58
    riser.data.bevel_depth = .032

    metadata = json.loads((HERE/'electrical-circuits.json').read_text())
    trusses = [-13.5984678+i*(4.28/7) for i in range(8)]
    for circuit in metadata['circuits']:
        if circuit['level'] != 'U':
            continue
        route = next(r for r in metadata['routes'] if r['from'] == circuit['feed'])
        obj = scene.objects[route['object']]
        old = [Vector(p) for p in route['points']]
        x = -2.93 if circuit['family'] == 'lighting' else -2.87
        peel_y = trusses[4] if circuit['family'] == 'lighting' else trusses[3]
        # Dress the supply inside the header before it leaves toward its first fitting.
        departure = Vector((old[-1].x, peel_y, 8.535))
        points = [old[0], Vector((x,-9.48,8.58)), Vector((x,peel_y,8.58))]
        points += cable_points([points[-1], departure, (old[-1].x,old[-1].y,8.438),old[-1]])[1:]
        obj.data.splines.clear()
        spline = obj.data.splines.new('POLY')
        spline.points.add(len(points)-1)
        for p, xyz in zip(spline.points, points):
            p.co = (*xyz, 1)
        route['points'] = [list(p) for p in points]
        assert (points[0]-Vector(metadata['nodes'][route['from']])).length < .0001
        assert (points[-1]-Vector(metadata['nodes'][route['to']])).length < .0001

    # Small saddles fix roof cables at actual truss crossings; branches have no tray.
    clips = 0
    for route in metadata['routes']:
        if not any(c['id']==route['circuit'] and c['level']=='U' for c in metadata['circuits']):
            continue
        points = list(map(Vector, route['points']))
        for y in trusses:
            for a, b in zip(points, points[1:]):
                if (a.y-y)*(b.y-y) >= 0 or abs(b.y-a.y)<.00001:
                    continue
                p = a.lerp(b, (y-a.y)/(b.y-a.y))
                if not (8.35 < p.z < 8.61) or abs(p.x+2.9)<.15:
                    continue
                member('roof cable clip crown', p+Vector((-.028,0,.022)), p+Vector((.028,0,.022)), .012, .012)
                for side in (-1, 1):
                    foot = Vector((p.x+side*.028,y,8.4975))
                    member('roof cable clip foot', foot, Vector((foot.x,y,p.z+.022)), .010, .010)
                clips += 1
                break
    metadata['tray'] = {'width':.21, 'roof_header_length':2.28418, 'roof_clips':clips,
                        'extent':'Garage board transfer, main vertical riser, short roof header; free branches clipped at trusses'}
    (HERE/'electrical-circuits.json').write_text(json.dumps(metadata, indent=2))
    bpy.context.view_layer.update()
    print('CABLE_TRAY_COMPLETE', count, 'members;', clips, 'roof clips; endpoints preserved', flush=True)


if __name__ == '__main__':
    from export_web import export
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-detail-v4.blend'))
    build(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    export(bpy.context.scene)
