"""Shared, unsimplified OSM road/place extraction and exact viewport selection."""

from collections import Counter
from pathlib import Path

import osmium
from shapely import from_wkb, transform
from shapely.geometry import Point, mapping

from ck.directory import excluded

PLACE_VALUES = {"city", "town", "village", "hamlet", "suburb"}


def source_features(source: Path, project, allowed: set[str], on_road, on_place) -> None:
    factory = osmium.geom.WKBFactory()

    class Handler(osmium.SimpleHandler):
        def node(self, node):
            tags = dict(node.tags)
            if tags.get("place") in PLACE_VALUES and tags.get("name"):
                x, y = project(node.location.lon, node.location.lat)
                on_place({"name": tags["name"], "x": x, "y": y, "id": f"n{node.id}"})

        def way(self, way):
            tags = dict(way.tags)
            if tags.get("highway") not in allowed or excluded(tags):
                return
            geometry = transform(
                from_wkb(factory.create_linestring(way)), project, interleaved=False
            )
            on_road(
                {
                    "id": way.id,
                    "kind": tags["highway"],
                    "name": tags.get("name", ""),
                    "ref": tags.get("ref", ""),
                    "access": tags.get("access", ""),
                },
                geometry,
            )

    Handler().apply_file(osmium.io.File(str(source), "pbf"), locations=True, idx="flex_mem")


def clipped_road(record: dict, geometry, extent) -> dict | None:
    clipped = geometry.intersection(extent)
    return None if clipped.is_empty else {**record, "geometry": mapping(clipped)}


def select_source(source: Path, project, extent, allowed: set[str], maximum: int):
    roads, places = [], []
    counts = Counter()

    def road(record, geometry):
        selected = clipped_road(record, geometry, extent)
        if selected is None:
            return
        if len(roads) >= maximum:
            raise ValueError("Prototype source-way guard reached; no ways silently dropped")
        roads.append(selected)
        counts[selected["kind"]] += 1

    def place(record):
        if extent.covers(Point(record["x"], record["y"])):
            places.append(record)

    source_features(source, project, allowed, road, place)
    return (
        sorted(roads, key=lambda x: x["id"]),
        sorted(places, key=lambda x: x["id"]),
        dict(sorted(counts.items())),
    )
