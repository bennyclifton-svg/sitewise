"""Author independent chalk stationery models. Run with Blender --background --python."""
from pathlib import Path
import json
import math
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PUBLIC = ROOT / 'frontend/public/landing-assets/system-3d'
PUBLIC.mkdir(parents=True, exist_ok=True)


def material(name, colour, roughness=.8):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*colour, 1)
    shader.inputs['Roughness'].default_value = roughness
    return mat


def box(name, location, size, mat, bevel=.008):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft paper edges', 'BEVEL')
        mod.width, mod.segments = bevel, 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def line(name, points, mat, radius=.002):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth, curve.bevel_resolution = radius, 2
    spline = curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def text(body, x, y, z, size=.1, mat=None):
    curve = bpy.data.curves.new(body, 'FONT')
    curve.body, curve.size, curve.extrude = body, size, .0003
    obj = bpy.data.objects.new(body, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = (x, y, z)
    obj.data.materials.append(mat or ink)
    return obj


def stack(title, subtitle='', pages=8):
    box('Bottom cover', (0, 0, .012), (1.4, 1.9, .024), cover)
    for i in range(pages):
        box(f'Paper leaf {i+1}', ((i % 3-1)*.004, (i % 2)*.006, .031+i*.009),
            (1.365, 1.86, .007), paper, .002)
    z = .041+pages*.009
    box('Top cover', (0, 0, z), (1.4, 1.9, .022), cover)
    z += .012
    line('Spine crease', [(-.61, -.88, z), (-.61, .88, z)], edge, .0015)
    heading = text(title, -.5, .43, z+.001, .14)
    bpy.context.view_layer.update()
    if heading.dimensions.x > 1.04:
        heading.data.size *= 1.04 / heading.dimensions.x
    if subtitle:
        text(subtitle, -.5, .16, z+.001, .053)
    for i in range(3):
        line('Editorial rule', [(-.5, -.14-i*.055, z+.001), (.36-i*.08, -.14-i*.055, z+.001)], edge, .0015)
    for i in range(3):
        line('Top corner detail', [(.4, .78-i*.045, z+.001), (.55, .78-i*.045, z+.001)], edge, .0015)
    return z


def roll(axis='Y', centre=(.43, 0, .23), length=1.85, radius=.16):
    verts, faces = [], []
    steps = 160
    for i in range(steps+1):
        angle = i/steps * math.pi*4.5
        r = radius + .006*angle
        for along in (-length/2, length/2):
            u, v = math.cos(angle)*r, math.sin(angle)*r
            point = (u, along, v) if axis == 'Y' else (along, u, v)
            verts.append(tuple(a+b for a, b in zip(centre, point)))
    for i in range(steps):
        faces.append((2*i, 2*i+1, 2*i+3, 2*i+2))
    mesh = bpy.data.meshes.new('Spiral paper mesh')
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new('Rolled paper with open spiral ends', mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(paper)
    for p in mesh.polygons:
        p.use_smooth = True
    mod = obj.modifiers.new('Paper thickness', 'SOLIDIFY')
    mod.thickness = .003
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def drawings():
    z = stack('SITEWISE', 'ARCHITECTURAL DRAWINGS', pages=3)
    # Plan linework is modelled, so it stays crisp when the sheet is viewed obliquely.
    for x0, y0, x1, y1 in [(-.5,-.74,.23,-.74),(-.5,-.74,-.5,.05),(.23,-.74,.23,.05),
                            (-.5,.05,.23,.05),(-.12,-.74,-.12,.05),(-.5,-.32,.23,-.32)]:
        line('Plan wall', [(x0,y0,z+.002),(x1,y1,z+.002)], ink, .0025)
    for i in range(7):
        y = -.68+i*.043
        line('Stair tread', [(-.09,y,z+.002),(.19,y,z+.002)], edge, .0017)
    line('Dimension baseline', [(-.55,-.82,z+.002),(.28,-.82,z+.002)], edge, .001)
    for x in [-.5,-.12,.23]:
        line('Dimension tick', [(x,-.86,z+.002),(x,-.77,z+.002)], edge, .001)
    roll(centre=(.46,0,z+.235))


def programme():
    z = stack('COST & PROGRAMME', pages=3)
    for i in range(8):
        y = .18-i*.11
        line('Programme row', [(-.52,y,z+.003),(.54,y,z+.003)], edge, .0014)
    for i in range(6):
        x = -.3+i*.168
        line('Programme column', [(x,.18,z+.003),(x,-.59,z+.003)], edge, .0012)
    for i in range(6):
        x = -.25+i*.105
        box('Blue programme activity', (x,-.11*i+.11,z+.004), (.24,.044,.002), blue, .001)
    for i in range(4):
        text(f'Q{i+1}', -.25+i*.19,.23,z+.004,.035)
    roll('X', (0,-.79,z+.13), 1.42, .07)


def contract():
    z=stack('CONTRACT', 'Scope and coordination', 10)
    for i in range(9):
        y=-.23-i*.044
        line('Contract paragraph', [(-.5,y,z+.002),(.47-(i%3)*.07,y,z+.002)], edge, .0015)
    for x in [-.4,.18]:
        line('Signature flourish', [(x+t*.25,-.78+math.sin(t*19)*.018+t*.055,z+.003) for t in [i/40 for i in range(41)]], ink,.002)


def emails():
    z=stack('SiteWise', 'CORRESPONDENCE', 6)
    box('Envelope', (0,-.42,z+.018), (1.27,.7,.025), paper)
    line('Envelope folded flap', [(-.63,-.08,z+.032),(0,-.49,z+.034),(.63,-.08,z+.032)], edge,.002)
    line('Envelope seams', [(-.63,-.76,z+.032),(-.18,-.41,z+.033)], edge,.0015)
    line('Envelope seams', [(.63,-.76,z+.032),(.18,-.41,z+.033)], edge,.0015)


def hard_hat():
    verts, faces=[], []
    rings, segments=24,64
    for i in range(rings+1):
        phi=.001+(math.pi/2-.001)*i/rings
        for j in range(segments):
            angle=j/segments*math.tau
            verts.append((.61*math.sin(phi)*math.cos(angle),.74*math.sin(phi)*math.sin(angle),.13+.72*math.cos(phi)))
    for i in range(rings):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments
            faces.append((a,b,b+segments,a+segments))
    mesh=bpy.data.meshes.new('Elliptical safety shell')
    mesh.from_pydata(verts,[],faces)
    obj=bpy.data.objects.new('Hard hat dome',mesh)
    bpy.context.collection.objects.link(obj);mesh.materials.append(cover)
    for p in mesh.polygons:p.use_smooth=True
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Shell wall', 'SOLIDIFY');mod.thickness=.022
    bpy.ops.object.modifier_apply(modifier=mod.name)
    verts=[];faces=[]
    for ring in range(2):
        for j in range(segments):
            t=j/segments*math.tau
            rx=.6 if ring==0 else .75
            ry=.73 if ring==0 else .88+max(0,-math.sin(t))*.13
            verts.append((rx*math.cos(t),ry*math.sin(t),.125-ring*.027))
    for j in range(segments):faces.append((j,(j+1)%segments,(j+1)%segments+segments,j+segments))
    mesh=bpy.data.meshes.new('Full protective brim');mesh.from_pydata(verts,[],faces)
    obj=bpy.data.objects.new('Front extended brim',mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(cover)
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Brim thickness','SOLIDIFY');mod.thickness=.025;bpy.ops.object.modifier_apply(modifier=mod.name)
    for x in [-.2,0,.2]:
        line('Raised crown rib', [(x,.68*math.sin(t),.14+.72*math.sqrt(1-(x/.65)**2)*math.cos(t)+.018) for t in [-1.25+i*2.5/50 for i in range(51)]],cover,.018)
    for x in [-.48,.48]:box('Harness attachment', (x,-.55,.16),(.12,.08,.13),cover)
    box('Front logo panel', (0,-.753,.3), (.51,.033,.17), cover, .015)
    logo=text('SiteWise',-.21,-.772,.265,.11)
    logo.rotation_euler=(math.pi/2,0,0)


ASSETS=[('drawings',drawings),('cost-programme',programme),('hard-hat',hard_hat),
        ('contract-coordination',contract),('planning-legislation',lambda:stack('Planning\nLegislation','Planning framework',10)),
        ('ncc-bca',lambda:stack('NCC / BCA','National Construction Code',10)),
        ('australian-standards',lambda:stack('Australian\nStandards','Reference standards',10)),
        ('advice',lambda:stack('SiteWise','Advice',8)),('emails',emails)]
manifest=[]
for slug, build in ASSETS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    cover=material('Chalk ivory',(.86,.85,.81))
    paper=material('Warm white paper',(.94,.93,.90))
    edge=material('Soft graphite rules',(.43,.44,.42))
    ink=material('Warm graphite typography',(.12,.13,.12))
    blue=material('SiteWise azure',(.015,.30,.59))
    build()
    # Bake text/curves to mesh; every GLB works without external fonts or images.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.convert(target='MESH')
    model_objects=list(bpy.context.selected_objects)
    for obj in model_objects:obj['asset']=slug
    bpy.ops.export_scene.gltf(filepath=str(PUBLIC/f'{slug}.glb'),export_format='GLB',use_selection=True,export_yup=True)
    triangles=sum(len(o.data.polygons) for o in model_objects)
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
    scene.render.film_transparent=True
    scene.world=bpy.data.worlds.new('White studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
    for location,energy,size in [((-3,-4,6),450,4),((3,2,4),150,3)]:
        bpy.ops.object.light_add(type='AREA',location=location)
        light=bpy.context.object;light.data.energy=energy;light.data.shape='DISK';light.data.size=size
        light.rotation_euler=(Vector((0,0,.1))-light.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(2.8,-4.3,5.5))
    camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,.1))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=2.65;scene.camera=camera
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/f'{slug}.blend'))
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(PUBLIC/f'{slug}.png')
    bpy.ops.render.render(write_still=True)
    manifest.append({'name':slug,'glb':f'{slug}.glb','preview':f'{slug}.png','mesh_objects':len(model_objects),'faces':triangles,'bytes':(PUBLIC/f'{slug}.glb').stat().st_size})
    print(f'ASSET COMPLETE {slug}',flush=True)
(PUBLIC/'manifest.json').write_text(json.dumps(manifest,indent=2))
