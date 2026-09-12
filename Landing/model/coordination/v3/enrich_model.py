"""Add illustrative shading, ducted AC, continuous ground cover and a garage vehicle.

Keep the registered master intact; export from a separate editable detail checkpoint.
"""
import bpy
import math
import sys
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from export_web import export
from build_integrated import material

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'sitewise-integrated-v3.blend'))
scene = bpy.context.scene
chalk = material('Detail | Chalk', '#F9F7F3')

def bounds(obj):
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    return Vector([min(p[i] for p in points) for i in range(3)]), Vector([max(p[i] for p in points) for i in range(3)])

def tag(obj, name, system, motion=''):
    obj.name = 'Detail | ' + name
    obj['sw_system'] = system
    obj['sw_label'] = name
    if motion:
        obj['sw_motion'] = motion
    obj.data.materials.clear()
    obj.data.materials.append(chalk)
    return obj

def box(name, position, size, system='mechanical', motion=''):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = tag(bpy.context.object, name, system, motion)
    obj.scale = size
    return obj

def tube(name, points, radius=.14):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    return tag(obj, name, 'mechanical')

# Derive hoods from the existing window extents, including their opening direction.
windows = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render
           and o.name.startswith('WD -') and o.get('sw_glass')]
for i, obj in enumerate(windows):
    lo, hi = bounds(obj)
    centre = (lo+hi)/2
    if hi.x-lo.x < .3:
        direction = 1 if centre.x > 0 else -1
        box(f'Window hood {i+1}', (centre.x+direction*.27, centre.y, hi.z+.15),
            (.65, hi.y-lo.y+.32, .085), 'architecture')
    elif hi.y-lo.y < .3:
        direction = -1 if centre.y < -9 or 0 < centre.y < 3 else 1
        box(f'Window hood {i+1}', (centre.x, centre.y+direction*.27, hi.z+.15),
            (hi.x-lo.x+.32, .65, .085), 'architecture')

# Ground cover sits below existing paths, patios and planting beds and bridges panel seams.
box('Continuous garden ground cover', (9.4, 2.05, -.025), (5.0,39.5,.15), 'landscape')
box('Front garden infill', (3.15,-18.1,-.025), (17.5,7.8,.15), 'landscape')
box('Rear garden infill', (3.1,18.4,-.025), (17.4,7.0,.15), 'landscape')
box('Service corridor permeable ground cover', (6.4,2.05,-.035), (.82,39.5,.13), 'landscape')
box('East building setback ground cover', (6.1,.45,-.035), (1.65,29.5,.13), 'landscape')
box('Garage approach ground cover', (-5.5,.45,-.035), (1.3,29.5,.13), 'landscape')
box('Driveway boundary ground cover', (-11.8,0,-.035), (.4,44,.13), 'landscape')

# Supply air remains separate from the existing bathroom/kitchen extraction system.
box('Roof void air handling unit', (.3,-11.4,8.8), (1.3,.75,.48))
box('Supply plenum', (1.2,-11.4,8.8), (.5,.64,.4))
box('Return air filter box', (-.55,-11.4,8.8), (.36,.7,.48))
box('Condensate tray', (.3,-11.4,8.53), (1.5,.9,.05))
room_ports = [(-2.6,-12.65,8.32),(3.3,-12.5,8.32),(2.6,-11.8,5.58),(-1.5,-12.1,5.58)]

def rounded_route(waypoints):
    """Round each change of direction before sampling the flexible duct ribs."""
    route = [Vector(p) for p in waypoints]
    points = [route[0]]
    def line(end):
        start = points[-1]
        count = max(1, math.ceil((end-start).length/.09))
        points.extend(start.lerp(end,j/count) for j in range(1,count+1))
    for a,b,c in zip(route,route[1:],route[2:]):
        radius = min(.3,(b-a).length/3,(c-b).length/3)
        entry=b+(a-b).normalized()*radius
        exit_point=b+(c-b).normalized()*radius
        line(entry)
        for j in range(1,9):
            t=j/8
            points.append((1-t)**2*entry+2*(1-t)*t*b+t*t*exit_point)
    line(route[-1])
    return points

for i, end in enumerate(room_ports):
    start = Vector((1.35,-11.4,8.8))
    target = Vector(end)
    points = []
    if i < 2:
        for j in range(33):
            t=j/32
            p=start.lerp(target,t)
            p.z += .22*math.sin(math.pi*t)
            points.append(p)
    else:
        # Paired supply drops stay separate from the wet-service stack at X=4.4.
        riser_x = 3.7-(i-2)*.48
        points = rounded_route([start,(riser_x,-9.85,8.8),
            (riser_x,-9.85,5.79),(end[0],end[1],5.79),target])
    tube(f'Flexible supply duct room {i+1}', points)
    # Close-pitched wire ribs make flexible duct readable in the discipline view.
    for j in range(2,len(points)-1,2):
        tangent=(points[j+1]-points[j-1]).normalized()
        reference = Vector((0,0,1)) if abs(tangent.z)<.95 else Vector((1,0,0))
        u=tangent.cross(reference).normalized()
        v=tangent.cross(u)
        ring=[points[j]+.148*(u*math.cos(k*math.tau/12)+v*math.sin(k*math.tau/12)) for k in range(13)]
        tube(f'Duct {i+1} reinforcing rib {j}', ring, .012)
    box(f'Room {i+1} supply diffuser', end, (.42,.42,.065))
    for j in range(4):
        box(f'Room {i+1} diffuser vane {j}', (end[0]-.135+j*.09,end[1],end[2]-.045), (.025,.34,.02))
tube('Return air flexible connection', [(-.72,-11.4,8.8),(-1,-11.4,8.65),(-1,-11.4,8.32)], .20)
box('Ceiling return air grille', (-1,-11.4,8.30), (.62,.52,.065))

# Outdoor condenser is outside the east wall, clear of the garage route.
box('Outdoor condenser plinth', (5.83,-12,.12), (.72,1.24,.14))
for y in (-12.38,-11.62):
    box('Condenser vibration isolation foot', (5.83,y,.235), (.45,.1,.09))
box('Outdoor condenser cabinet', (5.83,-12,.7), (.46,1.05,.85))
for radius in (.10,.18,.26,.34):
    tube('Condenser circular fan guard', [(6.075,-12+radius*math.cos(k*math.tau/48),
        .72+radius*math.sin(k*math.tau/48)) for k in range(49)], .014)
for k in range(8):
    angle=k*math.tau/8
    tube('Condenser radial fan guard', [(6.09,-12,.72),
        (6.09,-12+.34*math.cos(angle),.72+.34*math.sin(angle))], .012)
for k in range(5):
    angle=k*math.tau/5
    blade=box('Condenser fan blade', (6.07,-12+.16*math.cos(angle),.72+.16*math.sin(angle)), (.025,.12,.25))
    blade.rotation_euler.x=angle
for j in range(9):
    box('Condenser intake louvre', (5.82,-11.465,.36+j*.08), (.36,.025,.025))
for i,radius in enumerate((.026,.04)):
    y=-11.64+i*.13
    tube('Insulated refrigerant '+('liquid' if i==0 else 'suction')+' line',
        rounded_route([(5.65,y,.5),(5.45,y,.5),(5.45,y,8.8),(.3,y,8.8),(.3,-11.4,8.8)]), radius)
box('Condenser service isolator', (5.43,-11.15,1.3), (.14,.18,.24), 'electrical')

assert sum(p[2]>8 for p in room_ports)==2
assert sum(5.5<p[2]<5.7 for p in room_ports)==2
assert all((a-b).length>0 for a,b in zip(points,points[1:]))

# Replace one measured garage panel with independently addressable roller slats.
door = scene.objects['DOO - 018_Paint - Titanium White_0.001']
lo, hi = bounds(door)
door.hide_render = True
for o in list(scene.objects):
    if o.name == 'DOO - 018_Metal - Iron_0.001':
        o.hide_render = True
for i in range(21):
    box(f'Garage roller slat {i}', (-4.81,-10.93335,.55+i*.1), (.065,2.8,.096), 'architecture', f'door:{i}')
box('Garage roller hood', (-4.58,-10.93335,2.85), (.5,3.04,.43), 'architecture')

# Use the supplied vehicle, omitting the two remote orphan meshes from its source.
before = set(scene.objects)
bpy.ops.import_scene.gltf(filepath=str(HERE.parents[1]/'car.glb'))
imported = list(set(scene.objects)-before)
rotation = Matrix.Rotation(-math.pi/2,4,'Z')
source_centre = Vector((-.00321436,.25293136,.50074452))
vehicle_dark = material('Detail | Vehicle dark trim', '#35434C')
for obj in imported:
    if obj.type != 'MESH':
        continue
    if obj.name in ('Object_291','Object_292'):
        obj.hide_render = True
        continue
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = Matrix.Translation(Vector((-2.12,-10.93335,.50))) @ rotation @ Matrix.Scale(.5,4) @ Matrix.Translation(-source_centre) @ world
    source_name = obj.name
    trim = any(any(word in mat.name.lower() for word in ('borracha','vidro','glass','pneu')) for mat in obj.data.materials if mat)
    tag(obj, 'Vehicle '+source_name, 'civil', 'car')
    if trim:
        obj.data.materials.clear()
        obj.data.materials.append(vehicle_dark)
    obj['source_asset'] = 'PROJECT CAR90 | Land Rover Defender - Edition Grasmere Green | CC-BY-4.0'
    if len(obj.data.polygons)>800:
        modifier=obj.modifiers.new('Web simplification','DECIMATE')
        modifier.ratio=.16

bpy.context.view_layer.update()
from structure_revision import build as revise_structure
revise_structure(scene)
from condenser_placement import build as place_condenser
place_condenser(scene)
from cable_tray import build as add_cable_tray
add_cable_tray(scene)
from civil_stormwater import build as revise_stormwater
revise_stormwater(scene)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-detail-v4.blend'))
export(scene)
print('DETAIL_EXPORT_COMPLETE', flush=True)
