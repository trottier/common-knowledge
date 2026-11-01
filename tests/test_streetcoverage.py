"""Spatial coverage tests without SVG rendering or a font dependency."""

from copy import deepcopy

import pytest
from shapely.geometry import box, shape

from ck.streetcoverage import complete_detail_sheets


def fixture():
    return {
        "policy": {"scale_denominator": 25000, "max_pages": 12, "max_inset_depth": 5},
        "sheets": [
            {
                "id": "R1C1",
                "page": 2,
                "row": 0,
                "column": 0,
                "bounds": [0, 0, 100, 100],
                "neighbors": {},
            }
        ],
        "roads": [
            {
                "id": 7,
                "name": "Short Street",
                "geometry": {"type": "LineString", "coordinates": [[49, 50], [51, 50]]},
            },
            {
                "id": 8,
                "name": "",
                "geometry": {"type": "LineString", "coordinates": [[48, 50], [52, 50]]},
            },
            {
                "id": 9,
                "name": "Off Sheet",
                "geometry": {"type": "LineString", "coordinates": [[200, 200], [210, 200]]},
            },
        ],
    }


def spatial_factory(data, bounds):
    visible, unnamed, placed, missing = [], [], [], []
    for road in data["roads"]:
        line = shape(road["geometry"]).intersection(box(*bounds))
        if line.is_empty or line.length == 0:
            continue
        visible.append(road["id"])
        if not road["name"]:
            unnamed.append(road["id"])
            continue
        record = {"name": road["name"], "source_ways": [road["id"]]}
        # This road needs a real larger-scale frame, not just a relabeled base page.
        (placed if bounds[2] - bounds[0] <= 25 else missing).append(record)
    return "<svg/>", {
        "street_name_coverage": {
            "source_way_ids": visible,
            "unnamed_source_way_ids": unnamed,
            "placed_labels": placed,
            "missing_labels": missing,
        }
    }


def test_larger_scale_insets_close_source_way_coverage_and_keep_parent_navigation():
    data = fixture()
    original = deepcopy(data)
    sheets, coverage = complete_detail_sheets(data, spatial_factory)
    assert data == original
    assert coverage["expected_way_ids"] == coverage["labeled_way_ids"] == [7]
    assert coverage["missing_way_ids"] == []
    assert coverage["unnamed_source_way_ids"] == [8]
    assert coverage["source_names"] == ["Short Street"]
    assert coverage["complete"] is True
    assert coverage["inset_count"] == 1
    assert [sheet[0]["id"] for sheet in sheets] == ["R1C1", "I01"]
    assert [sheet[0]["page"] for sheet in sheets] == [2, 3]
    assert sheets[-1][0]["effective_scale_denominator"] == 6250
    assert sheets[-1][0]["parent"] == "R1C1"
    assert sheets[-1][0]["neighbors"] == {"back_to_base": "R1C1"}


@pytest.mark.parametrize(("setting", "value"), [("max_pages", 2), ("max_inset_depth", 1)])
def test_unresolved_coverage_fails_with_names_and_ids_at_the_limit(setting, value):
    data = fixture()
    data["policy"][setting] = value
    with pytest.raises(ValueError, match=rf"{setting}.*7 \(Short Street\)"):
        complete_detail_sheets(data, spatial_factory)


def test_deterministic_insets_and_unnamed_roads_do_not_create_invented_targets():
    data = fixture()
    first = complete_detail_sheets(data, spatial_factory)
    data["roads"].reverse()
    second = complete_detail_sheets(data, spatial_factory)
    assert [row[0] for row in first[0]] == [row[0] for row in second[0]]
    assert first[1] == second[1]
    data["roads"] = [road for road in data["roads"] if not road["name"]]
    sheets, coverage = complete_detail_sheets(data, spatial_factory)
    assert len(sheets) == 1
    assert coverage["expected_way_ids"] == coverage["source_names"] == []
    assert coverage["inset_count"] == 0


def test_already_labeled_base_sheet_needs_no_insets():
    data = fixture()
    data["sheets"][0]["bounds"] = [40, 40, 60, 60]
    sheets, coverage = complete_detail_sheets(data, spatial_factory)
    assert len(sheets) == 1
    assert coverage["labeled_way_ids"] == [7]
    assert coverage["inset_count"] == 0


def test_equal_names_at_disconnected_locations_require_both_source_ways_labeled():
    data = fixture()
    data["roads"][0]["name"] = "Main Street"
    data["roads"][0]["geometry"]["coordinates"] = [[19, 50], [21, 50]]
    data["roads"].append(
        {
            "id": 10,
            "name": "Main Street",
            "geometry": {"type": "LineString", "coordinates": [[79, 50], [81, 50]]},
        }
    )
    _, coverage = complete_detail_sheets(data, spatial_factory)
    assert coverage["expected_way_ids"] == coverage["labeled_way_ids"] == [7, 10]
    assert coverage["source_names"] == ["Main Street"]
    assert coverage["named_count"] == 2
    assert coverage["inset_count"] == 2
