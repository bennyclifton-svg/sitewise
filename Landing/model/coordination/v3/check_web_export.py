"""Validate the shipped scene's default presentation and discipline inventory."""
import json
import struct
from pathlib import Path

root = Path(__file__).resolve().parents[4]
with (root / 'frontend/public/landing-assets/coordination/sitewise-coordination.glb').open('rb') as stream:
    stream.seek(12)
    length, _ = struct.unpack('<II', stream.read(8))
    data = json.loads(stream.read(length))
assert len(data['scenes']) == 1
assert not any('carriageway' in n['name'].lower() for n in data['nodes'])
systems = set()
count = 0
for node in data['nodes']:
    system = node.get('extras', {}).get('sw_system')
    systems.add(system)
    if system == 'context' or 'mesh' not in node:
        continue
    for primitive in data['meshes'][node['mesh']]['primitives']:
        material = data['materials'][primitive['material']]
        assert 'Default' in material['name'], material['name']
    count += 1
assert systems >= {'architecture', 'interiors', 'structure', 'electrical', 'mechanical', 'hydraulic', 'civil', 'landscape'}
print(f'PASS: {count} chalk/glass development batches; eight disciplines; no street carriageway.')
