# Focus-dwelling geometry audit

Read from `sitewise-kitchen-checkpoint.blend`, without saving changes to that scene.
All coordinates below are in the existing kitchen's local U/V/Z frame, recorded in
`structure-audit-summary.json`; imported units are presumed metres from fixture scale.

| Level | Floor finish | Ceiling underside | Evidence |
| --- | ---: | ---: | --- |
| Ground | 0.50 / bedroom 0.51 | 2.92 | Existing ground slab, carpet and first-floor underside |
| Living | 3.22 | 5.64 | `SLA - 008` floor group and `SLA - 010...024` upper slab |
| Upper | 5.94 / wet rooms 5.95 | 8.39 | Carpet, tile and thin ceiling source meshes |

The ground slab occupies U[-5.3557,4.1243], V[-2.6252,1.9451], Z[0.20,0.50].
Its source ID is `SLA - 007_Concrete - Foundation_0.029`.
The living floor extends east to U4.5743; the adjoining balcony extends west to U-5.9399.
The upper floor's broad extent is U[-5.3059,4.8474], with actual stair and wet-room voids.
These extents must not be substituted for filled rectangular slabs.
The plaster objects own slab undersides/sides; separate finish meshes own many top faces.

The source contains 32 tall plaster wall runs in this dwelling. Their centre lines,
extents and Z ranges are recorded individually with 34 detected void bands.
Of those bands, two describe the stair slope and one is a small ceiling notch.
Those three are explicitly marked separately from door/window voids.
Frame generation should use actual wall solid intervals to preserve the sloped stair profile.

The roof is a 15-degree gable, ridge parallel to V at U-0.3658.
The underside ridge is Z9.7187; west/east eave underside is approximately Z8.38/8.37.
Measured underside planes are Z=0.2679U+9.8167 and Z=-0.2679U+9.6207.
`RT - 024_Wall white plaster_0` and its `.001` partner are the sloped roof sheets.
`RT - 025_Wall white plaster_0.002` is part of the stair wall and is not roof framing.

Fixtures and furnishings remain source-linked in the JSON. Useful UV centres include:
dining (0.7485,0.7313), sofa (-2.3150,0.9121), ground bed (2.5590,-1.6112),
upper beds (3.0183,-1.6352) and (-3.6659,0.9551).
The PNG/SVG floor plans show actual mesh sections, door swings and fixture footprints.

Confidence is high for these measured mesh relationships and the roof pitch; room use
is inferred from furnishings. True foundation geometry, ground conditions, loads,
member sizing, structural wall roles and compliant details remain unverified.
Several tiny landscaping/step slabs also use the foundation material and are excluded
from the proposed building foundation system.
