"""Create a small wall-hosted illustrative Australian/NZ double-GPO library."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coordination'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'sitewise-lighting-checkpoint.blend'))
scene = bpy.context.scene
source_objects = list(scene.objects)
focus = Vector((-26,-23,0))-Vector((-24.757655,-11.917233,0))
U = Vector((.98703,-.16053,0)).normalized()
V = Vector((.16053,.98703,0)).normalized()
UP = Vector((0,0,1))


def world(u,v,z):
    return focus+U*u+V*v+UP*z


def uvz(point):
    delta=point-focus
    return Vector((delta.dot(U),delta.dot(V),point.z))


def bounds(obj):
    points=[uvz(obj.matrix_world@Vector(p)) for p in obj.bound_box]
    return (Vector(tuple(min(p[i] for p in points) for i in range(3))),
            Vector(tuple(max(p[i] for p in points) for i in range(3))))


walls=[]
obstacles=[]
for obj in source_objects:
    if obj.type!='MESH':
        continue
    low,high=bounds(obj)
    if high.x < -6 or low.x > 5 or high.y < -3 or low.y > 2.2:
        continue
    if obj.get('source_name','').startswith('SW -'):
        walls.append((obj,low,high,obj.matrix_world.inverted()))
    if not obj.hide_render:
        obstacles.append((obj,low,high))


def host_at(point,direction):
    candidates=[]
    for obj,lo,hi,inverse in walls:
        if point.z<lo.z or point.z>hi.z:
            continue
        hit,p,n,_=obj.ray_cast(inverse@point,(inverse.to_3x3()@direction).normalized())
        if not hit:
            continue
        p=obj.matrix_world@p
        distance=(p-point).length
        normal=(obj.matrix_world.to_3x3()@n).normalized()
        if distance<.65 and abs(normal.z)<.02 and abs(normal.dot(direction))>.98:
            candidates.append((distance,obj,p,inverse))
    if not candidates:
        raise RuntimeError(f'No wall found near {list(uvz(point))}')
    return min(candidates,key=lambda x:x[0])


def material(name,color):
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*color,1)
    mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=.68
    return mat


chalk=material('GPO | chalk white plate',(.81,.81,.76))
switch_mat=material('GPO | chalk rocker',(.70,.71,.68))
dark=material('GPO | dark socket recess',(.035,.042,.045))
collection=bpy.data.collections.new('CHECKPOINT 03 | General power outlets')
scene.collection.children.link(collection)


def box_mesh(name,center,size,angle=0):
    c=Vector(center)
    rotate=Matrix.Rotation(angle,3,'Z')
    verts=[c+rotate@Vector((x*size[0]/2,y*size[1]/2,z*size[2]/2))
           for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),
                         (1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    return mesh


# Local coordinates: X along plate, Y up plate, Z out from host wall.
templates=[('plate',box_mesh('GPO plate', (0,0,.0055),(.115,.073,.011)),chalk)]
for side,x in [('left',-.028),('right',.028)]:
    templates.append((f'{side} switch',box_mesh(f'GPO {side} switch',(x,.025,.012),(.014,.007,.003)),switch_mat))
    for pole,dx,dy,angle in [('active',-.008,.003,-math.pi/6),('neutral',.008,.003,math.pi/6),('earth',0,-.014,0)]:
        templates.append((f'{side} {pole} slot',box_mesh(f'GPO {side} {pole}',(x+dx,dy,.0115),(.0027,.010,.001),angle),dark))
for _,mesh,mat in templates:
    mesh.materials.append(mat)

# Each starting point is inside its named room; direction points toward the wall.
schedule=[
 ('G01','Ground entry',-4.25,-2.3,.90,'-V','General cleaning/entry point'),
 ('G02','Ground multipurpose',-4.25,1.6,.90,'+V','General workpoint'),
 ('G03','Ground multipurpose',-1.25,1.6,.90,'+V','General workpoint'),
 ('G04','Ground multipurpose',-2.3,-1.2,1.10,'-V','Flexible workpoint'),
 ('G05','Laundry',.65,.72,1.65,'+U','General utility point; dedicated laundry appliance point separate'),
 ('G06','Ground bedroom',1.45,-2.30,.90,'-V','Bedside left'),
 ('G07','Ground bedroom',3.70,-2.30,.90,'-V','Bedside right'),
 ('G08','Ground bathroom',3.65,1.04,1.62,'-V','General wet-room provision for consultant review'),
 ('L01','Living',-3.72,1.6,3.64,'+V','General workpoint clear of sofa'),
 ('L02','Living',-1.25,-1.2,3.64,'-V','Media/workpoint on solid stair-side wall'),
 ('L03','Living',-.58,1.6,3.64,'+V','General charging point'),
 ('L04','Dining',1.45,1.6,3.66,'+V','General dining provision'),
 ('L05','Kitchen worktop',4.25,.65,4.43,'+U','General worktop power between sink and hob'),
 ('L06','Kitchen worktop',4.25,1.73,4.43,'+U','General worktop power beside return'),
 ('L07','Living powder room',2.45,-2.30,4.38,'-V','General wet-room provision for consultant review'),
 ('U01','West bedroom',-4.77,1.60,6.40,'+V','Bedside left'),
 ('U02','West bedroom',-2.56,1.60,6.40,'+V','Bedside right'),
 ('U03','West bedroom',-2.8,-1.20,6.42,'-V','General desk/workpoint'),
 ('U04','East bedroom',1.84,-2.30,6.40,'-V','Bedside left'),
 ('U05','East bedroom',4.09,-2.30,6.40,'-V','Bedside right'),
 ('U06','East bedroom',4.02,.55,6.40,'+V','General desk/workpoint'),
 ('U07','West ensuite',-1.80,.12,7.14,'-U','General wet-room provision away from shower and basin'),
 ('U08','East ensuite',3.84,1.02,7.16,'-V','General wet-room provision for consultant review'),
 ('U09','Upper landing',.18,.50,6.38,'-U','General cleaning point'),
]
directions={'+U':U,'-U':-U,'+V':V,'-V':-V}
records=[]
rejected=[]
assemblies=[]
for item in schedule:
    suffix,room,u,v,z,side,purpose=item
    identity=f'GPO-{suffix}'
    direction=directions[side]
    _,host,surface,inverse=host_at(world(u,v,z),direction)
    normal=-direction
    right=UP.cross(normal).normalized()
    origin=surface+normal*.001
    orientation=Matrix(((right.x,UP.x,normal.x,origin.x),
                        (right.y,UP.y,normal.y,origin.y),
                        (right.z,UP.z,normal.z,origin.z),(0,0,0,1)))
    corner_checks=[]
    for x,y in [(-.0575,-.0365),(-.0575,.0365),(.0575,-.0365),(.0575,.0365),(0,0)]:
        expected=surface+right*x+UP*y
        ray=expected+normal*.10
        hit,point,_,_=host.ray_cast(inverse@ray,(inverse.to_3x3()@-normal).normalized())
        error=(host.matrix_world@point-expected).length if hit else None
        corner_checks.append(dict(local_xy=[x,y],host_hit=hit,error_m=error))
    if not all(c['host_hit'] and c['error_m']<.002 for c in corner_checks):
        rejected.append(dict(id=identity,reason='Plate crosses opening or nonplanar host',checks=corner_checks))
        continue
    # Broadphase plus triangle overlap catches furniture/window collisions.
    plate=templates[0][1]
    plate_points=[orientation@vertex.co for vertex in plate.vertices]
    local_points=[uvz(p) for p in plate_points]
    low=Vector(tuple(min(p[i] for p in local_points) for i in range(3)))
    high=Vector(tuple(max(p[i] for p in local_points) for i in range(3)))
    plate_tree=BVHTree.FromPolygons(plate_points,[p.vertices[:] for p in plate.polygons])
    clashes=[]
    for obstacle,slo,shi in obstacles:
        if obstacle==host or any(low[i]>shi[i] or high[i]<slo[i] for i in range(3)):
            continue
        tree=BVHTree.FromPolygons([obstacle.matrix_world@vert.co for vert in obstacle.data.vertices],
                                 [poly.vertices[:] for poly in obstacle.data.polygons])
        pairs=plate_tree.overlap(tree)
        if pairs:
            clashes.append(dict(object=obstacle.name,pairs=len(pairs)))
    if clashes:
        rejected.append(dict(id=identity,reason='Plate overlaps visible scene geometry',clashes=clashes))
        continue
    root=bpy.data.objects.new(f'{identity} | {room}',None)
    root.matrix_world=orientation
    root.empty_display_size=.035
    root.empty_display_type='PLAIN_AXES'
    collection.objects.link(root)
    parts=[]
    for label,mesh,_ in templates:
        obj=bpy.data.objects.new(f'{identity} | {label}',mesh)
        obj.parent=root
        collection.objects.link(obj)
        if label=='plate':
            bevel=obj.modifiers.new('Moulded plate edge','BEVEL')
            bevel.width=.0025
            bevel.segments=3
        obj['fixture_id']=identity
        obj['system']='Electrical general power'
        obj['room']=room
        obj['host_wall']=host['source_name']
        obj['provenance']='Authored illustrative Australian/NZ double GPO; no manufacturer specification'
        parts.append(obj.name)
    root['fixture_id']=identity
    root['host_wall']=host['source_name']
    root['room']=room
    assemblies.append(root)
    records.append(dict(id=identity,room=room,purpose=purpose,uvz=list(uvz(surface)),world_xyz=list(surface),
                        host_wall_source=host['source_name'],normal_world=list(normal),normal_uv=[normal.dot(U),normal.dot(V),normal.z],
                        root_object=root.name,objects=parts,wall_offset_m=.001,plate_dimensions_m=[.115,.073,.011],
                        plate_corner_checks=corner_checks,visible_geometry_overlaps=[],
                        status='Illustrative provision; circuit and load unassigned; electrical consultant placement review pending',
                        dedicated_appliance_power='Separate, not represented by this general-purpose outlet'))

output=dict(collection=collection.name,type='Australian/NZ double GPO',materials='Chalk-white plate with geometric dark socket slots',
            source_scene='sitewise-lighting-checkpoint.blend',count=len(records),outlets=records,rejected=rejected,
            scope='General-purpose power only. Illustrative positions, not a compliance or circuit design.',
            validation='All accepted outlets raycast to an actual source wall at center and four plate corners; visible geometry checked for triangle overlap.')
(OUT/'gpo-checkpoint.json').write_text(json.dumps(output,indent=2))
if rejected:
    print('GPO_REJECTED',json.dumps(rejected),flush=True)
    raise RuntimeError('Revise rejected outlet positions before delivering library')
for obj in source_objects:
    bpy.data.objects.remove(obj,do_unlink=True)
for col in list(bpy.data.collections):
    if col!=collection:
        bpy.data.collections.remove(col)
bpy.ops.outliner.orphans_purge(do_recursive=True)
scene['gpo_scope']=output['scope']
scene.unit_settings.system='METRIC'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'sitewise-gpo-library.blend'))

# One close-up proof only, in an unsaved audit arrangement.
selected=assemblies[0]
for assembly in assemblies[1:]:
    for obj in assembly.children:
        obj.hide_render=True
selected.matrix_world=Matrix.Identity(4)
wall_mesh=box_mesh('GPO proof wall',(0,0,-.014),(.27,.17,.026))
wall_obj=bpy.data.objects.new('GPO proof wall',wall_mesh)
scene.collection.objects.link(wall_obj)
wall_mesh.materials.append(material('GPO proof wall chalk',(.61,.62,.59)))
camera_data=bpy.data.cameras.new('GPO detail camera')
camera=bpy.data.objects.new('GPO detail camera',camera_data)
scene.collection.objects.link(camera)
camera.location=Vector((0,0,.25))
camera.rotation_euler=(0,0,0)
camera_data.type='ORTHO'
camera_data.ortho_scale=.17
scene.camera=camera
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1280
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO'
scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_shadows=True
scene.render.filepath=str(OUT/'17-gpo-detail.png')
scene.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
print('GPO_CHECKPOINT_COMPLETE',len(records),flush=True)
