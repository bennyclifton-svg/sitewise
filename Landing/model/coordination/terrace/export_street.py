"""Extract existing service endpoints and scene anchors for the landing presentation."""
import json
import struct
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
with (HERE / 'option-7/terrace-7.glb').open('rb') as stream:
    stream.read(12)
    length, _ = struct.unpack('<II', stream.read(8))
    document = json.loads(stream.read(length))
routes = json.loads((HERE / 'option-7/service-routes.json').read_text())


def world(point):
    return [round(point[0], 5), round(point[2], 5), round(-point[1], 5)]


def route(house, label):
    return next(item for item in routes if item['name'] == f'TH{house:02} | {label}')


homes = []
for house in range(1, 8):
    electric = route(house, 'Underground electricity service')
    water = route(house, 'Water service')
    sewer = route(house, 'Sanitary lateral')
    front = route(house, 'Downpipe')
    rear = route(house, 'Downpipe.001')
    homes.append(dict(house=house, power=world(electric['points'][0]), board=world(electric['points'][-1]),
        water=world(water['points'][0]), coldRiser=world(water['points'][-1]),
        sewer=world(sewer['points'][-1]), frontDrain=world(front['points'][-1]),
        rearDrain=world(rear['points'][2])))

trees, doors, replacements = [], [], []
for node in document['nodes']:
    name, extras = node.get('name', ''), node.get('extras', {})
    if 'mesh' not in node:
        continue
    for primitive in document['meshes'][node['mesh']]['primitives']:
        position = document['accessors'][primitive['attributes']['POSITION']]
        minimum, maximum = position['min'], position['max']
        centre = [(a + b) / 2 for a, b in zip(minimum, maximum)]
        if 'Natural tree trunk' in name:
            trees.append(dict(house=extras['sw_dwelling'], base=[centre[0], minimum[1], centre[2]], rear=centre[2] < -9))
        if 'White single entry door' in name:
            doors.append(dict(house=extras['sw_dwelling'], point=[maximum[0] + .18, 2.3, maximum[2] + .15]))
        if any(label in name for label in ('Sewer street main', 'Stormwater street main', 'Water service')):
            replacements.append(dict(house=extras['sw_dwelling'], system=extras['sw_system'], minimum=minimum, maximum=maximum,
                material=document['materials'][primitive['material']]['name']))

assert len(trees) == 14 and len(doors) == 7 and len(homes) == 7
data = {'homes': homes, 'trees': trees, 'doors': doors, 'replacements': replacements}
(ROOT / 'frontend/src/landing/terrace-street-data.json').write_text(json.dumps(data, indent=2))
counts = Counter(item['system'] for item in routes)
summary = {
    'scope': 'Illustrative landing-model inventory and street tie-in audit; not an engineering/clash certification.',
    'source_routes': dict(counts), 'source_route_total': len(routes),
    'homes_with_power_water_sewer_and_front_rear_downpipes': len(homes),
    'water_meter_box_source_count': sum('Water meter box' in node.get('name', '') for node in document['nodes']),
    'existing_stormwater_main_diameter_m': .30,
    'presentation_stormwater_main_diameter_m': .40,
    'presentation_sewer_centre_elevation_m': -1.9,
    'findings': [
        'All seven dwelling sanitary and electricity laterals already reach their original street mains.',
        'Stormwater downpipe ends and pit laterals have about 60 mm lateral separation; explicit connecting branches are added.',
        'Water service lines bypass any above-ground meter; seven connected meter loops are added beside the front enclosures.',
        'Rear downpipes previously ran to front drainage without individual rear pits; seven rear pits are added.',
        'Existing building services are retained. New sewer drops tie original laterals into the lower street main.',
        'New overhead power connects two poles, a pole riser, a front pillar and the existing electricity distribution conduit.',
    ],
}
(HERE / 'street-services-audit.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary))
