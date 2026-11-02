import copy

import pytest
from shapely.geometry import LineString, box, mapping, shape

from ck.preparedparts import part_scene


def fixture():
    def road(identifier, name, coords):
        return {
            "id": identifier,
            "kind": "residential",
            "name": name,
            "geometry": mapping(LineString(coords)),
        }

    return {
        "county": mapping(box(0.5, 0.5, 3.5, 1.5)),
        "policy": {"county_name": "Synthetic County"},
        "sheets": [
            {"id": "L", "bounds": [0, 0, 2, 2], "page": 2, "neighbors": {"east": "R"}},
            {"id": "R", "bounds": [2, 0, 4, 2], "page": 3, "neighbors": {"west": "L"}},
        ],
        "roads": [
            road(1, "Cross-boundary Street", [(1, 1), (3, 1)]),
            road(2, "Outside county context", [(1, 1.8), (3, 1.8)]),
            road(3, "", [(0.75, 0.75), (1, 0.75)]),
            road(4, "Right road", [(3, 1), (3.4, 1)]),
        ],
        "settlements": [{"id": "n1", "name": "Source place", "x": 1, "y": 1.8}],
        "zip_areas": [
            {"code": "02806", "geometry": mapping(box(0, 0, 2, 2)), "label_point": [1, 1]},
            {"code": "02809", "geometry": mapping(box(2, 0, 4, 2)), "label_point": [3, 1]},
        ],
        "pois": [
            {"id": "p1", "x": 1, "y": 1, "number": 19},
            {"id": "p2", "x": 3, "y": 1, "number": 20},
        ],
        "water": [],
    }


def part():
    return {"id": "P01", "geometry": mapping(box(0.5, 0.5, 2, 1.5)), "zctas": ["02806"]}


def test_part_reuses_authenticated_frames_and_preserves_visible_context_and_unnamed_ways():
    original = fixture()
    before = copy.deepcopy(original)
    result = part_scene(original, part(), 0.000001)
    assert original == before
    assert [row["id"] for row in result["sheets"]] == ["L"]
    assert result["sheets"][0]["neighbors"] == {}
    assert {row["id"] for row in result["roads"]} == {1, 2, 3}
    assert shape(result["roads"][0]["geometry"]).bounds == (1, 1, 2, 1)
    assert result["roads"][2]["name"] == ""
    assert result["parent_frame_audit"]["county_source_way_ids"] == [1, 3]
    assert result["parent_frame_audit"]["context_source_way_ids"] == [2]
    assert result["settlements"] == original["settlements"]
    assert result["pois"] == [{"id": "p1", "x": 1, "y": 1, "number": 1}]
    assert result["coverage_scope"]["whole_county"] is False


def test_invalid_extra_geometry_or_false_zip_association_fail():
    value = part()
    value["geometry"] = mapping(box(0, 0, 3, 2))
    with pytest.raises(ValueError, match="valid subset"):
        part_scene(fixture(), value, 0.000001)
    value = part()
    value["zctas"] = ["02809"]
    with pytest.raises(ValueError, match="ZIP labels"):
        part_scene(fixture(), value, 0.000001)


def test_missing_parent_coverage_is_not_silently_used_as_complete_context():
    data = fixture()
    data["sheets"] = data["sheets"][:1]
    value = part()
    value["geometry"] = data["county"]
    value["zctas"] = ["02806", "02809"]
    with pytest.raises(ValueError, match="exceeds authenticated"):
        part_scene(data, value, 0.000001)


def test_duplicate_source_id_is_not_deduplicated_away():
    data = fixture()
    data["roads"].append(data["roads"][0])
    with pytest.raises(ValueError, match="Duplicate authenticated"):
        part_scene(data, part(), 0.000001)
