# Shared cadastral scene — initial siting study

The user authorised an illustrative lot selected from the existing cadastral artwork.
`build_siting_study.py` uses a closed source quadrilateral near normalised image
position (0.6692, 0.7744). The same projective transformation rectifies the chosen lot
and neighbouring traced segments. This is a local illustrative reconstruction, not a
geographic projection or a recovered survey.

The derived scene contains a 24 × 44 illustrative-coordinate lot, 60 neighbouring
source-derived boundary segments and the supplied full development, rigidly rotated
to align its dominant axes with the parcel. Building scale is unchanged. The selected
lot dimensions are chosen for the demonstration, not read from cadastral evidence.
The building wall/roof bounds are checked to lie within the lot; that does not establish
planning setbacks, easements, access compliance or utility availability.

Two cameras render the exact same geometry and building placement:

- `09-cadastral-isometric.png` — spatial view for the left of the hero.
- `10-cadastral-plan.png` — plan view for the right-hand cadastral treatment.

The selected parcel has a quiet fill and stronger outline. Boundary-clearance witness
lines make the site relationship legible without invented dimensions or statutory labels.
The map rests on level ground; no terrain heights are invented. The final broader
landscape composition and colour/light assessment are still pending.
The current landing's animated map wave is unsuitable for the selected parcel: the
new composition must keep boundaries and the building registered while cameras move.
The existing landing renderer has not been changed in this study.

`sitewise-siting-study.blend` is editable. `siting-study.json` contains the selected
source points, derived lot, transformation, neighbouring segments and building bounds.

Next, combine the siting and in-situ reveal studies into one camera sequence. Retain
the lot and street context while approaching a dwelling. The later utility chapter
will investigate routes from the building to boundary connections and local networks;
no real utility lines, capacities or connection points have been asserted at this stage.
