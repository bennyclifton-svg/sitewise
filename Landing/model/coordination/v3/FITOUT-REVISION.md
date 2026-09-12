# Kitchen envelope correction

Run `fitout_revision.build(scene)` after registering the rich source scene and
before building any services. It moves 38 cabinet/appliance components together.
No mesh data, scale, architecture, ceiling lights or dining pendants change.

Actual vertex measurements found the north edge at Y−8.8035, while the inside
face of the existing north wall is Y−9.2834: approximately 480 mm of protrusion.
The correction applies the same world translation to every kitchen part:

`(-0.0057068062, -0.4998870194, 0)` metres.

The resulting cabinet envelope has 20 mm clearance from the north and east wall
faces. It stays within the floor/ceiling/south envelope. Mesh intersection checks
against all nearby original wall geometry find no overlapping triangles.

`fitout-revision-audit.json` records each before/after transform, changed object
name, measured room faces, final service ports and classification lists:

- `interior_object_names`: joinery, curtains and all visible retained source
  coffee tables, dining tables, sofas and beds.
- `retained_furniture_source_names` and `retained_furniture_object_names`: exact
  source and scene IDs for the original furnishings; these receive a category
  tag only, with their positions unchanged.
- `appliance_object_names`: 21 electrical appliance components.
- `mechanical_object_names`: the hood canopy.
- `shared_sink_and_hood_source_objects`: Object 54 contains both sink and hood
  components; export endpoint associations supply its service relationships.

The sink drain check is `(4.7207136154, -11.5945644379, 3.99)` and the hood extract
port is `(4.8936772346, -10.3983545303, 5.4260003662)` in registered world metres.
Both are derived from unchanged local source vertices through the new matrix.

Electrical appliance endpoints now also use Object 54's current placement matrix
instead of the historical placement JSON. The full electrical endpoint and route
continuity audit passes after the move. The wet-services author received the
exact delta and derives its fitting ports from the same retained local geometry.

`fitout-revision-plan.png` is the visually checked overhead review, and
`fitout-revision-review.blend` is an isolated assembled review scene with updated
electrical connections. The original source blend and GLBs remain unchanged.
