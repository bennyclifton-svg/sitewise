# Rear garden checkpoint

Current editable model: `../sitewise-gardens-v8.blend`, built from the retained
`../sitewise-facade-v7.blend` by `garden_revision.py`. This includes the latest
facade treatments, paving infill and wall-base closures.

Each of the five existing rear terraces receives a timber slatted pergola,
a wall ledger, an outer beam and two posts. Pergolas follow the terrace levels
(360 mm for the southern three; 60 mm for the northern two). A timber breakfast
table and two chairs sit on each terrace. Existing terrace geometry is retained.

Twenty-one spherical shrub proxies are replaced by five branching, leaf-built
trees with different silhouettes, lower spreading shrubs and grass clumps.
Planting stays in the rear gardens, outside the service corridor. Tree shapes
are illustrative, not specified species. The geometry adds no image textures.

Pergolas are Architecture with Landscape membership; furniture and planting are
Landscape. Garden finishes are retained in the whole-project view. LAN now
approaches from the rear to show all five gardens.

`garden-revision.json` records terrace levels and per-dwelling quantities.
`render_gardens.py` creates the overview and breakfast close-up without modifying
the editable model. `export_web.py` defaults to the garden checkpoint.
