"""One illustrative source-derived parcel patch, rendered in plan and isometric."""
import bpy
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
DATA = ROOT.parents[1] / 'frontend/public/landing-assets/cadastral-lines.json'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-camera-review.blend'))
scene = bpy.context.scene

# A closed quadrilateral observed in the existing traced map. Reconstruction is
# illustrative: the artwork supplies neither real parcel dimensions nor a CRS.
source_lot = np.array([[.690882,.794547],[.641547,.768488],
                       [.646713,.753015],[.697647,.781388]])
target_lot = np.array([[12,-22],[12,22],[-12,22],[-12,-22]])
equations, values = [], []
for (x,y),(u,v) in zip(source_lot,target_lot):
    equations += [[x,y,1,0,0,0,-u*x,-u*y], [0,0,0,x,y,1,-v*x,-v*y]]
    values += [u,v]
H = np.append(np.linalg.solve(np.array(equations), np.array(values)),1).reshape((3,3))

def transform(point):
    p = H @ np.array([*point,1.0])
    if abs(p[2]) < .00001:
        return None
    return (float(p[0]/p[2]),float(p[1]/p[2]))

def material(name,color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color,1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color,1)
    node.inputs['Roughness'].default_value = .9
    return mat

boundary = material('Siting | quiet boundary',(.32,.39,.47))
selected = material('Siting | selected parcel blue',(.025,.10,.30))
lot_surface = material('Siting | selected lot surface',(.72,.77,.79))
map_collection = bpy.data.collections.new('SITING | shared plan and isometric geometry')
scene.collection.children.link(map_collection)

def line(name,points,mat=boundary,width=.025,z=-.03):
    data = bpy.data.curves.new(name,'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = width
    data.bevel_resolution = 1
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for node,p in zip(spline.points,points):
        node.co = (p[0],p[1],z,1)
    obj = bpy.data.objects.new(name,data)
    map_collection.objects.link(obj)
    data.materials.append(mat)
    return obj

segments=[]
for polyline in json.loads(DATA.read_text())['lines']:
    for a,b in zip(polyline,polyline[1:]):
        p,q=transform(a),transform(b)
        if p is None or q is None:
            continue
        if max(abs(n) for n in (*p,*q)) > 100:
            continue
        segments.append([p,q])
        line('Source-derived cadastral boundary',[p,q])

# Align the supplied building's dominant axes with the illustrative parcel.
rotation = Matrix.Rotation(math.atan2(.16053,.98703),4,'Z')
building_points=[]
for obj in list(scene.objects):
    if obj.type != 'MESH' or obj.hide_render or 'source_name' not in obj:
        continue
    obj.matrix_world = rotation @ obj.matrix_world
    if obj.get('system') in ['04 Walls','06 Roof']:
        building_points.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)
minimum = [min(p[i] for p in building_points) for i in range(2)]
maximum = [max(p[i] for p in building_points) for i in range(2)]
assert minimum[0]>-12 and maximum[0]<12 and minimum[1]>-22 and maximum[1]<22

# The ground remains level. No survey elevations or invented terrain are implied.
plane = bpy.data.objects['Studio ground | not survey geometry']
plane.location.z = -.12
mesh=bpy.data.meshes.new('Illustrative lot ground')
mesh.from_pydata([(x,y,-.07) for x,y in target_lot],[],[(0,1,2,3)])
mesh.update()
obj=bpy.data.objects.new('Selected illustrative parcel | not surveyed',mesh)
map_collection.objects.link(obj)
mesh.materials.append(lot_surface)
line('Selected lot boundary',[*target_lot,target_lot[0]],selected,.075)

def dimension(name,a,b):
    line(name,[a,b],selected,.03,z=.025)
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    n=(-dy/length*.32,dx/length*.32)
    for p in [a,b]:
        line(name+' | tick',[(p[0]-n[0],p[1]-n[1]),(p[0]+n[0],p[1]+n[1])],selected,.025,z=.025)

dimension('Illustrative boundary clearance | side',(-12,1),(minimum[0],1))
dimension('Illustrative boundary clearance | opposite side',(maximum[0],-2),(12,-2))
dimension('Illustrative boundary clearance | front',(0,-22),(0,minimum[1]))
dimension('Illustrative boundary clearance | rear',(0,maximum[1]),(0,22))

scene.render.resolution_x=1500
scene.render.resolution_y=1125
scene.cycles.samples=24
camera=bpy.data.objects['Camera | reverse study']
scene.camera=camera
camera.location=(-45,-60,52)
camera.rotation_euler=(Vector((0,0,2))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=76
scene.render.filepath=str(OUT/'09-cadastral-isometric.png')
bpy.ops.render.render(write_still=True)
plan_data=bpy.data.cameras.new('Siting | plan camera')
plan_camera=bpy.data.objects.new(plan_data.name,plan_data)
scene.collection.objects.link(plan_camera)
plan_camera.location=(0,0,100)
plan_camera.rotation_euler=(0,0,0)
plan_data.type='ORTHO'
plan_data.ortho_scale=76
scene.camera=plan_camera
scene.render.filepath=str(OUT/'10-cadastral-plan.png')
bpy.ops.render.render(write_still=True)
scene.camera=camera
scene['siting_provenance']='Illustrative parcel reconstructed from source artwork; no surveyed boundaries, CRS or planning compliance'
scene['utility_status']='Street and utility investigation layer planned; no infrastructure geometry asserted'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'sitewise-siting-study.blend'))
(OUT/'siting-study.json').write_text(json.dumps({
    'status':'Illustrative siting; not a surveyed or approved placement',
    'source_file':str(DATA), 'source_lot':source_lot.tolist(),
    'lot':target_lot.tolist(), 'homography':H.tolist(),
    'context_segments':segments, 'building_bounds':{'min':minimum,'max':maximum},
    'building_rotation_radians':math.atan2(.16053,.98703),
    'units':'Illustrative imported-model coordinate units; not verified metres',
    'limits':['Plan and isometric share exact geometry',
              'Boundary clearance ticks are relationships, not statutory setbacks',
              'Perspective rectification and dimensions are illustrative',
              'No utility network has been modelled or inferred']
},indent=2))
print('SITING_COMPLETE',len(segments),'source-derived map segments; building contained in lot',flush=True)
