"""Static blue/chalk hero studies from the registered illustrative siting scene."""
import bpy
import json
import math
import sys
from collections import Counter
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

OUT=Path(__file__).resolve().parent
REPO=OUT.parents[2]
WEB=REPO/'frontend/public/landing-assets/coordination'
WEB.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'sitewise-siting-study.blend'))
scene=bpy.context.scene
siting=json.loads((OUT/'siting-study.json').read_text())
source_transforms={o.name:[list(row) for row in o.matrix_world] for o in scene.objects if o.get('source_name')}

def material(name,color,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    n=m.node_tree.nodes.get('Principled BSDF')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.88
    n.inputs['Emission Color'].default_value=(*color,1);n.inputs['Emission Strength'].default_value=emission
    return m

blue=material('Hero | rich blue ground',(.004,.085,.34))
blue_lot=material('Hero | selected parcel blue',(.005,.095,.36))
blue_paving=material('Hero | blue access surface',(.009,.105,.36))
blue_context=material('Hero | quiet cadastral blue',(.035,.19,.46),.05)
blue_selected=material('Hero | selected boundary',(.16,.38,.64),.04)
chalk=material('Hero | warm chalk',(.83,.82,.77))
graphite=material('Hero | quiet glazing',(.105,.16,.21))
warm=material('Hero | selective interior warmth',(.80,.60,.32),.38)
warm_glazing=[]
for obj in list(scene.objects):
    if obj.type=='LIGHT':obj.hide_render=True
    if obj.type not in ['MESH','CURVE'] or obj.hide_render:continue
    if obj.name.startswith('Illustrative boundary clearance'):
        obj.hide_render=True;continue
    mat=None
    if obj.name=='Studio ground | not survey geometry':mat=blue
    elif obj.name=='Selected illustrative parcel | not surveyed':mat=blue_lot
    elif obj.name.startswith('Source-derived cadastral boundary'):mat=blue_context
    elif obj.name=='Selected lot boundary':mat=blue_selected
    elif obj.get('system')=='01 Site':mat=blue_paving
    elif obj.get('source_name'):
        mat=graphite if 'Glass' in obj['source_name'] else chalk
        corners=[obj.matrix_world@Vector(p) for p in obj.bound_box]
        centre=sum(corners,Vector())/8
        if obj['source_name'].startswith('DOO - 020_Glass') and centre.y<1:
            mat=warm;warm_glazing.append(obj['source_name'])
    if mat:
        obj.data=obj.data.copy();obj.data.materials.clear();obj.data.materials.append(mat)

lighting=bpy.data.collections.new('HERO | art-direction lighting')
scene.collection.children.link(lighting)
def area(name,position,target,energy,size,color):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);lighting.objects.link(o);o.location=position
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o
area('Hero key | directional daylight',(-24,-30,45),(0,0,2),15500,8,(1,.94,.85))
area('Hero fill | quiet sky',(24,-10,26),(0,0,4),5000,22,(.78,.87,1))
area('Hero rim | upper roof',(-8,36,32),(0,0,5),8500,15,(.95,.97,1))
scene.world.use_nodes=True
background=scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value=(.72,.80,.95,1);background.inputs['Strength'].default_value=.18

camera=bpy.data.objects['Camera | reverse study'];scene.camera=camera
camera.location=(-44,-65,58)
target=Vector((0,0,1.5));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=62;camera.data.dof.use_dof=False
scene.render.resolution_x=1200;scene.render.resolution_y=1320;scene.render.resolution_percentage=100
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'

# Keep the full parcel within the left image; camera framing never moves the site geometry.
points=[Vector((x,y,0)) for x,y in siting['lot']]
for obj in scene.objects:
    if obj.get('system') in ['04 Walls','06 Roof'] and not obj.hide_render:
        points.extend(obj.matrix_world@Vector(p) for p in obj.bound_box)
for _ in range(8):
    bpy.context.view_layer.update()
    projected=[world_to_camera_view(scene,camera,p) for p in points]
    required=max(max(abs(p.x-.5)/.425,abs(p.y-.5)/.435) for p in projected)
    if required<=1.001:break
    camera.data.ortho_scale*=required*1.005

for name,matrix in source_transforms.items():
    assert all(abs(bpy.data.objects[name].matrix_world[i][j]-matrix[i][j])<.00001 for i in range(4) for j in range(4)),name

# The plan uses actual projected roof outlines and the exact shared cadastral segments.
roof_edges=set();roof_faces=[]
for obj in scene.objects:
    if not obj.get('source_name','').startswith(('RT - 024_','RT - 029_')) or obj.hide_render:continue
    normal_matrix=obj.matrix_world.to_3x3().inverted().transposed()
    edges=Counter()
    for face in obj.data.polygons:
        normal=normal_matrix@face.normal
        if normal.normalized().z<.70:continue
        pts=[obj.matrix_world@obj.data.vertices[i].co for i in face.vertices]
        area_world=sum((pts[i]-pts[0]).cross(pts[i+1]-pts[0]).length/2 for i in range(1,len(pts)-1))
        if area_world<1:continue
        plan=[(round(p.x,4),round(-p.y,4)) for p in pts]
        roof_faces.append(plan)
        for p,q in zip(plan,plan[1:]+plan[:1]):edges[tuple(sorted((p,q)))]+=1
    for edge,count in edges.items():
        if count==1:roof_edges.add(edge)

def polyline(points):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in points)
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-52 -32 104 64" fill="none">',
    '<title>SiteWise illustrative development in its selected parcel</title>',
    '<desc>Plan of the same source-derived lot and building placement as the isometric hero. Illustrative reconstruction; not a survey or verified utility map.</desc>',
    '<g stroke="#A6BCD4" stroke-width="0.15" opacity="0.52" stroke-linecap="round">']
for a,b in siting['context_segments']:
    svg.append(f'<path d="M{a[0]:.3f},{-a[1]:.3f}L{b[0]:.3f},{-b[1]:.3f}"/>')
svg.append('</g>')
lot=[(x,-y) for x,y in siting['lot']]
svg.append(f'<polygon points="{polyline(lot)}" fill="#EDF3F9" fill-opacity=".48" stroke="#698DB5" stroke-width=".24"/>')
svg.append('<g fill="#DAE5F0" fill-opacity=".60">')
for polygon in roof_faces:svg.append(f'<polygon points="{polyline(polygon)}"/>')
svg.append('</g><g stroke="#7796B9" stroke-width=".16" opacity=".90" stroke-linejoin="round">')
for a,b in sorted(roof_edges):svg.append(f'<path d="M{a[0]:.3f},{a[1]:.3f}L{b[0]:.3f},{b[1]:.3f}"/>')
svg.append('</g></svg>')
(WEB/'sitewise-hero-plan.svg').write_text('\n'.join(svg),encoding='utf-8')
(OUT/'sitewise-hero-plan.svg').write_text('\n'.join(svg),encoding='utf-8')
manifest=dict(stage='Static opening hero; animation deferred',source_scene='sitewise-siting-study.blend',
    assets=dict(isometric='/landing-assets/coordination/sitewise-hero-isometric.webp',plan='/landing-assets/coordination/sitewise-hero-plan.svg'),
    lot=siting['lot'],building_bounds=siting['building_bounds'],building_rotation_radians=siting['building_rotation_radians'],
    camera=dict(position=list(camera.location),target=list(target),ortho_scale=camera.data.ortho_scale),
    image_size=[1200,1320],ground='Level rich-blue ground; near #125BA7 family, lit scene color',
    source_transform_check='All building source transforms unchanged from registered siting scene',
    plan_roof_faces=len(roof_faces),plan_roof_edges=len(roof_edges),warm_glazing=warm_glazing,
    provenance=dict(building_title='Duplex houses at 22 ARNWOOD STREET MANUREWA',author='MyStudioNZ',license_from_metadata='CC-BY-4.0',
        source_url='https://sketchfab.com/3d-models/duplex-houses-at-22-arnwood-street-manurewa-ef88f585f3d045c89c849ddd64495ad5',
        modifications='Chalk/blue materials, selective interior warmth, art-direction lighting, illustrative source-derived parcel placement',
        cadastral='Perspective artwork rectified into an illustrative local parcel; no CRS/survey/utility verification'),
    structural_direction='No structural overlay in this hero; reinforced-concrete columns/slabs are the active future direction')
(OUT/'static-hero-manifest.json').write_text(json.dumps(manifest,indent=2))
(WEB/'sitewise-hero-credits.json').write_text(json.dumps(manifest['provenance'],indent=2))
scene['stage']=manifest['stage'];scene['illustration_status']=manifest['provenance']['cadastral']
scene['structural_direction']=manifest['structural_direction']
scene.render.filepath=str(OUT/'19-static-hero-isometric.png')
print('STATIC_HERO_PLAN_READY',len(roof_faces),len(roof_edges),'camera scale',camera.data.ortho_scale,flush=True)
if '--plan-only' not in sys.argv:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'sitewise-static-hero.blend'))
    bpy.ops.render.render(write_still=True)
    print('STATIC_HERO_RENDER_COMPLETE',flush=True)
