"""Complete-area proposals retain real ZIP codes, residuals, and every supplied county way."""

import copy
import math

import pytest
from shapely import union_all
from shapely.geometry import LineString, box, mapping, shape

from ck.countyparts import plan_county_parts, sheet_budget


def fixture():
    return {
        "crs": "EPSG:32619",
        "county": mapping(union_all([box(0, 0, 8, 4), box(10, 0, 11, 1)])),
        "zctas": ["02806", "02809"],
        "zip_areas": [
            {"code": "02806", "geometry": mapping(box(-2, -1, 3, 5))},
            {"code": "02809", "geometry": mapping(box(3, 0, 7, 4))},
        ],
        "roads": [
            {
                "id": 1,
                "name": "Cross-boundary Street",
                "geometry": mapping(LineString([(-2, 2), (12, 2)])),
            },
            {"id": 2, "name": "", "geometry": mapping(LineString([(7.5, 0), (7.5, 4)]))},
            {
                "id": 3,
                "name": "Island Road",
                "geometry": mapping(LineString([(10.1, 0.5), (10.9, 0.5)])),
            },
            {
                "id": 99,
                "name": "Outside context",
                "geometry": mapping(LineString([(20, 20), (21, 20)])),
            },
        ],
        "settlements": [{"id": "n1", "name": "Source hamlet", "x": 10.5, "y": 0.5}],
        "policy": {
            "map_width_mm": 100,
            "map_height_mm": 100,
            "scale_denominator": 20,
            "overlap_fraction": 0,
            "max_pages": 20,
            "pdf_max_bytes": 10_000,
        },
    }


def limits(**changes):
    return {
        "max_parts": 32,
        "max_depth": 8,
        "max_evaluations": 256,
        "max_candidate_sheets": 256,
        "coverage_tolerance_m2": 0.000001,
        **changes,
    }


def unknown(geometry, codes):
    return {"kind": "unknown", "pages": None, "bytes": None}


def synthetic_bytes(geometry, codes):
    return {
        "kind": "predicted",
        "pages": None,
        "bytes": math.ceil(geometry.area * 100),
        "evidence": "Synthetic unit fixture only; no real PDF or population estimate",
    }


def test_one_county_default_does_not_claim_unmeasured_byte_or_street_acceptance():
    data = fixture()
    result = plan_county_parts(data, unknown, limits())
    assert len(result["parts"]) == 1 and not result["split_trigger"]
    assert result["needs_measurement"] is True
    assert result["parts"][0]["budget"]["bytes"] is None
    assert result["coverage"]["outside_zcta_area_m2"] == 5
    assert result["coverage"]["assigned_source_way_ids"] == [1, 2, 3]
    assert result["coverage"]["context_source_way_ids"] == [99]


def test_byte_trigger_preserves_island_residual_crosscounty_zip_and_all_source_ways():
    data = fixture()
    data["policy"]["pdf_max_bytes"] = 800
    before = copy.deepcopy(data)
    result = plan_county_parts(data, synthetic_bytes, limits())
    assert data == before
    assert len(result["parts"]) > 1 and result["split_trigger"] == ["PDF bytes"]
    county = shape(data["county"])
    areas = [shape(row["geometry"]) for row in result["parts"]]
    assert union_all(areas).equals(county)
    assert sum(g.area for g in areas) == county.area
    assert all(g.difference(county).is_empty for g in areas)
    assert result["coverage"]["missing_source_way_ids"] == []
    assert sum(part["outside_zcta_area_m2"] for part in result["parts"]) == 5
    assert {code for part in result["parts"] for code in part["zctas"]} == {"02806", "02809"}
    assert all(part["budget"]["bytes"] <= 800 for part in result["parts"])
    assert {key for part in result["parts"] for key in part["unnamed_source_way_ids"]} == {2}
    assert any(
        {"id": "n1", "name": "Source hamlet"} in part["source_localities"]
        for part in result["parts"]
    )
    data["zip_areas"].reverse()
    data["roads"].reverse()
    assert plan_county_parts(data, synthetic_bytes, limits()) == result


def test_actual_label_guard_failure_can_trigger_split_without_inventing_page_count():
    def measured(geometry, codes):
        return {
            "kind": "measured",
            "pages": None,
            "bytes": None,
            "page_limit_exceeded": geometry.area > 8,
            "evidence": "Synthetic bounded label factory reached its actual page guard",
        }

    result = plan_county_parts(fixture(), measured, limits())
    assert result["split_trigger"] == ["actual named-label page-limit failure"]
    assert all(part["budget"]["pages"] is None for part in result["parts"])
    assert all(not part["budget"]["page_limit_exceeded"] for part in result["parts"])


def test_intersecting_sheet_guard_does_not_reject_empty_rectangle_cells():
    data = fixture()
    data.update(
        county=mapping(union_all([box(0, 0, 1, 1), box(7, 7, 8, 8)])),
        zctas=[],
        zip_areas=[],
        roads=[],
        settlements=[],
    )
    data["policy"]["max_pages"] = 4
    budget = sheet_budget(shape(data["county"]), data["policy"], 256)
    assert budget == {"candidate_sheets": 16, "base_sheets": 2, "base_guard_exceeded": False}
    assert len(plan_county_parts(data, unknown, limits())["parts"]) == 1


@pytest.mark.parametrize(
    "change,match",
    [
        ({"max_depth": 0}, "max_depth"),
        ({"max_parts": 1}, "part-count"),
        ({"max_evaluations": 1}, "evaluation limit"),
        ({"max_candidate_sheets": 1}, "candidate-cell"),
    ],
)
def test_explicit_work_and_file_caps_fail_without_dropping_area(change, match):
    data = fixture()
    data["policy"]["pdf_max_bytes"] = 800
    with pytest.raises(ValueError, match=match):
        plan_county_parts(data, synthetic_bytes, limits(**change))


def test_missing_zip_geometry_is_not_misclassified_as_non_zcta_residual():
    data = fixture()
    data["zip_areas"].pop()
    with pytest.raises(ValueError, match="missing=.*02809"):
        plan_county_parts(data, unknown, limits())


def test_overlapping_source_zip_polygons_need_resolution_not_arbitrary_assignment():
    data = fixture()
    data["zip_areas"][1]["geometry"] = mapping(box(2, 0, 7, 4))
    with pytest.raises(ValueError, match="overlap"):
        plan_county_parts(data, unknown, limits())


def test_geographic_degrees_cannot_be_treated_as_metres():
    data = fixture()
    data["crs"] = "EPSG:4326"
    with pytest.raises(ValueError, match="projected CRS"):
        plan_county_parts(data, unknown, limits())


def test_no_zip_range_expansion_or_duplicate_way_ids():
    data = fixture()
    data["zctas"] = ["02806-02809"]
    with pytest.raises(ValueError, match="five-digit"):
        plan_county_parts(data, unknown, limits())
    data = fixture()
    data["roads"].append(data["roads"][0])
    with pytest.raises(ValueError, match="Duplicate source way"):
        plan_county_parts(data, unknown, limits())
