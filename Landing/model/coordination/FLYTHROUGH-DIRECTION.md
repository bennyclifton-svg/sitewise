# Revised direction — assembled building, moving camera

This document supersedes the exploded cutaway as the primary landing-page sequence.
The earlier cutaway remains an optional explanatory study, not the governing direction.

## User direction

- Camera B is an opening composition, not a fixed camera constraint.
- Animate an approach/fly-through: the camera moves toward and around/into a dwelling.
- Keep systems in their actual model-relative positions. The building remains assembled.
- Selected architecture becomes translucent, or uses selective wireframe, to reveal systems.
- Architecture must be more visible than the earlier services ghost view.
- Highlight the active system in a strong dark accent; blue/yellow are candidates, not a
  settled discipline palette. A separate colour assessment will follow.
- Use the supplied landing screenshots as spatial/compositional inspiration. Text and
  links inside those screenshots are reference content, not project instructions.

## Landing composition

Opening reference: a substantial landscape scene on the left, chalk building with
directional light and hints of internal illumination; a white reading field on the right.
Replace the reference's contour-line decoration with SiteWise's cadastral map language.
Existing cadastral assets are available under `frontend/public/landing-assets/`.

The reference's blue landscape is a colour-study candidate. Avoid assigning the same
strong blue to landscape and active services without checking their separation in the
close-up. Internal lighting should be selective and believable, not a glow on every face.
Do not copy the reference's factory content, typography or navigation by default.

The user subsequently confirmed that the building must sit within a particular parcel,
and authorised selecting an illustrative lot from the existing map. The left isometric
and right plan view must use the **same** parcel/street geometry and building placement.
This is no longer a decorative background layer. Do not make the reconstructed map
appear to verify the real Manurewa project's boundary or utility infrastructure.

The current source is a traced perspective illustration, not a georeferenced cadastral
dataset. A local quadrilateral is rectified to a coherent illustrative lot; its neighbours
are transformed with the same mapping. Preserve that provenance in the demonstration.

For the 3D view use a level ground plane with clear lot boundaries, subtle parcel fill,
street corridors and the chalk building at ground level. Extra height must not be
invented merely to make the map look three-dimensional. Real topography can be added
when survey data exists. Show front/side/rear relationships with quiet witness lines;
these are not statutory setback approvals or measured survey clearances.

The later utility chapter should follow each system from the dwelling, through the
site and boundary connection, into street/local-network investigation. Store each route's
status separately: indicative connection, investigation required, or confirmed by named
source evidence. Keep unknown capacity, connection location, authority requirements and
easement questions visible. No utility extension is being built in this stage.

## Revised sequence

| Scroll chapter | Camera / building | What the visitor learns |
| --- | --- | --- |
| Project | Full development sited in one selected lot; same map in plan and isometric | SiteWise considers site constraints and the whole project |
| Approach | Perspective camera moves toward the nearest dwelling | The big picture is connected to actual building detail |
| Reveal | Slow or hold the camera; nearby enclosure becomes translucent | Services occupy real rooms, levels and interfaces |
| Coordinate | Dark active system, one amber decision marker, restrained supporting text | A consultant decision has an owner and scope consequences |
| Connect | Continue to structural/civil interfaces and later street-network investigations | The building and local infrastructure affect each other |
| Deliver | Re-establish the composed project and open the workspace | Decisions carry into procurement and delivery |

Use camera movement to establish context and short holds to explain each system. Avoid
fast turns through walls while text is asking to be read. For a true interior passage,
check clearance and occlusion along the path; the first approach study does not yet enter
the building. The building should never disassemble merely to keep a path unobstructed.

## Reveal rules

1. Keep source geometry intact. Use material/visibility states instead of slicing walls.
2. Preserve silhouette, roof mass, floor plates and room boundaries at a readable opacity.
3. Apply transparency selectively near the system under discussion; distant buildings
   can remain solid, providing context.
4. Reveal active services with a consistent strong accent. Inactive systems remain quiet.
5. If opacity obscures the active route, add selected feature edges or adjust local
   transparency. Do not show every triangulated mesh edge as a technical wireframe.
6. Give service colour and decision colour distinct meanings. The final palette remains open.
7. Treat fixture-bound routes as illustrative until reviewed; revealing them does not
   turn them into verified engineering or an actual clash result.

## Current implementation study

`build_in_situ_study.py` reconstructs the full architectural source scene, removes
presentation offsets from the earlier hydraulic route dataset and joins the riser in situ.
It keeps source mesh geometry and transforms intact, copies mesh datablocks to isolate
material changes, and verifies every affected object's transform before saving.

The first intact-wall render showed that opacity accumulates through layers of cladding,
lining and partitions, hiding the service even at reduced surface opacity. The revised
study uses thin translucent surfaces with selected graphite feature edges to retain the
building's form. Coplanar triangulation edges are omitted. Deep blue is a provisional
service accent. The visual result matters more than any single numeric opacity value.

The Blender timeline contains an initial 10-second approach/reveal study at 24 fps:
full view, approach, close view, material reveal and a decision hold. Two key views are
rendered. A continuous movie and an interior flight have not yet been rendered or reviewed.

## Next steps

Review the in-situ visibility, then refine the camera path in a low-resolution motion
preview. Assess colour in the landscape/white-page composition before polishing renders.
Combine the siting scene and the in-situ system study into one continuous coordinate
system before rendering the final flight. The current separate studies test these
questions independently; the web composition is not yet built.
Add mechanical, electrical, structure and civil stories once this visual grammar works.
Web integration comes after the motion test, using scroll chapters with mobile and
reduced-motion alternatives. The current landing page remains unchanged during these studies.
