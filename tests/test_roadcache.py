import json
import subprocess
from pathlib import Path

import pytest
from shapely.geometry import box

from ck.catalog import Item
from ck.countyproof import read_roads
from ck.roadcache import binding, build_cache, digest, read_cached_roads

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"residential", "primary", "footway"}
EPOCH = 1793404800


@pytest.fixture
def prepared(tmp_path):
    xml = tmp_path / "source.osm"
    xml.write_text("""<osm version="0.6">
      <node id="1" version="1" lon="0.1" lat="0.1">
        <tag k="place" v="city"/><tag k="name" v="A"/></node>
      <node id="2" version="1" lon="0.9" lat="0.1"/>
      <node id="3" version="1" lon="0.5" lat="0.5">
        <tag k="place" v="hamlet"/><tag k="name" v="B"/></node>
      <node id="10" version="1" lon="0.25" lat="0.25">
        <tag k="place" v="village"/><tag k="name" v="C"/></node>
      <node id="11" version="1" lon="1.5" lat="0.5"/><node id="12" version="1" lon="2" lat="0.5"/>
      <way id="10" version="1"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/>
        <tag k="name" v="Loop &amp; Lane"/><tag k="access" v="private"/></way>
      <way id="11" version="1"><nd ref="3"/><nd ref="10"/><tag k="highway" v="footway"/>
        <tag k="name" v="Short"/></way>
      <way id="12" version="1"><nd ref="2"/><nd ref="3"/><tag k="highway" v="primary"/>
        <tag k="ref" v="A1"/></way>
      <way id="13" version="1"><nd ref="11"/><nd ref="12"/><tag k="highway" v="residential"/>
        <tag k="name" v="Outside"/></way>
      <way id="14" version="1"><nd ref="1"/><nd ref="3"/><tag k="highway" v="residential"/>
        <tag k="power" v="substation"/><tag k="name" v="Excluded"/></way>
    </osm>""")
    source = tmp_path / "source.pbf"
    subprocess.run(["osmium", "cat", str(xml), "-o", str(source)], check=True)
    item = Item(
        id="geofabrik_ri",
        family="geodata",
        title="Original test fixture",
        url="[[VERIFY: synthetic fixture has no publisher URL]]",
        version="fixture",
        size_bytes=source.stat().st_size,
        sha256=digest(source),
        license="CC0-1.0",
        attribution="Original synthetic test",
        license_proof_url="[[VERIFY: fixture]]",
        placement="hub_only",
        dest="build/inputs/",
        profiles=["sample"],
    )
    output = tmp_path / "prepared"
    result = build_cache(ROOT, source, item, ALLOWED, "EPSG:4326", EPOCH, output)
    generated = Item(
        **{
            **item.model_dump(),
            "id": "road_cache_ri",
            "family": "generated",
            "url": None,
            "inputs": [item.id],
            "pipeline_version": result["pipeline_version"],
            "sha256": result["sha256"],
            "size_bytes": result["size_bytes"],
        }
    )
    return source, item, generated, output


@pytest.mark.parametrize("extent", [box(0, 0, 1, 1), box(0.9, 0.1, 1, 0.9), box(1, 0, 3, 1)])
def test_cached_geometry_attributes_ids_order_and_counts_equal_direct(prepared, extent):
    source, item, generated, output = prepared
    expected = read_roads(source, lambda x, y: (x, y), extent, ALLOWED, 50)
    actual = read_cached_roads(
        ROOT,
        {item.id: item, generated.id: generated},
        output,
        extent,
        ALLOWED,
        "EPSG:4326",
        50,
        EPOCH,
    )
    assert actual[:3] == expected
    assert not any(road["id"] == 14 for road in actual[0])
    assert all("geometry" in road and "access" in road and "ref" in road for road in actual[0])


def test_major_road_overview_subset_retains_exact_direct_semantics(prepared):
    source, item, generated, output = prepared
    extent = box(0, 0, 1, 1)
    expected = read_roads(source, lambda x, y: (x, y), extent, {"primary"}, 50)
    actual = read_cached_roads(
        ROOT,
        {item.id: item, generated.id: generated},
        output,
        extent,
        ALLOWED,
        "EPSG:4326",
        50,
        EPOCH,
        {"primary"},
    )
    assert actual[:3] == expected


def test_selected_way_guard_and_unsupported_display_selection_remain_fatal(prepared):
    _, item, generated, output = prepared
    arguments = (
        ROOT,
        {item.id: item, generated.id: generated},
        output,
        box(0, 0, 1, 1),
        ALLOWED,
        "EPSG:4326",
    )
    with pytest.raises(ValueError, match="source-way guard"):
        read_cached_roads(*arguments, 1, EPOCH)
    with pytest.raises(ValueError, match="display selection"):
        read_cached_roads(*arguments, 50, EPOCH, {"motorway"})


@pytest.mark.parametrize("change", ["database", "audit", "crs", "filter", "epoch", "source"])
def test_unpinned_or_mismatched_cache_cannot_be_reused(prepared, change):
    _, item, generated, output = prepared
    crs, allowed, epoch = "EPSG:4326", ALLOWED, EPOCH
    if change == "database":
        with (output / "files/roads.sqlite").open("ab") as stream:
            stream.write(b"changed")
    elif change == "audit":
        (output / "binding.json").write_text("{}")
    elif change == "crs":
        crs = "EPSG:32619"
    elif change == "filter":
        allowed = {"residential"}
    elif change == "epoch":
        epoch += 1
    else:
        item = item.model_copy(update={"version": "different"})
    with pytest.raises(ValueError):
        read_cached_roads(
            ROOT,
            {item.id: item, generated.id: generated},
            output,
            box(0, 0, 1, 1),
            allowed,
            crs,
            50,
            epoch,
        )


def test_review_notes_and_unrelated_catalog_data_do_not_invalidate_cache(prepared):
    _, item, generated, output = prepared
    changed = item.model_copy(update={"review": "[[VERIFY: different human review note]]"})
    assert binding(ROOT, item, ALLOWED, "EPSG:4326") == binding(ROOT, changed, ALLOWED, "EPSG:4326")
    catalog = {item.id: changed, generated.id: generated, "unrelated_zcta": changed}
    read_cached_roads(ROOT, catalog, output, box(0, 0, 1, 1), ALLOWED, "EPSG:4326", 50, EPOCH)


def test_tiny_cache_database_and_manifest_are_deterministic(prepared, tmp_path):
    source, item, _, output = prepared
    again = tmp_path / "again"
    build_cache(ROOT, source, item, ALLOWED, "EPSG:4326", EPOCH, again)
    assert (output / "files/roads.sqlite").read_bytes() == (
        again / "files/roads.sqlite"
    ).read_bytes()
    assert json.loads((output / "generation.json").read_text()) == json.loads(
        (again / "generation.json").read_text()
    )
    with pytest.raises(ValueError, match="no overwrite"):
        build_cache(ROOT, source, item, ALLOWED, "EPSG:4326", EPOCH, again)
