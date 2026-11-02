import json
from pathlib import Path

import pytest
from shapely.geometry import box, mapping

from ck.countyproof import (
    area_geometry,
    html_document,
    output_names,
    overview_name,
    prepare,
    producer_recipe,
)


@pytest.mark.parametrize(
    "name", ["../outside.pdf", "extra/Overview.pdf", "Overview.txt", "a:b.pdf"]
)
def test_area_overview_cannot_escape_the_county_or_become_a_non_pdf(name):
    with pytest.raises(ValueError):
        overview_name({"overview_filename": name})


def test_printed_area_overview_reference_matches_the_actual_filename():
    root = Path(__file__).resolve().parents[1]
    policy = {
        "county_name": "Synthetic county",
        "state": "RI",
        "epoch": 0,
        "scale_denominator": 25000,
    }
    data = {"policy": policy, "zctas": [], "pois": [], "fonts": []}
    assert overview_name(policy) == "0_OVERVIEW.pdf"
    for name in ("0_OVERVIEW.pdf", "Synthetic area 00000 - Overview.pdf"):
        policy["overview_filename"] = name
        document = html_document(root, "Fixture", "detail", [], "", "", "Fixture.pdf", data)
        assert f"<strong>{name}</strong>" in document


def feature(code, geometry):
    return {"properties": {"GEOID": code}, "geometry": mapping(geometry)}


def test_whole_county_remains_default_and_area_scope_never_extends_across_county():
    county = box(0, 0, 10, 10)
    assert area_geometry(county, [], {}) == (county, {"kind": "county", "whole_county": True})
    policy = {"scope_zctas": ["02903"], "expected_zctas": ["02903"], "area_name": "Test area"}
    selected, scope = area_geometry(county, [feature("02903", box(5, 0, 20, 10))], policy)
    assert selected.equals(box(5, 0, 10, 10))
    assert scope["whole_county"] is False
    assert scope["zctas"] == ["02903"]


@pytest.mark.parametrize(
    "codes,features,name",
    [
        ([], [], "Area"),
        (["02903", "02903"], [], "Area"),
        (["02903"], [], "Area"),
        (["02903"], [feature("02903", box(20, 20, 30, 30))], "Area"),
        (["02903"], [feature("02903", box(0, 0, 10, 10))], ""),
    ],
)
def test_unverified_empty_or_ambiguous_area_scope_fails(codes, features, name):
    policy = {"scope_zctas": codes, "expected_zctas": codes, "area_name": name}
    with pytest.raises(ValueError):
        area_geometry(box(0, 0, 10, 10), features, policy)


def test_area_leaf_stays_in_readable_county_folder_and_preserves_zip_gaps():
    policy = {"state": "RI", "county_name": "Providence County", "area_name": "Providence area"}
    folder, leaf, name = output_names(policy, ["02903", "02906"])
    assert folder.as_posix() == "3_MAPS_AND_PLACES/RI/Providence County"
    assert leaf == "Providence area 02903,02906.pdf"
    assert name == "Providence area"
    with pytest.raises(ValueError, match="FAT-safe"):
        output_names({**policy, "area_name": "Unsafe: area"}, ["02903"])
    with pytest.raises(ValueError, match="single FAT-safe"):
        output_names({**policy, "area_name": "Extra/folder"}, ["02903"])
    with pytest.raises(ValueError, match="FAT-safe"):
        output_names(policy, [f"{number:05}" for number in range(100)])


@pytest.mark.parametrize("state,county", [("CA", "06081"), ("RI", "06081"), ("RI", "44bad")])
def test_other_state_or_bad_county_cannot_use_ri_sources(tmp_path, state, county):
    with pytest.raises(ValueError, match="Rhode Island source set only"):
        prepare(*(tmp_path for _ in range(5)), {"state": state, "county": county})


def test_recipe_binds_selected_policy_and_ignores_unselected_county_config(tmp_path):
    root = Path(__file__).resolve().parents[1]
    selected = "pipelines/atlas/providence-02903-proof.json"
    recipe = producer_recipe(root, root / selected)
    for name in recipe["source_files"]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / name).read_bytes())
    initial = producer_recipe(tmp_path, tmp_path / selected)
    unrelated = tmp_path / "pipelines/atlas/bristol-proof.json"
    unrelated.write_text("unrelated configuration")
    assert producer_recipe(tmp_path, tmp_path / selected) == initial
    config = json.loads((tmp_path / selected).read_text())
    config["max_pages"] += 1
    (tmp_path / selected).write_text(json.dumps(config))
    assert producer_recipe(tmp_path, tmp_path / selected)["version"] != initial["version"]
