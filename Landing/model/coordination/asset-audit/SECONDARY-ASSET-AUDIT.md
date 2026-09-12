# Apartment and car source audit

Audited 2026-09-08 by parsing GLB JSON and importing copies into Blender 5.1.2.
The source GLBs and existing development scenes were not modified. Preview
images use Blender Workbench; they show asset geometry, not final lighting.

## Interior source

`interior-design.glb`: **Modern Apartment**, author **Visthétique**.
Embedded metadata records **CC-BY-4.0** and this source:
https://sketchfab.com/3d-models/modern-apartment-1fbb649cd6624f2bb7b7d6e30c6533a5

- File: 209,556,540 bytes; 241 mesh primitives; 2,991,575 triangles;
  101 materials; 85 embedded images (44,801,312 bytes).
- Imported dimensions: 20.844 × 8.249 × 3.163 metres. The individually measured
  appliances appear to use a plausible metre scale.
- No animation and no exported punctual light objects. Luminous material
  geometry exists, but real scene light emitters and electrical connections
  still need adding.

### Confirmed reusable objects

| Source group | Geometry confirmed | Triangles | Integration note |
| --- | --- | ---: | --- |
| `Refrigator.001` | Fridge/freezer | 19,237 | 0.698 × 0.704 × 1.823 m; separate group |
| `Hobs.001` | Flat cooktop | 157 | 0.879 × 0.582 m; cooking markings rely on material/texture and need geometric detail for chalk treatment |
| `Hood` | Chimney range hood, light component | 36,238 | 1.294 × 0.908 × 0.874 m; resize to target kitchen deliberately |
| `Oven.001` | Oven assembly with two doors and controls | 2,699 | 0.698 × 0.646 × 0.985 m; separate group |
| `Sink` | Sink, drainer and tap | 23,269 | 0.951 × 0.474 × 0.530 m including tap |
| `Dishwasher.001` | Dishwasher | 987 | 0.660 × 0.612 × 0.857 m; useful water/waste/electrical endpoint |
| `DiningTable.001` | Table, six chairs, two globe pendants | 37,158 | Pendants share material meshes with furnishings; separate loose components before reuse |
| `Curtatins` | Full-height curtains | 62,794 | Several windows are combined across a 19.676 m span; extract one set and fit to target opening |
| `Zebra Curtains` | Window blinds | 7,150 | Combined across several windows; extract one set |
| `Bed` | Bed with pillows/bedding | 136,986 | Useful optional bedroom focal detail; simplify before replication |
| `CouchSet` | Sofa, armchairs and living-area accessories | 178,731 | Extract sofa/cushions only; avoid importing all decor |
| `BedroomRug` | Rug | 8,448 | Optional; not needed for service explanation |
| `ElectricPlugs` | Socket/plug detail | 12,005 | Many positions combined; select one reusable unit |

Also present: washer/dryer, bathroom fittings, wardrobes, bookcase, desk and
small decorative lamps in `BedDecors` and `OficeDecors`. No independently named
or visually verified microwave was found. A simple explicitly authored microwave
is preferable to assuming an oven door is a microwave.

Recommended minimum extract: needed appliances, one sofa, one curtain pair,
two globe pendants; add simple repeatable downlights. Avoid transplanting the
whole apartment or its architectural shell. Appliance selection above totals
82,587 source triangles before simplification/material consolidation.

Evidence: [inventory](interior-design-audit.json),
[furnishing overview](interior-furnishings-overview.png),
[appliance extract](interior-kitchen-appliances.png),
[dining and pendants](interior-dining-pendants.png).

## Car source

`car.glb`: **Land Rover Defender - Edition Grasmere Green**, author
**PROJECT CAR90**. Embedded metadata records **CC-BY-4.0** and this source:
https://sketchfab.com/3d-models/land-rover-defender-edition-grasmere-green-b7596dc0abc749c3b076d1f830715a54

- File: 25,059,360 bytes; 151 mesh primitives; 681,239 triangles;
  16 materials; two images (133,099 bytes); no animations.
- Detailed complete vehicle suitable for illustrative driveway movement.
- Two source components, `Object_291` and `Object_292`, sit approximately
  100 m away. Their combined 44,336 triangles are excluded from the audit
  preview only. Exclude them from any working vehicle collection.
- Main vehicle imported bounds: **9.798 m long × 4.120 m wide × 3.955 m high**.
  Normalize its scale and ground contact before siting. A 0.5 uniform scale
  would produce an illustrative 4.899 × 2.060 × 1.978 m vehicle; these are
  scaled model measurements, not verified manufacturer dimensions.
- Four tyres are separate meshes: `Object_34`, `Object_38`, `Object_40`,
  `Object_42`, each using `Borracha_.001`. This supports wheel rotation and
  steering after grouping tyre/rim components and creating correct pivots.
  There is no ready-made car rig.
- Simplify geometry, consolidate chalk materials, then build a reversible
  driveway path animation. A visual animation alone does not establish a
  compliant swept path or parking provision.

Evidence: [inventory](car-audit.json), [vehicle preview](car-overview.png).

## Attribution record

Keep each source author, title, source URL, embedded license statement and a
record of modifications with downstream extracts. This audit records supplied
metadata; no external license verification was performed.
