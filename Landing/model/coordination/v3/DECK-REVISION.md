# Deck and awning connection checkpoint

Current model: `../sitewise-decks-v9.blend`, built from the retained
`../sitewise-gardens-v8.blend` using `deck_revision.py`.

All five rear terrace blocks are hidden and replaced with 28 mm timber deck
boards, 6 mm joints and shallow timber fascias. Decks meet the recessed rear
wall and extend 180 mm beyond the post faces. The southern three retain their
360 mm terrace level; the northern two finish at 120 mm to clear the lawn.
Furniture and post bases follow those finished levels.

Rafters now reach the ground-floor rear cladding at X=4.7482, rather than stopping
at the upper facade line. A 100 mm-deep wall-mounted timber trimmer supports
their house ends; outer beams retain their 200 mm depth. Awning members are
adjusted to keep the trimmer on the wall and preserve bearing at each end.

All five rear pits move into the open garden between the decks and boundary.
Grates finish at lawn level, with existing invert levels retained. Six connecting
pipe routes are rebuilt with their endpoints attached to the relocated pits.
Updated drainage geometry is recorded in `civil-stormwater-decks.json`.

The boards and fascias total 732 added quad polygons across all five decks.
No new planting is added. `deck-revision.json` records the quantities and
coordinates. `render_decks.py` generates overview and close-up renders.

Deck boards and fascias belong exclusively to the Landscape package, for design
and detailing by the landscape architect. Pergola classification is unchanged.
