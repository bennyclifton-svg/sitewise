# Chalk palette checkpoint

Historical palette study. `../sitewise-premium-v11.blend` is now the current
editable model and viewer source; see `PREMIUM-FACADE.md`.

Current editable model: `../sitewise-chalk-v10.blend`, derived from the latest
`sitewise-decks-v9.blend`. Run `chalk_palette.py` to reproduce and export.

Architecture and fixtures use matte chalk white (#F7F7F4). The former balcony
oak retains only a faint warm tint (#E7E3DD); bronze and mineral facade details
are white. No geometry is changed. Garden/deck materials are retained.

Viewer daylight uses a neutral key and restrained fill, with shadow casting and
reception retained. The sun-path lighting no longer introduces an amber midday
cast. Whole-project and Architecture selections use the chalk palette.

The two hero headline roles use the existing Manifa Advertising face. Animation
waits for that font, and the preload now matches it. Copy is unchanged.

Desktop and 390px mobile browser inspection passed; no horizontal overflow.
Frontend typecheck, lint and viewer build passed.
