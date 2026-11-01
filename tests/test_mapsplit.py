import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from shapely import box

from ck.fetch import digest
from ck.generated import generation_manifest
from ck.mapsplit import (
    SplitSettings,
    child_bounds,
    clip_source,
    collect_mixed_maps,
    preserve_failure,
    settings_for,
    split_sources,
    split_version,
    verify_union,
)

ROOT = Path(__file__).resolve().parents[1]
EPOCH = 1793404800


def reference_fixture(tmp_path):
    xml = tmp_path / "reference.osm"
    xml.write_text("""<osm version="0.6">
      <node id="1" lat="1" lon="1"/><node id="2" lat="1" lon="2"/>
      <node id="3" lat="1" lon="3"/>
      <node id="5" lat="2" lon="9"/><node id="6" lat="2" lon="10"/>
      <node id="99" lat="3" lon="8"><tag k="amenity" v="pharmacy"/></node>
      <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/></way>
      <way id="11"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/></way>
      <way id="12"><nd ref="5"/><nd ref="6"/><tag k="highway" v="residential"/></way>
      <relation id="20"><member type="way" ref="10" role="from"/>
        <member type="node" ref="2" role="via"/><member type="way" ref="11" role="to"/>
        <tag k="type" v="restriction"/><tag k="restriction" v="no_right_turn"/>
      </relation></osm>""")
    source = tmp_path / "reference.osm.pbf"
    subprocess.run(["osmium", "cat", str(xml), "--output", str(source)], check=True)
    return source


def test_overlap_preserves_cross_boundary_restrictions_and_detects_missing_places(tmp_path):
    source = reference_fixture(tmp_path)
    original = digest(source)
    parts = [tmp_path / "west.osm.pbf", tmp_path / "east.osm.pbf"]
    for bounds, output in zip([[0, 0, 2.5, 4], [2.5, 0, 11, 4]], parts, strict=True):
        clip_source(source, bounds, output, 0.001)
    empty = tmp_path / "empty.osm.pbf"
    assert clip_source(source, [-50, -50, -49, -49], empty, 0.001)["count"]["nodes"] == 0
    assert verify_union(source, parts, tmp_path)["all_objects_and_attributes_equal"] is True
    with pytest.raises(ValueError, match="union differs"):
        verify_union(source, parts[:1], tmp_path)
    assert digest(source) == original


def test_adaptive_partition_is_bounded_and_repeats_without_changing_source(tmp_path):
    nodes, ways = [], []
    for number in range(128):
        lon, lat = 1 + number % 16, 1 + number // 16
        first = 2 * number + 1
        nodes.extend(
            [
                f'<node id="{first}" lat="{lat}" lon="{lon}"/>',
                f'<node id="{first + 1}" lat="{lat + 0.01}" lon="{lon + 0.01}"/>',
            ]
        )
        name = hashlib.sha256(str(number).encode()).hexdigest()
        ways.append(
            f'<way id="{number + 1}"><nd ref="{first}"/><nd ref="{first + 1}"/>'
            f'<tag k="highway" v="residential"/><tag k="name" v="{name}"/></way>'
        )
    xml = tmp_path / "spread.osm"
    xml.write_text('<osm version="0.6">' + "".join(nodes + ways) + "</osm>")
    source = tmp_path / "spread.osm.pbf"
    subprocess.run(["osmium", "cat", str(xml), "--output", str(source)], check=True)
    settings = SplitSettings(
        max_part_bytes=2048,
        max_parts=128,
        max_depth=12,
        overlap_degrees=0.001,
        max_heap_mib=256,
    )
    original = digest(source)
    results = []
    for repeat in ["a", "b"]:
        stage = tmp_path / repeat
        stage.mkdir()
        parts, coverage = split_sources(source, stage, "CA", settings)
        assert len(parts) > 1
        assert all(part["source_bytes"] <= 2048 for part in parts)
        assert coverage["all_objects_and_attributes_equal"] is True
        results.append((parts, coverage))
    assert results[0] == results[1]
    assert digest(source) == original
    limited = tmp_path / "limited"
    limited.mkdir()
    with pytest.raises(ValueError, match="maximum split depth"):
        split_sources(
            source,
            limited,
            "CA",
            settings.model_copy(update={"max_part_bytes": 1024, "max_depth": 1}),
        )
    assert (
        box(*child_bounds([0, 0, 4, 2])[0])
        .union(box(*child_bounds([0, 0, 4, 2])[1]))
        .equals(box(0, 0, 4, 2))
    )


def test_failure_logs_survive_staging_cleanup(tmp_path):
    stage = tmp_path / "stage"
    (stage / "inspections").mkdir(parents=True)
    (stage / "inspections/CA_001.creator.log").write_text("Synthetic Java heap failure")
    output = tmp_path / "result"
    preserve_failure(stage, output, ValueError("Synthetic failure"))
    assert not output.exists()
    failure = tmp_path / "result.failure"
    assert "heap failure" in (failure / "inspections/CA_001.creator.log").read_text()
    assert json.loads((failure / "failure.json").read_text())["complete"] is False


def split_fixture(tmp_path, items):
    folder = tmp_path / "CA"
    (folder / "files/data").mkdir(parents=True)
    (folder / "regions").mkdir()
    (folder / "inspections").mkdir()
    source = reference_fixture(tmp_path)
    (folder / "files/data/CA_roads_places.osm.pbf").write_bytes(source.read_bytes())
    parts = []
    for number, bounds in enumerate([[0, 0, 2.5, 4], [2.5, 0, 11, 4]], 1):
        source_path = f"regions/CA_{number:03d}.osm.pbf"
        info = clip_source(source, bounds, folder / source_path, 0.001)
        name = f"CA_{number:03d}_roads_places.obf"
        inspection = f"inspections/{name}.txt"
        (folder / "files" / name).write_bytes(b"Synthetic regional OBF")
        (folder / inspection).write_text("Synthetic inspection fixture")
        parts.append(
            {
                "name": name,
                "source_path": source_path,
                "inspection_path": inspection,
                "source_sha256": digest(folder / source_path),
                "source_bytes": (folder / source_path).stat().st_size,
                "object_counts": info["count"],
            }
        )
    coverage = verify_union(source, [folder / part["source_path"] for part in parts], folder)
    (folder / "parts.json").write_text(
        json.dumps({"state": "CA", "settings": settings_for(ROOT).model_dump(), "parts": parts})
    )
    (folder / "coverage.json").write_text(json.dumps(coverage))
    (folder / "filter.json").write_text("{}")
    (folder / "inspection.txt").write_text("Synthetic combined inspection")
    (folder / "files/CA_SOURCE.txt").write_text("Synthetic attribution")
    (folder / "files/CA_PARTS.txt").write_text("Synthetic parts list")
    return folder


def pin_folder(items, identifier, folder, version):
    metadata = generation_manifest(
        folder,
        version,
        {key: items[key].sha256 for key in items[identifier].inputs},
        complete=True,
        epoch=EPOCH,
        intermediates=[
            path.relative_to(folder).as_posix()
            for path in sorted(folder.rglob("*"))
            if path.is_file()
            and not path.is_relative_to(folder / "files")
            and path.name != "generation.json"
        ],
    )
    items[identifier] = items[identifier].model_copy(update=metadata)


def test_mixed_collection_requires_every_part_even_when_a_partial_manifest_is_repinned(
    tmp_path, monkeypatch
):
    import geopandas as gpd

    from ck.androidmaps import pipeline_version
    from ck.catalog import load_catalog

    items = load_catalog(ROOT)
    codes = tmp_path / "codes.txt"
    codes.write_text("STUSAB|STATE\nRI|44\nCA|06\n")
    counties = gpd.GeoDataFrame(
        {"STATEFP": ["44", "06"]}, geometry=[box(0, 0, 1, 1), box(2, 2, 3, 3)], crs=4326
    )
    monkeypatch.setattr("ck.mapsplit.cached_input", lambda *args: codes)
    monkeypatch.setattr("ck.mapsplit.read_boundaries", lambda *args: counties)
    legacy = tmp_path / "RI"
    (legacy / "files/data").mkdir(parents=True)
    for name in ["RI_roads_places.obf", "data/RI_roads_places.osm.pbf", "RI_SOURCE.txt"]:
        (legacy / "files" / name).write_bytes(b"Synthetic legacy payload")
    (legacy / "inspection.txt").write_text("Synthetic inspection")
    (legacy / "filter.json").write_text("{}")
    pin_folder(items, "android_map_ri", legacy, pipeline_version(ROOT))
    split = split_fixture(tmp_path, items)
    pin_folder(items, "android_map_ca", split, split_version(ROOT))
    with pytest.raises(ValueError, match="Missing Android map jurisdictions: CA"):
        collect_mixed_maps(ROOT, items, tmp_path, [legacy], tmp_path / "missing", EPOCH)
    result = collect_mixed_maps(ROOT, items, tmp_path, [legacy, split], tmp_path / "set", EPOCH)
    assert result["jurisdictions"] == 2
    assert len(list((tmp_path / "set/files").glob("*.obf"))) == 3
    data = json.loads((split / "parts.json").read_text())
    removed = data["parts"].pop()
    (split / "parts.json").write_text(json.dumps(data))
    (split / "files" / removed["name"]).unlink()
    pin_folder(items, "android_map_ca", split, split_version(ROOT))
    with pytest.raises(ValueError, match="union differs"):
        collect_mixed_maps(ROOT, items, tmp_path, [legacy, split], tmp_path / "partial", EPOCH)


def test_split_cli_and_preparation_use_only_explicit_prepared_inputs(monkeypatch, capsys):
    from ck.catalog import load_catalog
    from ck.cli import main
    from ck.preparation import generated_actions

    items = load_catalog(ROOT)
    ordinary = generated_actions(ROOT, items, "android_map_ca")[0]["args"]
    assert "--split" not in ordinary
    items["android_map_ca"].pipeline_version = split_version(ROOT)
    assert "--split" in generated_actions(ROOT, items, "android_map_ca")[0]["args"]
    calls = []
    monkeypatch.setattr(
        "ck.mapsplit.build_split_map", lambda *args: calls.append(args) or {"fixture": True}
    )
    common = [
        "--root",
        str(ROOT),
        "android-map",
        "--split",
        "--state",
        "CA",
        "--osm-id",
        "geofabrik_us",
        "--output",
        "unused",
        "--epoch",
        str(EPOCH),
    ]
    with pytest.raises(SystemExit):
        main(common)
    assert not calls
    assert "checked prepared state source" in capsys.readouterr().err
    assert (
        main([*common, "--prepared", "prepared-fixture", "--prepared-id", "android_extract_ca"])
        == 0
    )
    assert calls[0][-2:] == (Path("prepared-fixture"), "android_extract_ca")
