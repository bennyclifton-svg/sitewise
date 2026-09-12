import json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[4]
p=root/'frontend/public/landing-assets/coordination/sitewise-coordination.glb'
with p.open('rb') as f:
 f.seek(12)
 length,_=struct.unpack('<II',f.read(8))
 data=json.loads(f.read(length))
materials={m['name'] for m in data['materials']}
assert {'Facade | Warm limestone','Facade | Satin bronze','Facade | Balcony oak','Facade | Mineral inset'} <= materials
systems={n.get('extras',{}).get('sw_system') for n in data['nodes']}
assert systems >= {'architecture','structure','interiors','electrical','mechanical','hydraulic','civil','landscape'}
assert any(n.get('extras',{}).get('sw_motion')=='car' for n in data['nodes'])
assert any(str(n.get('extras',{}).get('sw_motion','')).startswith('rotor:') for n in data['nodes'])
audit=json.loads((Path(__file__).parent/'facade-revision.json').read_text())
assert len(audit['windows'])==58 and audit['preserved_meshes']==4990
assert {r['treatment'] for r in audit['windows']}=={'shallow surround','horizontal blade','quiet reveal'}
print('PASS: facade materials, three window treatments, eight disciplines, vehicle and rotor metadata; 4990 source meshes preserved.')
