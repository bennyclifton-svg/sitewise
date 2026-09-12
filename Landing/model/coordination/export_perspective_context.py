"""Export one source-derived cadastral neighbourhood for both hero views."""

import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / "frontend/public/landing-assets/cadastral-lines.json"
PALETTE = REPO / "Landing/design/colour-system/sitewise-colours.json"
WEB_PLAN = REPO / "frontend/public/landing-assets/coordination/sitewise-hero-plan.svg"
RADIUS = 220.0
VIEW_BOX = [-140, -110, 280, 220]
POLE_EPSILON = 0.0001
NS = {"svg": "http://www.w3.org/2000/svg"}


def project(point, matrix):
    x, y = point
    denominator = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2]
    if abs(denominator) < POLE_EPSILON:
        return None, denominator
    result = [(row[0] * x + row[1] * y + row[2]) / denominator for row in matrix[:2]]
    return (result if all(map(math.isfinite, result)) else None), denominator


def clip_segment(a, b, bounds=(-RADIUS, -RADIUS, RADIUS, RADIUS)):
    """Liang–Barsky clipping retains only actual source edges inside the square."""
    xmin, ymin, xmax, ymax = bounds
    dx, dy = b[0] - a[0], b[1] - a[1]
    lower, upper = 0.0, 1.0
    for p, q in [(-dx, a[0] - xmin), (dx, xmax - a[0]),
                 (-dy, a[1] - ymin), (dy, ymax - a[1])]:
        if abs(p) < 1e-12:
            if q < 0:
                return None
            continue
        ratio = q / p
        if p < 0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower > upper:
            return None
    points = [[a[0] + lower * dx, a[1] + lower * dy],
              [a[0] + upper * dx, a[1] + upper * dy]]
    return points if math.dist(*points) > 1e-6 else None


def archived_roof_geometry():
    """Preserve the existing roof projection; SVG Y is the negative of scene Y."""
    archive = ET.parse(HERE / "sitewise-hero-plan.svg").getroot()
    groups = archive.findall("svg:g", NS)
    faces = []
    for polygon in groups[1].findall("svg:polygon", NS):
        points = [list(map(float, pair.split(","))) for pair in polygon.attrib["points"].split()]
        faces.append([[x, -y] for x, y in points])
    edges = []
    for path in groups[2].findall("svg:path", NS):
        values = list(map(float, re.findall(r"-?\d+(?:\.\d+)?", path.attrib["d"])))
        assert len(values) == 4
        x1, y1, x2, y2 = values
        edges.append([[x1, -y1], [x2, -y2]])
    assert len(faces) == 34 and len(edges) == 59
    return faces, edges


def svg_points(points):
    return " ".join(f"{x:.4f},{-y:.4f}" for x, y in points)


def svg_path(segments):
    return " ".join(f"M{a[0]:.4f},{-a[1]:.4f}L{b[0]:.4f},{-b[1]:.4f}" for a, b in segments)


def main():
    siting = json.loads((HERE / "siting-study.json").read_text(encoding="utf-8"))
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    palette = json.loads(PALETTE.read_text(encoding="utf-8"))
    colours = {name: palette["primitives"][name]["hex"] for name in
               ["cyan-100", "cyan-300", "cyan-600", "cyan-700", "neutral-0", "neutral-50"]}
    segments, origins, seen = [], [], set()
    total = poles = outside = duplicates = 0
    denominators = []
    for line_index, line in enumerate(source["lines"]):
        for point_index, (start, end) in enumerate(zip(line, line[1:])):
            total += 1
            a, da = project(start, siting["homography"])
            b, db = project(end, siting["homography"])
            denominators.extend([abs(da), abs(db)])
            if a is None or b is None or da * db <= 0:
                poles += 1
                continue
            clipped = clip_segment(a, b)
            if clipped is None:
                outside += 1
                continue
            key = tuple(sorted(tuple(round(value, 6) for value in point) for point in clipped))
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            segments.append([[round(value, 6) for value in point] for point in clipped])
            origins.append([line_index, point_index])

    roof_faces, roof_edges = archived_roof_geometry()
    lot_error = max(math.dist(project(point, siting["homography"])[0], expected)
                    for point, expected in zip(siting["source_lot"], siting["lot"]))
    assert lot_error < 1e-8
    assert all(abs(value) <= RADIUS + 1e-6 for edge in segments for point in edge for value in point)
    visible = sum(clip_segment(a, b, (-140, -110, 140, 110)) is not None for a, b in segments)
    context = {
        "version": 1,
        "status": siting["status"],
        "units": siting["units"],
        "coordinate_system": "Same local XY as siting-study.json; Z is vertical. SVG displays (x, -y).",
        "source_file": SOURCE.relative_to(REPO).as_posix(),
        "provenance": {
            "source_image_coordinates": source["source"],
            "reconstruction_method": source["metadata"]["method"],
            "reconstruction_limits": source["metadata"]["limitations"],
            "input_sha256": {path.relative_to(REPO).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in [SOURCE, HERE / "siting-study.json", HERE / "sitewise-hero-plan.svg"]}
        },
        "source_lot": siting["source_lot"],
        "lot": siting["lot"],
        "homography": siting["homography"],
        "clip_bounds": {"min": [-RADIUS, -RADIUS], "max": [RADIUS, RADIUS]},
        "context_segments": segments,
        "segment_sources": origins,
        "building_bounds": siting["building_bounds"],
        "building_rotation_radians": siting["building_rotation_radians"],
        "roof_geometry_source": "Landing/model/coordination/sitewise-hero-plan.svg (unchanged archived projection)",
        "building_roof_faces": roof_faces,
        "building_roof_edges": roof_edges,
        "plan_view_box": VIEW_BOX,
        "colours": {"source": PALETTE.relative_to(REPO).as_posix(), "version": palette["version"], "primitives": colours},
        "audit": {"source_polylines": len(source["lines"]), "source_segments": total,
                  "previous_context_segments": len(siting["context_segments"]),
                  "context_segments": len(segments), "segments_in_plan_bounds": visible,
                  "rejected_at_pole": poles, "outside_or_degenerate": outside,
                  "duplicate_segments": duplicates, "minimum_absolute_source_denominator": min(denominators),
                  "selected_lot_max_error": lot_error, "pole_epsilon": POLE_EPSILON},
        "limits": ["Perspective source artwork; no surveyed CRS, verified dimensions or utility mapping.",
                   "Only original source segments reprojected and clipped; no mirrored geometry, waves or invented subdivisions.",
                   "Both hero views consume this context; selected lot and building projection remain fixed."]
    }
    (HERE / "perspective-context.json").write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + " ".join(map(str, VIEW_BOX)) + '" fill="none">',
           '<title>SiteWise development and surrounding source-derived parcels</title>',
           '<desc>The same selected lot and roof projection as the perspective hero, with expanded cadastral context. Illustrative reconstruction, not a survey.</desc>',
           f'<path d="{svg_path(segments)}" stroke="{colours["cyan-600"]}" stroke-width="0.8" opacity="0.90" vector-effect="non-scaling-stroke" stroke-linecap="round"/>',
           f'<polygon points="{svg_points(siting["lot"])}" fill="{colours["cyan-100"]}" fill-opacity="0.72" stroke="{colours["cyan-700"]}" stroke-width="1.6" vector-effect="non-scaling-stroke"/>',
           f'<g fill="{colours["cyan-300"]}" fill-opacity="0.72">']
    svg.extend(f'<polygon points="{svg_points(face)}"/>' for face in roof_faces)
    svg.extend(['</g>', f'<path d="{svg_path(roof_edges)}" stroke="{colours["cyan-700"]}" stroke-width="0.65" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>', '</svg>'])
    WEB_PLAN.write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(json.dumps(context["audit"], indent=2))


if __name__ == "__main__":
    main()
