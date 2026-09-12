# Electrical coordination component

`electrical.py` exposes `build(scene) -> metadata`. Run it on the assembled rich
interior after the confirmed source-to-site rotation has been applied once. It
checks a known GPO anchor before creating geometry and refuses duplicate builds.
Original object transforms and fixture geometry are preserved.

The module adds:

- Two street poles and four overhead conductors parallel to the road, with a
  protected pole riser and an underground connection to the site pillar.
- Five individual underground feeds and five distribution boards, mounted by
  raycast to actual garage side-wall meshes. The garage doors remain clear.
- Three lighting circuit groups and three general-power circuit groups in the
  nearest dwelling, serving all 26 existing luminaires and 24 existing GPOs.
- Fourteen wall-hosted switches grouping every luminaire by room or circulation
  space, including the dining pendants and stairs.
- Five separate appliance circuits ending at the fitted induction hob, oven,
  microwave, fridge and range hood.

Distribution follows orthogonal ceiling routes with short fixture branches and
concealed wall drops. The west riser is shared; electrical distribution remains
distinct from the kitchen/wet-area services. The drawing represents routes and
relationships, not conductor counts, protective ratings or a wiring schematic.
No electrical design, load assessment, cable sizing or compliance is implied.

Every created mesh/curve has `sw_system='electrical'` and `sw_label`. Circuits have
`sw_circuit_id`; terminal branches have `sw_source_endpoint_id` and a source
object ID. Original GPO/light meshes are also tagged for mode selection. The hood
belongs to both electrical and mechanical service narratives; the master scene
may assign a primary mesh system while retaining both endpoint relationships.

## Checks and review

`check_electrical.py` creates an isolated registered copy and verifies all source
transforms remain fixed. `electrical-audit.json` reports 55 connected fitting
endpoints, 14 switches, 11 circuits, five boards and the exact source anchors.
The continuity check follows each circuit's paths to the DB riser and compares
each terminal with its registered endpoint. No disconnected routes or duplicate
IDs were found; maximum terminal error is below 0.001 mm.

`electrical-review.blend` is a standalone component review, not the master site.
`render_electrical_review.py` produces `electrical-in-situ-review.png` using a
temporary translucent architectural context; it does not overwrite the blend.
