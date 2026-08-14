"""Starter FFE rows from work type, work scope, and subclass.

The PMP carries one Finishes, Fixtures and Equipment register. When the user
has not yet recorded selections, seed the rows a competent PM would expect for
this work — wet-area fittings on a new house, cladding and roofing on an
envelope job, pumpsets on a fire upgrade — so the schedule is a working list
rather than an empty stub.
"""

from __future__ import annotations

from collections.abc import Sequence

_STATUS = "To be confirmed"
_NOTES = "Typical"
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

_SUBCLASS_PACKS: dict[str, tuple[str, ...]] = {
    "house": ("wet_areas", "kitchen", "envelope", "roofing", "paving"),
    "townhouses": ("wet_areas", "kitchen", "envelope", "roofing", "paving"),
    "apartments": ("wet_areas", "kitchen", "envelope", "roofing"),
    "btr": ("wet_areas", "kitchen", "envelope", "roofing"),
    "student_housing": ("wet_areas", "kitchen", "envelope", "roofing"),
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
                    "quantity": "TBC",
                    "finish": "TBC",
                    "status": _STATUS,
                    "notes": _NOTES,
                }
            )
    return rows
