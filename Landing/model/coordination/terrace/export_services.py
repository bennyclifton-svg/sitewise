"""Measured source bounds for reversible viewer service corrections."""
import json, struct, re
from pathlib import Path
HERE = Path(__file__).parent
ROOT = HERE.parents[3]
f = (HERE / 'option-7/terrace-7.glb').open('rb')
f.read(12); size, _ = struct.unpack('<II', f.read(8)); doc = json.loads(f.read(size))
routes = json.loads((HERE / 'option-7/service-routes.json').read_text())
actions, anchors = [], []
remove = r'^Street$|Underground electricity service|Downpipe|LED downlight|Double socket|lighting circuit|power radial|dedicated circuit|Supply air trunk|Bathroom extract duct|Dedicated kitchen exhaust|Cold branch|Hot branch|Fixture waste branch|Pit stormwater connection|Shared rainwater detention tank|Tank access lid|Detention inlet|Detention overflow'
context = r'Site ground|Public footpath|Street$|Kerb|Driveway crossover|Garage approach|Entry walk|Wheelie bin'
for node in doc['nodes']:
    if 'mesh' not in node: continue
    e = node.get('extras', {}); name = node.get('name', ''); h = e.get('sw_dwelling', 0); system = e.get('sw_system', '')
    label = name.split(' | ')[-1]
    for pr in doc['meshes'][node['mesh']]['primitives']:
        a = doc['accessors'][pr['attributes']['POSITION']]
        lo, hi = a['min'], a['max']
        item = dict(name=name, house=h, system=system, material=doc['materials'][pr['material']]['name'], minimum=lo, maximum=hi)
        if label in ('Meter cabinet', 'Distribution board', 'Electrical riser') or re.search(remove, label) or (h == 0 and label.startswith('Rear timber paling fence')):
            actions.append(dict(item, action='remove', memberships=[]))
        elif label.startswith(('Water street main', 'Electric street conduit')):
            actions.append(dict(item, action='split', memberships=['hydraulic' if label.startswith('Water') else 'electrical']))
        elif re.search(context, label): actions.append(dict(item, action='context', memberships=[system]))
        elif label.startswith(('Eaves gutter', 'Downpipe', 'Balcony drain', 'Rear balcony drainage')):
            actions.append(dict(item, action='split', memberships=['civil']))
        elif label.startswith(('Rangehood', 'AC outdoor condenser', 'Heat pump water heater')):
            actions.append(dict(item, action='split', memberships=[system, 'electrical']))
        if h == 1 and re.search(r'Oven$|Induction cooktop|Refrigerator|Washing machine|Rangehood|Switch plate|Smoke alarm', label):
            anchors.append(dict(name=label, point=[round((x+y)/2,5) for x,y in zip(lo,hi)]))
source = [dict(name=r['name'].split(' | ')[-1], points=[[p[0],p[2],-p[1]] for p in r['points']], radius=r['radius']) for r in routes if r['name'].startswith('TH01') and any(s in r['name'] for s in ['Supply air trunk', 'Dedicated kitchen exhaust'])]
(ROOT / 'frontend/src/landing/terrace-services-data.json').write_text(json.dumps(dict(actions=actions, anchors=anchors, routes=source), separators=(',', ':')))
print('Exported', len(actions), 'measured corrections and', len(anchors), 'equipment anchors')
