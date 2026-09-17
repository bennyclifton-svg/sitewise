# Detached housing study

Four separate street lots, using the user-supplied `L09 CC Plans.pdf` as the
architectural reference. House three is the blue cutaway. The existing terrace
model, its viewer bundle and landing-page integration are untouched by this work.

## Reference and interpretation

Reference path: `D:/AI Projects/Test Data/Newham Kit/L09 CC Plans.pdf`.
Read sheets 2–8: site, ground floor, first floor, four elevations and sections.
The source PDF remains outside the public web assets.

The source establishes a two-storey, four-bedroom house with a double garage,
front balcony, multi-purpose room, kitchen and walk-in pantry, family and dining
spaces, laundry, WC, upper sitting area, bathroom, ensuite and walk-in robe.
The area schedule totals 225.84 m², including covered external spaces and garage.
The source has 2.750 m ground and 2.450 m upper ceiling heights, a 3.070 m
floor-to-floor rise, an 86 mm garage setdown and a 25-degree main tiled hip roof.
The model uses a local ground-floor datum of 0.310 m rather than the source survey RL.

The four-lot repetition is an illustrative arrangement authorised by the user,
not the source subdivision. Architectural geometry is a first review study:
overall form and programme follow the reference; room coordinates, openings,
stair geometry and lower-roof junctions need a dimension-by-dimension fidelity
pass before this is treated as a finished copy. Source dimensions and preliminary
room placements are in `frontend/src/landing/detached-layout.ts`.

The services, foundation sizes, furniture and landscaping are schematic additions.
They are not extracted engineering designs. Equipment sits in the garage and
electrical feeds rise overhead rather than crossing the entrance.

## Controlled variation

1. Weatherboard pair: two upper windows, brick piers through the balcony to balustrade height, timber posts above and pillar letterbox.
2. Fine battens: mirrored lot with its garage beside house one, full-height lightweight front and garage-side upper return, with supported walls and garage parapet retained as brick, three upper windows, glazed entry panel and post-mounted letterbox.
3. Rendered pair: two upper openings, wider baluster spacing and brick-pier letterbox; exposed framing/interiors/services remain blue.
4. Masonry base: three upper windows, rendered walls, stone-clad columns to roof height, framed fascia and wide letterbox.

The supplied facade photographs inform a projecting balcony hip and stepped
garage-side eave with a 450 mm overhang. One joined roof surface replaces the
simple main hip; the rear slopes and floor plans remain unchanged. Upper-front
finishes and window openings vary independently of side and rear elevations.

All houses share one procedural definition. No four separate model-maintenance
paths, new dependencies, or copied GLB assets. Geometry is batched by discipline,
house and material behaviour using the existing batching and brickwork helpers.

## Separate review preview

- Page: `frontend/public/detached-study.html`
- Entry: `frontend/src/landing/detached-viewer.ts`
- Model: `detached-house.ts`, `detached-services.ts`, `detached-scene.ts`
- Build from `frontend/`: `node node_modules/vite/bin/vite.js build --config vite.detached.config.ts`
- Test: `pnpm test -- src/landing/detached-scene.test.ts`

The intended future plinth toggle will choose a scheme factory and its cutaway
house. It is deliberately not added to the existing landing page at this stage.
Industrial and commercial fit-out schemes are deferred.

## Elevation detailing pass

Compared again with sheets 5–8. Wall finishes now split around each opening:
continuous ground-floor face-brick bases and corbels, rendered walls, and upper
horizontal cladding. The 320 mm floor edge is enclosed. The balcony has side
returns, full-height posts, a soffit and the 650 mm moulded fascia from detail D01.
The main hip extends over the balcony, with ridge/hip caps and fascia, while the
garage has a 3-degree roof and raised rendered parapet. Tile joints, fine render
grain and cladding courses retain their material identity through detached-only
batching. Window glass and tall-window transoms are distinct from the wall finish.

Trees now have branches, twigs and individual leaves. Front beds, edging, strappy
groundcover, paving and letterboxes are illustrative landscape additions.
Raycast regression checks cover the door, upper glazing and floor-edge junction.

Roof detailing uses rectangular timber trusses, folded metal hip/ridge caps and
open half-round gutter profiles. Downpipes offset back to walls; the upper
garage outlet terminates at a spreader on the lower roof. Main and rear roofs
have continuous ceiling/eave linings, omitted on the blue cutaway. Exterior
wall bases and porch piers extend to ground. Balcony borders are stepped brick
corbels instead of tubular mouldings.

## Front elevation refinement — 13 September 2026

Front-view review found that repeated garage panels, thin window frames and
similar balcony rails overwhelmed the existing material variation. The shared
`detached-facade-details.ts` now adds five refinements to every house:

1. Deep window jambs and heads, projecting sills and underside drip edges.
2. Framed entry portals, thresholds and wall light fittings.
3. Individually jointed porch soffit boards, perimeter trims and recessed lights.
4. Deep garage reveals and head flashings, with modelled door joinery.
5. Pier caps and foot courses, plus a balcony drip edge.

Five elements differentiate the elevations without changing the floor plans:

| Element | House 1 | House 2 (mirrored) | House 3 | House 4 |
| --- | --- | --- | --- | --- |
| Window shading/heads | Bracketed hoods | Plain window frames | Broad canopies | Stone lintels |
| Balcony rails | Slender pickets, post collars | Paired pickets | Additional horizontal rails | Framed panels |
| Garage joinery | Shaker panels | Fine vertical slats | Broad horizontal panels | Wide vertical panels |
| Entry | Panelled door | Existing glazed door and battens | Blade canopy | Stone jambs |
| Balcony fascia | Existing stepped corbels | Vertical fascia battens | Projecting horizontal band | Stone inset |

All new details are tagged as architecture. House three retains its open blue
cutaway in the whole-scheme view, so its facade details remain hidden there.
These are illustrative design refinements, not amendments to the source drawings.

## Furnishings and house two cladding revision

Bedroom sliders in houses one and two have asymmetrically drawn pleated curtains.
Roller blinds are partly lowered in one window in house one, two in house two,
and one in house four; other openings remain clear. Allocation stays fixed on reload.
House two's projecting upper window surrounds and shade blades are removed.
Its front weatherboards extend over the floor edge and return along the upper
garage side to the rear of the garage (6.86 m depth). The mirrored opposite
supported side, rear portion and raised garage parapet retain brickwork.


## Latest facade and occupancy details

House two now uses a 120 mm lapped upper skin (previously 240 mm), 150 mm
board courses with a 16 mm lap and closed corner trims. The front and side
boards meet continuously. A cap connects the balcony hip crown to the main
ridge on all four definitions; house three retains its cutaway visibility.
House two's garage door is raised overhead, with one existing vehicle asset
parked inside facing the street. Its three front windows have midpoint transoms.
One balcony slider is fully stacked behind the fixed panel, exposing the curtain;
the balcony now has glazed front and side panels with retained handrails.

## Street services and front garden pass

A 1.5 m continuous footpath finishes at the front plinth edge. Four block
letterboxes align with the outer porch piers, behind the path. Three overhanging
street luminaires, four garden water meters and separate external electrical
and gas meter boxes complete the illustrative street services. Gas boxes are
classified with hydraulic services for the existing discipline filter.
Front trees vary in height, width and branching seed. Houses two and three
have narrow planters outside the garage driveways, staggered in depth to avoid
matching adjacent crowns. House two has an enclosed rear garage wall, stronger
30 mm weatherboard laps and widened masonry-to-cladding corner closures.
Ground-floor front windows have raised sills, lower heads and four-pane cross
rails. House two's glazed entry has five narrow vertical panes.
