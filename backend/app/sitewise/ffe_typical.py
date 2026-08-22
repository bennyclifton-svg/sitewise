"""Starter FFE rows from work type, work scope, and subclass.

The PMP carries one Finishes, Fixtures and Equipment register. When the user
has not yet recorded selections, seed the rows a competent PM would expect for
this work — wet-area fittings on a new house, cladding and roofing on an
envelope job, pumpsets on a fire upgrade — so the schedule is a working list
rather than an empty stub.
"""

from __future__ import annotations

from collections.abc import Sequence

_CONSTRUCTION_TYPES = frozenset({"new", "extend", "refurb", "remediation"})
_NEW_OR_EXTEND = frozenset({"new", "extend"})

# Packs are keyed by work-scope values where those exist, plus a few virtual
# packs used by subclass defaults (kitchen, envelope, paving, station_finishes).
_PACKS: dict[str, tuple[tuple[str, str], ...]] = {
    "wet_areas": (
        ("Wall and floor tiles", "Wet areas"),
        ("Basin", "Wet areas"),
        ("WC", "Wet areas"),
        ("Shower screen", "Wet areas"),
        ("Tapware", "Wet areas"),
    ),
    "kitchen": (
        ("Kitchen joinery", "Kitchen"),
        ("Appliances", "Kitchen"),
    ),
    "kitchen_joinery": (
        ("Kitchen joinery", "Kitchen"),
        ("Appliances", "Kitchen"),
    ),
    "envelope": (
        ("Facade cladding", "Envelope"),
        ("Render / paint", "Envelope"),
        ("Bricks / masonry", "Envelope"),
    ),
    "facade_system": (
        ("Facade cladding", "Envelope"),
        ("Render / paint", "Envelope"),
    ),
    "facade_cladding": (
        ("Facade cladding", "Envelope"),
        ("Render / paint", "Envelope"),
    ),
    "curtain_wall": (("Curtain wall / cladding", "Envelope"),),
    "roofing": (("Roof sheeting / covering", "Roof"),),
    "glazing": (("Windows / glazing", "Envelope"),),
    "waterproofing": (("Waterproofing membrane", "Wet areas / envelope"),),
    "waterproofing_rectification": (("Waterproofing membrane", "Envelope"),),
    "weatherproofing_tie_in": (("Weatherproofing / flashing", "Envelope tie-in"),),
    "flooring": (("Floor finish", "Interior"),),
    "joinery": (("Joinery", "Interior"),),
    "partitions_walls": (("Wall finish / paint", "Interior"),),
    "ceilings": (("Ceiling finish", "Interior"),),
    "landscaping": (
        ("Paving", "External works"),
        ("External finishes", "External works"),
    ),
    "car_parking": (("Carpark pavement", "External works"),),
    "internal_roads": (("Pavement / paving", "External works"),),
    "paving": (("Paving", "External works"),),
    "fire_services": (
        ("Fire pumpset", "Fire services"),
        ("Sprinkler heads / valves", "Fire services"),
        ("Hydrant / hose reel fittings", "Fire services"),
        ("Fire detection / alarm equipment", "Fire services"),
    ),
    "mechanical_hvac": (("HVAC plant", "Plant"),),
    "lighting": (("Light fittings", "Interior / exterior"),),
    "external_lighting": (("External light fittings", "External works"),),
    "hydraulic_plumbing": (
        ("Tapware", "Wet areas"),
        ("Sanitaryware", "Wet areas"),
    ),
    "vertical_transport": (("Lift / vertical transport", "Core"),),
    "signage_wayfinding": (("Signage", "Public areas"),),
    "station_finishes": (
        ("Paving", "Platform / concourse"),
        ("Facade cladding", "Envelope"),
        ("Roof sheeting / covering", "Roof"),
        ("Light fittings", "Station"),
        ("Signage", "Public areas"),
    ),
    "solar_pv": (
        ("PV modules", "Roof / array"),
        ("Inverters", "Plant"),
        ("Mounting system", "Roof / array"),
        ("Battery storage", "Plant"),
    ),
    "energy_generation_storage": (
        ("PV modules", "Roof / array"),
        ("Inverters", "Plant"),
        ("Mounting system", "Roof / array"),
        ("Battery storage", "Plant"),
    ),
}

# Display order follows construction: envelope and external works, then
# internal finishes, then sanitaryware, then kitchen appliances, then plant.
_ITEM_SEQUENCE: dict[str, tuple[int, int]] = {
    "facade cladding": (0, 0),
    "render / paint": (0, 1),
    "bricks / masonry": (0, 2),
    "curtain wall / cladding": (0, 3),
    "windows / glazing": (0, 4),
    "roof sheeting / covering": (0, 5),
    "waterproofing membrane": (0, 6),
    "weatherproofing / flashing": (0, 7),
    "paving": (0, 8),
    "external finishes": (0, 9),
    "carpark pavement": (0, 10),
    "pavement / paving": (0, 11),
    "external light fittings": (0, 12),
    "floor finish": (1, 0),
    "wall finish / paint": (1, 1),
    "ceiling finish": (1, 2),
    "wall and floor tiles": (1, 3),
    "joinery": (1, 4),
    "kitchen joinery": (1, 5),
    "light fittings": (1, 6),
    "basin": (2, 0),
    "wc": (2, 1),
    "shower screen": (2, 2),
    "tapware": (2, 3),
    "sanitaryware": (2, 4),
    "vanity": (2, 5),
    "freestanding bath": (2, 6),
    "appliances": (3, 0),
}

_LOCATION_BAND: dict[str, int] = {
    "envelope": 0,
    "roof": 0,
    "external works": 0,
    "envelope tie-in": 0,
    "platform / concourse": 0,
    "interior": 1,
    "wet areas": 2,
    "wet areas / envelope": 0,
    "kitchen": 3,
}

_SUBCLASS_PACKS: dict[str, tuple[str, ...]] = {
    "house": (
        "envelope",
        "roofing",
        "glazing",
        "flooring",
        "paving",
        "wet_areas",
        "kitchen",
    ),
    "townhouses": (
        "envelope",
        "roofing",
        "glazing",
        "flooring",
        "paving",
        "wet_areas",
        "kitchen",
    ),
    "apartments": (
        "envelope",
        "roofing",
        "glazing",
        "flooring",
        "wet_areas",
        "kitchen",
    ),
    "btr": (
        "envelope",
        "roofing",
        "glazing",
        "flooring",
        "wet_areas",
        "kitchen",
    ),
    "student_housing": (
        "envelope",
        "roofing",
        "glazing",
        "flooring",
        "wet_areas",
        "kitchen",
    ),
    "rail_metro": ("station_finishes",),
    "energy_renewables": ("solar_pv",),
    "warehouse": ("envelope", "roofing", "paving"),
    "logistics_ecommerce": ("envelope", "roofing", "paving"),
    "office": ("flooring", "partitions_walls", "ceilings", "joinery", "kitchen"),
}

# Subclass packs that still apply on refurb/remediation — infrastructure and
# energy work, where the "finishes" are the asset itself.
_REFURB_SUBCLASS_PACKS = frozenset({"rail_metro", "energy_renewables"})
_INTERIOR_REFURB_SUBCLASSES = frozenset({"office"})
_FITOUT_SCOPES = frozenset(
    {
        "flooring",
        "partitions_walls",
        "ceilings",
        "joinery",
        "kitchen_joinery",
        "live_environment_fitout",
        "specialist_fitout",
        "workplace_furniture",
        "wet_areas",
    }
)


def typical_ffe_rows(
    *,
    work_type: str | None,
    work_scope: Sequence[str] = (),
    subclasses: Sequence[str] = (),
) -> list[dict[str, str]]:
    """Return starter FFE rows for construction work. Advisory returns none."""
    if work_type not in _CONSTRUCTION_TYPES:
        return []

    pack_keys: list[str] = []
    seen_packs: set[str] = set()

    def _add_pack(key: str) -> None:
        if key in _PACKS and key not in seen_packs:
            seen_packs.add(key)
            pack_keys.append(key)

    for scope in work_scope:
        _add_pack(str(scope))

    scope_set = {str(value) for value in work_scope}
    apply_subclass = work_type in _NEW_OR_EXTEND
    apply_interior_refurb = work_type == "refurb" and (
        not scope_set or bool(scope_set & _FITOUT_SCOPES)
    )
    for subclass in subclasses:
        if apply_subclass or subclass in _REFURB_SUBCLASS_PACKS:
            for pack in _SUBCLASS_PACKS.get(str(subclass), ()):
                _add_pack(pack)
        elif apply_interior_refurb and subclass in _INTERIOR_REFURB_SUBCLASSES:
            for pack in _SUBCLASS_PACKS.get(str(subclass), ()):
                _add_pack(pack)

    if not pack_keys:
        if work_type in _NEW_OR_EXTEND:
            _add_pack("envelope")
            _add_pack("roofing")
            _add_pack("glazing")
            _add_pack("flooring")
            _add_pack("paving")
        elif work_type == "remediation":
            _add_pack("envelope")
            _add_pack("roofing")
        else:
            _add_pack("partitions_walls")
            _add_pack("flooring")

    rows: list[dict[str, str]] = []
    seen_items: set[str] = set()
    for key in pack_keys:
        for item, location in _PACKS[key]:
            label = item.casefold()
            if label in seen_items:
                continue
            seen_items.add(label)
            rows.append(
                {
                    "item": item,
                    "location": location,
                    "finish": "TBC",
                    "notes": "",
                }
            )
    rows.sort(key=ffe_sequence_key)
    return rows


def ffe_sequence_key(row: dict[str, str]) -> tuple[int, int, str]:
    """Sort FFE rows in construction order, then by item name."""
    item = str(row.get("item") or "").strip()
    location = str(row.get("location") or "").strip()
    named = _ITEM_SEQUENCE.get(item.casefold())
    if named is not None:
        band, order = named
        return (band, order, item.casefold())
    if location.casefold() == "kitchen" and "joinery" in item.casefold():
        return (1, 5, item.casefold())
    band = _LOCATION_BAND.get(location.casefold(), 4)
    return (band, 50, item.casefold())
