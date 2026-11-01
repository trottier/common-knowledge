import hashlib
import os
from pathlib import Path

import pytest
from shapely import union_all
from shapely.geometry import Polygon, box, mapping
from weasyprint import HTML

from ck.config import read_yaml
from ck.countyproof import geometry_path, horizontal_layout, sheet_plan, svg_locator, svg_map


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
    root = Path(__file__).resolve().parents[1]
    item = next(
        item for item in read_yaml(root / "catalog/fonts.yaml") if item["id"] == "noto_sans"
    )
    cache = Path(os.environ.get("CK_FONT_CACHE", root / "cache"))
    font = cache / item["sha256"]
    if not font.is_file():
        if "CK_FONT_CACHE" in os.environ:
            pytest.fail("Authoritative CK_FONT_CACHE lacks its pinned Noto Sans font")
        pytest.skip("Requires the existing pinned font cache")
    assert hashlib.sha256(font.read_bytes()).hexdigest() == item["sha256"]
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


@pytest.mark.parametrize("element", ["table", "svg"])
def test_actual_horizontal_layout_rejects_off_page_table_or_svg(element):
    content = '<table style="width:150mm"><tr><td>Sheet</td><td>Page</td></tr></table>'
    if element == "svg":
        content = '<svg width="150mm" height="20mm"><rect width="100" height="20"/></svg>'
    document = HTML(string="<style>@page{size:100mm 100mm;margin:10mm}</style>" + content).render()
    with pytest.raises(ValueError, match="Horizontal"):
        horizontal_layout(document)


def test_actual_side_by_side_locator_and_two_column_table_fit_page():
    document = HTML(
        string="""<style>
      @page {size:letter;margin:10mm} body {margin:0}
      .row {display:flex;gap:4mm} svg {width:94mm;height:100mm;flex:none}
      table {width:88mm;flex:none;table-layout:fixed}
      </style><div class="row"><svg><rect width="20" height="20"/></svg>
      <table><tr><th>Sheet</th><th>Page</th></tr>
      <tr><td>R1C1</td><td>page 2</td></tr></table></div>"""
    ).render()
    checked = horizontal_layout(document)
    assert any(entry["tag"] == "table" for entry in checked)
    assert any(entry["tag"] == "svg" for entry in checked)
