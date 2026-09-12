"""Read-only focus-dwelling geometry audit; never saves or edits the Blender scene."""
import bpy
import json
import math
from collections import defaultdict
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-kitchen-checkpoint.blend'))
center = Vector((-24.757655, -11.917233, 0))
focus = Vector((-26, -23, 0)) - center
U = Vector((.98703, -.16053, 0)).normalized()
V = Vector((.16053, .98703, 0)).normalized()
inventory = {r['name']: r for r in json.loads((ROOT / 'model-inventory.json').read_text())}

def local(point):
    q = point - focus
    return Vector((q.dot(U), q.dot(V), q.z))

rows = []
mesh_data = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or not obj.get('source_name'):
        continue
    verts = [local(obj.matrix_world @ v.co) for v in obj.data.vertices]
    lo = [min(v[i] for v in verts) for i in range(3)]
    hi = [max(v[i] for v in verts) for i in range(3)]
    if hi[1] < -3.2 or lo[1] > 3.2 or hi[2] < -.5:
        continue
    name = obj['source_name']
    original = inventory.get(name, {})
    row = dict(name=name, system=obj.get('system'), min=[round(v,4) for v in lo],
               max=[round(v,4) for v in hi], center=[round((lo[i]+hi[i])/2,4) for i in range(3)],
               parents=original.get('parents',[])[:3], materials=original.get('materials',[]),
               visible=not obj.hide_render)
    rows.append(row)
    mesh_data.append((obj, verts, row))

result = dict(source_scene='sitewise-kitchen-checkpoint.blend', coordinate_system=dict(
    world_origin=list(focus), source_center=list(center), U=list(U), V=list(V),
    point_to_world='focus + U*u + V*v + (0,0,z)'),
    units='Imported coordinate units; metres presumed from fixture scale, not survey verified',
    focus_filter='Mesh overlaps local V [-3.2,3.2]; shared/large meshes retained and flagged by bounds',
    objects=rows)
(OUT / 'structure-audit-inventory.json').write_text(json.dumps(result, indent=2))

# Horizontal sections retain real wall openings; no bounding-box walls are invented.
sections = {}
for label,z in [('ground',1.30),('living',4.20),('upper',6.90)]:
    segments=[]
    for obj,verts,row in mesh_data:
        if row['system'] not in ['04 Walls','05 Envelope']:
            continue
        if not row['min'][2] <= z <= row['max'][2]:
            continue
        for face in obj.data.polygons:
            points=[]
            ids=list(face.vertices)
            for a,b in zip(ids, ids[1:]+ids[:1]):
                p,q=verts[a],verts[b]
                if (p.z-z)*(q.z-z)<0:
                    t=(z-p.z)/(q.z-p.z)
                    pt=p+(q-p)*t
                    points.append([round(pt.x,4), round(pt.y,4)])
            if len(points)==2 and (Vector(points[0])-Vector(points[1])).length>.001:
                if max(points[0][1],points[1][1])>=-3.2 and min(points[0][1],points[1][1])<=3.2:
                    segments.append(dict(source=row['name'], a=points[0],b=points[1],system=row['system']))
    sections[label]=dict(z=z,segments=segments)
    # Stable labelled SVGs can be inspected without changing source-scene visibility.
    scale=65; x0=-7; x1=7; y0=-3.6; y1=3.6
    def xy(p): return ((p[0]-x0)*scale+35,(y1-p[1])*scale+50)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="980" height="590" viewBox="0 0 980 590">',
         '<rect width="980" height="590" fill="#f7f6f1"/>',
         f'<text x="35" y="25" font-family="sans-serif" font-size="17">{label.title()} — actual mesh section at Z {z:.2f}; U → / V ↑</text>']
    for u in range(-7,8):
        x,_=xy((u,0));svg.append(f'<path d="M{x} 45V525" stroke="#dfdfd7"/><text x="{x}" y="550" font-family="sans-serif" font-size="12">{u}</text>')
    for v in range(-3,4):
        _,y=xy((0,v));svg.append(f'<path d="M30 {y}H955" stroke="#dfdfd7"/><text x="10" y="{y}" font-family="sans-serif" font-size="12">{v}</text>')
    svg.append('<clipPath id="plot"><rect x="30" y="45" width="925" height="480"/></clipPath><g clip-path="url(#plot)">')
    for seg in segments:
        a,b=xy(seg['a']),xy(seg['b'])
        color='#363c40' if seg['system']=='04 Walls' else '#b68f54'
        svg.append(f'<path d="M{a[0]:.2f} {a[1]:.2f}L{b[0]:.2f} {b[1]:.2f}" stroke="{color}" stroke-width="1.4"/>')
    for row in rows:
        if row['min'][1]<-3.2 or row['max'][1]>3.2: continue
        if not row['min'][2]-1 <= z <= row['max'][2]+.5: continue
        if not row['name'].startswith(('Sink General','Cooktop','Basin 24','WC 24','Shower Cabin','Mop Sink','WashingMachine')):continue
        x,y=xy(row['center']);text=row['name'].split('_')[0].split(' - ')[0][:16]
        svg.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#205991"/><text x="{x+4}" y="{y-4}" font-family="sans-serif" font-size="9" fill="#205991">{text}</text>')
    svg.extend(['</g>','<text x="35" y="575" font-family="sans-serif" font-size="11">Graphite: walls; ochre: envelope/doors/windows; blue: source fixture anchors. Illustrative geometry audit.</text>','</svg>'])
    (OUT/f'structure-audit-{label}-plan.svg').write_text('\n'.join(svg))
(OUT/'structure-audit-sections.json').write_text(json.dumps(sections,indent=2))

def merge_ranges(ranges, tolerance=.003):
    merged=[]
    for a,b in sorted(ranges):
        if b-a<.003: continue
        if merged and a <= merged[-1][1]+tolerance:
            merged[-1][1]=max(b,merged[-1][1])
        else: merged.append([a,b])
    return merged

def clustered(values, tol=.002):
    out=[]
    for v in sorted(values):
        if not out or v-out[-1]>tol:out.append(v)
    return out

wall_runs=[]
roof_planes=[]
floor_top_faces=[]
for obj,verts,row in mesh_data:
    dims=[row['max'][i]-row['min'][i] for i in range(3)]
    if row['system']=='04 Walls' and 'Wall white plaster' in row['name'] and dims[2]>2 and min(dims[:2])<.15:
        major=0 if dims[0]>dims[1] else 1
        transverse=1-major
        z_levels=clustered(v.z for v in verts)
        holes=[]
        for za,zb in zip(z_levels,z_levels[1:]):
            if zb-za<.005:continue
            z=(za+zb)/2
            ranges=[]
            for face in obj.data.polygons:
                points=[]
                ids=list(face.vertices)
                for a,b in zip(ids,ids[1:]+ids[:1]):
                    p,q=verts[a],verts[b]
                    if (p.z-z)*(q.z-z)<0:
                        t=(z-p.z)/(q.z-p.z)
                        points.append((p+(q-p)*t)[major])
                if len(points)==2:ranges.append(sorted(points))
            solid=merge_ranges(ranges)
            previous=row['min'][major]
            for a,b in solid+[[row['max'][major],row['max'][major]]]:
                if a-previous>.04:holes.append(dict(start=round(previous,4),end=round(a,4),bottom=round(za,4),top=round(zb,4)))
                previous=max(previous,b)
        merged=[]
        for h in holes:
            prev=next((p for p in merged if abs(p['start']-h['start'])<.005 and abs(p['end']-h['end'])<.005 and abs(p['top']-h['bottom'])<.005),None)
            if prev:prev['top']=h['top']
            else:merged.append(h)
        for hole in merged:
            if row['name']=='SW - 574_Wall white plaster_0.008':
                hole['type']='Stair slope cutout; bands approximate a sloped edge, not rectangular openings'
            elif hole['top']-hole['bottom']<.2 or hole['end']-hole['start']<.2:
                hole['type']='Small edge/notch; not a door/window opening'
            else:hole['type']='Model void; verify assembly before assigning door/window type'
        wall_runs.append(dict(source=row['name'],axis='U' if major==0 else 'V',
            at=round(row['center'][transverse],4), start=row['min'][major],end=row['max'][major],
            bottom=row['min'][2],top=row['max'][2],thickness=round(dims[transverse],4),
            openings=merged,confidence='Measured wall voids; rough framing clearances not specified'))
    if row['system']=='06 Roof' and row['name'].startswith('RT - 024'):
        planes=defaultdict(lambda:dict(area=0,count=0,example=None))
        for face in obj.data.polygons:
            points=[verts[i] for i in face.vertices]
            if len(points)<3:continue
            normal=(points[1]-points[0]).cross(points[2]-points[0])
            if normal.length<.00001:continue
            normal.normalize()
            if abs(normal.z)<.6:continue
            if normal.z<0:normal=-normal
            a,b=-normal.x/normal.z,-normal.y/normal.z
            c=points[0].z-a*points[0].x-b*points[0].y
            key=tuple(round(p,4) for p in (a,b,c))
            area=sum((points[i]-points[0]).cross(points[i+1]-points[0]).length/2 for i in range(1,len(points)-1))
            planes[key]['area']+=area;planes[key]['count']+=1
            planes[key]['example']=[[round(p,4) for p in point] for point in points[:4]]
        roof_planes.append(dict(source=row['name'],planes=[dict(z_equals_aU_bV_c=list(k),area=round(v['area'],3),faces=v['count'],example=v['example'],pitch_degrees=round(math.degrees(math.atan(math.hypot(k[0],k[1]))),3)) for k,v in planes.items() if v['area']>.3]))
    if (row['system']=='03 Floor plates' and not row['name'].startswith('SLA - 012') or row['name']=='SLA - 007_Concrete - Foundation_0.029') and dims[0]>2 and dims[1]>1:
        faces=[]
        for face in obj.data.polygons:
            points=[verts[i] for i in face.vertices]
            if all(abs(p.z-row['max'][2])<.001 for p in points):
                faces.append([[round(v,4) for v in p] for p in points])
        if faces:floor_top_faces.append(dict(source=row['name'],top=row['max'][2],faces=faces))

summary=dict(coordinates=result['coordinate_system'],
    levels=[dict(name='ground',slab_top=.5,bedroom_finish=.51,ceiling_underside=2.92),
            dict(name='living',finished_floor=3.22,ceiling_underside=5.64),
            dict(name='upper',finished_floor=5.94,wet_finish=5.95,ceiling_underside=8.39)],
    wall_runs=wall_runs,roof_planes=roof_planes,floor_top_faces=floor_top_faces,
    slabs=[r for r in rows if r['name'].startswith('SLA') and not r['name'].startswith('SLA - 012') and r['max'][0]-r['min'][0]>2 and r['max'][1]-r['min'][1]>1 and r['max'][2]-r['min'][2]<.4],
    furniture=[r for r in rows if r['name'].startswith(('double bed','Dining Table','Coffee Table','Sofa Bed'))],
    fixtures=[r for r in rows if r['system']=='08 Hydraulic fixtures' and 'Ceramic' in r['name']],
    limits=['Floor footprints are bounding extents; actual meshes retain stair voids and step changes.',
            'Foundations material also labels landscape step slabs; true footing geometry and dimensions are unverified.',
            'Wall apertures are measured model voids, not specified timber rough openings.',
            'Roof RT - 025 is a stair-wall component and must not be treated as roof.'])
(OUT/'structure-audit-summary.json').write_text(json.dumps(summary,indent=2))
print('WALL_RUNS',len(wall_runs),'OPENINGS',sum(len(r['openings']) for r in wall_runs),flush=True)
print('ROOF_PLANES',json.dumps(roof_planes),flush=True)
print('STRUCTURE_AUDIT_COMPLETE',len(rows),flush=True)
