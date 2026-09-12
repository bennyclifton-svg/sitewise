"""Build an undistorted, animation-ready plan from the saved NSW parcel snapshot."""

import hashlib
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ASSETS = REPO / "frontend/public/landing-assets/coordination"
SOURCE = HERE / "nsw-cadastre-source.json"
ORIGIN = (308678.0, 6262154.0)
VIEW_BOX = (-280, -360, 560, 720)


def area(ring):
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(ring, ring[1:])) / 2)


def main():
    source = json.loads(SOURCE.read_text())
    assert source["data"]["spatialReference"]["wkid"] == 7856
    parcels, edges, seen_polygons = [], {}, set()
    maximum_length_error = 0.0
    for feature in source["data"]["features"]:
        rings = feature["geometry"]["rings"]
        local = [[[round(x - ORIGIN[0], 3), round(ORIGIN[1] - y, 3)]
                  for x, y in ring] for ring in rings]
        # Coincident strata may share one footprint: draw its boundary once.
        signature = tuple(sorted(tuple(sorted(tuple(p) for p in ring)) for ring in local))
        if signature in seen_polygons:
            continue
        seen_polygons.add(signature)
        attributes = feature["attributes"]
        parcels.append({"id": str(attributes["objectid"]), "rings": local,
                        "area_m2": round(area(local[0]) - sum(area(r) for r in local[1:]), 2)})
        for original, ring in zip(rings, local):
            assert ring[0] == ring[-1], "Unclosed parcel ring"
            for i, (a, b) in enumerate(zip(ring, ring[1:])):
                assert all(math.isfinite(v) for p in (a, b) for v in p)
                maximum_length_error = max(maximum_length_error,
                    abs(math.dist(a, b) - math.dist(original[i], original[i + 1])))
                key = tuple(sorted((tuple(a), tuple(b))))
                if a != b:
                    edges.setdefault(key, []).append(str(attributes["objectid"]))
    assert maximum_length_error < 0.003
    boundaries = [{"id": f"edge-{i}", "points": key, "parcels": ids}
                  for i, (key, ids) in enumerate(sorted(edges.items()))]
    visible = [p for p in parcels if any(-280 <= x <= 280 and -360 <= y <= 360
               for ring in p["rings"] for x, y in ring)]
    audit = {"source_features": len(source["data"]["features"]),
             "unique_footprints": len(parcels), "shared_boundaries": len(boundaries),
             "visible_parcels": len(visible),
             "median_visible_area_m2": round(statistics.median(p["area_m2"] for p in visible), 1),
             "maximum_edge_length_error_m": maximum_length_error,
             "projection": "GDA2020 / MGA zone 56 (EPSG:7856)",
             "transform": "Translation and Y-axis reflection only; 1 SVG unit = 1 metre"}
    asset = {"version": 1, "source": source["source_url"],
             "attribution": "© State of New South Wales (Spatial Services)",
             "licence": "https://creativecommons.org/licenses/by/3.0/au/",
             "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
             "origin_m": ORIGIN, "viewBox": VIEW_BOX,
             "audit": audit, "parcels": parcels, "boundaries": boundaries}
    (ASSETS / "sitewise-cadastral-plan.json").write_text(json.dumps(asset, separators=(",", ":")))
    path = " ".join(f"M{a[0]},{a[1]}L{b[0]},{b[1]}" for a, b in edges)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-280 -360 560 720" '
           'preserveAspectRatio="xMidYMid meet" fill="none">\n'
           '<title>Seven Hills cadastral plan</title>\n'
           '<desc>NSW Spatial Services parcel geometry in MGA zone 56 metres. '
           'North up, equal axis scale. © State of New South Wales (Spatial Services), '
           'CC BY 3.0 AU. Cropped and restyled for display.</desc>\n'
           f'<path d="{path}" stroke="#1E7F92" stroke-width="0.8" opacity="0.9" '
           'vector-effect="non-scaling-stroke" stroke-linejoin="round"/>\n</svg>\n')
    (ASSETS / "sitewise-cadastral-plan.svg").write_text(svg, encoding="utf-8")
    (HERE / "cadastral-plan-audit.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
