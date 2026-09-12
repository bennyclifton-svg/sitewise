"""Reconstruct visible parcel centerlines; this is a trace, not cadastral survey data."""

from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Landing/cadastral-landscape.png"
ASSETS = ROOT / "frontend/public/landing-assets"


def skeletonize(mask: np.ndarray) -> np.ndarray:
    pixels = np.pad(mask, 1)
    for iteration in range(100):
        changed = 0
        for phase in (0, 1):
            n = [pixels[:-2, 1:-1], pixels[:-2, 2:], pixels[1:-1, 2:],
                 pixels[2:, 2:], pixels[2:, 1:-1], pixels[2:, :-2],
                 pixels[1:-1, :-2], pixels[:-2, :-2]]
            count = sum(neighbor.astype(np.uint8) for neighbor in n)
            transitions = sum((~n[i] & n[(i + 1) % 8]).astype(np.uint8) for i in range(8))
            if phase == 0:
                corners = ~(n[0] & n[2] & n[4]) & ~(n[2] & n[4] & n[6])
            else:
                corners = ~(n[0] & n[2] & n[6]) & ~(n[0] & n[4] & n[6])
            remove = pixels[1:-1, 1:-1] & (count >= 2) & (count <= 6) & (transitions == 1) & corners
            changed += int(np.count_nonzero(remove))
            pixels[1:-1, 1:-1][remove] = False
        if not changed:
            print(f"Skeleton converged after {iteration + 1} iterations", flush=True)
            return pixels[1:-1, 1:-1]
    raise RuntimeError("Centerline thinning did not converge")


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        first, last = pending.pop()
        ax, ay = points[first]
        bx, by = points[last]
        dx, dy = bx - ax, by - ay
        denominator = math.hypot(dx, dy)
        furthest, distance = first, 0.0
        for index in range(first + 1, last):
            x, y = points[index]
            current = abs(dy * (x - ax) - dx * (y - ay)) / denominator if denominator else math.hypot(x - ax, y - ay)
            if current > distance:
                distance, furthest = current, index
        if distance > tolerance:
            keep.add(furthest)
            pending.extend(((first, furthest), (furthest, last)))
    return [points[index] for index in sorted(keep)]


def trace(skeleton: np.ndarray, offset_y: int) -> tuple[list[list[tuple[float, float]]], dict]:
    height, width = skeleton.shape
    locations = set(int(value) for value in np.flatnonzero(skeleton))

    def neighbors(location: int) -> list[int]:
        y, x = divmod(location, width)
        adjacent = []
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            target = location + dy * width + dx
            if 0 <= x + dx < width and 0 <= y + dy < height and target in locations:
                adjacent.append(target)
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            target = location + dy * width + dx
            if (0 <= x + dx < width and 0 <= y + dy < height and target in locations
                    and location + dx not in locations and location + dy * width not in locations):
                adjacent.append(target)
        return adjacent

    graph = {location: neighbors(location) for location in locations}
    seen: set[int] = set()
    retained: set[int] = set()
    for seed in graph:
        if seed in seen:
            continue
        component, stack = [], [seed]
        seen.add(seed)
        while stack:
            current = stack.pop()
            component.append(current)
            for target in graph[current]:
                if target not in seen:
                    seen.add(target)
                    stack.append(target)
        # Suppress isolated stars and short glow fragments, never synthesize missing lots.
        if len(component) >= 28:
            retained.update(component)

    graph = {location: adjacent for location, adjacent in graph.items() if location in retained}
    walked: set[tuple[int, int]] = set()
    polylines = []

    def walk(start: int, following: int) -> None:
        path = [start]
        previous, current = start, following
        while True:
            walked.add((min(previous, current), max(previous, current)))
            path.append(current)
            if len(graph[current]) != 2 or current == start:
                break
            other = graph[current][0] if graph[current][0] != previous else graph[current][1]
            if (min(current, other), max(current, other)) in walked:
                break
            previous, current = current, other
        if len(path) < 7 and (len(graph[path[0]]) == 1 or len(graph[path[-1]]) == 1):
            return
        points = [(float(item % width), float(item // width + offset_y)) for item in path]
        points = simplify(points, 1.4)
        if len(points) >= 2:
            polylines.append(points)

    for start, adjacent in graph.items():
        if len(adjacent) == 2:
            continue
        for following in adjacent:
            if (min(start, following), max(start, following)) not in walked:
                walk(start, following)
    for start, adjacent in graph.items():
        for following in adjacent:
            if (min(start, following), max(start, following)) not in walked:
                walk(start, following)
    return polylines, {"skeletonPixels": len(locations), "retainedPixels": len(retained)}


def boundary_radius(y: float) -> float:
    """Source stroke width grows towards the foreground in this perspective still."""
    depth = max(0.0, min(1.0, (y - 922) / 2150))
    return 3.0 + 10.0 * depth ** 1.4


def path_length(points) -> float:
    return float(np.linalg.norm(np.diff(np.asarray(points), axis=0), axis=1).sum())


def path_samples(points, spacing=4.0) -> np.ndarray:
    points = np.asarray(points, dtype=float)
    lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    distances = np.linspace(0, lengths[-1], max(3, math.ceil(lengths[-1] / spacing) + 1))
    return np.column_stack([np.interp(distances, lengths, points[:, axis]) for axis in (0, 1)])


def fit_axis(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    centre = np.mean(points, axis=0)
    _, _, vectors = np.linalg.svd(points - centre, full_matrices=False)
    direction = vectors[0]
    normal = np.array([-direction[1], direction[0]])
    return centre, direction, np.abs((points - centre) @ normal)


def trim_fitted_curve(samples, start, end, radius):
    """A fitted join can pass old samples; never draw backwards to those samples."""
    samples = np.asarray(samples)
    if math.dist(start, end) < .01:
        return [start, *(tuple(point) for point in samples), end]
    valid = np.ones(len(samples), dtype=bool)
    count = min(len(samples), max(3, math.ceil(radius)))
    for origin, ordered in ((start, samples), (end, samples[::-1])):
        _, axis, _ = fit_axis(ordered[:count])
        if axis @ (ordered[min(count - 1, len(ordered) - 1)] - ordered[0]) < 0:
            axis = -axis
        valid &= (samples - np.asarray(origin)) @ axis > .05
    indices = np.flatnonzero(valid)
    if not len(indices):
        return [start, end]
    return [start, *(tuple(point) for point in samples[indices[0]:indices[-1] + 1]), end]


def graph_faces(graph):
    outgoing = defaultdict(list)
    for index, edge in graph.items():
        for reverse in (False, True):
            line = edge["points"][::-1] if reverse else edge["points"]
            direction = next((point - line[0] for point in line[1:] if np.linalg.norm(point - line[0]) > .01), np.array([1.0, 0.0]))
            node = edge["b"] if reverse else edge["a"]
            outgoing[node].append((math.atan2(direction[1], direction[0]), index, reverse))
    for incident in outgoing.values():
        incident.sort()
    visited, faces = set(), []
    for index in graph:
        for reverse in (False, True):
            start, current = (index, reverse), (index, reverse)
            boundary, polygon = [], []
            while current not in visited:
                visited.add(current)
                edge = graph[current[0]]
                line = edge["points"][::-1] if current[1] else edge["points"]
                polygon.extend(line[:-1])
                boundary.append(current[0])
                node = edge["a"] if current[1] else edge["b"]
                incident = outgoing[node]
                position = next(i for i, entry in enumerate(incident) if entry[1:] == (current[0], not current[1]))
                following = incident[(position - 1) % len(incident)]
                current = (following[1], following[2])
            if current == start and len(polygon) >= 3:
                polygon = np.asarray(polygon)
                area = float(np.dot(polygon[:, 0], np.roll(polygon[:, 1], -1)) - np.dot(polygon[:, 1], np.roll(polygon[:, 0], -1))) / 2
                if area > 0:
                    faces.append((area, set(boundary), polygon))
    return sorted(faces, key=lambda face: face[0])


def collapse_sliver_faces(graph, joins):
    collapsed = 0
    next_index = max(graph, default=-1) + 1
    for _ in range(2):
        changed = 0
        for area, boundary, polygon in graph_faces(graph):
            if not boundary.issubset(graph):
                continue
            perimeter = path_length(np.vstack((polygon, polygon[0])))
            radius = boundary_radius(float(np.mean(polygon[:, 1])))
            centre, axis, errors = fit_axis(path_samples(np.vstack((polygon, polygon[0]))))
            # The two tests distinguish glow slivers from narrow but real roads:
            # both the area-derived width and the entire face must fit one stroke.
            if perimeter < .01 or 2 * area / perimeter >= radius * 1.15 or max(errors) >= radius * 1.6:
                continue
            nodes = {node for index in boundary for node in (graph[index]["a"], graph[index]["b"])}
            ordered = sorted((float((joins[node] - centre) @ axis), node) for node in nodes)
            groups = []
            for distance, node in ordered:
                if groups and distance - groups[-1][0][0] < radius * .8:
                    groups[-1].append((distance, node))
                else:
                    groups.append([(distance, node)])
            replacements, chain = {}, []
            for group in groups:
                representative = group[0][1]
                joins[representative] = centre + axis * np.mean([entry[0] for entry in group])
                for _, node in group:
                    replacements[node] = representative
                chain.append(representative)
            for index in boundary:
                graph.pop(index)
            for index, edge in list(graph.items()):
                edge["a"] = replacements.get(edge["a"], edge["a"])
                edge["b"] = replacements.get(edge["b"], edge["b"])
                edge["points"][0], edge["points"][-1] = joins[edge["a"]], joins[edge["b"]]
                if edge["a"] == edge["b"] and path_length(edge["points"]) < radius * 5:
                    graph.pop(index)
            for a, b in zip(chain, chain[1:]):
                graph[next_index] = {"a": a, "b": b, "points": np.array([joins[a], joins[b]])}
                next_index += 1
            collapsed += 1
            changed += 1
        if not changed:
            break
    return collapsed


def reconstruct_boundaries(polylines):
    """Build structural joins, then fit parcel runs independently of raster hooks."""
    points, node_ids, edges = [], {}, []
    for line in polylines:
        ends = []
        for point in (line[0], line[-1]):
            key = tuple(round(value, 3) for value in point)
            if key not in node_ids:
                node_ids[key] = len(points)
                points.append(np.asarray(key, dtype=float))
            ends.append(node_ids[key])
        edges.append({"a": ends[0], "b": ends[1], "points": np.asarray(line, dtype=float)})
    parent = list(range(len(points)))
    bounds = [(point.copy(), point.copy()) for point in points]

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    # Only collapse source-connected, short junction links. Proximity alone would
    # incorrectly join parallel road sides and neighbouring narrow parcels.
    for edge in sorted(edges, key=lambda item: path_length(item["points"])):
        a, b = find(edge["a"]), find(edge["b"])
        if a == b:
            continue
        low = np.minimum(bounds[a][0], bounds[b][0])
        high = np.maximum(bounds[a][1], bounds[b][1])
        radius = boundary_radius(float((low[1] + high[1]) / 2))
        if path_length(edge["points"]) <= radius * 1.8 and np.linalg.norm(high - low) <= radius * 2.2:
            parent[b] = a
            bounds[a] = (low, high)
    clusters = defaultdict(list)
    for node, point in enumerate(points):
        clusters[find(node)].append(point)
    joins = {node: np.mean(cluster, axis=0) for node, cluster in clusters.items()}
    graph, adjacency = {}, defaultdict(set)
    removed_loops = 0
    for edge in edges:
        a, b = find(edge["a"]), find(edge["b"])
        line = edge["points"].copy()
        radius = boundary_radius(float(np.mean(line[:, 1])))
        if a == b:
            extent = np.ptp(line, axis=0)
            area = abs(float(np.dot(line[:, 0], np.roll(line[:, 1], 1)) - np.dot(line[:, 1], np.roll(line[:, 0], 1)))) / 2
            if max(extent) < radius * 5 and area < radius * radius * 8:
                removed_loops += 1
                continue
        line[0], line[-1] = joins[a], joins[b]
        index = len(graph)
        graph[index] = {"a": a, "b": b, "points": line}
        adjacency[a].add(index)
        adjacency[b].add(index)

    def remove_edge(index):
        edge = graph.pop(index)
        adjacency[edge["a"]].discard(index)
        adjacency[edge["b"]].discard(index)
        return edge

    pending = deque(node for node, adjacent in adjacency.items() if len(adjacent) == 1)
    pruned_spurs = 0
    while pending:
        node = pending.popleft()
        if len(adjacency[node]) != 1:
            continue
        index = next(iter(adjacency[node]))
        edge = graph[index]
        if edge["a"] == edge["b"] or path_length(edge["points"]) > boundary_radius(joins[node][1]) * 3:
            continue
        remove_edge(index)
        pruned_spurs += 1
        pending.extend((edge["a"], edge["b"]))

    # Once glow connectors/spurs disappear, degree-two nodes are not structural
    # joins. Combining their runs lets the fit remove a hook across that node.
    pending = deque(node for node, adjacent in adjacency.items() if len(adjacent) == 2)
    next_index = len(edges)
    while pending:
        node = pending.popleft()
        if len(adjacency[node]) != 2:
            continue
        first, second = tuple(adjacency[node])
        one, two = graph[first], graph[second]
        if one["a"] == one["b"] or two["a"] == two["b"]:
            continue
        left = one["points"] if one["b"] == node else one["points"][::-1]
        right = two["points"] if two["a"] == node else two["points"][::-1]
        a = one["a"] if one["b"] == node else one["b"]
        b = two["b"] if two["a"] == node else two["a"]
        remove_edge(first)
        remove_edge(second)
        graph[next_index] = {"a": a, "b": b, "points": np.vstack((left, right[1:]))}
        adjacency[a].add(next_index)
        adjacency[b].add(next_index)
        next_index += 1
        pending.extend((a, b))

    collapsed_faces = collapse_sliver_faces(graph, joins)
    pair_counts = defaultdict(int)
    for edge in graph.values():
        pair_counts[tuple(sorted((edge["a"], edge["b"])))] += 1
    constraints = defaultdict(list)
    straight_count = 0
    for edge in graph.values():
        line = edge["points"]
        samples = path_samples(line)
        length = path_length(line)
        radius = boundary_radius(float(np.mean(line[:, 1])))
        trim = min(max(1, round(radius * 1.5 / 4)), (len(samples) - 2) // 5)
        interior = samples[trim:len(samples) - trim] if trim else samples
        centre, direction, errors = fit_axis(interior)
        straight = (edge["a"] != edge["b"]
                    and pair_counts[tuple(sorted((edge["a"], edge["b"])))] == 1
                    and float(np.quantile(errors, .95)) <= max(2.1, min(12, length * .035)))
        edge["straight"] = straight
        edge["samples"] = interior
        straight_count += int(straight)
        for node, reverse in ((edge["a"], False), (edge["b"], True)):
            if straight:
                origin, axis = centre, direction
            else:
                ordered = samples[::-1] if reverse else samples
                count = min(len(ordered), max(4, math.ceil(radius * 4 / 4)))
                origin, axis, _ = fit_axis(ordered[min(trim, count // 3):count])
            normal = np.array([-axis[1], axis[0]])
            constraints[node].append((normal, float(normal @ origin), min(length, 100) ** .5))

    fitted_joins, shifts = {}, []
    for node, incident in constraints.items():
        matrix = np.eye(2) * .03
        target = joins[node] * .03
        for normal, offset, weight in incident:
            matrix += np.outer(normal, normal) * weight
            target += normal * offset * weight
        position = np.linalg.solve(matrix, target)
        shift = float(np.linalg.norm(position - joins[node]))
        maximum = boundary_radius(joins[node][1]) * 3
        if shift > maximum:
            position = joins[node] + (position - joins[node]) * maximum / shift
        shifts.append(float(np.linalg.norm(position - joins[node])))
        fitted_joins[node] = tuple(float(round(value, 3)) for value in position)

    result, seen = [], set()
    for edge in graph.values():
        a, b = fitted_joins[edge["a"]], fitted_joins[edge["b"]]
        if edge["straight"]:
            line = [a, b]
        else:
            radius = boundary_radius(float(np.mean(edge["points"][:, 1])))
            line = simplify(trim_fitted_curve(edge["samples"], a, b, radius), 2.8)
        line = [point for index, point in enumerate(line) if index == 0 or math.dist(point, line[index - 1]) > .01]
        if len(line) < 2:
            continue
        key = tuple(line)
        reverse_key = tuple(reversed(line))
        if key not in seen and reverse_key not in seen:
            result.append(line)
            seen.add(key)
    return result, {
        "weldedJunctionNodes": len(points) - len(clusters),
        "removedArtifactPaths": removed_loops,
        "prunedSpurs": pruned_spurs,
        "collapsedGlowFaces": collapsed_faces,
        "straightRuns": straight_count,
        "curvedRuns": len(graph) - straight_count,
        "maxJunctionShiftPx": round(max(shifts, default=0), 3),
    }


def clip_to_bounds(polylines, width, height):
    """Clip fitted extensions to the source rectangle without bending the runs."""
    result = []
    for line in polylines:
        current = []
        for first, last in zip(line, line[1:]):
            x, y = first
            dx, dy = last[0] - x, last[1] - y
            low, high = 0.0, 1.0
            for direction, distance in ((-dx, x), (dx, width - x), (-dy, y), (dy, height - y)):
                if direction == 0:
                    if distance < 0:
                        high = -1
                        break
                elif direction < 0:
                    low = max(low, distance / direction)
                else:
                    high = min(high, distance / direction)
            if low > high:
                if len(current) > 1:
                    result.append(current)
                current = []
                continue
            ends = [tuple(round(max(0, min(limit, origin + position * change)), 3)
                          for origin, change, limit in ((x, dx, width), (y, dy, height)))
                    for position in (low, high)]
            if ends[0] == ends[1]:
                continue
            if current and current[-1] != ends[0]:
                result.append(current)
                current = []
            if not current:
                current.append(ends[0])
            current.append(ends[1])
        if len(current) > 1:
            result.append(current)
    return result


def deduplicate_segments(polylines):
    """One geometric boundary draws once, including reversed shared segments."""
    seen, result = set(), []
    for line in polylines:
        current = []
        for a, b in zip(line, line[1:]):
            a, b = tuple(a), tuple(b)
            key = tuple(sorted((a, b)))
            if a == b or key in seen:
                if len(current) > 1:
                    result.append(current)
                current = []
                continue
            seen.add(key)
            if not current:
                current.append(a)
            current.append(b)
        if len(current) > 1:
            result.append(current)
    return result


def main() -> None:
    started = perf_counter()
    source = Image.open(SOURCE).convert("RGB")
    width, height = source.size
    offset_y = round(height * .30)
    green = source.getchannel("G").crop((0, offset_y, width, height))
    intensity = np.asarray(green, dtype=np.int16)
    local = np.asarray(green.filter(ImageFilter.GaussianBlur(12)), dtype=np.int16)
    # Bright narrow ridges identify the visible lines rather than their glowing edges.
    mask = (intensity >= 48) & (intensity - local >= 6)
    print(f"Tracing {int(np.count_nonzero(mask)):,} ridge pixels", flush=True)
    skeleton = skeletonize(mask)
    polylines, counts = trace(skeleton, offset_y)
    polylines, reconstruction = reconstruct_boundaries(polylines)
    polylines = clip_to_bounds(polylines, width, height)
    normalized = deduplicate_segments([
        [(round(x / width, 6), round(y / height, 6)) for x, y in line]
        for line in polylines
    ])
    polylines = [[(x * width, y * height) for x, y in line] for line in normalized]
    segments = sum(len(line) - 1 for line in polylines)
    metadata = {
        "method": "source ridges; skeleton topology; bounded junction welding; glow-face collapse; interior line fitting; shared geometric intersections",
        "groundBounds": [0, offset_y, width, height],
        "polylineCount": len(polylines),
        "segmentCount": segments,
        **counts,
        **reconstruction,
        "limitations": "Boundary graph reconstructed from a perspective still. Lot arrangement and road morphology retained; glowing joins and near-straight source wave artifacts regularized. Blurred horizon excluded; unresolved lots are not invented.",
    }
    payload = {
        "version": 1,
        "source": {"width": width, "height": height, "bounds": [0, 0, width, height]},
        "metadata": metadata,
        "lines": normalized,
    }
    json_path = ASSETS / "cadastral-lines.json"
    json_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    paths = "\n".join('<path d="M' + " L".join(f"{x:g},{y:g}" for x, y in line) + '"/>' for line in polylines)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" fill="none">
<title>Cadastral landscape boundary trace</title>
<desc>Source-derived boundaries reconstructed with shared fitted junctions; parcel arrangement and major road curves retained.</desc>
<g stroke="#586660" stroke-width="2" stroke-linecap="butt" stroke-linejoin="miter" stroke-miterlimit="3">
{paths}
</g>
</svg>
'''
    svg_path = ASSETS / "cadastral-lines.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(json.dumps({**metadata, "jsonBytes": json_path.stat().st_size, "svgBytes": svg_path.stat().st_size, "seconds": round(perf_counter() - started, 2)}, indent=2))


if __name__ == "__main__":
    main()
