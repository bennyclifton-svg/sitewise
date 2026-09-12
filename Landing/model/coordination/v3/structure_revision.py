"""Illustrative continuous foundations and supported, evenly spaced roof trusses."""
import bpy
import json
import sys
from collections import Counter
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

def bounds(obj):
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    return [Vector([fn(p[i] for p in points) for i in range(3)]) for fn in (min,max)]

def build(scene):
    slab=scene.objects['V3 | RC ground slab 200mm']
    material=slab.data.materials[0]
    def mesh_object(name,vertices,faces):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
        obj['sw_system']='structure';obj['sw_component']='foundation' if 'foundation' in name or 'footing' in name else 'roof'
        mesh.materials.append(material)
        return obj
    def prism(name,a,b,width,bottom,top,extend=True):
        a,b=Vector(a),Vector(b)
        normal=Vector((-(b-a).y,(b-a).x,0)).normalized()*width/2
        # Slightly overlapping corners make the perimeter strip continuous.
        direction=(b-a).normalized()*(width/2 if extend else 0)
        corners=[a-direction+normal,b+direction+normal,b+direction-normal,a-direction-normal]
        vertices=[(p.x,p.y,z) for z in (bottom,top) for p in corners]
        return mesh_object(name,vertices,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])

    # Extract the actual exterior top-face loop, rather than a rectangle around the slab.
    vertices=[slab.matrix_world@v.co for v in slab.data.vertices]
    top=max(p.z for p in vertices)
    edges=Counter()
    for face in slab.data.polygons:
        ids=list(face.vertices)
        if all(abs(vertices[i].z-top)<.001 for i in ids):
            edges.update(tuple(sorted((a,b))) for a,b in zip(ids,ids[1:]+ids[:1]))
    remaining={edge for edge,count in edges.items() if count==1}
    loops=[]
    while remaining:
        a,b=remaining.pop();loop=[a,b]
        while loop[-1]!=loop[0]:
            edge=next(edge for edge in remaining if loop[-1] in edge)
            remaining.remove(edge)
            loop.append(edge[1] if edge[0]==loop[-1] else edge[0])
        loops.append(loop)
    outline=max(loops,key=lambda loop:abs(sum(vertices[a].x*vertices[b].y-vertices[b].x*vertices[a].y for a,b in zip(loop,loop[1:]))))
    for obj in list(scene.objects):
        if obj.name.startswith(('V3 | RC footing pad ','V3 | RC foundation pedestal ',
            'Detail | Perimeter strip footing ','Detail | Perimeter foundation stem ',
            'Detail | Front roof bearing beam','Detail | Rear roof bearing beam')):
            bpy.data.objects.remove(obj,do_unlink=True)
    for i,(a,b) in enumerate(zip(outline,outline[1:])):
        prism(f'Detail | Perimeter strip footing {i+1}',vertices[a],vertices[b],.6,-.66,-.30)
        prism(f'Detail | Perimeter foundation stem {i+1}',vertices[a],vertices[b],.22,-.30,top-.20)

    old=[o for o in scene.objects if o.name.startswith('V3 | Roof truss ')]
    first=[o for o in old if o.name.startswith('V3 | Roof truss 1 ')]
    chords=[o for o in old if o.name.endswith('bottom chord')]
    centres=sorted((sum(bounds(o),Vector((0,0,0)))/2).y for o in chords)
    start,end=centres[0],centres[-1]
    templates=[(o.name.split('V3 | Roof truss 1 ')[1],o.data.copy(),o.matrix_world.copy()) for o in first]
    chord_low,chord_high=bounds(scene.objects['V3 | Roof truss 1 bottom chord'])
    for obj in old:
        bpy.data.objects.remove(obj,do_unlink=True)
    positions=[start+(end-start)*i/7 for i in range(8)]
    for i,y in enumerate(positions):
        for suffix,data,matrix in templates:
            obj=bpy.data.objects.new(f'V3 | Roof truss {i+1} {suffix}',data.copy())
            scene.collection.objects.link(obj)
            obj.matrix_world=matrix.copy();obj.location.y+=y-start
            obj['sw_system']='structure';obj['sw_component']='roof'
    ridge=scene.objects['V3 | Roof ridge member']
    ridge_low,ridge_high=bounds(ridge)
    beam_width=ridge_high.x-ridge_low.x
    beam_depth=ridge_high.z-ridge_low.z
    for label,x in [('Front',chord_low.x),('Rear',chord_high.x)]:
        beam=prism(f'Detail | {label} roof bearing beam',(x,start-.10,0),(x,end+.10,0),
                   beam_width,chord_low.z-beam_depth,chord_low.z,False)
        beam.data.materials.clear();beam.data.materials.append(ridge.data.materials[0])
    bpy.context.view_layer.update()
    actual=sorted((sum(bounds(o),Vector((0,0,0)))/2).y for o in scene.objects if o.name.startswith('V3 | Roof truss ') and o.name.endswith('bottom chord'))
    assert len(actual)==8
    gaps=[b-a for a,b in zip(actual,actual[1:])]
    assert max(gaps)-min(gaps)<.00001
    assert not any(o.name.startswith('V3 | RC footing pad ') for o in scene.objects)
    metadata={'truss_count':len(actual),'truss_centres_y':actual,'spacing':gaps[0],
              'strip_segments':len(outline)-1,'slab_exterior_followed':True,'bearing_beams':2,
              'bearing_beam_section':[beam_width,beam_depth],'section_matches_ridge':True,
              'scope':'Illustrative geometry; member sizes and load capacity are not engineered.'}
    (HERE/'structure-revision.json').write_text(json.dumps(metadata,indent=2))
    print('STRUCTURE_REVISION',metadata,flush=True)

if __name__=='__main__':
    from export_web import export
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-detail-v4.blend'))
    build(bpy.context.scene)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    export(bpy.context.scene)
