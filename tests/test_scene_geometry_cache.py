"""A scene cache must preserve complete output and release its bounded geometry set."""

import copy
import gc
import hashlib
import json
import os
import weakref
from pathlib import Path

import pytest
from shapely.geometry import Polygon, mapping

from ck.config import read_yaml
from ck.countyproof import svg_map
from ck.streetlabels import SceneGeometryCache, street_labels

ROOT = Path(__file__).resolve().parents[1]


def road(number, name, coordinates):
    return {
        "id": number,
        "name": name,
        "kind": "residential",
        "access": "",
        "geometry": {"type": "LineString", "coordinates": coordinates},
    }


def scene():
    return {
        "roads": [
            road(1, "Connected Long Street", [(300010, 4610100), (300050, 4610100)]),
            road(2, "Connected Long Street", [(300050, 4610100), (300100, 4610100)]),
            road(3, "Connected Long Street", [(300010, 4610180), (300100, 4610180)]),
            road(4, "", [(300015, 4610150), (300100, 4610150)]),
            road(5, "Off Sheet", [(301000, 4611000), (301100, 4611000)]),
        ],
        "water": [
            mapping(
                Polygon(
                    [(300025, 4610120), (300080, 4610120), (300080, 4610140), (300025, 4610140)]
                )
            )
        ],
    }


def test_cache_builds_each_known_geometry_once_and_rejects_foreign_growth():
    data = scene()
    cache = SceneGeometryCache(data)
    assert cache.capacity == 6 and cache.size == 0
    with pytest.raises(RuntimeError):
        cache.shape(data["roads"][0]["geometry"])
    with cache:
        for geometry in [r["geometry"] for r in data["roads"]] + data["water"]:
            assert cache.shape(geometry) is cache.shape(geometry)
        assert cache.size == cache.capacity == 6
        with pytest.raises(ValueError, match="does not belong"):
            cache.shape(copy.deepcopy(data["roads"][0]["geometry"]))
        assert cache.size == 6
        with pytest.raises(RuntimeError):
            cache.__enter__()
    assert cache.size == cache.capacity == 0
    with pytest.raises(RuntimeError):
        cache.shape(data["roads"][0]["geometry"])
    with pytest.raises(RuntimeError):
        cache.__enter__()


def test_exception_exit_releases_geometry_and_new_scene_gets_fresh_result():
    data = scene()
    with pytest.raises(ValueError, match="fixture error"):
        with SceneGeometryCache(data) as cache:
            geometry = cache.shape(data["roads"][0]["geometry"])
            reference = weakref.ref(geometry)
            del geometry
            raise ValueError("fixture error")
    gc.collect()
    assert reference() is None and cache.size == cache.capacity == 0
    data["roads"][0]["geometry"]["coordinates"] = [(0, 0), (1, 1)]
    with SceneGeometryCache(data) as fresh:
        assert fresh.shape(data["roads"][0]["geometry"]).bounds == (0, 0, 1, 1)


@pytest.fixture(scope="module")
def font_path():
    item = next(r for r in read_yaml(ROOT / "catalog/fonts.yaml") if r["id"] == "noto_sans")
    path = Path(os.environ.get("CK_FONT_CACHE", ROOT / "cache")) / item["sha256"]
    if not path.is_file():
        if "CK_FONT_CACHE" in os.environ:
            pytest.fail("Authoritative font cache lacks the pinned font")
        pytest.skip("Needs the existing pinned font cache")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    return path


@pytest.mark.parametrize("overview", [False, True])
def test_complete_svg_and_audit_match_across_sheets_with_explicit_cache(font_path, overview):
    data = scene()
    data.update(
        county=mapping(
            Polygon([(300000, 4610000), (300200, 4610000), (300200, 4610240), (300000, 4610240)])
        ),
        crs="EPSG:32619",
        fonts=[{"path": str(font_path)}],
        pois=[],
        policy={
            **read_yaml(ROOT / "pipelines/atlas/bristol-proof.json"),
            "max_vertices_per_sheet": 100,
        },
    )
    bounds = [(300000, 4610000, 300200, 4610240), (300030, 4610060, 300170, 4610220)]
    before = json.dumps(data, sort_keys=True)
    expected = [svg_map(data, list(frame), overview) for frame in bounds]
    with SceneGeometryCache(data) as cache:
        actual = [svg_map(data, list(frame), overview, geometry_cache=cache) for frame in bounds]
        assert actual == expected
        assert cache.size == cache.capacity
        assert all(result[1]["road_source_ids"] == [1, 2, 3, 4] for result in actual)
    assert json.dumps(data, sort_keys=True) == before


def test_collision_and_missing_label_audits_are_identical(font_path):
    data = scene()
    policy = read_yaml(ROOT / "pipelines/atlas/bristol-proof.json")["street_labels"]
    args = (data["roads"], (300000, 4610000, 300200, 4610240), 100, 100, font_path, policy)
    # The reservation intentionally makes every name unplaceable; caching cannot clear it.
    expected = street_labels(*args, reserved=[(0, 0, 100, 100)])
    with SceneGeometryCache(data) as cache:
        actual = street_labels(*args, reserved=[(0, 0, 100, 100)], geometry_cache=cache)
    assert actual == expected and actual[1]["missing_labels"]
    assert actual[1]["unnamed_source_way_ids"] == [4]


@pytest.mark.parametrize("flag", [None, False, True])
def test_render_owns_context_and_binds_effective_flag_without_relabeling_preparation(
    tmp_path, monkeypatch, flag
):
    from ck import countyproof

    data = {**scene(), "producer": {"version": "original-preparation"}, "policy": {}}
    if flag is not None:
        data["policy"]["cache_source_geometries"] = flag
    observed = []

    def fake_render(root, actual, output, cache):
        if flag:
            cache.shape(actual["roads"][0]["geometry"])
            assert cache.size == 1
        else:
            assert cache is None
        observed.append(cache)
        output.mkdir()
        return {"producer": actual["producer"], "policy": actual["policy"]}

    monkeypatch.setattr(countyproof, "_render", fake_render)
    result = countyproof.render(ROOT, data, tmp_path / "out")
    assert result["producer"] == {"version": "original-preparation"}
    assert result["render_recipe"]["cache_source_geometries"] is bool(flag)
    if flag:
        assert observed[0].size == observed[0].capacity == 0


def test_failed_render_releases_its_owned_context(tmp_path, monkeypatch):
    from ck import countyproof

    data = {**scene(), "policy": {"cache_source_geometries": True}}
    observed = []

    def failure(root, actual, output, cache):
        cache.shape(actual["roads"][0]["geometry"])
        observed.append(cache)
        raise ValueError("Incomplete labels fixture")

    monkeypatch.setattr(countyproof, "_render", failure)
    with pytest.raises(ValueError, match="Incomplete labels"):
        countyproof.render(ROOT, data, tmp_path / "out")
    assert observed[0].size == observed[0].capacity == 0


@pytest.mark.parametrize("flag", ["false", 0, 1, None])
def test_render_rejects_ambiguous_cache_flags_before_output(tmp_path, flag):
    from ck.countyproof import render

    output = tmp_path / "out"
    with pytest.raises(ValueError, match="explicit boolean"):
        render(ROOT, {"policy": {"cache_source_geometries": flag}}, output)
    assert not output.exists()
