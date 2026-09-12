"""Facade-only refinement of v5; retain all source geometry and interior assignments."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_integrated import material
from export_web import export

def bounds(obj):
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    return Vector([min(p[i] for p in points) for i in range(3)]), Vector([max(p[i] for p in points) for i in range(3)])

def geometry(obj):
    return (tuple(tuple(r) for r in obj.matrix_world), tuple(tuple(v.co) for v in obj.data.vertices))

def apply(scene):
    original = {o.name: geometry(o) for o in scene.objects if o.type == 'MESH' and not o.name.startswith('Detail | Window hood')}
    limestone = material('Facade | Warm limestone', '#DED8CC')
    bronze = material('Facade | Satin bronze', '#716458')
    warm = material('Facade | Balcony oak', '#AC9274')
    mineral = material('Facade | Mineral inset', '#ADA697')
    bronze.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value = .35
    records = []
    def box(name, pos, size, mat):
        bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
        o = bpy.context.object
        o.name = 'Facade | ' + name
        o.scale = size
        o['sw_system'] = 'architecture'
        o['sw_label'] = name
        o.data.materials.append(mat)
        return o
    def finish(o, mat):
        o.data = o.data.copy()
        o.data.materials.clear()
        o.data.materials.append(mat)
        for p in o.data.polygons:
            p.material_index = 0
    for o in list(scene.objects):
        if o.name.startswith('Detail | Window hood'):
            bpy.data.objects.remove(o, do_unlink=True)
    windows = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render and o.name.startswith('WD -') and o.get('sw_glass')]
    for i, o in enumerate(windows):
        lo, hi = bounds(o)
        c = (lo + hi) / 2
        axis = 0 if hi.x-lo.x < .3 else 1
        tangent = 1-axis
        direction = (1 if c.x > 0 else -1) if axis == 0 else (-1 if c.y < -9 or 0 < c.y < 3 else 1)
        width, height = hi[tangent]-lo[tangent], hi.z-lo.z
        prominent = axis == 0 and c.x < -4 and lo.z > 6
        treatment = 'shallow surround' if prominent else 'horizontal blade' if width > 1.2 else 'quiet reveal'
        depth = .27 if prominent else .48 if width > 1.2 else .12
        edge = .035 if width > 1.2 else .025
        # Source glass sits within existing frames; new edges clear that frame.
        left, right, bottom, top = lo[tangent]-.13, hi[tangent]+.13, lo.z-.12, hi.z+.12
        normal = c[axis] + direction*(depth/2+.035)
        def part(label, u, z, w, h):
            pos = [0.,0.,z]; pos[axis] = normal; pos[tangent] = u
            size = [0.,0.,h]; size[axis] = depth; size[tangent] = w
            box(f'{i+1:02d} {treatment} {label}', pos, size, bronze)
        part('head',(left+right)/2,top,right-left+edge,edge)
        if prominent:
            part('sill',(left+right)/2,bottom,right-left+edge,edge)
            for label,u in [('left',left),('right',right)]:
                part(label,u,(bottom+top)/2,edge,top-bottom)
        records.append(dict(window=o.name,treatment=treatment,projection_m=depth))
    for o in list(scene.objects):
        if o.type != 'MESH' or o.hide_render or o.get('sw_system') != 'architecture' or o.name.startswith('Facade |'):
            continue
        lo,hi = bounds(o)
        if o.name.startswith('CI Tools Wall Covering'):
            # Existing covering meshes already include the opening cutouts.
            balcony = -3.6 < lo.x < -3.4 and hi.x < -3.3 and lo.z > 2.5 and hi.z < 6
            finish(o, warm if balcony else limestone)
        elif o.name.startswith(('BALUSTER -','POST -','RAIL -','TOPRAIL','INNER POST','RAIL CONNECTION')):
            finish(o, bronze)
        elif o.name.startswith('WD -') and not o.get('sw_glass'):
            finish(o,bronze)
        elif o.name.startswith('SLA -') and 'Wall white plaster' in o.name and 5.3 < lo.z < 5.7 and hi.z < 6:
            # Only downward exterior balcony soffit faces get the warm finish.
            slot = len(o.data.materials); o.data.materials.append(warm)
            for p in o.data.polygons:
                centre=o.matrix_world@p.center
                normal=o.matrix_world.to_3x3()@p.normal
                if centre.x < -3.5 and normal.z < -.9:
                    p.material_index=slot
    # A slim inset bay ties existing narrow side windows together; segmented at openings.
    groups = {}
    for o in windows:
        lo,hi=bounds(o); c=(lo+hi)/2
        if hi.y-lo.y < .3 and .7 < c.x < 1.7:
            groups.setdefault(round(c.y,0),[]).append((lo,hi))
    for key, openings in groups.items():
        direction=-1 if key < -9 or 0 < key < 3 else 1
        plane = (min(lo.y for lo,hi in openings) if direction<0 else max(hi.y for lo,hi in openings)) + direction*.055
        left=min(lo.x for lo,hi in openings)-.20; right=max(hi.x for lo,hi in openings)+.20
        base=.45 if key<3 else .15; top=8.35 if key<3 else 8.05
        cursor=base
        for lo,hi in sorted(openings,key=lambda pair:pair[0].z):
            a,b=lo.z-.13,hi.z+.13
            if a>cursor:
                box(f'Side bay {key} infill {cursor:.2f}',((left+right)/2,plane,(cursor+a)/2),(right-left,.025,a-cursor),mineral)
            for label,x0,x1 in [('left',left,lo.x-.13),('right',hi.x+.13,right)]:
                if x1>x0:
                    box(f'Side bay {key} {label} {a:.2f}',((x0+x1)/2,plane,(a+b)/2),(x1-x0,.025,b-a),mineral)
            cursor=max(cursor,b)
        if top>cursor:
            box(f'Side bay {key} upper infill',((left+right)/2,plane,(cursor+top)/2),(right-left,.025,top-cursor),mineral)
    bpy.context.view_layer.update()
    for name,before in original.items():
        assert geometry(scene.objects[name]) == before, f'Original geometry changed: {name}'
    result=dict(source='sitewise-detail-v5.blend', checkpoint='sitewise-facade-v6.blend', preserved_meshes=len(original), windows=records, side_bays=len(groups))
    (HERE/'facade-revision.json').write_text(json.dumps(result,indent=2))
    print('FACADE_VERIFIED',len(original),'original meshes unchanged;',len(records),'window treatments;',len(groups),'side bays',flush=True)

if __name__ == '__main__':
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-detail-v5.blend'))
    scene=bpy.context.scene
    apply(scene)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-facade-v6.blend'))
    if '--no-export' not in sys.argv:
        export(scene)
