"""Sample-house ownership, visitor cars and illustrative piled foundations."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from replicate_dwellings import bounds,transforms
from export_web import export
SOURCE=HERE.parent/'sitewise-compact-site-v18.blend'
TARGET=HERE.parent/'sitewise-sample-house-v19.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
placements=transforms(scene)
audit=dict(parked_cars=[],garden=[],services=[],piles=[],fence=[])
mat=scene.objects['V3 | RC ground slab 200mm'].data.materials[0]

def solid(name,vertices,faces):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.materials.append(mat)
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    return obj

def owner(obj,number=2,underground=False):
    obj['sw_reveal_dwelling']=number
    if underground:obj['sw_underground']=True

# Clone the existing licensed vehicle, keeping the original as the only moving car.
cars=[o for o in scene.objects if not o.hide_render and o.get('sw_motion')=='car']
assert cars
old_origin=Vector((-2.12,-13.43335,.5))
for i,y in enumerate((13.50,16.0),1):
    parked_matrix=Matrix.Translation(Vector((-3.0,y,.28)))@Matrix.Scale(.86,4)@Matrix.Translation(-old_origin)
    for original in cars:
        obj=original.copy();obj.data=original.data.copy();scene.collection.objects.link(obj)
        obj.name=f'Visitor car {i} | '+original.name
        obj.matrix_world=parked_matrix@original.matrix_world
        del obj['sw_motion'];obj['sw_parked_vehicle']=i
        obj['sw_civil_surface']=True
        if 'sw_reveal_dwelling' in obj:del obj['sw_reveal_dwelling']
    audit['parked_cars'].append(dict(bay=i,centre=[-3.0,y,.28]))

# Swap the roller assembly to the sample garage, restoring the old source panel.
old_panel=scene.objects['DOO - 018_Paint - Titanium White_0.001'];old_panel.hide_render=False;old_panel.hide_set(False)
old_track=scene.objects.get('DOO - 018_Metal - Iron_0.001')
if old_track:old_track.hide_render=False;old_track.hide_set(False)
new_panel=scene.objects['DOO - 018_Paint - Titanium White_0.002']
lo,hi=bounds(new_panel);garage_y=(lo.y+hi.y)/2
new_panel.hide_render=True;new_panel.hide_set(True)
# The source track stays in place as the new roller's bearing hardware.
delta=garage_y-old_origin.y
for obj in cars:
    obj.location.y+=delta;owner(obj)
    obj['sw_component']='sample_vehicle'
for obj in scene.objects:
    if str(obj.get('sw_motion','')).startswith('door:') or obj.name=='Detail | Garage roller hood':
        obj.location.y+=delta;owner(obj);obj['sw_service_systems']='["structure"]'
scene['sw_car_origin']=json.dumps([-2.12,.5,-garage_y])
audit['car_origin']=json.loads(scene['sw_car_origin'])

# Include the entire authored garden family, not just its deck/tree/awning subset.
for obj in scene.objects:
    if obj.name.startswith(('Garden | Townhouse 2 ','V3 | Shrub 2 ','V3 | Garden bed 2')):
        owner(obj);obj['sw_landscape_dwelling']=2;audit['garden'].append(obj.name)

# Split only the rear boundary stretch behind this garden into its own owned mesh.
fence=scene.objects['V3 | Perimeter 2']
lo,hi=bounds(scene.objects['V3 | Private lawn 2'])
ya,yb=lo.y,hi.y
for index,(left,right) in enumerate(((-100,ya),(ya,yb),(yb,100))):
    bm=bmesh.new();bm.from_mesh(fence.data);bmesh.ops.transform(bm,matrix=fence.matrix_world,verts=list(bm.verts))
    for y,normal in ((left,(0,1,0)),(right,(0,-1,0))):
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,y,0),plane_no=normal,clear_inner=True,dist=.00001)
    data=bpy.data.meshes.new(f'Sample rear fence {index}');bm.to_mesh(data);bm.free()
    for material in fence.data.materials:data.materials.append(material)
    obj=bpy.data.objects.new(f'Sample site | Rear fence section {index}',data);scene.collection.objects.link(obj);obj['sw_system']='landscape'
    if index==1:owner(obj);obj['sw_landscape_dwelling']=2;audit['fence'].append(obj.name)
bpy.data.objects.remove(fence,do_unlink=True)

# Associate dedicated utility feeds and the sample's shared driveway pit with it.
for obj in scene.objects:
    if obj.hide_render:continue
    ids=json.loads(obj.get('sw_endpoint_ids','[]'))
    hydraulic_feed=obj.get('sw_system')=='hydraulic' and ('TH02' in obj.name or 'WAT-feed-2' in obj.name)
    is_storm=obj.name.startswith('Storm |') and (any('House 2 ' in s for s in ids) or obj.name.startswith(('Storm | House 2 rear pit','Storm | Driveway pit 3 ')))
    is_roof=obj.name.startswith('Coordinated | TH02 ')
    is_power='DB-02' in obj.name
    if is_storm or is_roof or is_power or hydraulic_feed:
        owner(obj);audit['services'].append(obj.name)
        if obj.type in ('MESH','CURVE'):
            lo,hi=bounds(obj)
            if lo.z<0:obj['sw_underground']=True
    if obj.name.startswith('Storm | Driveway pit 3 grate'):
        obj.location.z+=.055
    elif obj.name.startswith('Storm | Driveway pit 3 chamber'):
        obj.data=obj.data.copy();inv=obj.matrix_world.inverted()
        for v in obj.data.vertices:
            p=obj.matrix_world@v.co
            if p.z>.2:p.z+=.055;v.co=inv@p
    elif obj.name.startswith('Storm | House 2 rear pit grate'):
        obj.location.z+=.04

# Twelve piles per dwelling: approximately 3 m across, three rows along its depth.
for number,matrix,record in placements:
    slab=scene.objects['V3 | RC ground slab 200mm' if number==1 else f'TH{number:02} | V3 | RC ground slab 200mm']
    lo,hi=bounds(slab);top=lo.z+.025
    for ix in range(4):
        x=lo.x+.40+(hi.x-lo.x-.8)*ix/3
        for iy in range(3):
            y=lo.y+.40+(hi.y-lo.y-.8)*iy/2
            vertices=[(x+.15*math.cos(k*math.tau/12),y+.15*math.sin(k*math.tau/12),z) for z in (top-4,top) for k in range(12)]
            faces=[tuple(reversed(range(12))),tuple(range(12,24))]+[(k,(k+1)%12,(k+1)%12+12,k+12) for k in range(12)]
            obj=solid(f'Foundations | TH{number:02} pile {ix+1}.{iy+1}',vertices,faces)
            obj['sw_system']='structure';obj['sw_component']='pile';obj['sw_dwelling']=number
            owner(obj,number,True)
            audit['piles'].append(dict(name=obj.name,diameter=.3,depth=4,head=[x,y,top]))
            vertices=[(x+dx,y+dy,z) for z in (top-.325,top+.025) for dy in (-.3,.3) for dx in (-.3,.3)]
            cap=solid(f'Foundations | TH{number:02} pile cap {ix+1}.{iy+1}',vertices,[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
            cap['sw_system']='structure';cap['sw_component']='pile_cap';owner(cap,number,True)

bpy.context.view_layer.update()
for i,centre in enumerate((13.5,16),1):
    objects=[o for o in scene.objects if o.get('sw_parked_vehicle')==i]
    extent=[bounds(o) for o in objects]
    low=Vector([min(p[0][k] for p in extent) for k in range(3)]);high=Vector([max(p[1][k] for p in extent) for k in range(3)])
    assert low.x>=-5.6 and high.x<=-.2 and low.y>=centre-1.25 and high.y<=centre+1.25,(i,low,high)
assert len(audit['piles'])==60 and len(audit['fence'])==1
assert len([o for o in scene.objects if str(o.get('sw_motion','')).startswith('door:')])==21
scene['sw_sample_house_v19']=json.dumps(audit)
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
(HERE/'sample-house-v19-audit.json').write_text(json.dumps(audit,indent=2))
export(scene)
print('SAMPLE_HOUSE_PASS', {k:len(v) for k,v in audit.items()},flush=True)
