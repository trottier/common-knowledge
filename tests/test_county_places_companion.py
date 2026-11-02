"""Actual point numbers, map coordinates, and historical exclusions must survive reuse."""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from ck.directory import Place

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "county_places_tool", ROOT / "tools/build_county_places.py"
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def place(index=1, **changes):
    return Place(
        id=f"fixture-{index}",
        name=f"Fixture {index}",
        category="public_library",
        address="Address from fixture",
        latitude=0.5,
        longitude=0.5,
        county="44001",
        county_name="Bristol County",
        source_id="fixture",
        as_of="fixture date",
        **changes,
    )


def fixtures():
    places = [place(i) for i in range(1, 34)]
    proof = {
        "policy": {"county": "44001", "county_name": "Bristol County"},
        "overview": {"poi_ids": [p.id for p in places]},
    }
    return (
        proof,
        {"places": [p.model_dump(exclude={"tags"}) for p in places]},
        {"places": [p.model_dump() for p in places]},
    )


def test_numbering_and_missing_addresses_are_not_guessed():
    proof, public, original = fixtures()
    public["places"][1]["address"] = original["places"][1]["address"] = ""
    places = tool.selected_places(proof, public, original)
    assert [p.id for p in places] == proof["overview"]["poi_ids"]
    assert places[1].address == ""


@pytest.mark.parametrize(
    "mutation", ["reorder", "missing", "duplicate", "sensitive", "changed", "another-county"]
)
def test_historical_membership_exclusions_and_content_cannot_drift(mutation):
    proof, public, original = fixtures()
    if mutation == "reorder":
        public["places"].reverse()
    elif mutation == "missing":
        original["places"].pop()
    elif mutation == "duplicate":
        original["places"][-1] = copy.deepcopy(original["places"][0])
    elif mutation == "sensitive":
        original["places"][0]["tags"] = {"power": "substation"}
    elif mutation == "changed":
        public["places"][0]["address"] = "Unverified replacement"
    else:
        proof["policy"]["county"] = "44003"
    with pytest.raises(ValueError):
        tool.selected_places(proof, public, original)


def map_proof():
    return {
        "crs": "EPSG:4326",
        "detail_pdf": "Actual fixture map.pdf",
        "sheets": [
            {
                "id": "R1C1",
                "bounds": [0, 0, 1, 1],
                "page": 2,
                "pdf": "Actual fixture map.pdf",
                "grid_columns": "ABCDE",
                "grid_rows": list(range(1, 7)),
                "inset_depth": 0,
            }
        ],
    }


def test_grid_uses_actual_bounds_top_origin_and_exact_edge_clamping():
    proof = map_proof()
    points = [
        place(1),
        Place.model_validate({**place(2).model_dump(), "latitude": 1, "longitude": 0}),
        Place.model_validate({**place(3).model_dump(), "latitude": 0, "longitude": 1}),
    ]
    refs = tool.point_references(proof, points)
    assert refs[points[0].id] == {
        "file": "Actual fixture map.pdf",
        "page": 2,
        "sheet": "R1C1",
        "grid": "C4",
    }
    assert refs[points[1].id]["grid"] == "A1"
    assert refs[points[2].id]["grid"] == "E6"


def test_overlap_selects_interior_sheet_and_never_uses_unrelated_inset():
    proof = map_proof()
    proof["sheets"] += [
        {**proof["sheets"][0], "id": "R1C2", "bounds": [0.4, 0, 1.4, 1], "page": 3},
        {**proof["sheets"][0], "id": "inset", "page": 99, "inset_depth": 1},
    ]
    p = Place.model_validate({**place().model_dump(), "longitude": 0.9})
    assert tool.point_references(proof, [p])[p.id]["sheet"] == "R1C2"


@pytest.mark.parametrize("mutation", ["outside", "grid", "filename", "bounds"])
def test_unknown_map_relationships_fail_instead_of_inventing_references(mutation):
    proof = map_proof()
    if mutation == "outside":
        proof["sheets"][0]["bounds"] = [5, 5, 6, 6]
    elif mutation == "grid":
        proof["sheets"][0]["grid_rows"] = [1, 2]
    elif mutation == "filename":
        proof["sheets"][0]["pdf"] = "Old atlas.pdf"
    else:
        proof["sheets"][0]["bounds"] = [1, 0, 0, 1]
    with pytest.raises(ValueError):
        tool.point_references(proof, [place()])
