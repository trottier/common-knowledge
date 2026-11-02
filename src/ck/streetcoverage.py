"""Bounded deterministic detail insets for complete named-source-way coverage."""

from shapely import union_all
from shapely.geometry import box, shape


def _lines(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == "LineString":
        if geometry.length > 0:
            yield geometry
    else:
        for part in getattr(geometry, "geoms", ()):
            yield from _lines(part)


def complete_detail_sheets(data, make_svg):
    """Label every named way observed in base sheets or fail with exact omissions.

    The factory receives the unchanged source data and each sheet's bounds.
    Existing page numbers, including any cover-page offset, count against max_pages.
    New roads seen only in inset context do not expand the original coverage target.
    """
    bases = sorted(data["sheets"], key=lambda sheet: (sheet["page"], sheet["id"]))
    if not bases:
        raise ValueError("Street coverage needs at least one base sheet")
    roads = {road["id"]: road for road in data["roads"]}
    maximum = data["policy"]["max_pages"]
    depth_limit = data["policy"]["max_inset_depth"]
    if maximum < max(sheet["page"] for sheet in bases) or depth_limit < 1:
        raise ValueError("Street coverage page/depth limits do not permit the base plan")
    extent = union_all([box(*sheet["bounds"]) for sheet in bases])
    results, expected, labeled, unnamed = [], set(), set(), set()

    def append(sheet, base=False):
        svg, audit = make_svg(data, sheet["bounds"])
        coverage = audit["street_name_coverage"]
        visible = set(coverage["source_way_ids"])
        anonymous = set(coverage["unnamed_source_way_ids"])
        if not anonymous <= visible or not visible <= roads.keys():
            raise ValueError("Street factory reports unknown or inconsistent source-way IDs")
        if base:
            expected.update(visible - anonymous)
            unnamed.update(anonymous)
        newly_labeled = set()
        for placement in coverage["placed_labels"]:
            for identifier in placement["source_ways"]:
                if identifier not in visible or roads[identifier]["name"] != placement["name"]:
                    raise ValueError("Street factory label does not match its visible source way")
                newly_labeled.add(identifier)
        if base or (newly_labeled & expected) - labeled:
            labeled.update(newly_labeled)
            results.append((sheet, svg, audit))

    for original in bases:
        sheet = dict(original)
        sheet["effective_scale_denominator"] = data["policy"]["scale_denominator"]
        sheet["inset_depth"] = 0
        append(sheet, base=True)
    for identifier in expected:
        if not roads[identifier]["name"]:
            raise ValueError("Unnamed source way was included in named coverage target")

    def failure(reason):
        missing = sorted(expected - labeled)
        description = ", ".join(
            f"{identifier} ({roads[identifier]['name']})" for identifier in missing
        )
        raise ValueError(f"Street coverage incomplete: {reason}; missing ways: {description}")

    while expected - labeled:
        target = min(expected - labeled)
        parts = list(_lines(shape(roads[target]["geometry"]).intersection(extent)))
        if not parts:
            failure(f"no visible line for way {target}")
        line = min(parts, key=lambda part: (-part.length, part.wkt))
        center = line.interpolate(0.5, normalized=True)
        parents = [sheet for sheet in bases if box(*sheet["bounds"]).covers(center)]
        if not parents:
            failure(f"no parent sheet for way {target}")
        parent = min(parents, key=lambda sheet: sheet["id"])
        west, south, east, north = parent["bounds"]
        for depth in range(1, depth_limit + 1):
            page = max(sheet["page"] for sheet, _, _ in results) + 1
            if page > maximum:
                failure(f"max_pages={maximum}")
            half_width = (east - west) / (2 ** (depth + 1))
            half_height = (north - south) / (2 ** (depth + 1))
            identifier = f"I{len(results) - len(bases) + 1:02}"
            sheet = {
                "id": identifier,
                "bounds": [
                    center.x - half_width,
                    center.y - half_height,
                    center.x + half_width,
                    center.y + half_height,
                ],
                "page": page,
                "parent": parent["id"],
                "parent_page": parent["page"],
                "neighbors": {"back_to_base": parent["id"]},
                "inset_depth": depth,
                "target_way_id": target,
                "effective_scale_denominator": data["policy"]["scale_denominator"] / 2**depth,
            }
            append(sheet)
            if target in labeled:
                break
        else:
            failure(f"max_inset_depth={depth_limit} for way {target}")

    return results, {
        "expected_way_ids": sorted(expected),
        "labeled_way_ids": sorted(expected & labeled),
        "missing_way_ids": sorted(expected - labeled),
        "unnamed_source_way_ids": sorted(unnamed),
        "source_names": sorted({roads[identifier]["name"] for identifier in expected}),
        "named_count": len(expected),
        "named_source_way_count": len(expected),
        "distinct_name_count": len({roads[identifier]["name"] for identifier in expected}),
        "base_sheet_count": len(bases),
        "inset_count": len(results) - len(bases),
        "complete": True,
    }
