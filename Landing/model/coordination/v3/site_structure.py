"""Site/civil/landscape and focus-dwelling RC components in registered site XY.

Integration calls build(scene) after registering the supplied interior once.
This module does not save or replace the integrated scene.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
AUDIT = json.loads((HERE.parent / 'structure-audit-summary.json').read_text())
ANGLE = math.atan2(.16053, .98703)
FOCUS = Matrix.Rotation(ANGLE, 4, 'Z') @ Vector(AUDIT['coordinates']['world_origin'])


def build(scene):
    source = {o.get('source_name'): o for o in scene.objects if o.get('source_name')}
    ground_id = 'SLA - 007_Concrete - Foundation_0.029'
    ground = source[ground_id]
    points = [ground.matrix_world @ v.co for v in ground.data.vertices]
    centre = Vector(tuple((min(p[i] for p in points) + max(p[i] for p in points)) / 2 for i in range(3)))
    expected = FOCUS + Vector((-.6157, -.34005, .35))
    assert (centre - expected).length < .002, 'Register the interior with +Rz once before site_structure.build'
    groups = {}
    for system in ('civil', 'landscape', 'structure'):
        collection = bpy.data.collections.new('V3 | ' + system.title())
        scene.collection.children.link(collection)
        groups[system] = collection
    objects, suppress, records = [], [], []

    def material(name, hex_colour):
        c = [int(hex_colour[i:i+2], 16) / 255 for i in (1, 3, 5)]
        linear = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c)
        mat = bpy.data.materials.new('V3 | ' + name)
        mat.diffuse_color = (*linear, 1)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*linear, 1)
        shader.inputs['Roughness'].default_value = .84
        return mat

    concrete = material('RC mineral concrete', '#C6C8C4')
    roof_metal = material('Roof framing mineral metal', '#9BADA8')
    paving = material('Civil paving', '#7A969A')
    path_mat = material('Pedestrian light paving', '#D4DBD7')
    timber = material('Lap and cap fence', '#9C9687')
    chalk = material('Chalk fixtures', '#F9F7F3')
    dark = material('Recess and slot', '#244448')
    soil = material('Garden mulch', '#66735D')
    leaves = [material('Plant green ' + str(i+1), c) for i, c in enumerate(('#557E56', '#73905F', '#426B51'))]
    lawn = material('Lawn green', '#68815B')

    def add(name, mesh, system, mat, label, provenance='Authored illustrative component'):
        obj = bpy.data.objects.new('V3 | ' + name, mesh)
        groups[system].objects.link(obj)
        mesh.materials.clear()
        mesh.materials.append(mat)
        obj['sw_system'] = system
        obj['sw_label'] = label
        obj['sw_provenance'] = provenance
        obj['sw_status'] = 'Illustrative coordination geometry; dimensions and compliance unverified'
        objects.append(obj)
        return obj

    def box(name, centre, size, system='civil', mat=paving, label=None):
        x, y, z = (n / 2 for n in size)
        verts = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
        mesh = bpy.data.meshes.new('V3 | ' + name)
        mesh.from_pydata(verts, [], [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        obj = add(name, mesh, system, mat, label or name)
        obj.location = centre
        return obj

    def ramp(name, xmin, xmax, ymin, ymax, z_west, z_east, label):
        verts = [(xmin,ymin,z_west-.1),(xmax,ymin,z_east-.1),(xmax,ymax,z_east-.1),(xmin,ymax,z_west-.1),
                 (xmin,ymin,z_west),(xmax,ymin,z_east),(xmax,ymax,z_east),(xmin,ymax,z_west)]
        mesh = bpy.data.meshes.new('V3 | ' + name)
        mesh.from_pydata(verts, [], [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        return add(name, mesh, 'civil', paving, label)

    def bbox(obj):
        pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
        return [[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]]

    # Garage entries use the five actual source door panels, not evenly spaced assumptions.
    garages = []
    for name, obj in source.items():
        if name.startswith('DOO - 018_Paint - Titanium White'):
            low, high = bbox(obj)
            garages.append(dict(source=name, x=(low[0]+high[0])/2, y=(low[1]+high[1])/2,
                                ymin=low[1], ymax=high[1], threshold=low[2]))
    garages.sort(key=lambda p: p['y'])
    assert len(garages) == 5, 'Expected the five source garage fronts'
    box('Public footpath', (0,-22.75,.005), (60,1.5,.16), mat=path_mat, label='Public footpath')
    for x, width in [(-20.8,18.4), (11.15,37.7)]:
        box('Kerb outside crossover', (x,-23.48,.075), (width,.16,.17), mat=path_mat)
    box('Shared driveway', (-9.65,-2.75,.17), (3.9,38.5,.2), label='Shared garage access')
    box('Building-side pedestrian path', (-6.75,-2.75,.185), (1.3,38.5,.18), mat=path_mat,
        label='Building-side pedestrian path to dwelling entries')
    box('Driveway crossover', (-9.65,-22.75,.065), (3.9,1.5,.16), label='Illustrative vehicle crossover')
    box('Pedestrian entry crossing', (-6.75,-22.75,.105), (1.3,1.5,.13), mat=path_mat)
    box('Driveway rear turning apron', (-9.65,17,.17), (3.9,1,.2), label='Rear access extent — turning unverified')
    for i, door in enumerate(garages):
        # Top surfaces meet measured garage thresholds despite source floor level changes.
        ramp('Garage apron ' + str(i+1), -6.1, door['x']+.05, door['ymin']-.10, door['ymax']+.10,
             .27, door['threshold'], 'Garage ' + str(i+1) + ' threshold connection')
        box('Garage pedestrian crossing '+str(i+1),(-6.90,door['y'],.17),
            (1.60,door['ymax']-door['ymin']+.20,.20),label='Garage access across pedestrian route')
        y = door['ymin'] - .65
        link=ramp('Entry link '+str(i+1),-6.1,door['x']+.05,y-.425,y+.425,.2825,door['threshold'],
                  'Pedestrian link to measured entry level')
        link.data.materials.clear();link.data.materials.append(path_mat)

    # User-requested lap/cap enclosure: coordinate centrelines remain on the selected parcel.
    fence_runs = [((-12,-22),(-12,22)),((12,-22),(12,22)),((-12,22),(12,22)),
                  ((-12,-22),(-11.6,-22)),((-7.7,-22),(-7.4,-22)),((-6.1,-22),(12,-22))]
    fence_points = []

    def fence(name, a, b, height=1.65, system='civil'):
        first=len(objects)
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx,dy)
        angle = math.atan2(dy,dx)
        count = max(1, math.ceil(length / .15))
        for i in range(count):
            t = (i+.5)/count
            centre = (a[0]+t*dx, a[1]+t*dy, height/2-.04)
            obj = box(name+' lap '+str(i+1), centre, (length/count+.018,.026,height), system, timber,
                      'Lap and cap boundary fence' if system=='civil' else 'Private garden division')
            obj.rotation_euler.z = angle
        cap = box(name+' cap', ((a[0]+b[0])/2,(a[1]+b[1])/2,height-.035), (length,.115,.065),system,timber)
        cap.rotation_euler.z = angle
        for i in range(math.ceil(length/2)+1):
            t = i / math.ceil(length/2)
            x,y = a[0]+t*dx,a[1]+t*dy
            box(name+' post '+str(i+1),(x,y,height/2-.02),(.09,.09,height+.06),system,timber)
            if system == 'civil': fence_points.append((x,y))
        # One semantic fence mesh per run keeps the interactive export inexpensive.
        bpy.context.view_layer.update()
        parts=objects[first:]
        verts,faces=[],[]
        for obj in parts:
            offset=len(verts)
            verts.extend(tuple(obj.matrix_world@v.co) for v in obj.data.vertices)
            faces.extend(tuple(offset+n for n in p.vertices) for p in obj.data.polygons)
        mesh=bpy.data.meshes.new('V3 | '+name+' combined')
        mesh.from_pydata(verts,[],faces)
        for obj in parts: bpy.data.objects.remove(obj,do_unlink=True)
        del objects[first:]
        add(name,mesh,system,timber,'Lap and cap boundary fence' if system=='civil' else 'Private garden division')

    for i, (a,b) in enumerate(fence_runs): fence('Perimeter '+str(i+1), a,b)
    fence('Pedestrian front gate',(-7.38,-21.96),(-6.12,-21.96),1.3)
    # Do not report the gate's four-centimetre setback as a boundary-centreline error.
    fence_points = [p for p in fence_points if abs(p[1]+21.96) > .001]
    box('Letterbox blade',(-7.55,-21.68,1.06),(.16,.45,2.2),mat=chalk,label='Front letterbox and entry marker')
    box('Cantilever entry hood',(-6.79,-21.64,2.12),(1.68,.9,.12),mat=chalk,label='Cantilever entry hood')
    for i in range(5):
        box('Letterbox '+str(i+1),(-7.55,-21.92,.55+i*.245),(.12,.075,.15),mat=dark,label='Dwelling letterbox '+str(i+1))

    # Relocate supplied bins into one small front store, preserving their source mesh detail.
    bins = sorted((o for n,o in source.items() if n.startswith('Rubish Bin')), key=lambda o:o.get('source_name'))
    box('Front bin store slab',(-1.9,-19.85,.025),(7.3,1.9,.15),label='Front collection store')
    for name, centre, size in [('back',(-1.9,-18.91,.68),(7.3,.10,1.4)),
                               ('west',(-5.55,-19.85,.68),(.10,1.9,1.4)),
                               ('east',(1.75,-19.85,.68),(.10,1.9,1.4))]:
        box('Bin store '+name,centre,size,mat=timber,label='Screened collection store')
    for i, original in enumerate(bins):
        obj = add('Relocated bin '+str(i+1), original.data.copy(), 'civil', chalk, 'Front waste collection',
                  'Supplied source mesh relocated from '+original.get('source_name'))
        obj.matrix_world = original.matrix_world.copy()
        low, high = bbox(obj)
        destination = Vector((-5.08+i*.70,-19.9,.115))
        obj.matrix_world.translation += destination - Vector(((low[0]+high[0])/2,(low[1]+high[1])/2,low[2]))
        suppress.append(original.get('source_name'))
    suppress.extend(n for n in source if n.startswith('Post-Box 01 24'))

    # Actual source slab bands identify paired seams and broad outdoor gaps.
    dwelling_bounds=[]
    for name,obj in source.items():
        if not name.startswith('SLA - 007_Concrete'):continue
        low,high=bbox(obj)
        if high[0]-low[0]>8 and high[1]-low[1]>2:
            dwelling_bounds.append(dict(source=name,min=low,max=high))
    dwelling_bounds.sort(key=lambda r:r['min'][1])
    assert len(dwelling_bounds)==5
    seams=[dict(y=(a['max'][1]+b['min'][1])/2,gap=b['min'][1]-a['max'][1],
                adjacent_sources=[a['source'],b['source']]) for a,b in zip(dwelling_bounds,dwelling_bounds[1:])]
    dividers = [-14.2] + [r['y'] for r in seams] + [14.9]
    garden_fence_records=[]
    for i,(ya,yb) in enumerate(zip(dividers,dividers[1:])):
        box('Private lawn '+str(i+1),(9.55,(ya+yb)/2,.005),(4.7,yb-ya-.12,.12),'landscape',lawn,
            'Private garden '+str(i+1))
        box('Garden bed '+str(i+1),(11.32,(ya+yb)/2,.06),(.7,yb-ya-.2,.16),'landscape',soil)
        if i:
            seam=seams[i-1]
            start=-5.50 if seam['gap']>.35 else 4.73
            fence('Garden divider '+str(i),(start,ya),(12,ya),1.55,'landscape')
            garden_fence_records.append(dict(y=ya,start_x=start,end_x=12,gap=seam['gap'],
                status='Crosses outdoor inter-building gap' if start<0 else 'Stops at east building face; tight paired seam'))
        count = max(2,int((yb-ya)/1.2))
        for j in range(count):
            y = ya+.45+(yb-ya-.9)*j/max(1,count-1)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=(11.25,y,.48))
            plant = bpy.context.object
            for col in list(plant.users_collection): col.objects.unlink(plant)
            groups['landscape'].objects.link(plant)
            plant.name='V3 | Shrub '+str(i+1)+' '+str(j+1)
            plant.scale=(.46,.48,.58 if j%2 else .42)
            plant.data.materials.append(leaves[(i+j)%len(leaves)])
            plant['sw_system']='landscape';plant['sw_label']='Garden planting'
            plant['sw_provenance']='Illustrative low-complexity planting; species/site conditions unassigned'
            objects.append(plant)

    # Connected planted bands wrap the development; buried-service corridor remains unplanted.
    landscape_strips=[]
    strip_specs=[('Front',-5.60,11.80,-17.4,-14.20),('Rear',-5.60,11.80,15.10,21.70)]
    for i,seam in enumerate(seams):
        if seam['gap']>.35:
            strip_specs.append(('Between buildings '+str(i+1),-5.50,11.80,seam['y']-.85,seam['y']+.85))
    for name,xa,xb,ya,yb in strip_specs:
        for left,right in [(xa,6.0),(6.8,xb)]:
            box(name+' landscape strip',((left+right)/2,(ya+yb)/2,.005),(right-left,yb-ya,.12),
                'landscape',lawn,'Continuous '+name.lower()+' landscape')
        landscape_strips.append(dict(name=name,x=[xa,xb],y=[ya,yb],service_gap_x=[6.0,6.8]))

    # Closed 200 mm slabs come from actual top-face triangles, with the stair holes intact.
    # The old plaster body meshes are unsuitable: they also include deep edge returns.
    slab_ids = [ground_id,'SLA - 008_Wall white plaster_0.002','SLA - 010_Wall white plaster_0.024',
                'SLA - 010_Wall white plaster_0.026','SLA - 009_Floorboards light_0.002',
                'SLA - 009_Wall white plaster_0.002']
    floor_faces={r['source']:r['faces'] for r in AUDIT['floor_top_faces']}
    balcony=source['SLA - 009_Floorboards - 03_0.002']
    balcony.data.calc_loop_triangles()
    balcony_faces=[]
    for tri in balcony.data.loop_triangles:
        points=[balcony.matrix_world@balcony.data.vertices[n].co for n in tri.vertices]
        if all(abs(p.z-3.22)<.002 for p in points):
            balcony_faces.append([[round(p.x-FOCUS.x,4),round(p.y-FOCUS.y,4),3.22] for p in points])
    assert balcony_faces, 'Source balcony top triangles missing'
    floor_faces['living-complete']=floor_faces['SLA - 008_Floorboards light_0.002']+balcony_faces
    slab_levels=[('ground',.50,ground_id),('living',3.22,'living-complete'),
                 ('upper',5.94,'SLA - 010_Render: Carpet - grey_0.077')]
    slab_checks=[]
    for level,top,key in slab_levels:
        xy=[];lookup={};triangles=[]
        for triangle in floor_faces[key]:
            indices=[]
            for p in triangle:
                coordinate=(round(p[0],4),round(p[1],4))
                if coordinate not in lookup: lookup[coordinate]=len(xy);xy.append(coordinate)
                indices.append(lookup[coordinate])
            a,b,c=[xy[i] for i in indices]
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:indices.reverse()
            triangles.append(indices)
        edge_counts={};edge_direction={}
        for triangle in triangles:
            for a,b in zip(triangle,triangle[1:]+triangle[:1]):
                edge=tuple(sorted((a,b)));edge_counts[edge]=edge_counts.get(edge,0)+1;edge_direction[edge]=(a,b)
        count=len(xy)
        vertices=[(FOCUS.x+u,FOCUS.y+v,z) for z in [top,top-.20] for u,v in xy]
        faces=list(triangles)+[[i+count for i in reversed(t)] for t in triangles]
        for edge,n in edge_counts.items():
            if n==1:
                a,b=edge_direction[edge];faces.append([b,a,a+count,b+count])
        mesh=bpy.data.meshes.new('V3 | '+level+' 200 mm concrete slab')
        mesh.from_pydata(vertices,[],faces);mesh.update()
        closed_edges={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                edge=tuple(sorted((a,b)));closed_edges[edge]=closed_edges.get(edge,0)+1
        assert all(n==2 for n in closed_edges.values()), ('Non-manifold slab edge',level)
        obj=add('RC '+level+' slab 200mm',mesh,'structure',concrete,'200 mm reinforced-concrete '+level+' slab',
                'Uniform extrusion of supplied floor-top footprint; stair voids retained; illustrative RC interpretation')
        obj['sw_source_id']=key;obj['sw_component']='slab';obj['sw_thickness']=.20
        low,high=bbox(obj)
        assert abs(high[2]-low[2]-.20)<.00001
        slab_checks.append(dict(level=level,source_footprint=key,top=top,bottom=top-.20,thickness=.20,
            closed_prism=True,upstands=False,source_xy_footprint_preserved=True,bounds=[low,high],
            top_triangles=len(triangles),boundary_edges=sum(n==1 for n in edge_counts.values())))
    suppress.extend(slab_ids)
    suppress.extend(['SLA - 008_Floorboards light_0.002','SLA - 010_Render: Carpet - grey_0.077',
                     'SLA - 009_Floorboards - 03_0.002'])

    # Complete western corner supports now bear on the actual living balcony plate.
    column_specs=[(-5.18,-2.525,.20),(-5.18,1.845,.18),(4.024,-2.525,.20),(4.024,1.845,.18),
                  (-2.50,1.825,.20),(1.06,1.825,.20),(1.30,-2.40,.20)]
    levels=[(.50,3.02),(3.22,5.74),(5.94,8.39)]

    def in_triangle(p, triangle):
        values=[]
        for a,b in zip(triangle,triangle[1:]+triangle[:1]):
            values.append((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
        return min(values)>=-.0001 or max(values)<=.0001

    def floor_contains(u,v,source_id):
        return any(in_triangle((u,v),t) for t in floor_faces[source_id])

    stair_void_checks={'living':not floor_contains(-1.50,-2.00,'living-complete'),
                       'upper':not floor_contains(-1.00,-2.00,'SLA - 010_Render: Carpet - grey_0.077')}
    assert all(stair_void_checks.values()), 'Measured stair void must remain open'

    # Only support positions that clear actual lower/upper stair openings survive.
    footprint_tests=[]
    for i,(u,v,width) in enumerate(column_specs):
        test={}
        for name in (ground_id,'living-complete','SLA - 010_Render: Carpet - grey_0.077'):
            okay=all(floor_contains(u+du,v+dv,name) for du in [-width/2,width/2] for dv in [-width/2,width/2])
            test[name]=okay
        assert all(test.values()), ('Column would overlap source floor void',u,v,test)
        footprint_tests.append(dict(uv=[u,v],source_floor_checks=test))
        for level,(za,zb) in enumerate(levels):
            obj=box('RC column '+str(i+1)+' level '+str(level+1),(FOCUS.x+u,FOCUS.y+v,(za+zb)/2),
                    (width,width,zb-za),'structure',concrete,'Concrete column stack '+str(i+1))
            obj['sw_component']='column';obj['sw_source_id']='Measured slab and opening audit'
        box('RC footing pad '+str(i+1),(FOCUS.x+u,FOCUS.y+v,-.48),(.85,.85,.36),'structure',concrete,
            'Illustrative concrete pad footing')
        box('RC foundation pedestal '+str(i+1),(FOCUS.x+u,FOCUS.y+v,0),(.32,.32,.60),'structure',concrete)
    for i,(u,v,width) in enumerate(column_specs):
        records.append(dict(id='C'+str(i+1),uv=[u,v],xy=[FOCUS.x+u,FOCUS.y+v],width=width,levels=levels))

    # Restrained pitched-roof trusses fit between the measured ceiling and roof underside.
    # Heel ends are shortened/tapered; final bearing connection still needs resolution.
    def roof_z(u): return min(.2679*u+9.8167,-.2679*u+9.6207)
    roof_objects=[]

    def roof_member(name,a,b,width,depth):
        a,b=Vector(a),Vector(b)
        obj=box(name,(0,0,0),(width,depth,(b-a).length),'structure',roof_metal,'Illustrative roof truss')
        obj.matrix_world=Matrix.Translation(FOCUS+(a+b)/2)@(b-a).to_track_quat('Z','Y').to_matrix().to_4x4()
        obj['sw_component']='roof';roof_objects.append(obj)
        return obj

    for i,v in enumerate([-2.46,-1.39,-.32,.75,1.82]):
        for side,ua,ub in [('west',-5.00,-.3658),('east',-.3658,4.32)]:
            # Explicit prism sections, clipped above ceiling instead of protruding through rooms.
            endpoints=[]
            for u in [ua,ub]:
                top=roof_z(u)-.025;bottom=max(8.412,top-.14)
                endpoints.extend([(FOCUS.x+u,FOCUS.y+v-.035,bottom),(FOCUS.x+u,FOCUS.y+v+.035,bottom),
                                  (FOCUS.x+u,FOCUS.y+v+.035,top),(FOCUS.x+u,FOCUS.y+v-.035,top)])
            mesh=bpy.data.meshes.new('V3 | clipped rafter')
            mesh.from_pydata(endpoints,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
            obj=add('Roof truss '+str(i+1)+' '+side+' rafter',mesh,'structure',roof_metal,
                    'Roof rafter under measured 15 degree plane','Illustrative rafter; tapered heel bearing unresolved')
            obj['sw_component']='roof';roof_objects.append(obj)
        roof_member('Roof truss '+str(i+1)+' bottom chord',(-4.80,v,8.46),(4.10,v,8.46),.07,.075)
        roof_member('Roof truss '+str(i+1)+' king post',(-.3658,v,8.49),(-.3658,v,9.57),.055,.055)
        roof_member('Roof truss '+str(i+1)+' west web',(-4.60,v,8.49),(-.3658,v,9.57),.055,.055)
        roof_member('Roof truss '+str(i+1)+' east web',(3.85,v,8.49),(-.3658,v,9.57),.055,.055)
    roof_member('Roof ridge member',(-.3658,-2.46,9.60),(-.3658,1.82,9.60),.10,.12)
    bpy.context.view_layer.update()
    roof_points=[obj.matrix_world@p.co for obj in roof_objects for p in obj.data.vertices]
    minimum_roof_clearance=min(roof_z(p.x-FOCUS.x)-p.z for p in roof_points)
    minimum_roof_z=min(p.z for p in roof_points)
    assert minimum_roof_clearance>.009 and minimum_roof_z>=8.405

    fence_error=max(min(abs(abs(x)-12),abs(abs(y)-22)) for x,y in fence_points)
    assert fence_error < .00001
    metadata=dict(module='site_structure',coordinate_contract='Registered site XY; root applies source rotation once',
                  focus_registered=list(FOCUS),collections={k:v.name for k,v in groups.items()},
                  object_counts={k:len(v.objects) for k,v in groups.items()},
                  suppress_source_names=sorted(set(suppress)),garage_entries=garages,
                  driveway=dict(x=[-11.6,-7.7],y=[-22,17.5],status='Illustrative; swept path and grades not certified'),
                  pedestrian_path=dict(x=[-7.4,-6.1],y=[-22,16.5],position='Between driveway and buildings'),
                  street=dict(road_y=[-34,-23.5],sidewalk_y=[-23.5,-22],carriageway_rendered=False),
                  fence=dict(type='Lap and cap timber',height=1.65,centreline_error=fence_error,runs=fence_runs,
                             access_openings=dict(vehicle_x=[-11.6,-7.7],pedestrian_x=[-7.4,-6.1])),
                  gardens=dict(x=[7.2,11.9],division_y=dividers,status='Divisions use measured slab/building midlines',
                               dwelling_bounds=dwelling_bounds,fence_runs=garden_fence_records,continuous_strips=landscape_strips),
                  service_reservations=dict(east_corridor_x=[6.0,6.8],tank_xy=[8,-18]),
                  bins_relocated=len(bins),slab_topology_checks=slab_checks,column_stacks=records,
                  column_floor_footprint_checks=footprint_tests,
                  stair_void_checks=stair_void_checks,
                  roof_framing=dict(truss_count=5,member_count=len(roof_objects),pitch_degrees=15,
                    minimum_z=minimum_roof_z,ceiling_z=8.39,minimum_roof_clearance=minimum_roof_clearance,
                    material='Neutral mineral metal; structural specification unassigned',
                    source_roof_ids=['RT - 024_Wall white plaster_0','RT - 024_Wall white plaster_0.001'],
                    heel_status='Shortened tapered rafter ends respect measured roof/ceiling void; final bearing design unresolved'),
                  unresolved_interfaces=[
                      dict(id='rc-west-transfer',anchor=[FOCUS.x-4.0,FOCUS.y-1.98,3.07],
                           question='Verify column/slab reinforcement and load transfer around the stair opening and balcony return.',
                           source_ids=slab_ids,disciplines=['Architecture','Structural engineering']),
                      dict(id='rc-roof-bearing',anchor=[FOCUS.x-3.8,FOCUS.y+1.7,8.39],
                           question='Agree the RC column-to-pitched-roof bearing and ceiling interface.',
                           disciplines=['Structural engineering','Architecture','Mechanical']),
                      dict(id='access-levels',anchor=[-6.1,garages[0]['y'],.27],
                           question='Resolve garage threshold grades, accessible pedestrian crossings and vehicle turning.',
                           disciplines=['Civil','Architecture','Traffic'])],
                  limits=['Imported model units are not verified metres.','Concrete column sizes, reinforcement, loads and soil bearing are unverified.',
                          'Slabs are closed uniform 200 mm extrusions of source floor-top footprints; structure is conceptual, not engineered.',
                          'Roof rafters/trusses fit the measured roof void; heel/bearing connections and member sizes remain unverified.',
                          'Garden divisions, fence, crossover and bin store are illustrative coordination proposals.',
                          'Root must suppress old ground fences and superseded site paving separately.'])
    (HERE/'site-structure-metadata.json').write_text(json.dumps(metadata,indent=2))
    return metadata


if __name__ == '__main__':
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-interior-checkpoint.blend'))
    scene=bpy.data.scenes['01 | Assembled interior']
    bpy.context.window.scene=scene
    visible=[o for o in scene.objects if not o.hide_render]
    transforms={o:o.matrix_world.copy() for o in visible}
    rotation=Matrix.Rotation(ANGLE,4,'Z')
    for obj,matrix in transforms.items():
        if obj.type not in ('CAMERA','LIGHT'):
            obj.parent=None
            obj.matrix_world=rotation@matrix
    bpy.context.view_layer.update()
    if '--audit' in sys.argv:
        rows=[]
        for obj in scene.objects:
            if obj.type!='MESH' or not obj.get('source_name'):continue
            pts=[obj.matrix_world@v.co for v in obj.data.vertices]
            low=[min(p[i] for p in pts) for i in range(3)];high=[max(p[i] for p in pts) for i in range(3)]
            if obj.get('system') in ['02 Substructure','03 Floor plates'] or (obj.get('system')=='04 Walls' and high[2]-low[2]>2):
                rows.append(dict(name=obj.get('source_name'),system=obj.get('system'),min=low,max=high))
        (HERE/'site-iteration-source-audit.json').write_text(json.dumps(rows,indent=2))
        print('SITE_ITERATION_AUDIT_READY',len(rows),flush=True)
        sys.exit(0)
    metadata=build(scene)
    # Component-only library; the source scene is read for geometry but never overwritten.
    component_scene=bpy.data.scenes.new('V3 | Site structure components')
    for name in metadata['collections'].values(): component_scene.collection.children.link(bpy.data.collections[name])
    bpy.data.libraries.write(str(HERE/'site-structure-components.blend'),{component_scene})
    print('SITE_STRUCTURE_READY',json.dumps({k:metadata[k] for k in ['object_counts','garage_entries']}),flush=True)
