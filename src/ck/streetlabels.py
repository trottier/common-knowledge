"""Deterministic, complete source-name labels for zoomable vector road sheets."""

import html
import math
from collections import defaultdict
from pathlib import Path

from fontTools.ttLib import TTFont
from shapely import line_merge, transform, union_all
from shapely.geometry import Polygon, box, shape


class SceneGeometryCache:
    """Optional cache for immutable source geometries during one prepared-scene render.

    Use a fresh context for each scene. Membership is bounded to that scene's road
    and water geometry dictionaries; foreign geometries are rejected. Keep this
    object outside scene/audit data, and do not mutate geometry mappings while open.
    """

    def __init__(self, scene: dict):
        self._sources = {
            id(geometry): geometry
            for geometry in [*(road["geometry"] for road in scene["roads"]), *scene["water"]]
        }
        self._geometries = {}
        self._active = False
        self._closed = False

    @property
    def capacity(self) -> int:
        return len(self._sources)

    @property
    def size(self) -> int:
        return len(self._geometries)

    def __enter__(self):
        if self._active or self._closed:
            raise RuntimeError("Use a fresh geometry-cache context for each scene")
        self._active = True
        return self

    def shape(self, geometry):
        if not self._active:
            raise RuntimeError("Geometry cache is outside its scene context")
        key = id(geometry)
        if key not in self._sources or self._sources[key] is not geometry:
            raise ValueError("Geometry does not belong to this prepared scene")
        if key not in self._geometries:
            self._geometries[key] = shape(geometry)
        return self._geometries[key]

    def __exit__(self, *_):
        self._geometries.clear()
        self._sources.clear()
        self._active = False
        self._closed = True


def nonempty_lines(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == "LineString":
        if geometry.length:
            yield geometry
    else:
        for part in getattr(geometry, "geoms", []):
            yield from nonempty_lines(part)


def street_components(roads, bounds, width, height, *, geometry_cache=None):
    """Join actual connected same-name segments; keep disconnected streets separate."""
    west, south, east, north = bounds
    frame = box(*bounds)
    groups = defaultdict(list)
    source_ids, unnamed_ids = [], []
    source_shape = geometry_cache.shape if geometry_cache is not None else shape
    ranks = {
        name: rank
        for rank, name in enumerate(
            ["motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified"]
        )
    }

    def project(x, y):
        return (x - west) / (east - west) * width, (north - y) / (north - south) * height

    for road in roads:
        parts = list(nonempty_lines(source_shape(road["geometry"]).intersection(frame)))
        if not parts:
            continue
        source_ids.append(road["id"])
        if not road["name"]:
            unnamed_ids.append(road["id"])
            continue
        for part in parts:
            groups[road["name"]].append(
                (
                    transform(part, project, interleaved=False),
                    road["id"],
                    ranks.get(road["kind"], 7),
                )
            )
    components = []
    for name, records in sorted(groups.items()):
        merged = list(nonempty_lines(line_merge(union_all([record[0] for record in records]))))
        parents = list(range(len(merged)))

        def find(index, parents=parents):
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        endpoints = {}
        for index, line in enumerate(merged):
            for coordinate in (line.coords[0], line.coords[-1]):
                if coordinate in endpoints:
                    parents[find(index)] = find(endpoints[coordinate])
                else:
                    endpoints[coordinate] = index
        connected = defaultdict(list)
        for index, line in enumerate(merged):
            connected[find(index)].append(line)
        for parts in sorted(connected.values(), key=lambda parts: union_all(parts).bounds):
            geometry = union_all(parts)
            matching = [record for record in records if record[0].intersects(geometry)]
            components.append(
                {
                    "name": name,
                    "lines": sorted(parts, key=lambda part: (-part.length, part.wkt)),
                    "source_ways": sorted({record[1] for record in matching}),
                    "rank": min(record[2] for record in matching),
                }
            )
    return components, source_ids, unnamed_ids


def street_labels(
    roads, bounds, width, height, font_path: Path, policy: dict, reserved=(), *, geometry_cache=None
):
    """Never require a full street name to fit one short OSM way."""
    components, source_ids, unnamed_ids = street_components(
        roads, bounds, width, height, geometry_cache=geometry_cache
    )
    with TTFont(font_path) as font:
        cmap = font.getBestCmap()
        advances = {chr(code): font["hmtx"][glyph][0] for code, glyph in cmap.items()}
        units = font["head"].unitsPerEm
    sizes = policy["font_sizes_mm"]
    if not sizes or any(size <= 0 for size in sizes) or sizes != sorted(set(sizes), reverse=True):
        raise ValueError("Street label sizes must be distinct, positive, and descending")
    padding, halo = policy["padding_mm"], policy["halo_mm"]
    cell_size = policy["collision_cell_mm"]
    occupied, cells = [], defaultdict(set)

    def cell_keys(bounds):
        left, top, right, bottom = bounds
        return [
            (x, y)
            for x in range(math.floor(left / cell_size), math.floor(right / cell_size) + 1)
            for y in range(math.floor(top / cell_size), math.floor(bottom / cell_size) + 1)
        ]

    def occupy(polygon):
        identifier = len(occupied)
        occupied.append(polygon)
        for key in cell_keys(polygon.bounds):
            cells[key].add(identifier)

    for rectangle in reserved:
        occupy(box(*rectangle))
    placements, missing, svg = [], [], []
    # Reserve the most difficult long names before short names consume their space.
    for component in sorted(
        components,
        key=lambda entry: (
            entry["rank"],
            -len(entry["name"]),
            entry["name"],
            entry["lines"][0].bounds,
        ),
    ):
        name = component["name"]
        preferred = sizes if component["rank"] <= 4 else sizes[1:]
        placed = None
        for size in preferred:
            text_width = sum(advances.get(char, units * 0.6) for char in name) / units * size
            half_width, half_height = text_width / 2 + padding + halo, size * 0.75 + padding + halo
            for line in component["lines"]:
                if placed:
                    break
                for fraction in policy["anchor_fractions"]:
                    if placed:
                        break
                    point = line.interpolate(fraction, normalized=True)
                    before = line.interpolate(max(0, fraction - 0.05), normalized=True)
                    after = line.interpolate(min(1, fraction + 0.05), normalized=True)
                    angle = math.atan2(after.y - before.y, after.x - before.x)
                    if angle > math.pi / 2:
                        angle -= math.pi
                    if angle < -math.pi / 2:
                        angle += math.pi
                    for offset in policy["offsets_mm"]:
                        if placed:
                            break
                        for orientation in dict.fromkeys([angle, 0.0]):
                            cosine, sine = math.cos(orientation), math.sin(orientation)
                            x = point.x - math.sin(angle) * offset
                            y = point.y + math.cos(angle) * offset
                            corners = [
                                (x + dx * cosine - dy * sine, y + dx * sine + dy * cosine)
                                for dx, dy in [
                                    (-half_width, -half_height),
                                    (half_width, -half_height),
                                    (half_width, half_height),
                                    (-half_width, half_height),
                                ]
                            ]
                            polygon = Polygon(corners)
                            left, top, right, bottom = polygon.bounds
                            if (
                                left < 0.5
                                or top < 0.5
                                or right > width - 0.5
                                or bottom > height - 0.5
                            ):
                                continue
                            neighbors = set().union(
                                *(cells[key] for key in cell_keys(polygon.bounds))
                            )
                            if any(polygon.intersects(occupied[index]) for index in neighbors):
                                continue
                            occupy(polygon)
                            callout = abs(offset) > size
                            if callout:
                                svg.append(
                                    f'<path d="M{point.x:.3f},{point.y:.3f} L{x:.3f},{y:.3f}" '
                                    'stroke="#555" stroke-width="0.12" fill="none"/>'
                                )
                            rotation = math.degrees(orientation)
                            attributes = (
                                f'x="{x:.3f}" y="{y + size * 0.32:.3f}" text-anchor="middle" '
                                f'font-size="{size}" '
                                f'transform="rotate({rotation:.3f} {x:.3f} {y:.3f})"'
                            )
                            escaped = html.escape(name)
                            svg.append(
                                f'<text {attributes} fill="#faf8ef" stroke="#faf8ef" '
                                f'stroke-width="{halo * 2}" stroke-linejoin="round">'
                                f"{escaped}</text>"
                            )
                            svg.append(f'<text {attributes} fill="#111">{escaped}</text>')
                            placed = {
                                "name": name,
                                "source_ways": component["source_ways"],
                                "x_mm": x,
                                "y_mm": y,
                                "font_size_mm": size,
                                "callout": callout,
                            }
                            placements.append(placed)
                            break
            if placed:
                break
        if not placed:
            missing.append({"name": name, "source_ways": component["source_ways"]})
    return "".join(svg), {
        "source_way_ids": source_ids,
        "unnamed_source_way_ids": unnamed_ids,
        "named_components": len(components),
        "source_names": sorted({component["name"] for component in components}),
        "placed_labels": placements,
        "missing_labels": missing,
    }
