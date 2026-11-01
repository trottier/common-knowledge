from pathlib import Path

import pytest
from shapely import union_all
from shapely.geometry import Polygon, box, mapping

from ck.countyproof import geometry_path, sheet_plan, svg_locator, svg_map


def policy():
    return {
        "map_width_mm": 190,
        "map_height_mm": 230,
        "scale_denominator": 25000,
        "overlap_fraction": 0.1,
        "max_pages": 64,
        "max_vertices_per_sheet": 100,
    }


def test_sheet_plan_covers_irregular_county_without_scaling_or_gaps():
    county = Polygon([(0, 0), (13000, 0), (13000, 7000), (5000, 16000), (0, 16000)])
    sheets = sheet_plan(county, policy())
    assert len(sheets) > 1
    assert all(s["bounds"][2] - s["bounds"][0] == pytest.approx(4750) for s in sheets)
    assert all(s["bounds"][3] - s["bounds"][1] == pytest.approx(5750) for s in sheets)
    assert county.difference(union_all([box(*s["bounds"]) for s in sheets])).area < 0.01
    ids = {s["id"] for s in sheets}
    assert all(set(s["neighbors"].values()) <= ids for s in sheets)
    assert sheet_plan(county, policy()) == sheets


def test_sheet_guard_fails_instead_of_dropping_county_coverage():
    limits = {**policy(), "max_pages": 2}
    with pytest.raises(ValueError, match="no coverage dropped"):
        sheet_plan(box(0, 0, 20000, 20000), limits)


def test_svg_polygon_holes_are_retained():
    polygon = Polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10)], holes=[[(2, 2), (3, 2), (3, 3), (2, 3)]]
    )
    assert geometry_path(polygon, lambda x, y: (x, y)).count(" Z") == 2


def test_geographic_locator_names_all_sheet_footprints_without_poi_crowding():
    county = box(0, 0, 10000, 12000)
    data = {
        "policy": policy(),
        "county": mapping(county),
        "water": [],
        "roads": [],
        "sheets": sheet_plan(county, policy()),
        "settlements": [{"name": "Fixture town", "x": 5000, "y": 6000}],
        "pois": [{"name": "Must not enter locator", "x": 4000, "y": 5000}],
    }
    svg, audit = svg_locator(data)
    assert all(sheet["id"] in svg for sheet in data["sheets"])
    assert "Fixture town" in svg
    assert "Must not enter locator" not in svg
    assert "<image" not in svg
    assert audit["poi_markers"] is False


def test_vector_svg_contains_escaped_road_text_and_no_raster_map():
    font = Path("/cache/bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d")
    if not font.is_file():
        pytest.skip("Requires the existing pinned font cache")
    from shapely.geometry import LineString

    county = box(300000, 4610000, 304750, 4615750)
    data = {
        "policy": policy(),
        "water": [],
        "county": mapping(county),
        "roads": [
            {
                "id": 42,
                "kind": "residential",
                "name": "Test <Road>",
                "access": "",
                "geometry": mapping(LineString([(300100, 4612000), (304600, 4612000)])),
            }
        ],
        "pois": [],
        "fonts": [{"path": str(font)}],
        "crs": "EPSG:32619",
    }
    svg, audit = svg_map(data, list(county.bounds))
    assert "Test &lt;Road&gt;" in svg
    assert "<image" not in svg
    assert audit["road_source_ids"] == [42]
    assert audit["placed_labels"][0]["name"] == "Test <Road>"
    assert len(audit["coordinate_labels"]) == 4
