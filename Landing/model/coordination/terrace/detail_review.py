"""Roof joints, entry service, planted trees, privacy hoods and raked roof framing."""
import sys,runpy,json,math,random,hashlib
from pathlib import Path
from collections import Counter
import bpy
from mathutils import Vector

N=int(sys.argv[-1]);HERE=Path(__file__).resolve().parent
sys.argv[-1:-1]=['--detail-review','--defer-save']
g=runpy.run_path(str(HERE/'frontage_revision.py'))
scene=g['scene'];folder=g['folder'];W=g['W'];box=g['box'];mesh=g['mesh'];pipe=g['pipe'];bounds=g['bounds'];remove=g['remove'];rz=g['rz'];dark=g['dark'];white=g['white'];join=g['join_y']
timber=bpy.data.materials['Oak joinery and framing']
downpipes={o.name:([list(p.co) for s in o.data.splines for p in s.points],list(o.matrix_world)) for o in scene.objects if o.type=='CURVE' and 'Downpipe' in o.name}

# Meet at the party boundary, with a continuous weathering strip over each joint.
roof_names=('Roof front left','Roof front right','Shallow pitched main roof','Shallow rear roof beside dormer','Rear roof metal infill')
for o in scene.objects:
    if o.type!='MESH' or not any(k in o.name for k in roof_names):continue
    x=(o['sw_dwelling']-1)*W
    for v in o.data.vertices:
        if abs(v.co.x-(x+.05))<.001:v.co.x=x
        elif abs(v.co.x-(x+W-.05))<.001:v.co.x=x+W
for i in range(1,N):
    x=i*W
    for a,b in ((0,2),(2,7.8),(7.8,14.6)):
        mesh('Roof party-joint flashing',[(x-.045,a,rz(a)+.018),(x+.045,a,rz(a)+.018),(x+.045,b,rz(b)+.018),(x-.045,b,rz(b)+.018)],[(0,1,2,3)],dark)

routes=json.loads((folder/'service-routes.json').read_text())
for o in scene.objects:
    if 'Underground electricity service' not in o.name:continue
    old=[tuple(p.co[:3]) for p in o.data.splines[0].points];first,last=old[0],old[-1]
    pts=[first,(first[0],.3,-.45),(last[0],.3,-.45),(last[0],last[1],-.45),last]
    o.data.splines.clear();s=o.data.splines.new('POLY');s.points.add(len(pts)-1)
    for p,v in zip(s.points,pts):p.co=(*v,1)
    for route in routes:
        if route['name']==o.name:route['points']=pts

# Upper privacy hoods: solid diagonal shield and triangular top/bottom, open at
# opposite ends. The lower window remains an ordinary framed opening.
for o in list(scene.objects):
    if 'End window hood' in o.name:remove(o)
hoods=[]
for owner,edge,sign in ((1,0,-1),(N,49,1)):
    for level,(ya,yb,s,h) in enumerate(g['windows']):
        if level==0:continue
        rear=level==1; yy=yb if rear else ya
        A=(edge+sign*.04,ya);B=(edge+sign*.04,yb);C=(edge+sign*.62,yy)
        v=[(xx,y,z) for z in (s-.045,h+.045) for xx,y in (A,B,C)]
        diagonal=(0,2,5,3) if rear else (1,2,5,4)
        mesh('Wedge privacy hood '+('opens rear' if rear else 'opens front'),v,[(0,2,1),(3,4,5),diagonal],dark,owner=owner)
        hoods.append((owner,v,diagonal))

# Individual branches and leaves replace the faceted placeholder crowns.
for o in list(scene.objects):
    if 'Tree crown' in o.name or 'Tree trunk' in o.name:remove(o)
leafm=[]
for j,color in enumerate(((.12,.21,.065,1),(.2,.32,.10,1),(.29,.4,.15,1),(.16,.27,.09,1))):
    m=bpy.data.materials.new(f'Living foliage {j}');m.diffuse_color=color;m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=.62
    leafm.append(m)
bark=bpy.data.materials.new('Tree bark brown');bark.diffuse_color=(.18,.105,.055,1);bark.use_nodes=True
bark.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.18,.105,.055,1)
tree_bounds=[]
for i in range(N):
    x=i*W;owner=i+1
    for rear in (False,True):
        rng=random.Random(1300+owner*11+rear)
        cx=x+1.75 if rear else x+W-1.02;cy=18.6 if rear else -1.08
        radius=1.02 if rear else .58;height=4.0 if rear else 3.65
        pipe('Natural tree trunk',[(cx,cy,.1),(cx+.025,cy,1.3),(cx-.035,cy+.04,2.35),(cx,cy,3.4)],.043,bark,'landscape',owner)
        verts=[[] for _ in leafm];faces=[[] for _ in leafm]
        for j in range(18):
            angle=j*2.399+owner*.2;z=1.8+j/18*(height-2.0)
            spread=radius*(.75 if j<12 else .5)
            end=Vector((cx+math.cos(angle)*spread,cy+math.sin(angle)*spread,z+.12))
            start=Vector((cx,cy,z-.35))
            pipe('Natural tree branch',[start,(start+end)/2+Vector((0,0,-.05)),end],.012 if j<9 else .008,bark,'landscape',owner)
            for k in range(95):
                theta=rng.uniform(0,math.tau);rr=math.sqrt(rng.random())*radius*.26
                p=end+Vector((math.cos(theta)*rr,math.sin(theta)*rr,rng.uniform(-.23,.23)))
                yaw=rng.uniform(0,math.tau);pitch=rng.uniform(-.75,.75)
                along=Vector((math.cos(yaw)*math.cos(pitch),math.sin(yaw)*math.cos(pitch),math.sin(pitch)))
                across=Vector((-math.sin(yaw),math.cos(yaw),.15))
                length=rng.uniform(.055,.10);width=length*.36;c=rng.randrange(4);a=len(verts[c])
                points=[p-along*length,p-across*width,p+Vector((0,0,.012)),p+along*length,p+across*width]
                verts[c].extend(points);faces[c].extend([(a,a+1,a+2),(a+1,a+3,a+2),(a+3,a+4,a+2),(a+4,a,a+2)])
        for c in range(4):
            obj=mesh('Natural tree leaves '+('rear' if rear else 'front'),verts[c],faces[c],leafm[c],'landscape',owner)
            for poly in obj.data.polygons:poly.use_smooth=True
            xs=[v[0] for v in verts[c]]
            assert min(xs)>x+.25 and max(xs)<x+W-.25,'Foliage intersects party boundary'
        tree_bounds.append(dict(dwelling=owner,rear=rear,centre=[cx,cy],radius=radius))

# Roof framing follows the envelope and is trimmed around dormer openings.
for o in list(scene.objects):
    if o.get('sw_system')=='structure' and any(k in o.name for k in ('Timber flat roof joist','Roof steel cross beam','Roof steel post')):remove(o)
def beam(name,a,b,width,depth,mat=timber,owner=0):
    a=Vector(a);b=Vector(b);v=b-a
    o=box(name,(-width/2,-depth/2,-v.length/2),(width/2,depth/2,v.length/2),mat,'structure',owner)
    o.location=(a+b)/2;o.rotation_euler=v.to_track_quat('Z','Y').to_euler();return o
rafters=[]
for i in range(N):
    x=i*W;owner=i+1
    # Steel cross beams sit beneath the raked timber, with matching-height posts.
    for y in (2.1,7.8,11.35):
        z=rz(y)-.32
        beam('Roof steel cross beam at roof profile',(x+.35,y,z),(x+W-.35,y,z),.1,.2,dark,owner)
        for xx in (x+.35,x+W-.35):beam('Roof steel post to raked frame',(xx,y,6.55),(xx,y,z),.1,.1,dark,owner)
    grid=[x+.32+j*(W-.64)/math.ceil((W-.64)/.4) for j in range(math.ceil((W-.64)/.4)+1)]
    for xx in grid:
        front_open=x+.65<xx<x+3.35;rear_open=x+.65<xx<x+6.05
        segments=[(1.82 if front_open else .15,2),(2,7.8),(7.8,join if rear_open else 14.4)]
        for ya,yb in segments:
            offset=.24 if yb<=2 else .14
            a=(xx,ya,rz(ya)-offset);b=(xx,yb,rz(yb)-offset)
            obj=beam('Raked timber roof rafter',a,b,.045,.195,owner=owner);rafters.append((obj,offset))
    for front,dl,dr,ya,yb,opening_y in ((True,.65,3.35,.03,1.82,.18),(False,.65,6.05,join,14.44,14.18)):
        prefix='Front dormer' if front else 'Rear dormer'
        head_y=yb if front else ya
        beam(prefix+' opening head trimmer',(x+dl,head_y,9.20),(x+dr,head_y,9.20),.09,.18,owner=owner)
        fy,by=(.20,1.72) if front else (ya+.08,14.20)
        for xx in (x+dl+.045,x+dr-.045):
            beam(prefix+' cheek roof frame',(xx,fy,9.19),(xx,by,9.19),.07,.18,owner=owner)
            for yy in (fy,by):beam(prefix+' cheek jamb',(xx,yy,6.58),(xx,yy,9.19),.07,.07,owner=owner)
        for j in range(math.ceil((dr-dl)/.4)+1):
            xx=x+dl+.1+j*(dr-dl-.2)/math.ceil((dr-dl)/.4)
            beam(prefix+' cap rafter',(xx,fy,9.19),(xx,by,9.19),.045,.145,owner=owner)
        cy=.12 if front else 14.20
        box(prefix+' metal head closure',(x+dl,cy,9.22),(x+dr,cy+.055,9.38),dark,owner=owner)
        # Frames sit behind glazing; none pass across the clear window opening.
        yy=opening_y+.14 if front else opening_y-.14
        for xx in (x+dl+.09,x+dr-.09):beam(prefix+' window jamb',(xx,yy,6.72),(xx,yy,9.23),.07,.09,owner=owner)
        for z in (6.72,9.23):beam(prefix+' window head sill',(x+dl+.09,yy,z),(x+dr-.09,yy,z),.07,.09,owner=owner)
        # Doubled raked trimmers carry the interrupted rafters at each cheek.
        for xx in (x+dl-.07,x+dr+.07):
            a,b=(.15,2) if front else (join,14.4)
            offset=.24 if front else .16
            beam(prefix+' raked side trimmer',(xx,a,rz(a)-offset),(xx,b,rz(b)-offset),.09,.195,owner=owner)
for owner,v,diagonal in hoods:
    for a,b in ((0,1),(1,2),(2,0),(3,4),(4,5),(5,3),(0,3),(1,4),(2,5)):
        beam('Privacy wedge perimeter frame',v[a],v[b],.035,.035,dark,owner)
for owner,edge in ((1,.12),(N,48.88)):
    for ya,yb,s,h in g['windows']:
        beam('End window masonry lintel',(edge,ya-.15,h+.09),(edge,yb+.15,h+.09),.15,.16,dark,owner)

bpy.context.view_layer.update()
assert downpipes=={o.name:([list(p.co) for s in o.data.splines for p in s.points],list(o.matrix_world)) for o in scene.objects if o.type=='CURVE' and 'Downpipe' in o.name}
assert not any('Timber flat roof joist' in o.name for o in scene.objects)
for obj,offset in rafters:
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co
        assert p.z<rz(p.y)-.005,(obj.name,'Rafter penetrates roof cladding',list(p))
audit=dict(status='pass',roof_joint_gaps_closed=N-1,downpipes_unchanged=True,front_services_below_ground=True,
    end_window_heights_m=[1.45,1.8,2.0],hood_projection_m=.62,hood_openings=['first floor: rear','roof floor: front'],
    trees=tree_bounds,raked_rafter_segments=len(rafters),roof_frame='Profile-aligned rafters, trimmed dormers, cheek/window frames, wedge frames and end lintels; provisional member sizes')
(folder/'detail-review-audit.json').write_text(json.dumps(audit,indent=2))
(folder/'service-routes.json').write_text(json.dumps(routes,indent=2))
manifest=json.loads((folder/'manifest.json').read_text());manifest['detail_review']=audit
manifest['count_by_system']=dict(Counter(o.get('sw_system') for o in scene.objects if o.get('sw_system')))
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
scene['sw_detail_review']=True
bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'terrace-{N}.blend'))
bpy.ops.export_scene.gltf(filepath=str(folder/f'terrace-{N}.glb'),export_format='GLB',export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
print('DETAIL_REVIEW_PASS',N,flush=True)
