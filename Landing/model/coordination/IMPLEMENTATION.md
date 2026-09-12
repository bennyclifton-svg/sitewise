# SiteWise — The Coordination Field

**Current direction:** `FLYTHROUGH-DIRECTION.md` supersedes the exploded cutaway as
the primary experience. The building stays assembled; a moving perspective camera and
selective translucent architecture reveal systems in situ.

**Current modelling backlog:** `MODELLING-CHECKPOINTS.md` governs the new kitchen,
appliances, lighting, GPOs, restrained furnishings, structure, services and car/traffic work.
Source audits are under `asset-audit/`. The latest user correction calls for reinforced-concrete
columns and slabs. The earlier timber model is superseded and retained only as a provisional
study; the user asked to leave it for now rather than rebuild it immediately.

## Agreed direction

- Show the full development; move into one dwelling to explain its systems.
- Added services and decision examples are illustrative, anchored to the supplied geometry.
- Establish the camera and material treatment before developing services and animation.
- Chalk architecture, mineral-grey detail, graphite drawing conventions and amber for open questions.
- The building leads. The existing interactive workspace follows as product proof.
- Do not use the Impeccable skill.
- Camera B approved as the opening position; chalk material treatment accepted for now.
- User prefers a fly-through/in-situ reveal with more visible architecture and dark
  service accents. Colour assessment remains pending.
- Both sides of the hero share one cadastral scene: isometric left, plan right.
  Building sits within an illustrative lot selected from the existing map. Site/boundary
  relationships lead into later street and utility-network investigations.

## 1. Source audit

Source: `Landing/model/duplex.glb`, 58,688,272 bytes. Imported by Blender 5.1.2.
The inventory contains 3,057 mesh objects and 901,265 imported vertices. Mesh objects are
material fragments, not quantities of construction elements. The source hierarchy has
ground, first and second floor groups; it is not a single two-storey duplex.

Embedded source metadata identifies **Duplex houses at 22 ARNWOOD STREET MANUREWA**,
by **MyStudioNZ**, with **CC-BY-4.0** metadata.
[Original model](https://sketchfab.com/3d-models/duplex-houses-at-22-arnwood-street-manurewa-ef88f585f3d045c89c849ddd64495ad5).
Preserve this attribution and describe the modified materials and illustrative additions
in the delivered asset credits. Do not relabel this building as the existing Seven Hills
workspace's project. Any transition between those demonstrations needs a clear distinction.

Assembly census groups material fragments by their immediate source parent. It finds:

| Named fixture | Assemblies |
| --- | ---: |
| Kitchen sinks | 5 |
| Cooktops | 5 |
| Washing machines | 5 |
| Laundry sinks | 5 |
| Toilets | 20 |
| Basins | 20 |
| Shower cabins | 15 |
| Explicitly named downpipes | 4 |

Five dwellings are inferred from the repeated kitchens/appliances and exterior; these
are modelling observations, not a verified dwelling schedule or quantity survey.
Source mesh IDs and world coordinates are recorded in `source-census.json`.
The apparent building bounds are roughly 15 × 29 × 10.3 coordinate units, including its
rotation and roof extent. These are bounding-box dimensions, not surveyed dimensions.

| System | Evidence in model | Work needed for the hero |
| --- | --- | --- |
| Site / civil | Ground, access, fences, exterior stairs and paving | Separate site from oversized context; add illustrative drainage routes, not invented survey contours |
| Substructure | Foundation-labelled slab meshes | Verify geometry visually; no assumed piling, geotechnical design or footings |
| Superstructure | Floor plates, walls, stairs | Separate levels and structural-looking geometry; load-bearing roles remain unverified |
| Envelope | Cladding, doors, windows, roof coverings | Group complete assemblies; distinguish roof coverings from any hidden frame |
| Fit-out | Kitchens, furniture, wet areas, finishes | Preserve recognisable rooms; simplify objects that do not aid the story |
| Hydraulics | Actual fixtures and some named downpipes | Add indicative supply, waste and risers with links back to fixture IDs |
| Mechanical | No complete mechanical network identified | Add one coherent illustrative ventilation/system-route concept after camera review |
| Electrical | Appliances; no complete network identified | Add indicative distribution, containment and selected endpoints |
| Fire | No verified fire strategy identified | Illustrate a separation/penetration coordination question; do not imply compliance or assume sprinklers |
| Planning | Built form and apparent site context only | Use a brief/approval question; any envelope must be expressly illustrative and avoid invented statutory setbacks |
| Procurement / trades | No work-package dataset in GLB | Derive example package associations from systems, not mesh counts |

Current name/material grouping is a first pass. In particular `SLA` also appears on
joinery and stair parts; `RT` does not prove a roof classification; a foundation material
does not prove an engineered footing. Check those groups in isolation before using them
for highlighting or quantity-related copy. Source object names are retained for traceability.

## 2. Still-image review

Deliver two orthographic views of the same full development, under identical studio
lighting, with original decorative context suppressed. Review the building silhouette,
readability of its levels, roof proportion, space for copy and how a dwelling close-up
would connect. The studio floor is presentation geometry, not survey evidence.

**Camera A:** courtyard/entry side; reveals level changes and repeating dwelling fronts.
**Camera B:** balcony/access side; makes exterior access and balcony interfaces prominent.
These are working descriptions, not surveyed orientation labels.

Review decision: Camera B selected; retain the current chalk treatment.
Produce one cutaway still of the nearest dwelling, keeping enough facade to retain
its identity and moving roof/floor assemblies as coherent groups.

## 3. Coordination storyboard

The sequence demonstrates how a question becomes an agreed instruction. Physical parts
remain recognisable throughout. An alignment animation alone does not signify approval.
All three narratives below are proposed examples, not defects detected in this building.

| Beat | Visual | Meaning / proposed copy |
| --- | --- | --- |
| Establish | Full development, calm orthographic view | Understand the whole building |
| Reveal | Roof and upper levels separate slightly; one dwelling remains the focus | Every system has an interface |
| Ask | Highlight fixtures and one indicative hydraulic route; amber point at a floor crossing | Where will the riser go? |
| Coordinate | Show reserved route and an example architect / structural / hydraulic decision | Agree the route and penetration responsibility |
| Carry forward | Route settles; adjacent slab and fit-out return to registration | Carry the decision into scope and trade packages |
| Deliver | Full building reforms; one quiet link opens product proof | Explore how SiteWise works |

Recommended primary story: **a wet-area riser and floor interface**. Fixtures provide a
real geometric anchor. The unresolved state is an unallocated route/penetration decision,
not a deliberately fabricated pipe crashing through a beam. The resolved example records
the responsible disciplines, a chosen route and the downstream hydraulic/structural scope.

Secondary close-up: **roof drainage meets site works**. Existing downpipe geometry anchors
an illustrative connection route. The open question is who designs and installs each part;
the example decision carries the connection and scope boundary into hydraulic/civil packages.
No invented sewer location, lawful discharge point, flow capacity or gravity compliance.

Third close-up: **mechanical equipment and architectural/planning interfaces**. An example
equipment location invites review of access, screening and noise assessment. The outcome
is a coordinated instruction and consultant scope, not an automatic planning approval.

Do not display the earlier placeholder metrics (12 disciplines, 38 decisions, 8 packages).
Only display values derived from the eventual demonstration dataset and label their status.
The coordination narrative should show human judgement; a scrolling visitor does not
actually approve a project decision or run SiteWise engineering analysis.

## 4. Model and motion implementation

1. Preserve the source GLB. Work in a derived Blender scene with original names and IDs.
2. Validate collections in isolation; partition by dwelling, level and system using actual
   geometry. Preserve complete assemblies, normals and source transforms.
3. Model services only after the still is agreed. Keep each added object in an illustrative
   collection with system, dwelling, decision and source-fixture references.
4. Keep the primary structure, architecture and MEP in distinct groups. Do not present
   architectural walls as an engineered frame without identifying that simplification.
5. Build one reversible motion test: coherent levels offset, selected system highlights,
   then all parts return exactly to their source-relative positions. No random scattering.
6. Use neutral mineral tones for system focus; amber indicates the open question. Keep
   resolved parts neutral rather than implying certainty with a green compliance signal.
7. Review one motion clip before propagating the treatment across every system.

## 5. Landing-page integration

Start in a separate review concept until placement is agreed; the current landing has
in-progress edits and a different synthetic project demonstration. Reuse the installed
Three.js dependency if interactive geometry is the chosen delivery format.

Export a dedicated texture-free, grouped web model; do not ship the original 58.7 MB GLB
as the hero. Measure geometry, draw calls and file size after simplification. Keep fine
fixture detail in the close-up asset if it cannot fit the opening payload reasonably.

Offer a meaningful still before loading 3D. Lazy-load close-up detail, cap rendering pixel
ratio and pause rendering when offscreen. Keep keyboard-accessible system selectors and
an explicit replay control; scroll animation must not trap scrolling. Reduced-motion
users receive the composed still and discrete system states. Mobile can use a dedicated
crop or rendered clip if geometry is too expensive. If WebGL fails, preserve the image,
explanation and CTA. Test these paths and retain a readable evidence/illustration label.

## Review gates and current status

1. Source audit and proposed storyboard: complete for discussion; classification caveats recorded.
2. Camera/material studies: Camera B and current chalk treatment approved.
3. Decision narrative: first wet-area riser example developed for review.
4. Added services and animation: illustrative hydraulic cutaway reviewed; direction changed
   to intact architecture and in-situ routes. Perspective approach/material-reveal keyframes
   and key-view renders prepared for review; continuous flight and other MEP systems pending.
5. Web integration: not started; separate concept recommended until review.

## Reproduction

From the repository root, use Blender 5.1.2:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/inspect_model.py
python Landing/model/audit_coordination.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/build_coordination.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/prepare_camera_studies.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/build_hydraulic_study.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/build_in_situ_study.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python Landing/model/build_siting_study.py
```

The census requires `model-inventory.json`; run the import first on a fresh checkout.
The Blender review file is `sitewise-camera-review.blend`. The original GLB is unchanged.
The next review file is `sitewise-hydraulic-study.blend`; route-to-fixture references and
presentation transforms are recorded in `hydraulic-study.json`.
