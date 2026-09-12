"""Reproduce the superseded timber study; current direction is RC columns/slabs.

The user asked to retain this earlier geometry for now, with no immediate rebuild.
This script is a historical modelling record, not the active structural specification.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from collections import Counter
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'coordination'
audit=json.loads((OUT/'structure-audit-summary.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/'sitewise-kitchen-checkpoint.blend'))
scene=bpy.context.scene
focus=Vector(audit['coordinates']['world_origin'])
U=Vector(audit['coordinates']['U']);V=Vector(audit['coordinates']['V'])
basis=Matrix(((U.x,V.x,0,focus.x),(U.y,V.y,0,focus.y),(0,0,1,0),(0,0,0,1)))
source={o.get('source_name'):o for o in scene.objects if o.get('source_name')}
collections={}
for name in ['Foundations','Ground wall frame','Living wall frame','Upper wall frame','Floor framing','Roof framing']:
    c=bpy.data.collections.new('STRUCTURE | '+name+' | illustrative')
    c['provenance']='Authored illustrative structure anchored to supplied architecture; not engineered'
    scene.collection.children.link(c);collections[name]=c

def material(name,color,opacity=1):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    nodes=m.node_tree.nodes;shader=nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1);shader.inputs['Roughness'].default_value=.78
    if opacity<1:
        out=nodes.get('Material Output');transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader')
        mix.inputs[0].default_value=opacity;m.node_tree.links.new(transparent.outputs[0],mix.inputs[1]);m.node_tree.links.new(shader.outputs[0],mix.inputs[2]);m.node_tree.links.new(mix.outputs[0],out.inputs[0])
    return m

timber=material('Structure | mineral blue timber',(.075,.18,.25))
concrete=material('Structure | chalk concrete',(.38,.42,.42))
meshes={}
for mat in [timber,concrete]:
    mesh=bpy.data.meshes.new(mat.name+' unit member')
    mesh.from_pydata([(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)],[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    mesh.materials.append(mat);meshes[mat.name]=mesh
records=[]
def member(name,a,b,width,depth,group,source_id=None,mat=timber):
    a,b=Vector(a),Vector(b);length=(b-a).length
    if length<.025:return
    obj=bpy.data.objects.new(name,meshes[mat.name]);collections[group].objects.link(obj)
    transform=Matrix.Translation((a+b)/2)@(b-a).to_track_quat('Z','Y').to_matrix().to_4x4()@Matrix.Diagonal((width,depth,length,1))
    obj.matrix_world=basis@transform
    obj['system']='Illustrative structure';obj['source_reference']=source_id or 'Authored working assumption'
    obj['engineering_status']='Conceptual; member sizing, loads, bearings, fixings and ground conditions unverified'
    records.append(dict(name=name,group=group,a=list(a),b=list(b),width=width,depth=depth,source=source_id))
    return obj

def ranges_union(values,tol=.003):
    merged=[]
    for a,b in sorted(values):
        if b-a<.002:continue
        if merged and a<=merged[-1][1]+tol:merged[-1][1]=max(merged[-1][1],b)
        else:merged.append([a,b])
    return merged
def intersection(first,second):
    return [[max(a,c),min(b,d)] for a,b in first for c,d in second if min(b,d)-max(a,c)>.001]

wall_geometry={}
for run in audit['wall_runs']:
    obj=source[run['source']]
    points=[basis.inverted()@obj.matrix_world@p.co for p in obj.data.vertices]
    wall_geometry[run['source']]=(points,[list(p.vertices) for p in obj.data.polygons])
def wall_slice(run,coordinate,axis):
    verts,faces=wall_geometry[run['source']]
    major=0 if run['axis']=='U' else 1
    fixed=major if axis=='vertical' else 2
    measured=2 if axis=='vertical' else major
    ranges=[]
    for ids in faces:
        hits=[]
        for a,b in zip(ids,ids[1:]+ids[:1]):
            p,q=verts[a],verts[b]
            if (p[fixed]-coordinate)*(q[fixed]-coordinate)<0:
                t=(coordinate-p[fixed])/(q[fixed]-p[fixed]);hits.append((p+(q-p)*t)[measured])
        if len(hits)==2:ranges.append(sorted(hits))
    return ranges_union(ranges)
def wall_point(run,s,z):
    return (s,run['at'],z) if run['axis']=='U' else (run['at'],s,z)

# Perimeter footings sit below the supplied .20-.50 ground slab; sizes are illustrative.
ground_edges=[((-5.3107,-2.5802), (4.0793,-2.5802)),((-5.3107,1.9001),(4.0793,1.9001)),((-5.3107,-2.5802),(-5.3107,1.9001)),((4.0793,-2.5802),(4.0793,1.9001)),((.2773,-2.5802),(.2773,1.9001))]
for i,(a,b) in enumerate(ground_edges):
    member(f'Foundation strip {i+1}',(*a,-.14),(*b,-.14),.45,.64,'Foundations','SLA - 007_Concrete - Foundation_0.029',concrete)
for i,(u,v) in enumerate([(-5.3107,-2.5802),(-5.3107,1.9001),(4.0793,-2.5802),(4.0793,1.9001)]):
    member(f'Foundation corner pad {i+1}',(u,v,-.62),(u,v,-.42),.72,.72,'Foundations',None,concrete)

for ri,run in enumerate(audit['wall_runs']):
    group='Ground wall frame' if run['bottom']<1 else 'Living wall frame' if run['bottom']<4 else 'Upper wall frame'
    major_width=.045;wall_depth=.07
    # Rotate section dimensions to place the thin stud inside its measured lining.
    studs=[run['start']+.06,run['end']-.06]
    s=run['start']+.60
    while s<run['end']-.06:studs.append(s);s+=.60
    for hole in run['openings']:
        if not hole['type'].startswith('Model void'):continue
        studs.extend([hole['start']-.025,hole['end']+.025])
    for si,s in enumerate(sorted(set(round(v,4) for v in studs))):
        if s<run['start']+.023 or s>run['end']-.023:continue
        spans=wall_slice(run,s-.0226,'vertical')
        spans=intersection(spans,wall_slice(run,s+.0226,'vertical'))
        for pi,(za,zb) in enumerate(spans):
            a=wall_point(run,s,za+.04);b=wall_point(run,s,zb-.04)
            obj=member(f'Wall {ri+1:02} stud {si+1:02}.{pi}',a,b,major_width if run['axis']=='U' else wall_depth,wall_depth if run['axis']=='U' else major_width,group,run['source'])
    for label,z in [('bottom plate',run['bottom']+.0225),('top plate',run['top']-.0225)]:
        spans=intersection(wall_slice(run,z-.0224,'horizontal'),wall_slice(run,z+.0224,'horizontal'))
        for pi,(a,b) in enumerate(spans):
            member(f'Wall {ri+1:02} {label} {pi}',wall_point(run,a+.002,z),wall_point(run,b-.002,z),wall_depth,.045,group,run['source'])
    for hi,hole in enumerate(run['openings']):
        if not hole['type'].startswith('Model void'):continue
        a,b=hole['start'],hole['end']
        if hole['top']+.16<run['top']:
            member(f'Wall {ri+1:02} opening {hi+1} header',wall_point(run,a-.045,hole['top']+.08),wall_point(run,b+.045,hole['top']+.08),wall_depth,.16,group,run['source'])
        if hole['bottom']>run['bottom']+.1:
            member(f'Wall {ri+1:02} opening {hi+1} sill',wall_point(run,a,hole['bottom']-.0225),wall_point(run,b,hole['bottom']-.0225),wall_depth,.045,group,run['source'])
    if run['source']=='SW - 574_Wall white plaster_0.008':
        # Actual angled stair profile, separate from the rectangular opening schedule.
        member('Stair wall sloping top plate',wall_point(run,-2.88,4.106),wall_point(run,-.8796,5.616),wall_depth,.045,group,run['source'])

# Floor joists are intersected with the exact source top polygons, preserving stair holes.
floor_ids=['SLA - 008_Wall white plaster_0.002','SLA - 010_Wall white plaster_0.024','SLA - 010_Wall white plaster_0.025','SLA - 010_Wall white plaster_0.026']
def floor_slice(faces,u):
    ranges=[]
    for face in faces:
        hits=[]
        for p,q in zip(face,face[1:]+face[:1]):
            if (p[0]-u)*(q[0]-u)<0:
                hits.append(p[1]+(q[1]-p[1])*(u-p[0])/(q[0]-p[0]))
        if len(hits)==2:ranges.append(sorted(hits))
    return ranges_union(ranges)
for fi,source_id in enumerate(floor_ids):
    slab=source[source_id]
    vertices=[basis.inverted()@slab.matrix_world@p.co for p in slab.data.vertices]
    bottom=min(p.z for p in vertices);top=max(p.z for p in vertices)
    # Plaster owns the slab underside and sides; the top finish is a separate source mesh.
    faces=[[list(vertices[i]) for i in face.vertices] for face in slab.data.polygons if all(abs(vertices[i].z-bottom)<.001 for i in face.vertices)]
    if not faces:raise RuntimeError('Missing source slab underside '+source_id)
    z=(bottom+top)/2
    low=min(p[0] for f in faces for p in f);high=max(p[0] for f in faces for p in f)
    u=low+.07;ji=0
    while u<high-.05:
        spans=intersection(floor_slice(faces,u-.0226),floor_slice(faces,u+.0226))
        for pi,(a,b) in enumerate(spans):
            member(f'Floor {fi+1} joist {ji+1:02}.{pi}',(u,a+.045,z),(u,b-.045,z),.045,.24,'Floor framing',source_id)
        u+=.45;ji+=1
    edge_counts=Counter()
    for face in faces:
        for p,q in zip(face,face[1:]+face[:1]):
            edge_counts[tuple(sorted((tuple(p[:2]),tuple(q[:2]))))]+=1
    for ei,(edge,count) in enumerate(edge_counts.items()):
        if count!=1:continue
        a,b=edge
        if math.dist(a,b)>.16:
            member(f'Floor {fi+1} boundary trimmer {ei}',(*a,z),(*b,z),.045,.24,'Floor framing',source_id)

# The source has a very shallow eave. Clip/taper the visual frame to the real roof void;
# the missing heel/bearing detail is an unresolved interface, not an invented solution.
def roof_underside(u):
    return .2679*u+9.8167 if u<=-.3658 else -.2679*u+9.6207

def tapered_rafter(name,eave_u,v,ridge_u,source_id):
    slope=.2679 if eave_u<ridge_u else -.2679
    intercept=9.8167 if eave_u<ridge_u else 9.6207
    full_depth_u=(8.412+.18+.015-intercept)/slope
    us=sorted([eave_u,full_depth_u,ridge_u])
    vertices=[]
    for u in us:
        top=roof_underside(u)-.015;bottom=max(8.412,top-.18)
        vertices.extend([(u,v-.035,bottom),(u,v+.035,bottom),(u,v+.035,top),(u,v-.035,top)])
    faces=[(0,3,2,1),(8,9,10,11)]
    for i in [0,4]:faces.extend([(i,i+1,i+5,i+4),(i+1,i+2,i+6,i+5),(i+2,i+3,i+7,i+6),(i+3,i,i+4,i+7)])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.materials.append(timber)
    obj=bpy.data.objects.new(name,mesh);collections['Roof framing'].objects.link(obj);obj.matrix_world=basis
    obj['system']='Illustrative structure';obj['source_reference']=source_id
    obj['engineering_status']='Ceiling/roof-clipped tapered visual rafter; heel, bearing and member design unresolved'
    records.append(dict(name=name,group='Roof framing',source=source_id,width=.07,
        depth='Up to .18 vertically, tapered to measured roof void',vertices_uvz=vertices))

ridge_u=-.3658;v0=-2.54;v1=1.85;rafter_i=0
while v0<=v1+.01:
    rafter_i+=1
    for label,eave_u in [('west',-5.10),('east',4.35)]:
        tapered_rafter(f'Roof rafter {rafter_i:02} {label}',eave_u,v0,ridge_u,'RT - 024_Wall white plaster_0'+('.001' if label=='east' else ''))
    member(f'Roof tie {rafter_i:02}',(-4.94,v0,8.45),(4.17,v0,8.45),.07,.07,'Roof framing','Conceptual reduced-depth tie clipped to roof void; span and heel design unverified')
    if rafter_i%2:
        member(f'Roof central post {rafter_i:02}',(ridge_u,v0,8.50),(ridge_u,v0,9.58),.07,.07,'Roof framing','Conceptual roof framing; not a designed truss')
    v0+=.6
member('Roof ridge board',(ridge_u,-2.58,9.54),(ridge_u,1.90,9.54),.075,.21,'Roof framing','RT - 024 roof-plane intersection')
roof_vertices=[basis.inverted()@obj.matrix_world@vertex.co for obj in collections['Roof framing'].objects for vertex in obj.data.vertices]
roof_qa=dict(minimum_z=min(v.z for v in roof_vertices),ceiling_z=8.39,
    minimum_roof_clearance=min(roof_underside(v.x)-v.z for v in roof_vertices))
if roof_qa['minimum_z']<8.40 or roof_qa['minimum_roof_clearance']<.005:
    raise RuntimeError('Roof members exceed measured void: '+str(roof_qa))

manifest=dict(stage='First focus-dwelling structural prototype',source_scene='sitewise-kitchen-checkpoint.blend',
    coordinates=audit['coordinates'],collection_names=[c.name for c in collections.values()],
    counts=dict(Counter(r['group'] for r in records)),members=records,roof_geometry_check=roof_qa,
    retained_source_ground_slab='SLA - 007_Concrete - Foundation_0.029, Z .20-.50; not duplicated in library',
    floor_rule='Added joists/trimmers only within existing 300 mm floor zones; source slab/finish presentation remains separately controlled',
    unresolved_interfaces=[
        dict(id='structure-east-floor-transfer',anchor_uvz=[4.1243,-.34,2.92],
            question='How is the living-floor edge supported beyond the ground-floor wall line?',
            observation='Ground east wall ends at U4.1243; living floor continues to U4.5743, a modelled offset of 0.45.',
            source_ids=['SLA - 007_Concrete - Foundation_0.029','SLA - 008_Wall white plaster_0.002'],
            disciplines=['Architecture','Structural engineering'],status='Illustrative coordination question; support strategy unverified'),
        dict(id='structure-stair-trimming',anchor_uvz=[-.85,-1.98,5.79],
            question='Agree stair-opening trimmers, bearings and the reserved service route before framing.',
            observation='Upper-floor mesh contains a stair void; joists in this study stop at the source opening polygons.',
            source_ids=['SLA - 010_Wall white plaster_0.024','SW - 574_Wall white plaster_0.008'],
            disciplines=['Architecture','Structural engineering','Hydraulics','Electrical'],status='Trimming shown conceptually; bearing and penetration details unresolved'),
        dict(id='structure-roof-services-zone',anchor_uvz=[4.35,-.34,8.43],
            question='Resolve the shallow roof heel/bearing detail and reserve ventilation/electrical routes in the remaining roof space.',
            observation='Measured ceiling is Z8.39; roof underside near east wall is only about Z8.407. Visual rafters taper and ties stop short to fit the real void; no bearing detail is asserted.',
            source_ids=['SLA - 010_Wall white plaster_0.035','RT - 024_Wall white plaster_0','RT - 024_Wall white plaster_0.001'],
            disciplines=['Structural engineering','Mechanical ventilation','Electrical','Architecture'],status='Illustrative coordination question; system routes and penetrations remain unassigned')],
    assumptions=['Timber studs/roof framing and concrete foundations authorized as an illustrative working assumption.',
        'Member sizes, spans, load-bearing roles, connections, fire separation, wind/bracing and foundation design are unverified.',
        'Floor openings clipped against actual source polygons; wall studs trimmed to actual wall solid intervals.',
        'Sloping stair wall treated separately; RT-025 not treated as roof.',
        'Roof rafters are tapered and ties shortened to remain above the existing ceiling and below roof covering. Heel/bearing design remains unresolved.',
        'Focus dwelling only; rest of development remains supplied architecture.'])
if '--render-only' not in sys.argv:
    (OUT/'structure-checkpoint.json').write_text(json.dumps(manifest,indent=2))
    bpy.data.libraries.write(str(OUT/'sitewise-structure-library.blend'),set(collections.values()),fake_user=True,compress=True)
print('STRUCTURE_LIBRARY_WRITTEN',manifest['counts'],flush=True)

# Review renders only: architecture stays in place and is selectively translucent.
ghost=material('Review | contextual architecture',(.73,.77,.77),.095)
roof_ghost=material('Review | contextual roof',(.75,.79,.78),.10)
floor_ghost=material('Review | contextual floor',(.72,.76,.75),.11)
for obj in list(scene.objects):
    if obj.type!='MESH' or not obj.get('source_name') or obj.hide_render:continue
    corners=[basis.inverted()@obj.matrix_world@Vector(p) for p in obj.bound_box]
    lo=[min(p[i] for p in corners) for i in range(3)];hi=[max(p[i] for p in corners) for i in range(3)]
    if obj.get('system')=='01 Site':obj.hide_render=True;continue
    if lo[1]<2.15 and hi[1]>-2.85 and hi[0]>-5.8 and lo[0]<5.1:
        if obj.get('source_name')=='SLA - 007_Concrete - Foundation_0.029':continue
        if obj['source_name'].startswith(('CI Tools Roof Covering','CI Tools Wall')):
            obj.hide_render=True
            continue
        obj.data=obj.data.copy();obj.data.materials.clear()
        obj.data.materials.append(roof_ghost if obj.get('system')=='06 Roof' else floor_ghost if obj.get('system')=='03 Floor plates' else ghost)
print('STRUCTURE_ARCHITECTURE_REVEAL_READY',flush=True)
for c in list(scene.collection.children):
    if c.name.startswith(('CHECKPOINT','SW Asset')):
        for obj in list(c.all_objects):
            if obj is not None:obj.hide_render=True
print('STRUCTURE_RENDER_START',flush=True)

scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.cycles.max_bounces=8;scene.cycles.transparent_max_bounces=8
scene.render.resolution_x=1280;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
camera=scene.camera;camera.data.type='ORTHO';camera.data.dof.use_dof=False
def render(filename,position,target,scale):
    camera.location=basis@Vector(position);look=basis@Vector(target)
    camera.rotation_euler=(look-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.filepath=str(OUT/filename);bpy.ops.render.render(write_still=True)
render('15-structure-overview.png',(-17,-19,16),(-.3,-.3,4.4),17)
render('16-structure-detail.png',(14,-16,12),(2.2,-1.9,5.7),8)
print('STRUCTURE_CHECKPOINT_COMPLETE',len(records),flush=True)
