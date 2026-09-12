"""Export sparse floor and roof contours for the discipline tour."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rebuild_paired_roofs import roof_surface, height, simplify

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent / 'sitewise-compact-site-v18.blend'))
surface = roof_surface(bpy.context.scene)
houses = []
for i, (south, north) in enumerate([(-13.764,-9.193),(-6.993,-2.423),(-2.309,2.262),(4.462,9.032),(9.146,13.717)]):
    south += bpy.context.scene.get('sw_dwelling_y_offset', 0)
    north += bpy.context.scene.get('sw_dwelling_y_offset', 0)
    lines = []
    def edge(a, b):
        for x, y, z in (a, b):
            lines.extend([round(x,4), round(z,4), round(-y,4)])
    offset = -.3 if i >= 3 else 0
    for z in (.5, 3.22, 5.94, 8.39):
        corners = [(-4.8,south,z+offset),(4.7,south,z+offset),(4.7,north,z+offset),(-4.8,north,z+offset)]
        for j in range(4):
            edge(corners[j], corners[(j+1)%4])
    for x in (-4.8,4.7):
        for y in (south,north):
            edge((x,y,.5+offset),(x,y,8.39+offset))
    for y in (south+.08,north-.08):
        points=[]
        for j in range(121):
            x=-4.75+9.4*j/120
            try:
                points.append(Vector((x,y,height(surface,x,y))))
            except AssertionError:
                continue
        for a,b in zip(simplify(points,.06),simplify(points,.06)[1:]):
            edge(a,b)
    for x in (-4.75,.18,4.65):
        points=[]
        for j in range(81):
            y=south+.08+(north-south-.16)*j/80
            try:
                points.append(Vector((x,y,height(surface,x,y))))
            except AssertionError:
                continue
        profile=simplify(points,.06)
        for a,b in zip(profile,profile[1:]):
            edge(a,b)
    houses.append(lines)
target=HERE.parents[3]/'frontend/public/landing-assets/coordination/dwelling-outlines.json'
target.write_text(json.dumps(houses,separators=(',',':')))
print('Exported outline segments:',sum(len(h)//6 for h in houses))
