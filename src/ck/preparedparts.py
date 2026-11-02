"""Derive a bounded part scene from an authenticated, complete parent sheet extent."""

import copy
from collections import Counter

from shapely import union_all
from shapely.geometry import Point, box, mapping, shape
from shapely.strtree import STRtree


def part_scene(data, part, tolerance_m2):
    geometry = shape(part["geometry"])
    county = shape(data["county"])
    if (
        geometry.is_empty
        or not geometry.is_valid
        or geometry.difference(county).area > tolerance_m2
    ):
        raise ValueError("Part must be a valid subset of the authenticated county")
    selected = [
        dict(row) for row in data["sheets"] if geometry.intersection(box(*row["bounds"])).area > 0
    ]
    if not selected:
        raise ValueError("Part has no parent frames")
    extent = union_all([box(*row["bounds"]) for row in selected])
    parent_extent = union_all([box(*row["bounds"]) for row in data["sheets"]])
    if (
        not extent.difference(parent_extent).is_empty
        or geometry.difference(extent).area > tolerance_m2
    ):
        raise ValueError("Part or street context exceeds authenticated parent extent")
    present = {row["id"] for row in selected}
    for index, row in enumerate(selected, 2):
        row["page"] = index
        row["neighbors"] = {k: v for k, v in row["neighbors"].items() if v in present}
    source_shapes = [shape(row["geometry"]) for row in data["roads"]]
    if len({row["id"] for row in data["roads"]}) != len(data["roads"]):
        raise ValueError("Duplicate authenticated source-way ID")
    tree = STRtree(source_shapes)
    chosen = sorted(
        tree.query(extent, predicate="intersects"), key=lambda index: data["roads"][index]["id"]
    )
    roads = [
        {**data["roads"][i], "geometry": mapping(source_shapes[i].intersection(extent))}
        for i in chosen
    ]
    owner_ids = {
        row["id"]
        for row, source in zip(data["roads"], source_shapes, strict=True)
        if source.intersects(geometry)
    }
    if not owner_ids <= {row["id"] for row in roads}:
        raise ValueError("A source county way was omitted from part context")
    for source in source_shapes:
        if source.intersection(geometry).difference(extent).length > 0:
            raise ValueError("A source way has uncovered geometry")
    zips = []
    for row in data["zip_areas"]:
        clipped = shape(row["geometry"]).intersection(county).intersection(geometry)
        if clipped.is_empty or clipped.area <= 0:
            continue
        point = Point(row["label_point"])
        if not clipped.covers(point):
            point = clipped.representative_point()
        zips.append({**row, "geometry": mapping(clipped), "label_point": [point.x, point.y]})
    codes = sorted(row["code"] for row in zips)
    if codes != part["zctas"]:
        raise ValueError("Part ZIP labels differ from actual source geometry")
    pois = [
        {**row, "number": number}
        for number, row in enumerate(
            [row for row in data["pois"] if geometry.covers(Point(row["x"], row["y"]))], 1
        )
    ]
    result = dict(data)
    result.update(
        county=mapping(geometry),
        sheets=selected,
        roads=roads,
        pois=pois,
        settlements=[
            row for row in data["settlements"] if extent.covers(Point(row["x"], row["y"]))
        ],
        water=[
            mapping(shape(row).intersection(extent))
            for row in data["water"]
            if shape(row).intersects(extent)
        ],
        zctas=codes,
        zip_areas=zips,
        road_counts=dict(sorted(Counter(row["kind"] for row in roads).items())),
    )
    result["policy"] = copy.deepcopy(data["policy"])
    result["policy"].update(
        area_name=data["policy"]["county_name"] + " - Part " + part["id"],
        expected_zctas=codes,
        status="Unreviewed partial county engineering proof; remaining areas are separate",
    )
    result["coverage_scope"] = {
        "kind": "authenticated_parent_county_part",
        "whole_county": False,
        "part_id": part["id"],
        "zctas": codes,
    }
    result["parent_frame_audit"] = {
        "parent_base_sheets": len(data["sheets"]),
        "selected_parent_frame_ids": [row["id"] for row in selected],
        "county_source_way_ids": sorted(owner_ids),
        "context_source_way_ids": sorted({r["id"] for r in roads} - owner_ids),
        "parent_extent_contains_part_and_context": True,
    }
    return result
