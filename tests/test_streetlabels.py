"""Independent coverage and honesty regressions for vector street labels."""

import hashlib
import os
from pathlib import Path
from xml.etree import ElementTree

import pytest

from ck.config import read_yaml
from ck.streetlabels import street_labels

ROOT = Path(__file__).resolve().parents[1]
BOUNDS = (0, 0, 100, 100)


@pytest.fixture(scope="module")
def font_path():
    item = next(
        item for item in read_yaml(ROOT / "catalog/fonts.yaml") if item["id"] == "noto_sans"
    )
    cache = Path(os.environ.get("CK_FONT_CACHE", ROOT / "cache"))
    path = cache / item["sha256"]
    if not path.is_file():
        if "CK_FONT_CACHE" in os.environ:
            pytest.fail("Authoritative CK_FONT_CACHE lacks its pinned Noto Sans font")
        pytest.skip("Requires the existing pinned font cache")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    return path


@pytest.fixture
def policy():
    # Engineering geometry fixture, not a handset legibility/coverage claim.
    return {
        "font_sizes_mm": [2.4, 1.8, 1.4, 1.1],
        "padding_mm": 0.12,
        "halo_mm": 0.16,
        "collision_cell_mm": 4,
        "anchor_fractions": [0.5, 0.25, 0.75, 0.125, 0.875],
        "offsets_mm": [-0.8, 0.8, -1.8, 1.8, -3, 3, -5, 5],
    }


def road(identifier, name, coordinates):
    return {
        "id": identifier,
        "name": name,
        "kind": "residential",
        "access": "",
        "geometry": {"type": "LineString", "coordinates": coordinates},
    }


def test_full_name_survives_two_short_connected_source_ways(font_path, policy):
    name = "Very Long Neighborhood Street"
    roads = [
        road(10, name, [(49.9, 50), (50, 50)]),
        road(11, name, [(50, 50), (50.1, 50)]),
    ]
    svg, audit = street_labels(roads, BOUNDS, 100, 100, font_path, policy)
    assert name in svg
    assert audit["source_names"] == [name]
    assert audit["named_components"] == 1
    assert audit["missing_labels"] == []
    assert len(audit["placed_labels"]) == 1
    assert audit["placed_labels"][0]["source_ways"] == [10, 11]


def test_empty_off_sheet_and_point_only_intersections_are_not_named_roads(font_path, policy):
    roads = [
        road(1, "Off Sheet Street", [(200, 200), (210, 210)]),
        road(2, "Empty Street", []),
        road(3, "Edge Touch Street", [(100, 50), (110, 50)]),
    ]
    svg, audit = street_labels(roads, BOUNDS, 100, 100, font_path, policy)
    assert svg == ""
    assert audit["source_way_ids"] == []
    assert audit["unnamed_source_way_ids"] == []
    assert audit["source_names"] == []
    assert audit["named_components"] == 0
    assert audit["placed_labels"] == audit["missing_labels"] == []


def test_disconnected_same_name_streets_have_separate_labeled_components(font_path, policy):
    roads = [
        road(21, "Main Street", [(30, 20), (70, 20)]),
        road(22, "Main Street", [(30, 80), (70, 80)]),
    ]
    _, audit = street_labels(roads, BOUNDS, 100, 100, font_path, policy)
    assert audit["source_names"] == ["Main Street"]
    assert audit["named_components"] == 2
    assert audit["missing_labels"] == []
    assert sorted(label["source_ways"] for label in audit["placed_labels"]) == [[21], [22]]


def test_dense_parallel_local_streets_cover_every_source_name(font_path, policy):
    roads = [
        road(
            index, f"Neighborhood Street {index:02}", [(45, 5 + index * 2.8), (55, 5 + index * 2.8)]
        )
        for index in range(32)
    ]
    svg, audit = street_labels(roads, BOUNDS, 100, 100, font_path, policy)
    expected = {entry["name"] for entry in roads}
    assert set(audit["source_names"]) == expected
    assert {label["name"] for label in audit["placed_labels"]} == expected
    assert audit["named_components"] == len(roads)
    assert audit["missing_labels"] == []
    for name in expected:
        assert name in svg


def test_svg_escapes_source_names_and_does_not_invent_names_for_unnamed_roads(font_path, policy):
    name = 'Oak & <Elm> "Lane"'
    roads = [
        road(30, name, [(20, 40), (80, 40)]),
        road(31, "", [(20, 70), (80, 70)]),
    ]
    svg, audit = street_labels(roads, BOUNDS, 100, 100, font_path, policy)
    document = ElementTree.fromstring(f"<svg>{svg}</svg>")
    texts = [element.text for element in document.iter("text")]
    assert texts and set(texts) == {name}
    assert "&amp;" in svg and "&lt;Elm&gt;" in svg
    assert audit["source_way_ids"] == [30, 31]
    assert audit["unnamed_source_way_ids"] == [31]
    assert audit["source_names"] == [name]
    assert {label["name"] for label in audit["placed_labels"]} == {name}
    assert audit["missing_labels"] == []


def test_impossible_label_area_reports_the_missing_component(font_path, policy):
    name = "A Street Name That Cannot Fit"
    roads = [road(40, name, [(40, 50), (60, 50)])]
    svg, audit = street_labels(roads, BOUNDS, 1, 1, font_path, policy)
    assert svg == ""
    assert audit["source_names"] == [name]
    assert audit["source_way_ids"] == [40]
    assert audit["named_components"] == 1
    assert audit["placed_labels"] == []
    assert audit["missing_labels"] == [{"name": name, "source_ways": [40]}]


def test_reserved_area_is_not_claimed_as_a_successful_label(font_path, policy):
    roads = [road(50, "Reserved Street", [(30, 50), (70, 50)])]
    _, audit = street_labels(
        roads, BOUNDS, 100, 100, font_path, policy, reserved=[(0, 0, 100, 100)]
    )
    assert audit["placed_labels"] == []
    assert audit["missing_labels"] == [{"name": "Reserved Street", "source_ways": [50]}]
