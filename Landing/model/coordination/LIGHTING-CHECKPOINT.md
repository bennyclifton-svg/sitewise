# Checkpoint 02 — lighting and restrained interior detail

8 September 2026. Continues the user-approved kitchen fit and all-electric assumption.

## Added

- A repeatable chalk downlight family across the focus dwelling's three occupied levels.
- Two extracted globe pendants over the existing dining table, with their drop fitted to the measured ceiling.
- One open curtain pair at the actual west-bedroom window. The central sheer is omitted so the opening stays visible.
- A slightly darker chalk textile on the source beds and sofa, retaining the existing furniture layout.
- Separate collections for visible fittings and presentation light sources. Each luminaire has an ID, room and electrical endpoint for the later service routes.
- 24 wall-hosted Australian/NZ double GPOs in the assembled interior checkpoint, covering all rooms with additional bedside and general worktop points.

The kitchen appliances and layout remain as approved. Original architectural transforms and openings are retained. The source GLBs are unchanged.

## Geometry and scope

The source model gives ground slab top Z 0.50 (bedroom finish 0.51), living floor 3.22 and upper floor 5.94. Measured ceiling undersides are 2.92, 5.64 and 8.39. These coordinates anchor the fixtures; they are not a lighting or engineering specification.

The curtains come from `interior-design.glb`, source groups `Curtatins_Black_0` and `Curtatins_White1_0`, Visthétique, CC-BY-4.0. The extract retains two outer panels and a rail; width and drop are adjusted to `WD - 006_Paint - Glossy White_0.035`. The pendants are extracted from `DiningTable.001` in the same asset. Detailed extraction manifests are in `asset-audit/`.

Light intensity and color are for presentation. Electrical circuits, switching, loads and photometric performance remain unassigned. Fittings in wet areas remain illustrative rather than specified products.

## Outputs

- `sitewise-lighting-checkpoint.blend` — full assembled development plus the fitted focus dwelling.
- `13-dining-lighting.png` — dining/kitchen close-up.
- `14-bedroom-lighting.png` — bedroom curtain and lighting close-up.
- `lighting-checkpoint.json` — named luminaire positions, room assignments and source provenance.
- `../build_lighting_checkpoint.py` — reproducible build from the approved kitchen scene.

Verified: all 26 luminaire mounts hit source ceiling geometry at nine sampled points; all 24 GPOs hit their host wall at five sampled points; curtain/source intersections were corrected and the final check found none. These are model-placement checks, not a code or electrical design assessment.

The user's later structural correction is reinforced-concrete columns and slabs. The timber prototype is superseded and remains a separate archived study for now; no immediate rebuild was requested. Next: fixture-anchored services, then the remaining site, car and fly-through checkpoints.
