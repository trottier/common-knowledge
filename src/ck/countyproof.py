"""Bounded county/area vector-PDF experiments; never adopt historical catalog pins."""

import csv
import gzip
import hashlib
import html
import json
import math
import resource
import time
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import geopandas as gpd
import mapbox_vector_tile
import osmium
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup
from pmtiles.reader import Reader
from pmtiles.tile import Compression
from pypdf import PdfReader
from pyproj import Transformer
from shapely import from_wkb, transform
from shapely.geometry import Point, box, mapping, shape
from weasyprint import HTML

from ck.catalog import load_catalog, safe_path
from ck.config import load_config, read_yaml
from ck.directory import excluded
from ck.generated import cached_input, verified_generated_files
from ck.geo import dms
from ck.geofonts import font_records, require_glyphs
from ck.render import OfflineFetcher, pdf_timestamp


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def producer_recipe(root: Path, policy_path: Path | None = None) -> dict:
    policy_path = policy_path or root / "pipelines/atlas/bristol-proof.json"
    selected_policy = policy_path.resolve().relative_to(root.resolve()).as_posix()
    paths = [
        "src/ck/countyproof.py",
        "src/ck/streetlabels.py",
        "src/ck/streetcoverage.py",
        "tools/prototype_county_map.py",
        selected_policy,
        "templates/county-proof.html.j2",
        "src/ck/render.py",
        "src/ck/geo.py",
        "src/ck/geofonts.py",
        "src/ck/directory.py",
        "src/ck/catalog.py",
        "src/ck/config.py",
        "src/ck/generated.py",
        "pipelines/geodata-fonts.yaml",
        "pipelines/androidmaps/settings.yaml",
        "pyproject.toml",
        "uv.lock",
        "Dockerfile.build",
        "config/debian.sources",
    ]
    hashes = {name: sha(root / name) for name in sorted(paths)}
    digest = hashlib.sha256(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"version": "county-vector-proof-v1-" + digest, "source_files": hashes}


def area_geometry(county, features: list[dict], policy: dict):
    """Use the whole county unless an explicitly named, bounded trial scope is selected."""
    from shapely import union_all

    selected = policy.get("scope_zctas")
    if selected is None:
        return county, {"kind": "county", "whole_county": True}
    if (
        not selected
        or sorted(set(selected)) != selected
        or selected != policy["expected_zctas"]
        or not policy.get("area_name")
    ):
        raise ValueError("Area trial needs an explicit name and unique verified ZIP-area scope")
    by_code = {feature["properties"]["GEOID"]: feature for feature in features}
    if len(by_code) != len(features) or not set(selected) <= by_code.keys():
        raise ValueError("Selected ZIP-area scope is absent or duplicated in pinned geometry")
    geometry = county.intersection(
        union_all([shape(by_code[code]["geometry"]) for code in selected])
    )
    if geometry.is_empty or not geometry.is_valid or geometry.area <= 0:
        raise ValueError("Selected ZIP-area scope does not intersect the county")
    return geometry, {
        "kind": "county_intersection_with_2020_zctas",
        "whole_county": False,
        "zctas": selected,
    }


def output_names(policy: dict, codes: list[str]) -> tuple[Path, str, str]:
    name = policy.get("area_name", policy["county_name"])
    for component in [name, policy["county_name"], policy["state"]]:
        if len(safe_path(component).parts) != 1:
            raise ValueError("Map names must be single FAT-safe folder or leaf components")
    leaf = name + " " + ",".join(codes) + ".pdf"
    folder = safe_path("3_MAPS_AND_PLACES/" + policy["state"] + "/" + policy["county_name"])
    safe_path(str(folder / leaf))
    return Path(folder), leaf, name


def check_intermediates(folder: Path, metadata: dict) -> None:
    for entry in metadata.get("intermediates", []):
        path = folder / entry["path"]
        if (
            path.is_symlink()
            or path.stat().st_size != entry["size_bytes"]
            or sha(path) != entry["sha256"]
        ):
            raise ValueError("Historical intermediate changed: " + str(path))


def sheet_plan(geometry, policy: dict) -> list[dict]:
    """County coverage first; boundaries do not shrink the chosen detail scale."""
    width = policy["map_width_mm"] * policy["scale_denominator"] / 1000
    height = policy["map_height_mm"] * policy["scale_denominator"] / 1000
    step_x = width * (1 - policy["overlap_fraction"])
    step_y = height * (1 - policy["overlap_fraction"])
    left, bottom, right, top = geometry.bounds
    columns = max(1, math.ceil(max(0, right - left - width) / step_x) + 1)
    rows = max(1, math.ceil(max(0, top - bottom - height) / step_y) + 1)
    if columns * rows > policy["max_pages"] - 1:
        raise ValueError("Prototype exceeds its explicit sheet guard; no coverage dropped")
    left -= (width + (columns - 1) * step_x - (right - left)) / 2
    top += (height + (rows - 1) * step_y - (top - bottom)) / 2
    result = []
    for row in range(rows):
        for column in range(columns):
            bounds = [
                left + column * step_x,
                top - row * step_y - height,
                left + column * step_x + width,
                top - row * step_y,
            ]
            if geometry.intersects(box(*bounds)):
                result.append(
                    {
                        "id": f"R{row + 1}C{column + 1}",
                        "row": row,
                        "column": column,
                        "bounds": bounds,
                        "page": len(result) + 2,
                    }
                )
    present = {(entry["row"], entry["column"]): entry for entry in result}
    for entry in result:
        entry["neighbors"] = {
            label: present[(entry["row"] + dy, entry["column"] + dx)]["id"]
            for label, dx, dy in [
                ("north", 0, -1),
                ("east", 1, 0),
                ("south", 0, 1),
                ("west", -1, 0),
            ]
            if (entry["row"] + dy, entry["column"] + dx) in present
        }
    from shapely import union_all

    if geometry.difference(union_all([box(*entry["bounds"]) for entry in result])).area > 0.01:
        raise ValueError("Sheet plan leaves county coverage gaps")
    return result


def read_roads(
    source: Path, project, extent, allowed: set[str], maximum: int
) -> tuple[list, list, dict]:
    roads, settlements = [], []
    counts = Counter()
    factory = osmium.geom.WKBFactory()

    class Handler(osmium.SimpleHandler):
        def node(self, node):
            tags = dict(node.tags)
            if tags.get("place") not in {
                "city",
                "town",
                "village",
                "hamlet",
                "suburb",
            } or not tags.get("name"):
                return
            x, y = project(node.location.lon, node.location.lat)
            if extent.covers(Point(x, y)):
                settlements.append({"name": tags["name"], "x": x, "y": y, "id": f"n{node.id}"})

        def way(self, way):
            tags = dict(way.tags)
            if tags.get("highway") not in allowed or excluded(tags):
                return
            line = transform(from_wkb(factory.create_linestring(way)), project, interleaved=False)
            clipped = line.intersection(extent)
            if clipped.is_empty:
                return
            if len(roads) >= maximum:
                raise ValueError("Prototype source-way guard reached; no ways silently dropped")
            roads.append(
                {
                    "id": way.id,
                    "kind": tags["highway"],
                    "name": tags.get("name", ""),
                    "ref": tags.get("ref", ""),
                    "access": tags.get("access", ""),
                    "geometry": mapping(clipped),
                }
            )
            counts[tags["highway"]] += 1

    Handler().apply_file(osmium.io.File(str(source), "pbf"), locations=True, idx="flex_mem")
    return (
        sorted(roads, key=lambda entry: entry["id"]),
        sorted(settlements, key=lambda x: x["id"]),
        dict(sorted(counts.items())),
    )


def water_polygons(source: Path, extent, inverse, project, policy: dict) -> tuple[list, dict]:
    """Decode only bounded water geometry; no POI/infrastructure tile properties."""
    geographic = transform(extent, inverse, interleaved=False)
    west, south, east, north = geographic.bounds
    z = policy["water_zoom"]
    n = 2**z

    def tile(longitude, latitude):
        return math.floor((longitude + 180) / 360 * n), math.floor(
            (1 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2 * n
        )

    x0, y0 = tile(west, north)
    x1, y1 = tile(east, south)
    if (x1 - x0 + 1) * (y1 - y0 + 1) > policy["max_water_tiles"]:
        raise ValueError("Water tile guard exceeded")
    polygons, missing, used = [], [], []
    with source.open("rb") as stream:

        def read(offset, length):
            stream.seek(offset)
            return stream.read(length)

        reader = Reader(read)
        header = reader.header()
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                payload = reader.get(z, x, y)
                if payload is None:
                    missing.append([z, x, y])
                    continue
                raw = (
                    gzip.decompress(payload)
                    if header["tile_compression"] == Compression.GZIP
                    else payload
                )
                if len(raw) > policy["max_decoded_tile_bytes"]:
                    raise ValueError("Decoded tile exceeds prototype guard")
                layers = mapbox_vector_tile.decode(raw, default_options={"y_coord_down": True})
                used.append([z, x, y])
                layer = layers.get("water")
                if not layer:
                    continue
                size = layer["extent"]

                def convert(xs, ys, x=x, y=y, size=size):
                    longitudes = tuple((x + value / size) / n * 360 - 180 for value in xs)
                    latitudes = tuple(
                        math.degrees(
                            math.atan(math.sinh(math.pi * (1 - 2 * (y + value / size) / n)))
                        )
                        for value in ys
                    )
                    return project(longitudes, latitudes)

                for feature in layer["features"]:
                    if feature["geometry"]["type"] not in {"Polygon", "MultiPolygon"}:
                        continue
                    polygon = transform(shape(feature["geometry"]), convert, interleaved=False)
                    if not polygon.is_valid:
                        raise ValueError("Source water polygon needs an explicit repair decision")
                    clipped = polygon.intersection(extent)
                    if not clipped.is_empty:
                        polygons.append(mapping(clipped))
    return polygons, {"used_tiles": used, "missing_tiles": missing, "zoom": z}


def prepare(
    root: Path, cache: Path, basemap: Path, points: Path, zip_source: Path, policy: dict
) -> dict:
    county_id = policy.get("county", "")
    if (
        policy.get("state") != "RI"
        or not isinstance(county_id, str)
        or len(county_id) != 5
        or not county_id.isdecimal()
        or not county_id.startswith("44")
    ):
        raise ValueError(
            "This county proof currently admits the pinned Rhode Island source set only"
        )
    items = load_catalog(root, load_config(root))
    ids = ["census_county_analysis", "geofabrik_ri"]
    raw = {key: cached_input(items[key], cache) for key in ids}
    basemap_meta, basemap_files = verified_generated_files(items["protomaps_ri"], basemap, items)
    points_meta, point_files = verified_generated_files(
        items["directory_ri"], points, items, allow_incomplete=True
    )
    check_intermediates(basemap, basemap_meta)
    check_intermediates(points, points_meta)
    if (
        basemap_meta["source_date_epoch"] != policy["epoch"]
        or points_meta["source_date_epoch"] != policy["epoch"]
    ):
        raise ValueError("Prototype historical sources have a different epoch")
    zip_item = items["census_zcta_county_2020"]
    if zip_source.stat().st_size != zip_item.size_bytes or sha(zip_source) != zip_item.sha256:
        raise ValueError("ZIP relationship source differs from measured research input")
    with zip_source.open() as stream:
        codes = sorted(
            {
                row["GEOID_ZCTA5_20"]
                for row in csv.DictReader(stream, delimiter="|")
                if row["GEOID_COUNTY_20"] == policy["county"] and row["GEOID_ZCTA5_20"]
            }
        )
    if policy.get("scope_zctas") is not None:
        if not set(policy["scope_zctas"]) <= set(codes):
            raise ValueError("Selected ZIP-area scope has no verified county relationship")
        codes = policy["scope_zctas"]
    if codes != policy["expected_zctas"]:
        raise ValueError("Actual county ZIP-area list differs from naming fixture")
    zip_geometry_item = items[policy["zcta_geometry_id"]]
    zip_geometry_path = cached_input(zip_geometry_item, cache)
    zip_features = json.loads(zip_geometry_path.read_text())["features"]
    if sorted(feature["properties"]["GEOID"] for feature in zip_features) != policy.get(
        "geometry_expected_zctas", codes
    ):
        raise ValueError("ZIP geometry and county relationship codes differ")
    county = gpd.read_file(
        f"/vsizip/{{{raw['census_county_analysis']}}}", where=f"GEOID='{policy['county']}'"
    ).to_crs(4326)
    if len(county) != 1 or county.iloc[0]["NAMELSAD"] != policy["county_name"]:
        raise ValueError("Expected exactly the named county")
    selected_county, coverage_scope = area_geometry(county.geometry.iloc[0], zip_features, policy)
    crs = county.estimate_utm_crs()
    forward = Transformer.from_crs(4326, crs, always_xy=True)
    backward = Transformer.from_crs(crs, 4326, always_xy=True)
    geometry = transform(selected_county, forward.transform, interleaved=False)
    zip_areas = []
    for feature in sorted(zip_features, key=lambda feature: feature["properties"]["GEOID"]):
        properties = feature["properties"]
        if properties["GEOID"] not in codes:
            continue
        area = shape(feature["geometry"])
        interior = Point(float(properties["INTPTLON"]), float(properties["INTPTLAT"]))
        if not area.is_valid or area.is_empty or not area.covers(interior):
            raise ValueError("Invalid ZIP area or Census interior point")
        zip_areas.append(
            {
                "code": properties["GEOID"],
                "geometry": mapping(transform(area, forward.transform, interleaved=False)),
                "label_point": list(forward.transform(interior.x, interior.y)),
            }
        )
    sheets = sheet_plan(geometry, policy)
    from shapely import union_all

    extent = union_all([box(*sheet["bounds"]) for sheet in sheets])
    road_policy = read_yaml(root / "pipelines/androidmaps/settings.yaml")
    roads, settlements, road_counts = read_roads(
        raw["geofabrik_ri"],
        forward.transform,
        extent,
        set(road_policy["road_values"]),
        policy["max_source_ways"],
    )
    water, water_audit = water_polygons(
        basemap_files["RI.pmtiles"], extent, backward.transform, forward.transform, policy
    )
    source = json.loads(point_files["RI_SOURCE_DATA.json"].read_text())
    pois = [
        dict(point)
        for point in source["places"]
        if point["county"] == policy["county"]
        and selected_county.covers(Point(point["longitude"], point["latitude"]))
    ]
    if len({point["id"] for point in pois}) != len(pois):
        raise ValueError("Historical source contains duplicate selected public-place IDs")
    if "expected_poi_count" in policy and len(pois) != policy["expected_poi_count"]:
        raise ValueError("Actual selected public-place count differs from the frozen scope")
    for index, point in enumerate(pois, 1):
        point["number"] = index
        point["x"], point["y"] = forward.transform(point["longitude"], point["latitude"])
    fonts = font_records(root, items, cache)
    require_glyphs(
        [road["name"] for road in roads] + [point["name"] for point in pois],
        [Path(font["path"]) for font in fonts],
    )
    inputs = {
        key: {
            "sha256": items[key].sha256,
            "size_bytes": items[key].size_bytes,
            "version": items[key].version,
        }
        for key in ids
    }
    inputs[zip_item.id] = {
        "sha256": zip_item.sha256,
        "size_bytes": zip_item.size_bytes,
        "version": zip_item.version,
    }
    inputs[zip_geometry_item.id] = {
        "sha256": zip_geometry_item.sha256,
        "size_bytes": zip_geometry_item.size_bytes,
        "version": zip_geometry_item.version,
    }
    return {
        "policy": policy,
        "inputs": inputs,
        "county": mapping(geometry),
        "coverage_scope": coverage_scope,
        "crs": crs.to_string(),
        "sheets": sheets,
        "roads": roads,
        "settlements": settlements,
        "water": water,
        "water_audit": water_audit,
        "pois": pois,
        "fonts": fonts,
        "historical_basemap": {
            "manifest": basemap_meta,
            "raw_manifest_sha256": sha(basemap / "generation.json"),
        },
        "historical_points": {
            "manifest": points_meta,
            "source_payload_sha256": sha(point_files["RI_SOURCE_DATA.json"]),
            "complete": points_meta["complete"],
        },
        "road_counts": road_counts,
        "zip_source_sha256": sha(zip_source),
        "zctas": codes,
        "zip_areas": zip_areas,
    }


def lines(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == "LineString":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from lines(part)


def geometry_path(geometry, pixel) -> str:
    if geometry.is_empty:
        return ""
    if geometry.geom_type in {"Polygon", "LineString", "LinearRing"}:
        rings = (
            [geometry.exterior, *geometry.interiors]
            if geometry.geom_type == "Polygon"
            else [geometry]
        )
        result = []
        for ring in rings:
            points = [pixel(x, y) for x, y in ring.coords]
            result.append(
                "M"
                + " L".join(f"{x:.3f},{y:.3f}" for x, y in points)
                + (" Z" if geometry.geom_type == "Polygon" else "")
            )
        return " ".join(result)
    return " ".join(geometry_path(part, pixel) for part in getattr(geometry, "geoms", []))


def scale_bar_geometry(world_width: float, width_mm: float, maximum_mm: float):
    if world_width <= 0 or not 0 < maximum_mm < width_mm - 16:
        raise ValueError("Invalid scale bar extent or reserved width")
    target = world_width * maximum_mm / width_mm
    magnitude = 10 ** math.floor(math.log10(target))
    metres = max(value * magnitude for value in (1, 2, 5) if value * magnitude <= target)
    return metres, metres / world_width * width_mm


def zip_overlay(data: dict, frame, pixel):
    areas, labels, reserved = [], [], []
    for index, area in enumerate(data.get("zip_areas", [])):
        color = data["policy"]["zcta_colors"][index % len(data["policy"]["zcta_colors"])]
        path = geometry_path(shape(area["geometry"]).intersection(frame), pixel)
        areas.append(
            f'<path d="{path}" fill="{color}" fill-opacity="0.12" '
            f'stroke="{color}" stroke-width="0.55" fill-rule="evenodd"/>'
        )
        x, y = pixel(*area["label_point"])
        label_y = y - 5
        reserved.append((x - 10, label_y - 4, x + 10, label_y + 4))
        labels.append(
            f'<path d="M{x:.3f},{y:.3f} V{label_y:.3f}" stroke="{color}" '
            'stroke-width="0.35"/>'
            f'<rect x="{x - 9:.3f}" y="{label_y - 3.8:.3f}" width="18" height="7.6" '
            f'rx="1" fill="white" stroke="{color}" stroke-width="0.55"/>'
            f'<text x="{x:.3f}" y="{label_y + 1.6:.3f}" text-anchor="middle" '
            f'font-size="4.8" font-weight="700" fill="{color}">{area["code"]}</text>'
        )
    return "".join(areas), "".join(labels), reserved


def svg_map(data: dict, bounds: list, overview: bool = False) -> tuple[str, dict]:
    from ck.streetlabels import street_labels

    width, height = data["policy"]["map_width_mm"], data["policy"]["map_height_mm"]
    west, south, east, north = bounds
    frame = box(*bounds)

    def pixel(x, y):
        return (x - west) / (east - west) * width, (north - y) / (north - south) * height

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm" '
        f'viewBox="0 0 {width} {height}">',
        f'<defs><clipPath id="frame"><rect width="{width}" height="{height}"/></clipPath></defs>',
        f'<rect width="{width}" height="{height}" fill="#faf8ef"/>',
        '<g clip-path="url(#frame)">',
    ]
    vertex_count = 0
    for entry in data["water"]:
        geometry = shape(entry).intersection(frame)
        path = geometry_path(geometry, pixel)
        if path:
            svg.append(f'<path d="{path}" fill="#daeef8" fill-rule="evenodd"/>')
    zip_shapes, zip_labels, zip_reserved = (
        zip_overlay(data, frame, pixel) if overview else ("", "", [])
    )
    svg.append(zip_shapes)
    road_features = []
    ranking = {
        "motorway": 0,
        "trunk": 1,
        "primary": 2,
        "secondary": 3,
        "tertiary": 4,
        "residential": 5,
        "unclassified": 6,
    }
    for road in data["roads"]:
        clipped = shape(road["geometry"]).intersection(frame)
        segments = list(lines(clipped))
        if not segments:
            continue
        vertex_count += sum(len(segment.coords) for segment in segments)
        if vertex_count > data["policy"]["max_vertices_per_sheet"]:
            raise ValueError("Sheet vertex guard exceeded; split explicitly")
        road_features.append(road["id"])
        priority = ranking.get(road["kind"], 7)
        stroke = "#d29042" if priority <= 2 else "#8c8c83" if priority <= 6 else "#b4afa4"
        line_width = (0.65 if priority <= 2 else 0.40 if priority <= 4 else 0.23) * (
            0.60 if overview else 1
        )
        dash = (
            ' stroke-dasharray="1,1"'
            if road["kind"] in {"path", "footway", "track", "cycleway", "steps", "bridleway"}
            or road["access"] == "private"
            else ""
        )
        svg.append(
            f'<path d="{geometry_path(clipped, pixel)}" fill="none" stroke="{stroke}" '
            f'stroke-width="{line_width}"{dash}/>'
        )
    county_path = geometry_path(shape(data["county"]).intersection(frame), pixel)
    svg.append(
        f'<path d="{county_path}" fill="none" stroke="#625f55" '
        'stroke-width="0.25" stroke-dasharray="1.5,1"/>'
    )
    label_roads = data["roads"]
    if overview:
        label_roads = [
            road for road in label_roads if road["kind"] in data["policy"]["overview_road_classes"]
        ]
    town_reserved = []
    for place in data.get("settlements", []):
        x, y = pixel(place["x"], place["y"])
        if 5 <= x <= width - 5 and 10 <= y <= height - 10:
            half_width = len(place["name"]) * 3.5 * 0.35 + 1
            town_reserved.append((x - half_width, y - 4, x + half_width, y + 1))
    label_svg, label_audit = street_labels(
        label_roads,
        bounds,
        width,
        height,
        Path(data["fonts"][0]["path"]),
        data["policy"]["street_labels"],
        [
            (0, 0, width, 9),
            (0, 9, 4, height),
            (6, height - 16, 14 + data["policy"]["scale_bar_max_width_mm"], height),
            (174, 12, 189, 28),
            *zip_reserved,
            *town_reserved,
        ],
    )
    placed = label_audit["placed_labels"]
    settlement_labels = []
    for place in data.get("settlements", []):
        x, y = pixel(place["x"], place["y"])
        if 5 <= x <= width - 5 and 10 <= y <= height - 10:
            svg.append(
                f'<text x="{x:.3f}" y="{y:.3f}" text-anchor="middle" '
                f'font-size="3.5" font-weight="700">{html.escape(place["name"])}</text>'
            )
            settlement_labels.append({"name": place["name"], "source_id": place["id"]})
    if overview:
        for point in data["pois"]:
            x, y = pixel(point["x"], point["y"])
            svg.append(
                f'<circle cx="{x:.3f}" cy="{y:.3f}" r="1.3" fill="#a53124"/>'
                f'<text x="{x + 1.7:.3f}" y="{y:.3f}" font-size="2.8" fill="#222">'
                f"{point['number']}</text>"
            )
    svg.append("</g>")
    inverse = Transformer.from_crs(data["crs"], 4326, always_xy=True)
    for column in range(1, 5):
        x = width * column / 5
        svg.append(
            f'<path d="M{x},0 V{height}" stroke="#aaa" '
            'stroke-width="0.12" stroke-dasharray="0.8,1"/>'
        )
    for row in range(1, 6):
        y = height * row / 6
        svg.append(
            f'<path d="M0,{y} H{width}" stroke="#aaa" '
            'stroke-width="0.12" stroke-dasharray="0.8,1"/>'
        )
    coordinates = []
    for y in [0, height]:
        for x in [0, width]:
            lon, lat = inverse.transform(
                west + x / width * (east - west), north - y / height * (north - south)
            )
            text = f"{lat:.4f}°, {lon:.4f}° · {dms(lat, 'lat')} {dms(lon, 'lon')}"
            coordinates.append(text)
            anchor = "start" if x == 0 else "end"
            svg.append(
                f'<text x="{x + (1 if x == 0 else -1)}" '
                f'y="{4 if y == 0 else height - 1}" text-anchor="{anchor}" '
                f'font-size="2.2">{html.escape(text)}</text>'
            )
    for column in range(5):
        svg.append(
            f'<text x="{width * (column + 0.5) / 5}" y="8" '
            f'font-size="2.6">{chr(65 + column)}</text>'
        )
    for row in range(6):
        svg.append(f'<text x="1" y="{height * (row + 0.5) / 6}" font-size="2.6">{row + 1}</text>')
    metres, mm = scale_bar_geometry(east - west, width, data["policy"]["scale_bar_max_width_mm"])
    svg.append(
        f'<rect x="6" y="{height - 14}" width="{mm + 4}" height="8" fill="white"/>'
        f'<path d="M8,{height - 11} h{mm}" stroke="black" stroke-width="0.6"/>'
        f'<text x="8" y="{height - 7}" font-size="2.6">{metres:g} m</text>'
    )
    svg.append(
        '<path d="M180,20 L178,25 L180,23 L182,25 Z" fill="black"/>'
        '<text x="177" y="18" font-size="2.5">Grid N</text>'
    )
    svg.append('<g clip-path="url(#frame)">' + label_svg + zip_labels + "</g>")
    svg.append("</svg>")
    return "".join(svg), {
        "road_source_ids": road_features,
        "road_vertices": vertex_count,
        "placed_labels": placed,
        "settlement_labels": settlement_labels,
        "street_name_coverage": label_audit,
        "coordinate_labels": coordinates,
        "grid_columns": "ABCDE",
        "grid_rows": [1, 2, 3, 4, 5, 6],
        "scale_bar": {"metres": metres, "width_mm": mm},
        "zip_area_labels": [area["code"] for area in data.get("zip_areas", [])] if overview else [],
    }


def svg_locator(data: dict) -> tuple[str, dict]:
    """Geographic page selection, separate from the county's POI overview."""
    width, height = data["policy"]["map_width_mm"], data["policy"]["map_height_mm"]
    west = min(sheet["bounds"][0] for sheet in data["sheets"])
    south = min(sheet["bounds"][1] for sheet in data["sheets"])
    east = max(sheet["bounds"][2] for sheet in data["sheets"])
    north = max(sheet["bounds"][3] for sheet in data["sheets"])
    frame = box(west, south, east, north)

    def pixel(x, y):
        return (x - west) / (east - west) * width, (north - y) / (north - south) * height

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}mm" height="{height}mm">',
        f'<rect width="{width}" height="{height}" fill="#faf8ef"/>',
    ]
    for water in data["water"]:
        path = geometry_path(shape(water).intersection(frame), pixel)
        if path:
            svg.append(f'<path d="{path}" fill="#daeef8" fill-rule="evenodd"/>')
    for road in data["roads"]:
        if road["kind"] in {"motorway", "trunk", "primary", "secondary"}:
            path = geometry_path(shape(road["geometry"]).intersection(frame), pixel)
            svg.append(f'<path d="{path}" fill="none" stroke="#d29042" stroke-width="0.5"/>')
    path = geometry_path(shape(data["county"]), pixel)
    svg.append(f'<path d="{path}" fill="none" stroke="#615c54" stroke-width="0.6"/>')
    for sheet in data["sheets"]:
        left, bottom, right, top = sheet["bounds"]
        x, y = pixel(left, top)
        x2, y2 = pixel(right, bottom)
        svg.append(
            f'<rect x="{x:.3f}" y="{y:.3f}" width="{x2 - x:.3f}" '
            f'height="{y2 - y:.3f}" fill="none" stroke="#2674ad" stroke-width="0.65"/>'
        )
        svg.append(
            f'<text x="{x + 2:.3f}" y="{y + 7:.3f}" font-size="5.5" '
            f'font-weight="700" fill="#155481">{sheet["id"]}</text>'
        )
    labels = []
    for place in data.get("settlements", []):
        x, y = pixel(place["x"], place["y"])
        if 8 < x < width - 8 and 8 < y < height - 8:
            svg.append(
                f'<text x="{x:.3f}" y="{y:.3f}" text-anchor="middle" '
                f'font-size="4.8" font-weight="700">{html.escape(place["name"])}</text>'
            )
            labels.append(place["name"])
    svg.append("</svg>")
    return "".join(svg), {
        "bounds": [west, south, east, north],
        "sheet_ids": [sheet["id"] for sheet in data["sheets"]],
        "settlement_labels": labels,
        "poi_markers": False,
    }


def html_document(
    root: Path,
    title: str,
    kind: str,
    pages: list,
    overview_svg: str,
    locator_svg: str,
    leaf: str,
    data: dict,
) -> str:
    env = Environment(
        loader=FileSystemLoader(root / "templates"),
        undefined=StrictUndefined,
        autoescape=True,
    )
    return env.get_template("county-proof.html.j2").render(
        title=title,
        kind=kind,
        pages=pages,
        overview_svg=Markup(overview_svg),
        locator_svg=Markup(locator_svg),
        leaf=leaf,
        policy=data["policy"],
        area_name=data["policy"].get("area_name", data["policy"]["county_name"]),
        zctas=data["zctas"],
        pois=data["pois"],
        timestamp=datetime.fromtimestamp(data["policy"]["epoch"], UTC).isoformat(),
        fonts=[{**font, "uri": Path(font["path"]).as_uri()} for font in data["fonts"]],
        families=",".join(f"CK{index}" for index in range(len(data["fonts"]))),
    )


def horizontal_layout(document) -> list[dict]:
    """Inspect actual pinned-WeasyPrint layout; pagination alone misses clipped tables."""
    checked = []
    for number, page in enumerate(document.pages, 1):
        for element in page._page_box.descendants():
            tag = str(element.element_tag).rsplit("}", 1)[-1]
            if tag not in {"svg", "table", "th", "td"}:
                continue
            left = element.border_box_x()
            right = left + element.border_width()
            checked.append(
                {
                    "page": number,
                    "tag": tag,
                    "left_px": left,
                    "right_px": right,
                    "page_width_px": page.width,
                }
            )
            if left < -0.5 or right > page.width + 0.5:
                raise ValueError(f"Horizontal {tag} overflow on page {number}: {left}..{right}")
    return checked


def render(root: Path, data: dict, output: Path) -> dict:
    from ck.streetcoverage import complete_detail_sheets

    if output.exists():
        raise ValueError("Choose a new proof output; no overwrite")
    output.mkdir(parents=True)
    folder, leaf, area_name = output_names(data["policy"], data["zctas"])
    files = output / folder
    files.mkdir(parents=True)
    audit = output / "audit"
    audit.mkdir()
    policy = data["policy"]
    rendered_sheets, street_coverage = complete_detail_sheets(data, svg_map)
    by_id = {sheet["id"]: sheet for sheet, _, _ in rendered_sheets}
    road_names = {road["id"]: road["name"] for road in data["roads"]}
    sheet_audits, pages = [], []
    for sheet, svg, measured in rendered_sheets:
        (audit / (sheet["id"] + ".svg")).write_text(svg)
        neighbors = "; ".join(
            f"{direction}: {identifier}, page {by_id[identifier]['page']}"
            for direction, identifier in sheet["neighbors"].items()
        )
        children = [child for child, _, _ in rendered_sheets if child.get("parent") == sheet["id"]]
        if children:
            neighbors += "; enlarged streets: " + (
                ", ".join(f"{child['id']} p{child['page']}" for child in children)
                if len(children) <= 5
                else "see the index at the end"
            )
        target_name = road_names.get(sheet.get("target_way_id"), "")
        if target_name:
            neighbors = f"Enlarged streets near {target_name}; " + neighbors
        pages.append(
            {
                **sheet,
                "svg": Markup(svg),
                "continuation": neighbors or "County edge: use the locator",
                "target_name": target_name,
            }
        )
        sheet_audits.append({**sheet, **measured, "pdf": leaf})
    county = shape(data["county"])
    left, bottom, right, top = county.bounds
    width = (
        max(right - left, (top - bottom) * policy["map_width_mm"] / policy["map_height_mm"]) * 1.04
    )
    height = width * policy["map_height_mm"] / policy["map_width_mm"]
    cx, cy = (left + right) / 2, (bottom + top) / 2
    overview_svg, overview_audit = svg_map(
        data, [cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2], True
    )
    (audit / "overview.svg").write_text(overview_svg)
    locator_svg, locator_audit = svg_locator(data)
    (audit / "locator.svg").write_text(locator_svg)
    layout_audits = {}
    for filename, title, kind in [
        (leaf, area_name + " detailed road maps", "detail"),
        ("0_OVERVIEW.pdf", area_name + " overview and historical places", "overview"),
    ]:
        document = html_document(root, title, kind, pages, overview_svg, locator_svg, leaf, data)
        (audit / (filename + ".html")).write_text(document)
        with pdf_timestamp(policy["epoch"]):
            document_pdf = HTML(
                string=document,
                url_fetcher=OfflineFetcher([Path(font["path"]).parent for font in data["fonts"]]),
            ).render()
            layout_audits[filename] = horizontal_layout(document_pdf)
            document_pdf.write_pdf(
                files / filename,
                pdf_identifier=hashlib.sha256(document.encode()).hexdigest().encode(),
                pdf_tags=True,
            )
        if (files / filename).stat().st_size > policy["pdf_max_bytes"]:
            raise ValueError("Actual PDF exceeds the provisional byte budget")
        if kind == "detail":
            reader = PdfReader(files / filename)
            destinations = {}

            def collect_outlines(entries, reader=reader, destinations=destinations):
                for entry in entries:
                    if isinstance(entry, list):
                        collect_outlines(entry)
                    else:
                        destinations[entry.title] = reader.get_destination_page_number(entry) + 1

            collect_outlines(reader.outline)
            if (
                len(reader.pages) < len(pages) + 1
                or len(reader.pages) > policy["max_pages"]
                or any(
                    destinations.get(area_name + " · " + sheet["id"]) != sheet["page"]
                    for sheet in pages
                )
            ):
                raise ValueError("Actual locator/sheet pagination differs; do not adopt this proof")
    result = {
        "status": "unreviewed proof; not a complete sample",
        "producer": data["producer"],
        "policy": policy,
        "coverage_scope": data.get("coverage_scope", {"kind": "county", "whole_county": True}),
        "detail_pdf": leaf,
        "locator": locator_audit,
        "horizontal_layout": layout_audits,
        "sheets": sheet_audits,
        "street_name_coverage": street_coverage,
        "overview": {**overview_audit, "poi_ids": [point["id"] for point in data["pois"]]},
        "road_counts": data["road_counts"],
        "water_audit": data["water_audit"],
        "inputs": data["inputs"],
        "fonts": data["fonts"],
        "zctas": data["zctas"],
        "historical_basemap": data["historical_basemap"],
        "historical_points": data["historical_points"],
        "zip_source_sha256": data["zip_source_sha256"],
        "crs": data["crs"],
        "files": [
            {
                "path": str(path.relative_to(output)),
                "sha256": sha(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(files.glob("*.pdf"))
        ],
    }
    (output / "prototype.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def run(
    root: Path,
    cache: Path,
    basemap: Path,
    points: Path,
    zip_source: Path,
    output: Path,
    pdf_budget_config: Path,
    policy_path: Path | None = None,
    counts_only: bool = False,
) -> None:
    started = time.monotonic()
    policy_path = policy_path or root / "pipelines/atlas/bristol-proof.json"
    policy = read_yaml(policy_path)
    budget = read_yaml(pdf_budget_config)["pdf"]
    maximum = Decimal(str(budget["max_file_mb"])) * 1_000_000
    if not maximum.is_finite() or maximum <= 0 or maximum != int(maximum):
        raise ValueError("Shared PDF MB budget must resolve to a positive whole byte count")
    policy["pdf_max_bytes"] = int(maximum)
    policy["pdf_budget_source_sha256"] = sha(pdf_budget_config)
    policy["pdf_budget"] = budget
    data = prepare(root, cache, basemap, points, zip_source, policy)
    prepared_seconds = time.monotonic() - started
    data["producer"] = producer_recipe(root, policy_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    (output.parent / (output.name + "-counts.json")).write_text(
        json.dumps(
            {
                "roads": data["road_counts"],
                "sheets": data["sheets"],
                "pois": len(data["pois"]),
                "water": data["water_audit"],
                "crs": data["crs"],
                "coverage_scope": data["coverage_scope"],
                "zctas": data["zctas"],
                "selected_area_m2": shape(data["county"]).area,
                "named_source_ways": sum(bool(road["name"]) for road in data["roads"]),
                "distinct_source_names": len(
                    {road["name"] for road in data["roads"] if road["name"]}
                ),
                "settlements": data["settlements"],
                "prepare_seconds": prepared_seconds,
            },
            indent=2,
        )
        + "\n"
    )
    if counts_only:
        print("Preflight counts only; no PDFs rendered and no complete-county claim")
        return
    render_started = time.monotonic()
    result = render(root, data, output)
    result["stage_timings"] = {
        "prepare_seconds": prepared_seconds,
        "render_seconds": time.monotonic() - render_started,
    }
    result["elapsed_seconds"] = time.monotonic() - started
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result["cgroup"] = {
        name: Path("/sys/fs/cgroup", name).read_text()
        for name in ["memory.peak", "memory.events"]
        if Path("/sys/fs/cgroup", name).exists()
    }
    (output / "prototype.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "files": result["files"],
                "sheets": len(result["sheets"]),
                "elapsed_seconds": result["elapsed_seconds"],
                "peak_rss_kib": result["peak_rss_kib"],
            },
            indent=2,
        )
    )
