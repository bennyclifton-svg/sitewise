"""Mirror complete even-numbered dwellings while retaining shared/end boundaries."""
import sys,json,shutil,re
from pathlib import Path
from collections import Counter
import bpy,bmesh
from mathutils import Matrix,Vector

N=int(sys.argv[-1]);W=49/N;folder=Path(__file__).resolve().parent/f'option-{N}'
master=folder/f'terrace-{N}.blend';baseline=folder/f'terrace-{N}-before-alternating.blend'
if not baseline.exists():
    shutil.copy2(master,baseline)
    for name in ('manifest.json','service-routes.json'):shutil.copy2(folder/name,folder/('before-alternating-'+name))
bpy.ops.wm.open_mainfile(filepath=str(baseline));scene=bpy.context.scene
fixed=('Strip footing','Masonry foundation stem','Masonry bearing wall','Internal wall plasterboard lining',
       'Brick end gable','End gable verge','End window','Wedge privacy hood','Privacy wedge perimeter frame',
       'Rear timber paling fence','Pale rear terrace privacy wall','Rear balcony privacy wing')
site_local=('Driveway crossover','Stormwater inspection pit','Pit grate','Pit stormwater connection')
mirrored={};preserved=[]
def bounds(o):
    ps=[o.matrix_world@Vector(p) for p in o.bound_box]
    return [min(p[i] for p in ps) for i in range(3)],[max(p[i] for p in ps) for i in range(3)]
for o in scene.objects:
    if o.type not in {'MESH','CURVE'}:continue
    owner=o.get('sw_dwelling',0)
    if owner==0 and any(k in o.name for k in site_local):
        lo,hi=bounds(o);owner=min(N,max(1,int(((lo[0]+hi[0])/2)/W)+1))
    if owner not in (2,4,6) or owner>N:continue
    if any(k in o.name for k in fixed):preserved.append(o.name);continue
    assert o.parent is None
    axis=(owner-.5)*W;R=Matrix.Identity(4);R[0][0]=-1;R[0][3]=2*axis
    local=o.matrix_world.inverted()@R@o.matrix_world
    o.data=o.data.copy()
    if o.type=='MESH':
        bm=bmesh.new();bm.from_mesh(o.data)
        bmesh.ops.transform(bm,matrix=local,verts=list(bm.verts))
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.normal_update();bm.to_mesh(o.data);bm.free()
    else:
        for s in o.data.splines:
            for p in s.points:
                q=local@Vector(p.co[:3]);p.co=(*q,p.co[3])
            for p in s.bezier_points:
                p.co=local@p.co;p.handle_left=local@p.handle_left;p.handle_right=local@p.handle_right
    o['sw_mirrored']=True;mirrored[o.name]=owner

# The communal tank stays in place; its inlet follows the final dwelling's pit.
if N==6:
    o=next(o for o in scene.objects if 'Detention inlet' in o.name)
    axis=(N-.5)*W
    for p in list(o.data.splines[0].points)[:2]:p.co.x=2*axis-p.co.x

routes=json.loads((folder/'before-alternating-service-routes.json').read_text())
for route in routes:
    if route['name'] in mirrored:
        axis=(mirrored[route['name']]-.5)*W
        route['points']=[[2*axis-p[0],p[1],p[2]] for p in route['points']]
    elif N==6 and 'Detention inlet' in route['name']:
        for p in route['points'][:2]:p[0]=2*(N-.5)*W-p[0]
bpy.context.view_layer.update()
garages=[]
for owner in range(1,N+1):
    o=next(o for o in scene.objects if o.get('sw_dwelling')==owner and 'Garage sectional door' in o.name)
    lo,hi=bounds(o);centre=(lo[0]+hi[0])/2-(owner-1)*W
    assert (centre>W/2)==(owner in (2,4,6))
    garages.append(dict(dwelling=owner,side='right' if centre>W/2 else 'left',bounds_x=[lo[0],hi[0]]))
audit=dict(status='pass',mirrored_dwellings=[2,4,6],objects_mirrored=len(mirrored),
    preserved_boundary_objects=len(preserved),garages=garages,
    paired_garages=[[i,i+1] for i in (2,4,6) if i+1<=N],
    scope='All dwelling disciplines mirrored, including crossings/pits; shared boundaries and exposed end-window treatments retained')
(folder/'alternating-audit.json').write_text(json.dumps(audit,indent=2))
(folder/'service-routes.json').write_text(json.dumps(routes,indent=2))
manifest=json.loads((folder/'before-alternating-manifest.json').read_text());manifest['alternating']=audit
for home in manifest['homes']:home['mirrored']=home['dwelling'] in (2,4,6)
manifest['count_by_system']=dict(Counter(o.get('sw_system') for o in scene.objects if o.get('sw_system')))
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
scene['sw_mirrored_dwellings']=[2,4,6]
bpy.ops.wm.save_as_mainfile(filepath=str(master))
bpy.ops.export_scene.gltf(filepath=str(folder/f'terrace-{N}.glb'),export_format='GLB',export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
print('ALTERNATING_PASS',N,audit['paired_garages'],flush=True)
