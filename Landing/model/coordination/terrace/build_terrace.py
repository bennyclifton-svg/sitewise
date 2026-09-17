"""Build a separate, authored terrace concept with inspectable discipline geometry.

Blender background: --python build_terrace.py -- --count 7 --render
Coordinates are metres: X along street, Y toward gardens, Z up. All structural
sizes and service routes are schematic allowances, not engineering design.
"""
import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
args = argparse.ArgumentParser()
args.add_argument('--count', type=int, choices=(6, 7), default=7)
args.add_argument('--render', action='store_true')
args.add_argument('--export', action='store_true')
args.add_argument('--views', default='street,detail,front,rear,coordination')
opt = args.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
N = opt.count
LENGTH = 49.0
W = LENGTH / N
DEPTH = 12.0
LEVELS = (.35, 3.45, 6.55)
OUT = HERE / f'option-{N}'
OUT.mkdir(exist_ok=True)
random.seed(24)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene['sw_status'] = 'Architectural coordination concept; engineering and compliance unresolved'
scene['sw_source'] = 'New street-facing site authorised by user; existing v23 retained separately'
groups = {}
for s in ('architecture', 'structure', 'electrical', 'mechanical', 'hydraulic', 'interiors', 'civil', 'landscape'):
    groups[s] = bpy.data.collections.new(s.title())
    scene.collection.children.link(groups[s])
owner = 0
records = []
routes = []


def material(name, colour, rough=.7, metal=0):
    m = bpy.data.materials.new(name)
    c = tuple(int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
    c = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c)
    m.diffuse_color = (*c, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*c, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    return m


cream = material('Warm lime render', 'E4DED0')
white = material('Plasterboard ivory', 'EEEAE1')
concrete = material('Concrete', 'ACAAA1')
dark = material('Bronze charcoal metal', '343A38', .36, .65)
timber = material('Oak joinery and framing', 'AD865C')
glass = material('Glazing', '819B9B', .16, .15)
glass.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value = .65
fabric = material('Linen curtains', 'D9D0BA')
stone = material('Limestone paving', 'BEB9AA')
asphalt = material('Road asphalt', '575A58')
soil = material('Planting mulch', '4D493B')
grass = material('Garden groundcover', '6D8055')
leaves = [material(f'Foliage {i}', c) for i, c in enumerate(('526445', '708052', '879164'))]
copper = material('Hot water copper', 'B76B46', .35, .6)
cold = material('Cold water blue', '3D8FA1')
waste = material('Sanitary drainage', '967E65')
storm = material('Stormwater green', '4D8276')
power = material('Electrical conduit amber', 'DDA144')
duct = material('Galvanised ductwork', '9BA9AA', .4, .6)
steel = material('Structural steel', '5C7175', .4, .6)
tile = material('Bathroom stone', 'B5B4A6')
bricks = []
for i, c in enumerate(('BC9376', 'C4A184', 'AE8167')):
    m = material(f'Warm brick {i + 1}', c)
    nodes, links = m.node_tree.nodes, m.node_tree.links
    tex = nodes.new('ShaderNodeTexBrick')
    tex.inputs['Color1'].default_value = m.diffuse_color
    tex.inputs['Color2'].default_value = tuple(v * .8 for v in m.diffuse_color[:3]) + (1,)
    tex.inputs['Mortar'].default_value = (.43, .39, .32, 1)
    tex.inputs['Scale'].default_value = 1
    tex.inputs['Mortar Size'].default_value = .006
    tex.inputs['Brick Width'].default_value = .23
    tex.inputs['Row Height'].default_value = .076
    coord = nodes.new('ShaderNodeTexCoord')
    sep = nodes.new('ShaderNodeSeparateXYZ')
    comb = nodes.new('ShaderNodeCombineXYZ')
    # Front/rear walls use real metre X/Z coordinates, not generated bounding-box UVs.
    links.new(coord.outputs['Object'], sep.inputs[0])
    geom=nodes.new('ShaderNodeNewGeometry')
    normal=nodes.new('ShaderNodeSeparateXYZ')
    links.new(geom.outputs['Normal'],normal.inputs[0])
    absolute=nodes.new('ShaderNodeMath');absolute.operation='ABSOLUTE'
    links.new(normal.outputs['X'],absolute.inputs[0])
    mix=nodes.new('ShaderNodeMixRGB')
    links.new(absolute.outputs[0],mix.inputs[0])
    links.new(sep.outputs['X'],mix.inputs[1])
    links.new(sep.outputs['Y'],mix.inputs[2])
    links.new(mix.outputs[0],comb.inputs['X'])
    links.new(sep.outputs['Z'], comb.inputs['Y'])
    links.new(comb.outputs[0], tex.inputs['Vector'])
    links.new(tex.outputs['Color'], nodes.get('Principled BSDF').inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .2
    bump.inputs['Distance'].default_value = .008
    links.new(tex.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs[0], nodes.get('Principled BSDF').inputs['Normal'])
    bricks.append(m)


def add(name, data, system, mat):
    obj = bpy.data.objects.new(f'TH{owner:02} | {name}', data)
    groups[system].objects.link(obj)
    if mat:
        data.materials.append(mat)
    obj['sw_system'] = system
    obj['sw_dwelling'] = owner
    obj['sw_status'] = 'Concept geometry; sizing provisional'
    return obj


def mesh(name, verts, faces, system, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    return add(name, data, system, mat)


def box(name, low, high, system='architecture', mat=cream):
    assert all(high[i] > low[i] for i in range(3)), (name, low, high)
    x, y, z = low
    a, b, c = high
    # Geometry authored in world coordinates so brick courses stay aligned.
    return mesh(name, [(x,y,z),(a,y,z),(a,b,z),(x,b,z),(x,y,c),(a,y,c),(a,b,c),(x,b,c)],
                [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)], system, mat)


def pipe(name, pts, radius, system, mat):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 1
    spline = data.splines.new('POLY')
    spline.points.add(len(pts) - 1)
    for p, co in zip(spline.points, pts):
        p.co = (*co, 1)
    obj = add(name, data, system, mat)
    routes.append(dict(name=obj.name, system=system, points=pts, radius=radius))
    return obj


def beam(name, a, b, width=.12, depth=.22, mat=steel):
    vec = Vector(b) - Vector(a)
    obj = box(name, (-width/2, -depth/2, -vec.length/2), (width/2, depth/2, vec.length/2), 'structure', mat)
    obj.location = (Vector(a) + Vector(b)) / 2
    obj.rotation_euler = vec.to_track_quat('Z', 'Y').to_euler()
    return obj


def wall_openings(name, x0, x1, y, z0, z1, openings, mat, thickness=.25, system='architecture'):
    cuts = sorted({x0, x1, *[v for o in openings for v in o[:2]]})
    for a, b in zip(cuts, cuts[1:]):
        active = sorted((o for o in openings if o[0] <= a and o[1] >= b), key=lambda o:o[2])
        bottom = z0
        for _, _, sill, head in active:
            if sill > bottom:
                box(name, (a,y,bottom), (b,y+thickness,sill), system, mat)
            bottom = max(bottom, head)
        if bottom < z1:
            box(name, (a,y,bottom), (b,y+thickness,z1), system, mat)


def window(name, x0, x1, y, sill, head, curtain=True):
    box(name+' glass', (x0+.055,y,sill+.06),(x1-.055,y+.025,head-.06), mat=glass)
    for x in (x0, x1-.045, (x0+x1)/2-.02):
        box(name+' stile',(x,y-.025,sill),(x+.045,y+.07,head),mat=dark)
    for z in (sill,head-.045):
        box(name+' rail',(x0,y-.025,z),(x1,y+.07,z+.045),mat=dark)
    if curtain:
        cy = y + (.17 if y < 6 else -.17)
        pipe(name+' recessed curtain track',[(x0,cy,head+.035),(x1,cy,head+.035)],.015,'interiors',dark)
        for left in (x0+.025,x1-.48):
            verts=[]
            for i in range(25):
                xx=left+i*.019
                yy=cy+.045*math.sin(i*math.pi/2)
                verts.extend([(xx,yy,sill+.04),(xx,yy,head-.02)])
            mesh(name+' pleated linen',verts,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(24)],'interiors',fabric)


def partition(name, x0, x1, y, base, door_x=None):
    opens=[] if door_x is None else [(door_x,door_x+.85,base,base+2.1)]
    wall_openings(name+' plasterboard',x0,x1,y,base,base+2.72,opens,white,.12,'interiors')
    for x in [x0+i*.45 for i in range(int((x1-x0)/.45)+1)]:
        if door_x is None or not door_x-.05 < x < door_x+.9:
            box(name+' timber stud',(x,y+.04,base),(x+.038,y+.078,base+2.72),'structure',timber)
    for z in (base,base+2.68):
        box(name+' timber plate',(x0,y+.04,z),(x1,y+.078,z+.038),'structure',timber)
    if door_x is not None:
        box(name+' door leaf open',(door_x,y,base+.025),(door_x+.04,y+.83,base+2.08),'interiors',timber)


def tree(x,y,height=3):
    pipe('Tree trunk',[(x,y,.1),(x,y,height*.72)],.07,'landscape',timber)
    for k in range(5):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=height*.27,
            location=(x+random.uniform(-.4,.4),y+random.uniform(-.4,.4),height*.68+random.uniform(-.2,.5)))
        obj=bpy.context.object
        for c in list(obj.users_collection):c.objects.unlink(obj)
        groups['landscape'].objects.link(obj)
        obj.name=f'TH{owner:02} | Tree crown'
        obj.data.materials.append(leaves[k%3])
        obj['sw_system']='landscape';obj['sw_dwelling']=owner


def stairs(x, y, base):
    # Two 900 mm flights, 18 equal risers and an intermediate landing.
    rise=3.1/18
    for i in range(9):
        box('Stair ascending tread',(x,y+i*.26,base+i*rise),(x+.9,y+(i+1)*.26,base+(i+1)*rise),'structure',timber)
        box('Stair return tread',(x+1.05,y+(8-i)*.26,base+(9+i)*rise),
            (x+1.95,y+(9-i)*.26,base+(10+i)*rise),'structure',timber)
    box('Stair intermediate landing',(x,y+2.34,base+9*rise-.14),(x+1.95,y+3.29,base+9*rise),'structure',timber)
    pipe('Stair handrail',[(x+.92,y,base+1),(x+.92,y+2.34,base+2.55),
         (x+1.02,y+2.34,base+2.55),(x+1.02,y,base+4.1)],.022,'interiors',dark)


def bathroom(x,y,z,label):
    box(label+' tile floor',(x,y,z),(x+1.8,y+2,z+.025),'interiors',tile)
    box(label+' vanity',(x,y+.2,z+.15),(x+.5,y+1.25,z+.85),'interiors',timber)
    box(label+' basin',(x-.02,y+.2,z+.85),(x+.53,y+.75,z+.92),'hydraulic',white)
    box(label+' mirror',(x+.03,y+.24,z+1.1),(x+.055,y+1.15,z+2),'interiors',glass)
    box(label+' WC',(x+1.05,y+.2,z+.05),(x+1.48,y+.92,z+.43),'hydraulic',white)
    box(label+' cistern',(x+1.03,y+.17,z+.42),(x+1.5,y+.36,z+.85),'hydraulic',white)
    box(label+' shower tray',(x+.85,y+1.05,z+.02),(x+1.75,y+1.95,z+.07),'hydraulic',white)
    box(label+' shower screen',(x+.83,y+1.04,z+.08),(x+.85,y+1.98,z+2.05),'interiors',glass)
    pipe(label+' shower',[(x+1.5,y+1.96,z+1),(x+1.5,y+1.96,z+2.1),(x+1.5,y+1.72,z+2.1)],.018,'hydraulic',dark)


def fitout(x,w):
    # Garden room / laundry at ground, living floor above, two roof bedrooms.
    for z in LEVELS:
        bathroom(x+w-2.25,7.05,z,'Wet core')
        partition('Wet core south',x+w-2.4,x+w-.25,6.88,z,x+w-2.35)
        partition('Wet core north',x+w-2.4,x+w-.25,9.12,z)
        box('Wet core west lining',(x+w-2.52,7,z),(x+w-2.4,9.1,z+2.72),'interiors',white)
    partition('Garage rear fire separation',x+.25,x+w-2.5,6.5,.35,x+2.6)
    box('Garage side separation',(x+3.7,.8,.35),(x+3.85,6.5,3.3),'interiors',white)
    for j in range(3):
        box('Laundry cabinet',(x+.3+j*.65,6.75,.35),(x+.93+j*.65,7.4,1.25),'interiors',white)
    box('Washing machine',(x+.32,6.76,.4),(x+.9,7.35,1.2),'electrical',white)
    for z in (.35,3.45):
        sy=9.8 if z<1 else 2.4
        box('Sofa base',(x+.4,sy,z+.12),(x+2.7,sy+.85,z+.48),'interiors',fabric)
        box('Sofa back',(x+.4,sy+.66,z+.45),(x+2.7,sy+.85,z+.9),'interiors',fabric)
        box('Coffee table',(x+1,sy-1,z+.3),(x+2.2,sy-.35,z+.42),'interiors',timber)
    z=3.45
    for j in range(5):
        xx=x+.3+j*.62
        box('Kitchen base cabinet',(xx,10.8,z),(xx+.6,11.48,z+.86),'interiors',timber)
        box('Kitchen drawer face',(xx,10.77,z+.55),(xx+.59,10.8,z+.8),'interiors',timber)
    box('Kitchen stone bench',(x+.28,10.77,z+.86),(x+3.42,11.5,z+.9),'interiors',stone)
    box('Refrigerator',(x+3.45,10.78,z),(x+4.15,11.5,z+2.1),'electrical',white)
    box('Oven',(x+2.15,10.72,z+.12),(x+2.72,11.4,z+.7),'electrical',dark)
    box('Induction hob',(x+2.08,10.86,z+.91),(x+2.78,11.4,z+.93),'electrical',dark)
    box('Kitchen sink',(x+.6,10.88,z+.905),(x+1.22,11.35,z+.92),'hydraulic',dark)
    pipe('Kitchen mixer',[(x+.92,11.42,z+.9),(x+.92,11.42,z+1.23),(x+.92,11.2,z+1.23)],.015,'hydraulic',dark)
    box('Rangehood',(x+2.1,10.94,z+1.6),(x+2.8,11.5,z+1.77),'mechanical',dark)
    box('Dining top',(x+1.1,7.6,z+.73),(x+2.9,8.5,z+.8),'interiors',timber)
    for xx in (x+1.2,x+2.6):
        for yy in (7.02,8.65):
            box('Dining chair',(xx,yy,z+.4),(xx+.42,yy+.43,z+.47),'interiors',fabric)
            box('Chair back',(xx,yy+.39,z+.43),(xx+.42,yy+.44,z+.95),'interiors',timber)
    for yy in (2.35,9.3):
        box('Roof bedroom bed',(x+.7,yy,6.65),(x+2.4,yy+2,7.07),'interiors',fabric)
        box('Bed headboard',(x+.68,yy+1.94,6.6),(x+2.42,yy+2.04,7.65),'interiors',timber)
        for xx in (x+.8,x+1.6):
            box('Pillow',(xx,yy+1.4,7.07),(xx+.64,yy+1.84,7.18),'interiors',white)
    partition('Upper front bedroom',x+.25,x+w-2.55,5.35,6.55,x+2.7)
    partition('Upper rear bedroom',x+.25,x+w-2.55,9.02,6.55,x+2.7)
    for yy in (4.7,9.3):
        box('Bedroom wardrobe',(x+.3,yy,6.55),(x+1.9,yy+.55,8.65),'interiors',timber)


def services(x,w):
    rx=x+w-2.25
    # Wet riser and duct riser remain beside (not inside) the stair opening.
    box('Service riser enclosure',(rx-.16,6.85,.35),(rx+.34,7.03,9.35),'interiors',white)
    for dx,rad,mat,name in ((0,.018,cold,'Cold riser'),(.09,.014,copper,'Hot riser'),(.23,.055,waste,'Soil and vent stack')):
        pipe(name,[(rx+dx,7.12,-.85 if name=='Soil and vent stack' else .5),
             (rx+dx,7.12,9.6 if name=='Soil and vent stack' else 7.1)],rad,'hydraulic',mat)
    pipe('Sanitary lateral',[(rx+.23,7.12,-.85),(rx+.23,-5.8,-1.15)],.055,'hydraulic',waste)
    pipe('Water service',[(x+4.3,-5.1,-.65),(x+4.3,-3.8,-.65),(rx,7.12,-.65),(rx,7.12,.5)],.018,'hydraulic',cold)
    box('Water meter box',(x+4.17,-3.86,.15),(x+4.47,-3.56,.5),'hydraulic',dark)
    for z in LEVELS:
        for dx,mat,name in ((0,cold,'Cold branch'),(.09,copper,'Hot branch')):
            pipe(name,[(rx+dx,7.12,z+.15),(rx+dx,8.9,z+.15),(x+w-.65,8.9,z+.15)],.012,'hydraulic',mat)
        for yy in (7.6,8.65):
            pipe('Fixture waste branch',[(x+w-.85,yy,z+.05),(rx+.23,yy,z-.13),(rx+.23,7.12,z-.13)],.025,'hydraulic',waste)
        box('Bathroom extract grille',(rx+.7,8,z+2.58),(rx+.95,8.25,z+2.62),'mechanical',white)
        pipe('Bathroom extract duct',[(rx+.83,8.13,z+2.67),(rx+.65,7.42,z+2.67),(rx+.65,7.42,9.65)],.065,'mechanical',duct)
    pipe('Sink waste',[(x+.92,11.15,4.3),(x+.92,11.15,3.25),(rx+.23,11.15,3.25),(rx+.23,7.12,3.25)],.025,'hydraulic',waste)
    for dx,mat in ((0,cold),(.07,copper)):
        pipe('Kitchen supply',[(rx+dx,7.12,3.65),(rx+dx,11.2,3.65),(x+.95+dx,11.2,3.65),(x+.95+dx,11.2,4.34)],.012,'hydraulic',mat)
    box('Heat pump water heater',(x+w-1.05,12.4,.1),(x+w-.35,13.05,1.8),'hydraulic',white)
    pipe('Water heater connection',[(rx,7.12,.65),(rx,12.7,.65),(x+w-.8,12.7,.65)],.018,'hydraulic',cold)
    pipe('Hot water return to riser',[(x+w-.65,12.7,1.5),(rx+.09,12.7,1.5),(rx+.09,7.12,1.5)],.014,'hydraulic',copper)
    box('AC outdoor condenser',(x+w-2.05,12.4,.2),(x+w-1.2,12.8,1.1),'mechanical',white)
    for j in range(10):
        box('Condenser grille',(x+w-2.01,12.82,.28+j*.075),(x+w-1.24,12.835,.31+j*.075),'mechanical',dark)
    for z in LEVELS:
        box('Ducted AC indoor unit',(x+2.75,6.75,z+2.55),(x+3.75,7.4,z+2.85),'mechanical',duct)
        pipe('AC refrigerant pair',[(x+w-1.6,12.6,.7),(rx+.45,12.6,.7),(rx+.45,7.4,.7),
             (rx+.45,7.4,z+2.7),(x+3.75,7.1,z+2.7)],.024,'mechanical',copper)
        pipe('AC condensate',[(x+3.2,7.2,z+2.55),(rx+.32,7.2,z+2.5),(rx+.32,7.2,.15),(rx+.32,12.3,.15)],.016,'hydraulic',cold)
        for yy in (2.9,10):
            pipe('Supply air trunk',[(x+3.15,7.1,z+2.72),(x+3.15,yy,z+2.72),(x+2.6,yy,z+2.72),(x+2.6,yy,z+2.6)],.06,'mechanical',duct)
            box('Linear AC supply slot',(x+1.9,yy,z+2.58),(x+2.7,yy+.08,z+2.62),'mechanical',dark)
        box('AC return grille',(x+2.85,6.65,z+2.5),(x+3.5,6.7,z+2.7),'mechanical',white)
    pipe('Dedicated kitchen exhaust',[(x+2.45,11.2,5.18),(x+2.45,11.2,5.95),(x+2.45,12.2,5.95)],.075,'mechanical',duct)
    bx=x+3.94
    box('Distribution board',(bx,.95,1.1),(bx+.15,1.45,1.75),'electrical',white)
    box('Meter cabinet',(x+w-.55,.02,.65),(x+w-.16,.24,1.55),'electrical',dark)
    pipe('Underground electricity service',[(x+w-.4,-4.65,-.45),(x+w-.4,.3,-.45),(bx,.3,1.4),(bx,1.2,1.4)],.032,'electrical',power)
    pipe('Electrical riser',[(bx,1.2,1.4),(bx,6.62,1.4),(bx,6.62,9.3)],.027,'electrical',power)
    for level,z in enumerate(LEVELS):
        for j,(xx,yy) in enumerate(((1.3,2.7),(3,4.8),(1.3,8),(2.4,10.3),(w-1.2,8.1))):
            box('LED downlight',(x+xx-.06,yy-.06,z+2.58),(x+xx+.06,yy+.06,z+2.62),'electrical',white)
            pipe(f'L{level} lighting circuit {j}',[(bx,6.62,z+2.8),(x+xx,6.62,z+2.8),(x+xx,yy,z+2.8),(x+xx,yy,z+2.6)],.009,'electrical',power)
        for yy in (2.8,8.3,10.4):
            box('Double socket',(x+.255,yy,z+.25),(x+.285,yy+.12,z+.33),'electrical',white)
            pipe(f'L{level} power radial',[(bx,6.62,z+2.83),(x+.32,6.62,z+2.83),(x+.32,yy,z+2.83),(x+.32,yy,z+.3)],.012,'electrical',power)
        box('Switch plate',(x+w-2.63,6.7,z+1.05),(x+w-2.59,6.78,z+1.17),'electrical',white)
        box('Smoke alarm',(x+3.65,6.5,z+2.68),(x+3.8,6.65,z+2.72),'electrical',white)
    for name,xx,yy,zz in (('Oven',2.4,11.3,3.9),('AC',w-1.6,12.6,.7),('Water heater',w-.6,12.6,.7),('Washer',.6,7.1,.9)):
        pipe(name+' dedicated circuit',[(bx,6.62,2.95),(x+xx,6.62,2.95),(x+xx,yy,2.95),(x+xx,yy,zz)],.012,'electrical',power)


def dwelling(i):
    global owner
    owner=i+1
    x=i*W
    w=W
    brick=bricks[(i//2)%3]
    sx=x+w-2.25
    # Footings below side bearing walls and a cross footing; service openings reserved.
    bearing_x=(x+.12,x+w-.12) if i==N-1 else (x+.12,)
    for xx in bearing_x:
        box('Strip footing',(xx-.38,0,-.85),(xx+.38,12,-.4),'structure',concrete)
        box('Masonry foundation stem',(xx-.14,0,-.4),(xx+.14,12,.25),'structure',concrete)
    box('Ground bearing slab',(x+.25,.25,.15),(x+w-.25,11.75,.35),'structure',concrete)
    for z in LEVELS[1:]:
        # Slabs built around the actual U-stair opening and a wet service sleeve.
        box('Floor slab main',(x+.25,.25,z-.22),(sx-.1,11.75,z),'structure',concrete)
        box('Floor slab stair front',(sx-.1,.25,z-.22),(x+w-.25,3,z),'structure',concrete)
        box('Floor slab stair rear',(sx-.1,6.45,z-.22),(x+w-.25,6.85,z),'structure',concrete)
        box('Floor slab rear',(sx-.1,7.5,z-.22),(x+w-.25,11.75,z),'structure',concrete)
        beam('Stair opening trimmer',(sx-.13,3,z-.12),(sx-.13,6.45,z-.12),.15,.2)
    for xx in bearing_x:
        box('Masonry bearing wall',(xx-.12,.25,.35),(xx+.12,11.75,6.55),'structure',brick)
    for xx in (x+.245,x+w-.265):
        box('Internal wall plasterboard lining',(xx,.35,.35),(xx+.015,11.65,6.53),'interiors',white)
    for z in LEVELS:
        box('Oak floor finish',(x+.27,6.65 if z<1 else 2,z+.002),(sx-.15,11.65,z+.02),'interiors',timber)
    for z in LEVELS[:2]:stairs(sx,3,z)
    for z in LEVELS:
        for ya,yb in ((2,6.5),(7.6,11.6)):
            box('Suspended plasterboard ceiling',(x+.26,ya,z+2.6),(sx-.15,yb,z+2.625),'interiors',white)
        box('Service bulkhead soffit',(x+2.7,6.65,z+2.48),(x+3.8,7.5,z+2.5),'interiors',white)
        box('AC maintenance access hatch',(x+2.85,6.76,z+2.47),(x+3.5,7.36,z+2.48),'interiors',cream)
    garage=(x+.4,x+3.5,.35,2.65)
    entry=(x+4.15,x+w-.45,.35,2.95)
    wall_openings('Ground frontage',x,x+w,.55,.35,3.45,[garage,entry],cream,.28)
    box('Garage sectional door',(x+.45,.78,.4),(x+3.45,.86,2.6),mat=cream)
    for z in (.82,1.25,1.68,2.11):
        box('Garage horizontal joint',(x+.46,.77,z),(x+3.44,.781,z+.013),mat=stone)
    box('Recessed entry door',(x+4.2,1.15,.36),(x+5.13,1.22,2.7),mat=timber)
    box('Entry pull',(x+4.96,1.08,1.25),(x+4.98,1.13,1.85),mat=dark)
    for z in (3.17,6.27):
        beam('Facade spanning beam',(x+.2,.6,z),(x+w-.2,.6,z),.22,.3)
    balcony=(x+.55,x+3.85,3.65,5.95)
    slit=(x+4.55,x+w-.5,3.8,6.2)
    wall_openings('Brick street wall',x,x+w,0,3.45,6.6,[balcony,slit],brick,.32)
    # Actual deep brick returns and sheltered ceiling distinguish loggia from a flat window.
    for xx in (x+.4,x+3.85):
        box('Loggia masonry return',(xx,.28,3.45),(xx+.15,1.9,6.32),mat=brick)
    box('Loggia ceiling',(x+.55,.25,6.22),(x+3.85,1.95,6.32),mat=cream)
    box('Loggia tiled floor',(x+.55,.25,3.46),(x+3.85,1.95,3.49),mat=stone)
    window('Loggia sliding door',x+.55,x+3.85,1.95,3.5,6.12)
    window('Tall stair window',x+4.55,x+w-.5,.3,3.8,6.2)
    for j in range(29):
        xx=x+.59+j*(3.22/28)
        pipe('Loggia vertical baluster',[(xx,.36,3.65),(xx,.36,4.65)],.009,'architecture',dark)
    pipe('Loggia handrail',[(x+.55,.36,4.65),(x+3.85,.36,4.65)],.02,'architecture',dark)
    pipe('Loggia bottom rail',[(x+.55,.36,3.7),(x+3.85,.36,3.7)],.014,'architecture',dark)
    # Tall pale entrance blade and sheltered approach.
    verts=[(x+4.03,-.3,.35),(x+4.03,1.1,.35),(x+4.03,1.1,5.6),(x+4.03,-.3,3.05),
           (x+4.16,-.3,.35),(x+4.16,1.1,.35),(x+4.16,1.1,5.6),(x+4.16,-.3,3.05)]
    mesh('Expressed entrance blade',verts,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3)],'architecture',cream)
    rear_open=[(x+.5,x+3.7,z+.1,z+2.4) for z in LEVELS[:2]]
    wall_openings('Rear brick elevation',x,x+w,11.75,.35,6.6,rear_open,brick,.25)
    for z in LEVELS[:2]:window('Rear garden glazing',x+.5,x+3.7,11.72,z+.1,z+2.4)
    # Roof: high metal volume over principal bay; lower linking roof at entry bay.
    a,b=x+.05,x+w-.05
    lo,hi=6.6,9.65
    p=[(a,0,lo),(b,0,lo),(b,12,lo),(a,12,lo),
       (a,2,hi),(b,2,hi),(b,10,hi),(a,10,hi)]
    # Front slope has a real gap for the dormer, no metal across its glazing.
    dx0,dx1=x+.65,x+3.35
    def fz(y):return lo+(hi-lo)*y/2
    mesh('Roof front left',[(a,0,lo),(dx0,0,lo),(dx0,2,hi),(a,2,hi)],[(0,1,2,3)],'architecture',dark)
    mesh('Roof front right',[(dx1,0,lo),(b,0,lo),(b,2,hi),(dx1,2,hi)],[(0,1,2,3)],'architecture',dark)
    mesh('Roof dormer upper flashing',[(dx0,1.82,fz(1.82)),(dx1,1.82,fz(1.82)),(dx1,2,hi),(dx0,2,hi)],[(0,1,2,3)],'architecture',dark)
    mesh('Roof sides and top',p,[(1,2,6,5),(3,0,4,7),(4,5,6,7)],'architecture',dark)
    mesh('Rear roof left',[(a,12,lo),(dx0,12,lo),(dx0,10,hi),(a,10,hi)],[(0,1,2,3)],'architecture',dark)
    mesh('Rear roof right',[(dx1,12,lo),(b,12,lo),(b,10,hi),(dx1,10,hi)],[(0,1,2,3)],'architecture',dark)
    mesh('Rear dormer upper flashing',[(dx0,10.18,fz(1.82)),(dx1,10.18,fz(1.82)),(dx1,10,hi),(dx0,10,hi)],[(0,1,2,3)],'architecture',dark)
    for xx in (dx0,dx1-.09):
        box('Dormer metal cheek',(xx,.03,6.55),(xx+.09,2.1,9.28),mat=dark)
    box('Dormer cap',(dx0,-.04,9.28),(dx1,2.2,9.38),mat=dark)
    window('Boxed roof dormer',dx0+.09,dx1-.09,.18,6.75,9.22)
    # Rear dormer projects through the rear roof slope.
    for xx in (dx0,dx1-.09):box('Rear dormer cheek',(xx,9.8,6.55),(xx+.09,11.9,9.28),mat=dark)
    box('Rear dormer cap',(dx0,9.8,9.28),(dx1,12.04,9.38),mat=dark)
    window('Rear roof dormer',dx0+.09,dx1-.09,11.85,6.75,9.22)
    # Steel portal rafters with secondary timber roof framing.
    for yy in (2.1,6,9.9):
        beam('Roof steel cross beam',(a+.3,yy,9.45),(b-.3,yy,9.45),.1,.2)
        for xx in (a+.3,b-.3):beam('Roof steel post',(xx,yy,6.55),(xx,yy,9.45),.1,.1)
    for j in range(13):
        xx=a+.25+j*(w-.5)/12
        beam('Timber flat roof joist',(xx,2.1,9.5),(xx,9.9,9.5),.045,.18,timber)
    for j in range(int(w/.32)):
        xx=a+.1+j*.32
        if not dx0-.03 < xx < dx1+.03:
            pipe('Front standing seam',[(xx,.04,fz(.04)+.025),(xx,1.95,fz(1.95)+.025)],.012,'architecture',dark)
        if not dx0-.03 < xx < dx1+.03:
            pipe('Rear standing seam',[(xx,10.05,9.6),(xx,11.96,6.69)],.012,'architecture',dark)
    for yy in (0,12):
        pipe('Eaves gutter',[(a,yy,6.61),(b,yy,6.61)],.065,'hydraulic',dark)
        px=x+w-.16
        pipe('Downpipe',[(px,yy,6.6),(px,yy,.25),(px,yy,-.45),(px,-3.4,-.6)],.045,'hydraulic',dark)
    pipe('Balcony drain',[(x+3.7,1.8,3.42),(x+3.7,.35,3.36),(x+3.7,.35,-.5),(x+3.7,-3.4,-.6)],.025,'hydraulic',storm)
    # Selective fixed vertical fins in the tall window recess.
    for j in range(5):
        xx=x+4.65+j*(w-5.25)/4
        box('Integrated bronze privacy fin',(xx,.08,3.83),(xx+.025,.25,6.15),mat=dark)
    fitout(x,w)
    services(x,w)
    box('Garage approach',(x+.35,-3.7,.04),(x+3.6,.55,.12),'civil',stone)
    box('Entry walk',(x+4.17,-3.7,.05),(x+5.2,1.1,.13),'civil',stone)
    box('Front planting bed',(x+5.35,-3.7,.04),(x+w-.15,-.3,.19),'landscape',soil)
    tree(x+w-.7,-1.6,2.6)
    # Fence gate at garage and pedestrian access; panels share one rhythm.
    for j in range(int(w/.105)):
        xx=x+.03+j*.105
        box('Front vertical fence / gate',(xx,-3.81,.18),(xx+.038,-3.75,1.25),'landscape',cream)
    for xx in (x+.12,x+3.65,x+4.12,x+5.23,x+w-.1):
        box('Fence gate post',(xx,-3.86,.12),(xx+.055,-3.7,1.32),'landscape',cream)
    for z in (.35,1.07):
        box('Fence gate rail',(x,-3.82,z),(x+w,-3.76,z+.045),'landscape',cream)
    box('Rear terrace paving',(x+.25,12.05,.05),(x+w-.25,14.1,.15),'landscape',stone)
    box('Rear garden',(x+.2,14.15,-.04),(x+w-.2,17.85,.04),'landscape',grass)
    for xx in (x+.18,x+w-.18):
        box('Garden dividing fence',(xx,12,.05),(xx+.065,18,1.7),'landscape',timber)
    tree(x+1.2,16.3,3.2)
    for xx in (x+.4,x+3.7):
        box('Pergola post',(xx,13.9,.15),(xx+.08,13.98,2.75),'landscape',dark)
    for j in range(13):
        xx=x+.4+j*.275
        box('Pergola slat',(xx,12,2.75),(xx+.045,14,2.86),'landscape',timber)
    # Plant equipment screening remains open above and in front for ventilation.
    for j in range(12):
        box('Plant privacy screen',(x+w-2.15+j*.155,13.25,.2),(x+w-2.11+j*.155,13.3,1.85),'landscape',timber)
    for k in range(2):
        box('Wheelie bin',(x+.4+k*.65,-1.7,.15),(x+.92+k*.65,-1.1,1.12),'civil',dark)
    for j in range(9):
        box('Bin enclosure slat',(x+.32+j*.145,-1.82,.14),(x+.37+j*.145,-1.78,1.3),'landscape',timber)
    box('Bin enclosure end',(x+.27,-1.82,.14),(x+.32,-.94,1.3),'landscape',timber)
    records.append(dict(dwelling=owner,width_m=round(w,3),depth_m=12,levels=list(LEVELS),
        garage_clear_width_m=3.1,stair_flight_m=.9,loggia_clear_m=[3.3,1.6],
        ground_passage_clear_m=round(w-2.25-3.85,3),
        garden_depth_m=6,roof_peak_m=9.65,ac_system='Ducted indoor units on three levels; rear condenser',
        roof_rooms=2,ground_garden_room=1))


def site():
    global owner
    owner=0
    box('Site ground',(-1,-3.9,-.2),(LENGTH+1,18,.0),'civil',stone)
    box('Public footpath',(-5,-6,-.13),(LENGTH+5,-3.9,.02),'civil',stone)
    box('Street',(-10,-15,-.18),(LENGTH+10,-6,-.08),'civil',asphalt)
    box('Kerb',(-5,-6.15,-.12),(LENGTH+5,-6,.06),'civil',concrete)
    for i in range(N):
        x=i*W
        box('Driveway crossover',(x+.3,-6.15,-.07),(x+3.65,-3.9,.035),'civil',stone)
        box('Stormwater inspection pit',(x+W-.4,-3.6,-.85),(x+W-.05,-3.25,.045),'civil',concrete)
        for j in range(6):box('Pit grate',(x+W-.39+j*.057,-3.58,.048),(x+W-.37+j*.057,-3.28,.059),'civil',dark)
        pipe('Pit stormwater connection',[(x+W-.22,-3.4,-.6),(x+W-.22,-6.4,-.75)],.075,'civil',storm)
    for name,y,z,r,mat in (('Water street main',-5.1,-.65,.065,cold),('Sewer street main',-5.8,-1.15,.11,waste),
                           ('Stormwater street main',-6.4,-.75,.15,storm),('Electric street conduit',-4.65,-.45,.05,power)):
        pipe(name,[(-2,y,z),(LENGTH+2,y,z)],r,'civil',mat)
    box('Shared rainwater detention tank',(LENGTH-4,14.5,-1.9),(LENGTH-.5,17.5,-.35),'civil',concrete)
    box('Tank access lid',(LENGTH-2.8,15.4,.03),(LENGTH-2.1,16.1,.09),'civil',dark)
    pipe('Detention inlet',[(LENGTH-.16,-3.4,-.6),(LENGTH-.16,15,-.6),(LENGTH-.5,15,-.6)],.1,'civil',storm)
    pipe('Detention overflow',[(LENGTH-.5,16,-.55),(LENGTH+.5,16,-.55),(LENGTH+.5,-6.4,-.75)],.1,'civil',storm)
    for x in (-1,LENGTH+1):
        box('End boundary wall',(x,-3.9,.0),(x+.12,18,.5),'landscape',cream)
    box('Rear boundary fence',(-1,18,.0),(LENGTH+1,18.08,1.8),'landscape',timber)


def camera(name, position, target, ortho=None):
    data=bpy.data.cameras.new(name)
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=position
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    data.lens=46
    if ortho:
        data.type='ORTHO';data.ortho_scale=ortho
    return obj


site()
for i in range(N):dwelling(i)
owner=0
scene.world=bpy.data.worlds.new('Warm overcast sky')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.73,.83,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
light=bpy.data.lights.new('Afternoon sun','SUN');light.energy=2.2;light.angle=.12
sun=bpy.data.objects.new('Afternoon sun',light);scene.collection.objects.link(sun)
sun.rotation_euler=(math.radians(28),math.radians(-25),math.radians(-35))
fill=bpy.data.lights.new('Street soft light','AREA');fill.energy=4000;fill.shape='DISK';fill.size=22
fill_obj=bpy.data.objects.new('Street soft light',fill);scene.collection.objects.link(fill_obj)
fill_obj.location=(LENGTH/2,-12,15)
fill_obj.rotation_euler=(Vector((LENGTH/2,4,3))-fill_obj.location).to_track_quat('-Z','Y').to_euler()
views={
    'street':camera('Street perspective',(LENGTH+16,-42,18),(LENGTH*.52,4,4.2)),
    'front':camera('Front elevation',(LENGTH/2,-40,4.8),(LENGTH/2,4,4.8),LENGTH+5),
    'rear':camera('Garden perspective',(-8,39,19),(LENGTH*.45,7,3.5)),
    'detail':camera('Dwelling pair detail',(14,-19,9),(7,3,4.3)),
    'coordination':camera('Services and structure',(LENGTH+8,-26,24),(LENGTH*.5,5,3),LENGTH+9),
    'plan':camera('Plan',(W/2,6,35),(W/2,6,0),15.5),
}
scene.camera=views['street']
scene.render.engine='CYCLES'
scene.cycles.samples=20
scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
scene['sw_design_option']=f'{N} street-facing homes'
scene['sw_module_width_m']=W
scene['sw_discipline_scope']=','.join(groups)
manifest=dict(option=N,frontage_m=LENGTH,site_depth_m=21.9,source_boundary_retained=False,
    count_by_system=dict(Counter(o.get('sw_system') for o in scene.objects if o.get('sw_system'))),
    homes=records,routes=len(routes),assumptions=['New illustrative site, no surveyed boundary',
      'North orientation unconfirmed; fins are a privacy concept',
      'Masonry ground/first storeys; provisional RC slabs and steel/timber roof',
      'Two roof bedrooms and flexible ground garden room per home',
      'No structural calculations, plant sizing or authority connection approval'])
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
(OUT/'service-routes.json').write_text(json.dumps(routes,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'terrace-{N}.blend'))
print('TERRACE_SAVED',json.dumps(manifest['count_by_system']),flush=True)
if opt.export:
    bpy.ops.export_scene.gltf(filepath=str(OUT/f'terrace-{N}.glb'),export_format='GLB',
        export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
if opt.render:
    for name in opt.views.split(','):
        scene.camera=views[name]
        if name=='coordination':
            for s in ('architecture','interiors','landscape','civil'):groups[s].hide_render=True
        scene.render.filepath=str(OUT/f'{name}.png')
        bpy.ops.render.render(write_still=True)
        print('RENDERED',name,flush=True)
    for c in groups.values():c.hide_render=False
    # Cut plans isolate TH01 and slice above each floor, retaining furniture below cut.
    originals={}
    scene.render.resolution_x=1000;scene.render.resolution_y=1400
    for level,z in enumerate(LEVELS):
        for obj,data in originals.items():obj.data=data
        originals={}
        for obj in scene.objects:
            if obj.type not in {'MESH','CURVE'}:continue
            points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
            low=min(p.z for p in points);high=max(p.z for p in points)
            obj.hide_render=obj.get('sw_dwelling')!=1 or low>z+1.15 or high<z-.24
            if not obj.hide_render and obj.type=='MESH' and high>z+1.15:
                originals[obj]=obj.data
                obj.data=obj.data.copy()
                inv=obj.matrix_world.inverted()
                for v in obj.data.vertices:
                    point=obj.matrix_world@v.co
                    point.z=min(point.z,z+1.15)
                    v.co=inv@point
            elif not obj.hide_render and obj.type=='CURVE' and high>z+1.15:
                obj.hide_render=True
        scene.camera=views['plan']
        labels=[]
        positions=[('GARAGE',1.8,3),('ENTRY',W-1.1,1.8),('STAIR',W-1.2,4.7),
            ('GARDEN ROOM',2,9.2),('BATH / LAUNDRY',W-1.2,8)] if level==0 else (
            [('LOGGIA',2.1,.9),('LIVING',2.1,4.2),('DINING',2.1,8.8),('KITCHEN',2.1,10.2),
             ('STAIR',W-1.2,4.7),('BATH',W-1.2,8)] if level==1 else
            [('BEDROOM 1',2.3,2.2),('LANDING',2.4,6.8),('BEDROOM 2',2.3,10.9),('BATH',W-1.2,8)])
        for label,xx,yy in positions:
            data=bpy.data.curves.new('Plan label','FONT');data.body=label;data.size=.18;data.align_x='CENTER'
            obj=bpy.data.objects.new(label,data);scene.collection.objects.link(obj)
            data.materials.append(dark);obj.location=(xx,yy,z+1.2);labels.append(obj)
        scene.render.filepath=str(OUT/f'plan-{level}.png')
        bpy.ops.render.render(write_still=True)
        for obj in labels:bpy.data.objects.remove(obj,do_unlink=True)
