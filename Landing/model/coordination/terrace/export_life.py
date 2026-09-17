"""Extract existing vehicle and measured opening bounds for the static lived-in scene."""
import copy
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'frontend/public/landing-assets/coordination'


def read_glb(path):
    with path.open('rb') as stream:
        stream.read(12)
        size, _ = struct.unpack('<II', stream.read(8))
        document = json.loads(stream.read(size))
        size, _ = struct.unpack('<II', stream.read(8))
        return document, stream.read(size)


def vehicle_subset():
    source, binary = read_glb(PUBLIC / 'sitewise-coordination.glb')
    assert not source.get('images'), 'Vehicle extraction expects the existing untextured web asset'
    nodes = [copy.deepcopy(node) for node in source['nodes'] if node.get('extras', {}).get('sw_motion') == 'car']
    assert nodes, 'Existing vehicle is missing'
    meshes, accessors, views = [], [], []
    accessor_map, view_map = {}, {}
    output = bytearray()

    def view(index):
        if index not in view_map:
            item = copy.deepcopy(source['bufferViews'][index])
            start = item.get('byteOffset', 0)
            data = binary[start:start + item['byteLength']]
            item.update(buffer=0, byteOffset=len(output))
            output.extend(data)
            output.extend(b'\0' * (-len(output) % 4))
            view_map[index] = len(views)
            views.append(item)
        return view_map[index]

    def accessor(index):
        if index not in accessor_map:
            item = copy.deepcopy(source['accessors'][index])
            assert 'sparse' not in item
            if 'bufferView' in item:
                item['bufferView'] = view(item['bufferView'])
            accessor_map[index] = len(accessors)
            accessors.append(item)
        return accessor_map[index]

    for node in nodes:
        mesh = copy.deepcopy(source['meshes'][node['mesh']])
        for primitive in mesh['primitives']:
            primitive['attributes'] = {key: accessor(value) for key, value in primitive['attributes'].items()}
            if 'indices' in primitive:
                primitive['indices'] = accessor(primitive['indices'])
            draco = primitive.get('extensions', {}).get('KHR_draco_mesh_compression')
            if draco:
                draco['bufferView'] = view(draco['bufferView'])
        node['mesh'] = len(meshes)
        node['extras'] = {'sw_system': 'civil', 'sw_dwelling': 3, 'sw_life': 'parked-car'}
        meshes.append(mesh)
    document = dict(asset=source['asset'], scene=0, scenes=[{'nodes': list(range(len(nodes)))}],
                    nodes=nodes, meshes=meshes, materials=source['materials'], accessors=accessors,
                    bufferViews=views, buffers=[{'byteLength': len(output)}])
    for key in ('extensionsUsed', 'extensionsRequired'):
        if key in source:
            document[key] = source[key]
    encoded = json.dumps(document, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    result = struct.pack('<III', 0x46546C67, 2, 28 + len(encoded) + len(output))
    result += struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
    result += struct.pack('<II', len(output), 0x004E4942) + output
    (PUBLIC / 'terrace-car.glb').write_bytes(result)
    print(f'Existing vehicle: {len(nodes)} parts, {len(result)} bytes')


document, _ = read_glb(Path(__file__).parent / 'option-7/terrace-7.glb')
openings, blinds = [], []
for node in document['nodes']:
    name, extras = node.get('name', ''), node.get('extras', {})
    house = extras.get('sw_dwelling', 0)
    garage = house in (3, 6) and ('Garage sectional door' in name or 'Garage horizontal joint' in name)
    entry = house == 1 and ('White single entry door' in name or 'Entry handle' in name)
    window = house != 5 and ('Loggia sliding door glass' in name or 'Boxed roof dormer glass' in name or 'Tall stair window glass' in name)
    if not (garage or entry or window):
        continue
    assert not any(key in node for key in ('matrix', 'translation', 'rotation', 'scale'))
    for primitive in document['meshes'][node['mesh']]['primitives']:
        position = document['accessors'][primitive['attributes']['POSITION']]
        item = dict(house=house, minimum=position['min'], maximum=position['max'])
        if garage or entry:
            openings.append(dict(item, kind='garage' if garage else 'entry'))
        else:
            # Fixed variation: open, half drawn and fully drawn, differing by floor.
            pattern = [0, .5, 1, .3, .75, 0, 1]
            offset = 2 if 'dormer' in name else 1 if 'stair' in name else 0
            blinds.append(dict(item, closed=pattern[(house - 1 + offset) % len(pattern)]))
rear_blades = []
for node in document['nodes']:
    if 'Shared full-height rear privacy wall' not in node.get('name', ''):
        continue
    for primitive in document['meshes'][node['mesh']]['primitives']:
        position = document['accessors'][primitive['attributes']['POSITION']]
        rear_blades.append(dict(house=0, kind='rear-blade', minimum=position['min'], maximum=position['max']))
assert len(rear_blades) == 6

cutaway_finishes = []
finish_names = ('plasterboard', 'drywall', 'ceiling', 'bulkhead', 'lining',
                'privacy wall', 'door head', 'door open', 'door leaf open', 'garage side separation',
                'ground powder side', 'upper bathroom side', 'laundry side', 'plant access hatch')
for node in document['nodes']:
    extras, name = node.get('extras', {}), node.get('name', '')
    if extras.get('sw_dwelling') != 5:
        continue
    system = extras.get('sw_system')
    interior = system == 'interiors' and any(word in name.lower() for word in (*finish_names, 'curtain', 'pleated linen', 'robe'))
    partition = system == 'structure' and any(word in name.lower() for word in ('timber stud', 'top plate')) and any(word in name for word in ('Garage rear separation', 'Ground powder', 'Upper bathroom', 'Bed 3 entry', 'Bed 4 entry', 'Laundry entry', 'Bed 2 entry', 'Master suite entry'))
    if not (interior or partition):
        continue
    assert not any(word in name.lower() for word in ('stair screen', 'stair handrail', 'appliance', 'cabinet', 'rafter', 'roof post'))
    for primitive in document['meshes'][node['mesh']]['primitives']:
        position = document['accessors'][primitive['attributes']['POSITION']]
        cutaway_finishes.append(dict(house=5, kind='finish', name=name, system=system,
            material=document['materials'][primitive['material']]['name'],
            minimum=position['min'], maximum=position['max']))
assert len(cutaway_finishes) > 40

target = ROOT / 'frontend/src/landing/terrace-life-data.ts' 
target.write_text('// Generated by Landing/model/coordination/terrace/export_life.py.\n'
    'export type Opening = { house: number; minimum: [number, number, number]; maximum: [number, number, number]; kind: string }\n'
    'export type Finish = Opening & { name: string; material: string; system: string }\n'
    'export type Blind = Omit<Opening, "kind"> & { closed: number }\n'
    f'export const openings: Opening[] = {json.dumps(openings)}\n'
    f'export const blinds: Blind[] = {json.dumps(blinds)}\n'
    f'export const rearBlades: Opening[] = {json.dumps(rear_blades)}\n'
    f'export const cutawayFinishes: Finish[] = {json.dumps(cutaway_finishes)}\n')
vehicle_subset()
print(f'Measured {len(openings)} door parts and {len(blinds)} window openings')

print(f'Measured {len(cutaway_finishes)} removable unit-5 wall, ceiling and service-enclosure finishes')
