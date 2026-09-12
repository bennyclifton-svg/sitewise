"""Highlight the incoming shared utility networks with the sample house."""
import bpy,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from export_web import export
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'sitewise-solid-foundations-v20.blend'))
scene=bpy.context.scene
route_prefixes=('WAT-main-','WAT-street-to-boundary','WAT-meter','WAT-site-main-','SAN-main-','SAN-street-branch','SAN-site-collector')
power_names=('Street conductor ','Pole service cable to protected riser','Protected pole riser','Underground street service to site pillar','Site electricity pillar','Site pillar access panel')
names=[]
for obj in scene.objects:
    if obj.hide_render:continue
    route=str(obj.get('sw_route_id',''))
    if route.startswith(route_prefixes) or (obj.name.startswith('V3 | Electrical | ') and any(s in obj.name for s in power_names)) or obj.name in ('V3 | Potable meter enclosure','Development | Shared sanitary collector'):
        obj['sw_reveal_dwelling']=2;names.append(obj.name)
assert any('Street conductor' in n for n in names)
assert any('SAN-main-' in n for n in names) and any('WAT-main-' in n for n in names)
scene['sw_utility_highlight_v21']=json.dumps(names)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent/'sitewise-connected-mains-v21.blend'))
(HERE/'connected-mains-v21-audit.json').write_text(json.dumps(names,indent=2))
export(scene)
print('CONNECTED_MAINS_PASS',len(names),flush=True)
