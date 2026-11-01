import json
import subprocess
from pathlib import Path

import osmium
import pytest
from shapely import MultiPolygon, box

from ck.fetch import digest
from ck.mapextract import (
    build_state_extracts,
    collect_android_maps,
    extract_roads,
    policy,
    prepared_state_source,
    recipe_version,
    source_inputs,
)

ROOT = Path(__file__).resolve().parents[1]


def road_fixture(tmp_path):
    xml = tmp_path / "fixture.osm"
    xml.write_text("""<osm version="0.6">
      <node id="1" version="1" lat="1" lon="1"/>
      <node id="2" version="1" lat="1" lon="2"/>
      <node id="3" version="1" lat="1" lon="3"/>
      <node id="99" version="1" lat="40" lon="40"/>
      <way id="10" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="residential"/></way>
      <way id="11" version="1"><nd ref="2"/><nd ref="3"/>
        <tag k="highway" v="residential"/></way>
      <relation id="20" version="1"><member type="way" ref="10" role="from"/>
        <member type="node" ref="2" role="via"/><member type="way" ref="11" role="to"/>
        <tag k="type" v="restriction"/><tag k="restriction" v="no_right_turn"/>
      </relation></osm>""")
    source = tmp_path / "fixture.osm.pbf"
    subprocess.run(["osmium", "cat", str(xml), "--output", str(source)], check=True)
    return source


def identifiers(path):
    found = set()

    class Reader(osmium.SimpleHandler):
        def node(self, node):
            found.add("n" + str(node.id))

        def way(self, way):
            found.add("w" + str(way.id))

        def relation(self, relation):
            found.add("r" + str(relation.id))

    Reader().apply_file(str(path))
    return found


def test_smart_clip_keeps_cross_boundary_ways_and_complete_turn_restrictions(tmp_path):
    source = road_fixture(tmp_path)
    original = digest(source)
    output = tmp_path / "state.osm.pbf"
    extract_roads(source, box(0.5, 0.5, 1.5, 1.5), output, 0.001)
    assert identifiers(output) == {"n1", "n2", "n3", "w10", "w11", "r20"}
    assert digest(source) == original


def test_empty_jurisdiction_clip_is_rejected_even_when_references_are_valid(tmp_path):
    source = road_fixture(tmp_path)
    # Osmium 1.15 also rejects an empty file while producing extended JSON
    # (there is no bounding box). Either audit failure must stop the build.
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        extract_roads(source, box(-60, -60, -59, -59), tmp_path / "empty.osm.pbf", 0.001)


def test_caribbean_sources_override_the_listed_us_parent():
    settings = policy(ROOT)
    assert settings.source_for("PR") == "geofabrik_puerto_rico"
    assert settings.source_for("VI") == "geofabrik_virgin_islands"
    assert settings.source_for("RI") == "geofabrik_us"
    assert settings.source_for("GU") == "geofabrik_oceania"


def test_antimeridian_clip_merges_both_sides_and_excludes_unrelated_regions(tmp_path):
    source = tmp_path / "dateline.osm"
    source.write_text("""<osm version="0.6">
      <node id="1" lat="1" lon="179"/><node id="2" lat="1" lon="179.5"/>
      <node id="3" lat="1" lon="-179"/><node id="4" lat="1" lon="-179.5"/>
      <node id="5" lat="1" lon="0"/>
      <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/></way>
      <way id="11"><nd ref="3"/><nd ref="4"/><tag k="highway" v="residential"/></way>
    </osm>""")
    pbf = tmp_path / "dateline.osm.pbf"
    subprocess.run(["osmium", "cat", str(source), "--output", str(pbf)], check=True)
    output = tmp_path / "merged.osm.pbf"
    geometry = MultiPolygon([box(178, 0, 180, 2), box(-180, 0, -178, 2)])
    extract_roads(pbf, geometry, output, 0.001)
    assert identifiers(output) == {"n1", "n2", "n3", "n4", "w10", "w11"}


def test_state_extract_rejects_wrong_parent_and_binds_census_coverage(tmp_path, monkeypatch):
    import geopandas as gpd

    from ck.catalog import load_catalog
    from ck.generated import generation_manifest

    items = load_catalog(ROOT)
    prepared = tmp_path / "prepared"
    (prepared / "files").mkdir(parents=True)
    source = road_fixture(tmp_path)
    (prepared / "files/roads_places.osm.pbf").write_bytes(source.read_bytes())
    measured = generation_manifest(
        prepared,
        recipe_version(ROOT, "android-source-v1"),
        source_inputs(ROOT, items, "geofabrik_us"),
        complete=True,
        epoch=946684800,
    )
    identifier = "android_source_us"
    items[identifier] = items["directory_points"].model_copy(
        update={
            "id": identifier,
            "inputs": list(source_inputs(ROOT, items, "geofabrik_us")),
            **measured,
        }
    )
    codes = tmp_path / "states.txt"
    codes.write_text("STUSAB|STATE\nRI|44\nAS|60\n")
    counties = gpd.GeoDataFrame(
        {"STATEFP": ["44", "60"]},
        geometry=[box(0.5, 0.5, 1.5, 1.5), box(40, 40, 41, 41)],
        crs=4326,
    )
    monkeypatch.setattr("ck.mapextract.cached_input", lambda *args: codes)
    monkeypatch.setattr("ck.mapextract.read_boundaries", lambda *args: counties)
    wrong = tmp_path / "wrong"
    with pytest.raises(ValueError, match="parent OSM source disagree"):
        build_state_extracts(ROOT, items, tmp_path, prepared, identifier, wrong, 946684800, ["AS"])
    assert not wrong.exists()
    output = tmp_path / "extracted"
    measured = build_state_extracts(
        ROOT, items, tmp_path, prepared, identifier, output, 946684800, ["RI"]
    )
    assert identifiers(output / "files/RI_roads_places.osm.pbf") == {
        "n1",
        "n2",
        "n3",
        "w10",
        "w11",
        "r20",
    }
    assert json.loads((output / "states.json").read_text())["states"] == {"RI": "44"}
    extracted_id = "android_extract_ri"
    items[extracted_id] = items[identifier].model_copy(
        update={
            "id": extracted_id,
            "inputs": [identifier, "census_county_analysis", "census_states"],
            **{key: measured[key] for key in ["size_bytes", "sha256", "pipeline_version"]},
        }
    )
    assert (
        prepared_state_source(
            ROOT, items, output, extracted_id, "RI", "geofabrik_us", 946684800
        ).name
        == "RI_roads_places.osm.pbf"
    )
    with pytest.raises(ValueError, match="state and parent source disagree"):
        prepared_state_source(
            ROOT, items, output, extracted_id, "AS", "geofabrik_oceania", 946684800
        )
    (output / "states.json").write_text("{}")
    with pytest.raises(ValueError, match="mapping changed"):
        prepared_state_source(ROOT, items, output, extracted_id, "RI", "geofabrik_us", 946684800)


def test_national_map_collection_requires_every_jurisdiction_and_bound_audits(
    tmp_path, monkeypatch
):
    import geopandas as gpd

    from ck.androidmaps import pipeline_version
    from ck.catalog import load_catalog
    from ck.generated import generation_manifest

    items = load_catalog(ROOT)
    codes = tmp_path / "states.txt"
    codes.write_text("STUSAB|STATE\nRI|44\nAS|60\n")
    counties = gpd.GeoDataFrame(
        {"STATEFP": ["44", "60"]}, geometry=[box(0, 0, 1, 1), box(2, 2, 3, 3)], crs=4326
    )
    monkeypatch.setattr("ck.mapextract.cached_input", lambda *args: codes)
    monkeypatch.setattr("ck.mapextract.read_boundaries", lambda *args: counties)
    folders = []
    for state in ["RI", "AS"]:
        folder = tmp_path / state
        (folder / "files/data").mkdir(parents=True)
        (folder / "files" / f"{state}_roads_places.obf").write_bytes(b"Synthetic OBF fixture")
        (folder / "files/data" / f"{state}_roads_places.osm.pbf").write_bytes(b"Synthetic database")
        (folder / "files" / f"{state}_SOURCE.txt").write_text("Synthetic attribution")
        (folder / "inspection.txt").write_text("Synthetic inspection fixture")
        (folder / "filter.json").write_text("{}")
        identifier = "android_map_" + state.lower()
        item = items[identifier]
        measured = generation_manifest(
            folder,
            pipeline_version(ROOT),
            {key: items[key].sha256 for key in item.inputs},
            complete=True,
            epoch=946684800,
            intermediates=["inspection.txt", "filter.json"],
        )
        items[identifier] = item.model_copy(update=measured)
        folders.append(folder)
    with pytest.raises(ValueError, match="Missing Android map jurisdictions: AS"):
        collect_android_maps(ROOT, items, tmp_path, folders[:1], tmp_path / "missing", 946684800)
    result = collect_android_maps(ROOT, items, tmp_path, folders, tmp_path / "complete", 946684800)
    assert result["jurisdictions"] == 2
    assert len(list((tmp_path / "complete/files").glob("*.obf"))) == 2
    (folders[0] / "inspection.txt").write_text("Changed audit")
    with pytest.raises(ValueError, match="audit changed"):
        collect_android_maps(ROOT, items, tmp_path, folders, tmp_path / "changed", 946684800)


def test_source_cli_dispatches_without_prepared_state_arguments(monkeypatch, capsys):
    from ck.cli import main

    calls = []

    def build(root, items, cache, output, osm_id, epoch):
        calls.append((osm_id, epoch))
        return {"fixture": True}

    monkeypatch.setattr("ck.mapextract.build_road_source", build)
    assert (
        main(
            [
                "--root",
                str(ROOT),
                "android-source",
                "--osm-id",
                "geofabrik_us",
                "--output",
                "unused-fixture",
                "--epoch",
                "946684800",
            ]
        )
        == 0
    )
    assert calls == [("geofabrik_us", 946684800)]
    assert json.loads(capsys.readouterr().out) == {"fixture": True}
