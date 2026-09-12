"""Generate a source-linked assembly census for coordination art direction."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = json.loads((ROOT / 'model-inventory.json').read_text())
prefixes = {'toilets': 'WC 24', 'basins': 'Basin 24', 'showers': 'Shower Cabin',
            'kitchen_sinks': 'Sink General', 'laundry_sinks': 'Mop Sink',
            'washing_machines': 'WashingMachine', 'cooktops': 'Cooktop',
            'named_downpipes': 'roof_downpipe'}
assemblies = {}
for kind, prefix in prefixes.items():
    groups = {}
    for row in rows:
        if row['name'].startswith(prefix):
            groups.setdefault(row['parents'][0], []).append(row)
    assemblies[kind] = []
    for name, parts in groups.items():
        lo = [min(p['min'][i] for p in parts) for i in range(3)]
        hi = [max(p['max'][i] for p in parts) for i in range(3)]
        assemblies[kind].append({'source_assembly': name,
            'source_meshes': [p['name'] for p in parts],
            'center_blender_world': [round((lo[i]+hi[i])/2, 4) for i in range(3)],
            'bounds_min': lo, 'bounds_max': hi})
result = {'source': 'duplex.glb', 'source_title': 'Duplex houses at 22 ARNWOOD STREET MANUREWA',
          'author': 'MyStudioNZ', 'license_from_embedded_metadata': 'CC-BY-4.0',
          'source_url': 'https://sketchfab.com/3d-models/duplex-houses-at-22-arnwood-street-manurewa-ef88f585f3d045c89c849ddd64495ad5',
          'mesh_count': len(rows), 'imported_vertex_count': sum(r['vertices'] for r in rows),
          'counts': {k: len(v) for k, v in assemblies.items()},
          'assemblies': assemblies,
          'limitations': ['Assembly counts are inferred from imported object names, not a verified quantity survey.',
                         'Dimensions use imported coordinates; survey scale has not been independently verified.',
                         'No approved engineering or planning documents supplied.',
                         'Five dwellings inferred from kitchens and appliances; verify against drawings before factual publication.']}
(ROOT / 'coordination' / 'source-census.json').write_text(json.dumps(result, indent=2))
print(json.dumps({k: v for k, v in result.items() if k != 'assemblies'}, indent=2))
