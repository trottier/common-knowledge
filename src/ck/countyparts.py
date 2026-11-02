"""Deterministic complete-area county file proposals; never a PDF or label acceptance claim."""

import math
import re

from pyproj import CRS
from shapely import normalize, union_all
from shapely.geometry import Point, box, mapping, shape


def sheet_budget(geometry, policy, max_candidates):
    """Count intersecting base sheets, with a separate explicit bound on planning work."""
    width = policy["map_width_mm"] * policy["scale_denominator"] / 1000
    height = policy["map_height_mm"] * policy["scale_denominator"] / 1000
    overlap = policy["overlap_fraction"]
    if width <= 0 or height <= 0 or not 0 <= overlap < 1:
        raise ValueError("Invalid map scale, frame, or overlap")
    dx, dy = width * (1 - overlap), height * (1 - overlap)
    west, south, east, north = geometry.bounds
    columns = max(1, math.ceil(max(0, east - west - width) / dx) + 1)
    rows = max(1, math.ceil(max(0, north - south - height) / dy) + 1)
    candidates = columns * rows
    if candidates > max_candidates:
        raise ValueError("County planner candidate-cell work limit reached; no coverage dropped")
    west -= (width + (columns - 1) * dx - (east - west)) / 2
    north += (height + (rows - 1) * dy - (north - south)) / 2
    useful = sum(
        geometry.intersects(
            box(west + x * dx, north - y * dy - height, west + x * dx + width, north - y * dy)
        )
        for y in range(rows)
        for x in range(columns)
    )
    return {
        "candidate_sheets": candidates,
        "base_sheets": useful,
        "base_guard_exceeded": useful > policy["max_pages"] - 1,
    }


def plan_county_parts(data, evaluate, limits):
    """Keep one county unless a measured/predicted cap or existing sheet guard fails.

    evaluate(projected_geometry, exact_ZCTA_codes) returns kind (measured,
    predicted, or unknown), pages, bytes, and an evidence explanation. Unknown
    values stay unknown. No inset/byte/population extrapolation is built in.
    """
    for key in ("max_parts", "max_evaluations", "max_candidate_sheets"):
        if type(limits[key]) is not int or limits[key] < 1:
            raise ValueError(f"Positive explicit planner limit required: {key}")
    if type(limits["max_depth"]) is not int or limits["max_depth"] < 0:
        raise ValueError("Nonnegative explicit max_depth required")
    tolerance = limits["coverage_tolerance_m2"]
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("Positive explicit coverage tolerance required")
    crs = CRS.from_user_input(data["crs"])
    if not crs.is_projected or any(axis.unit_conversion_factor != 1 for axis in crs.axis_info):
        raise ValueError("County planning needs a projected CRS in metres")
    county = shape(data["county"])
    if county.is_empty or not county.is_valid or county.area <= 0:
        raise ValueError("Invalid county geometry")
    codes = data["zctas"]
    if codes != sorted(set(codes)) or any(not re.fullmatch(r"\d{5}", code) for code in codes):
        raise ValueError("ZIP codes must be exact, sorted, unique five-digit source codes")
    features = {row["code"]: shape(row["geometry"]) for row in data["zip_areas"]}
    if len(features) != len(data["zip_areas"]) or set(features) != set(codes):
        raise ValueError(
            f"ZIP geometry inventory differs; missing={sorted(set(codes) - set(features))}; "
            f"extra={sorted(set(features) - set(codes))}"
        )
    clipped, claimed = {}, county.difference(county)
    for code in codes:
        area = features[code]
        if not area.is_valid or area.is_empty:
            raise ValueError(f"Invalid source ZIP geometry: {code}")
        area = county.intersection(area)
        if area.is_empty or area.area <= 0:
            raise ValueError(f"Verified ZIP has no county area: {code}")
        if area.intersection(claimed).area > tolerance:
            raise ValueError("Source ZIP polygons overlap; no arbitrary code assignment")
        clipped[code] = area
        claimed = claimed.union(area)
    residual = county.difference(claimed)
    policy, memo = data["policy"], {}
    if type(policy["max_pages"]) is not int or policy["max_pages"] < 2:
        raise ValueError("Existing max_pages must permit a locator and detail")
    if type(policy["pdf_max_bytes"]) is not int or policy["pdf_max_bytes"] <= 0:
        raise ValueError("Existing PDF byte cap is required")

    def zip_codes(geometry):
        return [code for code in codes if clipped[code].intersection(geometry).area > 0]

    def budget(geometry):
        geometry = normalize(geometry)
        key = geometry.wkb_hex
        if key not in memo:
            if len(memo) >= limits["max_evaluations"]:
                raise ValueError("County planner evaluation limit reached; no coverage dropped")
            estimate = dict(evaluate(geometry, zip_codes(geometry)))
            if set(estimate) - {"kind", "pages", "bytes", "evidence", "page_limit_exceeded"}:
                raise ValueError("Budget evidence contains unknown fields")
            if estimate.get("kind") not in {"measured", "predicted", "unknown"}:
                raise ValueError("Budget evidence must distinguish measurements and predictions")
            if estimate["kind"] != "unknown" and not estimate.get("evidence"):
                raise ValueError("Measured/predicted budgets need an evidence explanation")
            if type(estimate.get("page_limit_exceeded", False)) is not bool:
                raise ValueError("Invalid measured page-limit result")
            if estimate.get("page_limit_exceeded") and estimate["kind"] != "measured":
                raise ValueError("An actual label-plan limit failure needs measured evidence")
            base = sheet_budget(geometry, policy, limits["max_candidate_sheets"])
            for field in ("pages", "bytes"):
                value = estimate.get(field)
                if value is not None and (type(value) is not int or value <= 0):
                    raise ValueError("Invalid page/byte estimate")
                if estimate["kind"] == "unknown" and value is not None:
                    raise ValueError("Unknown budgets cannot carry asserted counts")
            if (
                base["base_sheets"] is not None
                and estimate.get("pages") is not None
                and estimate["pages"] < base["base_sheets"] + 1
            ):
                raise ValueError("PDF page estimate contradicts the base-sheet lower bound")
            failures = []
            if base["base_guard_exceeded"]:
                failures.append("intersecting base-sheet guard")
            if estimate.get("page_limit_exceeded"):
                failures.append("actual named-label page-limit failure")
            if estimate.get("pages") is not None and estimate["pages"] > policy["max_pages"]:
                failures.append("PDF pages")
            if estimate.get("bytes") is not None and estimate["bytes"] > policy["pdf_max_bytes"]:
                failures.append("PDF bytes")
            memo[key] = {
                **base,
                **estimate,
                "cap_failures": failures,
                "needs_measurement": estimate.get("pages") is None
                or estimate.get("bytes") is None
                or estimate["kind"] != "measured",
            }
        return memo[key]

    whole = budget(county)
    if not whole["cap_failures"]:
        geometries = [county]
    else:
        atoms = []

        def divide(geometry, depth):
            if not budget(geometry)["cap_failures"]:
                atoms.append(geometry)
                return
            if depth >= limits["max_depth"]:
                raise ValueError(
                    f"County part still exceeds caps at max_depth; ZIPs={zip_codes(geometry)}; "
                    f"bounds={geometry.bounds}; no coverage dropped"
                )
            west, south, east, north = geometry.bounds
            if east - west >= north - south:
                middle = (west + east) / 2
                frames = [box(west, south, middle, north), box(middle, south, east, north)]
            else:
                middle = (south + north) / 2
                frames = [box(west, south, east, middle), box(west, middle, east, north)]
            children = [geometry.intersection(frame) for frame in frames]
            if any(child.is_empty or child.area <= 0 for child in children):
                raise ValueError("Cannot bisect failing county area without losing geography")
            for child in children:
                divide(child, depth + 1)

        # Partition source ZIP areas and the explicit remainder, retaining all water/islands/gaps.
        for geometry in [*clipped.values(), residual]:
            if not geometry.is_empty and geometry.area > 0:
                divide(geometry, 0)
        geometries = []
        for geometry in sorted(
            atoms, key=lambda g: (g.bounds[0], -g.bounds[3], normalize(g).wkb_hex)
        ):
            merged = geometries[-1].union(geometry) if geometries else geometry
            if (
                geometries
                and budget(merged)["kind"] != "unknown"
                and not budget(merged)["cap_failures"]
            ):
                geometries[-1] = merged
            else:
                geometries.append(geometry)
        if len(geometries) > limits["max_parts"]:
            raise ValueError("County part-count limit reached; no coverage dropped")
    combined = union_all(geometries)
    missing_area, extra_area = county.difference(combined).area, combined.difference(county).area
    overlap_area = sum(g.area for g in geometries) - combined.area
    if max(missing_area, extra_area, overlap_area) > tolerance:
        raise ValueError("County partition has missing, extra, or overlapping area")
    roads = {row["id"]: row for row in data["roads"]}
    if len(roads) != len(data["roads"]):
        raise ValueError("Duplicate source way ID")
    expected = {key for key, row in roads.items() if shape(row["geometry"]).intersects(county)}
    assigned, parts = set(), []
    for number, geometry in enumerate(geometries, 1):
        identifiers = sorted(
            key for key in expected if shape(roads[key]["geometry"]).intersects(geometry)
        )
        assigned.update(identifiers)
        localities = sorted(
            {
                (row["id"], row["name"])
                for row in data.get("settlements", [])
                if geometry.covers(Point(row["x"], row["y"]))
            }
        )
        parts.append(
            {
                "id": f"P{number:02}",
                "geometry": mapping(normalize(geometry)),
                "zctas": zip_codes(geometry),
                "source_localities": [{"id": key, "name": name} for key, name in localities],
                "outside_zcta_area_m2": geometry.intersection(residual).area,
                "source_way_ids": identifiers,
                "unnamed_source_way_ids": [key for key in identifiers if not roads[key]["name"]],
                "budget": budget(geometry),
            }
        )
    if assigned != expected:
        raise ValueError(f"County source ways omitted: {sorted(expected - assigned)}")
    return {
        "status": "Plan only; PDF bytes, street labels, and handset checks remain separate gates",
        "whole_county_default": len(parts) == 1,
        "split_trigger": whole["cap_failures"],
        "parts": parts,
        "limits": dict(limits),
        "evaluations": len(memo),
        "coverage": {
            "county_area_m2": county.area,
            "missing_area_m2": missing_area,
            "extra_area_m2": extra_area,
            "overlap_area_m2": max(0, overlap_area),
            "outside_zcta_area_m2": residual.area,
            "zctas": codes,
            "expected_source_way_ids": sorted(expected),
            "source_way_scope": "Supplied county ways; verify extract completeness separately",
            "assigned_source_way_ids": sorted(assigned),
            "missing_source_way_ids": [],
            "context_source_way_ids": sorted(set(roads) - expected),
        },
        "needs_measurement": any(part["budget"]["needs_measurement"] for part in parts),
    }
