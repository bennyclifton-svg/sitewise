"""Editable presentation-model revision for the second dwelling's exposed view."""
import bpy
import json
import re
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from replicate_dwellings import bounds
from export_web import export

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-satin-white-v15.blend'))
scene = bpy.context.scene
audit = dict(removed_planters=[], structural_stairs=[], landscape=[], removed_trusses=[], moved_unit=[])
for obj in list(scene.objects):
    if obj.hide_render or obj.type not in ('MESH', 'CURVE'):
        continue
    if obj.type == 'MESH' and not obj.data.vertices:
        continue
    if re.match(r'Premium \| Balcony \d+ (planter |soil|fine planting)', obj.name):
        audit['removed_planters'].append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
        continue
    if obj.name.startswith('Garden | Townhouse 2 ') and any(s in obj.name for s in ('deck', 'awning', 'tree')):
        obj['sw_landscape_dwelling'] = 2
        audit['landscape'].append(obj.name)
    lo, hi = bounds(obj)
    # Source stairs are individual carpet/lino tread solids, not named stair objects.
    if obj.name.startswith(('SLA - 010_Render: Carpet', 'SLA - 010_Lino')) and .12 < hi.z-lo.z < .35 and hi.x-lo.x < 1.5 and hi.y-lo.y < 1.5:
        obj['sw_system'] = 'structure'
        obj['sw_component'] = 'stair'
        audit['structural_stairs'].append(obj.name)
    if re.match(r'Roof v13 \| TH02 \| Truss [56] ', obj.name):
        audit['removed_trusses'].append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)

unit_labels = ('Roof void air handling unit', 'Supply plenum', 'Return air filter box', 'Condensate tray')
unit_parts = [o for o in scene.objects if o.name.startswith('TH02 | Detail | ') and any(o.name.endswith(s) for s in unit_labels)]
assert len(unit_parts) == 4
for obj in unit_parts:
    if obj.name.endswith('Supply plenum'):
        obj.data = obj.data.copy()
        lo, hi = bounds(obj)
        inverse = obj.matrix_world.inverted()
        for v in obj.data.vertices:
            p = obj.matrix_world @ v.co
            p.x = lo.x + (p.x-lo.x)*.6
            v.co = inverse @ p
    obj.location.x += 1.02
    obj.location.y += .5
    obj['sw_coordination_revision'] = 'Moved 0.5 m toward shared party wall into truss service bay'
    audit['moved_unit'].append(obj.name)

# Keep connected ducts and pipe endpoints attached while retaining the room outlets.
for obj in scene.objects:
    if obj.hide_render or not obj.name.startswith('TH02 | Detail | ') or obj in unit_parts:
        continue
    if not any(s in obj.name for s in ('Flexible supply', 'reinforcing rib', 'Return air flexible', 'refrigerant', 'Condensate')):
        continue
    obj.data = obj.data.copy()
    inverse = obj.matrix_world.inverted()
    def shift(co):
        p = obj.matrix_world @ Vector(co[:3])
        dx=max(-.8-p.x, 0, p.x-1.5)
        dy=max(-5.12-p.y, 0, p.y+4.14)
        dz=max(8.5-p.z, 0, p.z-9.08)
        weight=max(0, 1-(dx*dx+dy*dy+dz*dz)**.5/.9)
        p.x += (1.02-.2*min(1,max(0,(p.x-.95)/.5)))*weight
        p.y += .5*weight
        return inverse @ p
    if obj.type == 'MESH':
        for v in obj.data.vertices: v.co = shift(v.co)
    elif obj.type == 'CURVE':
        for spline in obj.data.splines:
            for p in spline.points: p.co = (*shift(p.co), p.co.w)
            for p in spline.bezier_points:
                p.handle_left=shift(p.handle_left); p.handle_right=shift(p.handle_right); p.co=shift(p.co)

bpy.context.view_layer.update()
tray = scene.objects['TH02 | Detail | Condensate tray']
lo, hi = bounds(tray)
ties = [o for o in scene.objects if o.name.startswith('Roof v13 | TH02 | Truss ') and o.name.endswith('bottom tie')]
centres = sorted((bounds(o)[0].y+bounds(o)[1].y)/2 for o in ties)
assert len(centres) == 6
assert not any(lo.y-.10 < y < hi.y+.10 for y in centres)
audit['truss_centres_y'] = centres
audit['unit_bay_clearance_m'] = [lo.y-max(y for y in centres if y<lo.y)-.033, min(y for y in centres if y>hi.y)-hi.y-.033]
assert audit['removed_planters'] and audit['structural_stairs'] and audit['landscape']
scene['sw_exposed_revision'] = json.dumps(audit)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-exposed-v16.blend'))
(HERE/'exposed-dwelling-audit.json').write_text(json.dumps(audit, indent=2))
export(scene)
print('EXPOSED_REVISION', {k:len(v) if isinstance(v,list) else v for k,v in audit.items()}, flush=True)
