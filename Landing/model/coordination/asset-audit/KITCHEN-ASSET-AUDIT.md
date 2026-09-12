# Supplied kitchen — quick audit

`kitchen.glb` is **Cucina Telaio con Gola — Italian Groove Kitchen**, by
**baldoVReal**, with embedded **CC-BY-4.0** metadata.
[Embedded source link](https://sketchfab.com/3d-models/cucina-telaio-con-gola-italian-groove-kitchen-9f8c7a62dcc54f0bb5238094f2822f8b).

The file is 11,186,068 bytes, with 58 mesh objects, 119,386 triangles and eight
textures. Objects are grouped by generic material IDs (`Object_2` etc.), rather than
named appliance assemblies. Reusing selected shapes is practical, but requires some
geometry separation and explicit provenance.

The imported bounds are approximately 3210 × 2470 × 2700 units. The kitchen's
recognisable cabinetry indicates millimetre-like source units: the derived copy uses
a 0.001 scale. The 2700-unit height includes a backdrop panel; the actual upper
cabinet height is approximately 2190 units. Scale is a modelling interpretation,
not a manufacturer-verified dimension.

## Visually confirmed

- L-shaped base cabinets, tall tower and overhead cabinets.
- Countertop with sink/drainer and a modelled mixer tap.
- Gas cooktop with modelled grates/burner details.
- Chimney range hood, including canopy.
- Tall appliance bays; some oven/microwave-looking fronts rely on image planes.
- Decorative plants, bottles/jars and shelving which add geometry but little
  value to the coordination story.

The minimum first fit uses supplied joinery, worktop, sink/tap, hob and hood,
removes decorative objects and replaces the ambiguous image-based appliance fronts.
The apartment supplies the separate fridge and double-door oven geometry; a simple
microwave is authored with actual housing, glass, controls and handle.

The user selected an all-electric kitchen. The first-fit scene replaces the source gas
hob with an authored induction surface and geometric cooking-zone markings. Circuit
and load design remain unassigned; no gas network is implied.

## Evidence and outputs

- `kitchen-a.png` / `kitchen-b.png`: source geometry previews, front and rear.
- `kitchen-inventory.json`: source objects, bounds, materials and triangle counts.
- `kitchen-source.blend`: imported source preserved for selective extraction.
- `audit_kitchen.py`: reproducible Blender audit.

All changes apply to derived scenes. The original GLB remains unchanged. Retain
source credits when delivering extracted geometry. This audit records the supplied
license metadata; it is not an external verification of that metadata.
