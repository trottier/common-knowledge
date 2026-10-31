import gzip
import io
from pathlib import Path

import pytest
from mapbox_vector_tile.Mapbox import vector_tile_pb2 as mvt
from pmtiles.reader import MemorySource, Reader, all_tiles
from pmtiles.tile import Compression, TileType, zxy_to_tileid

from ck.laptopmap import TileWriter, bounded_tiles, build_laptop_tiles, narrow_tile, settings_for

ROOT = Path(__file__).resolve().parents[1]


def sample_tile():
    tile = mvt.tile()

    def layer(name, kind, details=None, extras=None):
        result = tile.layers.add()
        result.name, result.version, result.extent = name, 2, 4096
        feature = result.features.add()
        feature.id, feature.type = 7, mvt.tile.LineString
        feature.geometry.extend([9, 0, 0, 10, 20, 20])
        props = {"kind": kind, "name": "Synthetic road", **(extras or {})}
        if details:
            props["kind_detail"] = details
        for key, value in props.items():
            feature.tags.extend([len(result.keys), len(result.values)])
            result.keys.append(key)
            result.values.add().string_value = value
        return result

    layer("roads", "minor_road", "residential", {"phone": "SECRET-CONTACT"})
    layer("pois", "substation", extras={"name": "SECRET-FACILITY"})
    layer("places", "locality", extras={"power": "substation", "name": "SECRET-SITE"})
    layer("water", "water", "dam", {"name": "SECRET-DAM"})
    return tile.SerializeToString(deterministic=True)


def archive(path, entries):
    with path.open("wb") as output:
        temporary = io.BytesIO()
        writer = TileWriter(output, temporary)
        for identifier, payload in entries:
            writer.add(identifier, gzip.compress(payload, mtime=0))
        writer.finish({"tile_type": TileType.MVT, "tile_compression": Compression.GZIP}, {})


def test_narrow_map_preserves_geometry_and_removes_hidden_source_values():
    original = sample_tile()
    data = narrow_tile(original, settings_for(ROOT))
    result = mvt.tile()
    result.ParseFromString(data)
    assert [layer.name for layer in result.layers] == ["roads"]
    assert list(result.layers[0].features[0].geometry) == [9, 0, 0, 10, 20, 20]
    assert result.layers[0].features[0].id == 7
    assert b"SECRET" not in data and b"power" not in data and b"phone" not in data
    assert b"Synthetic road" in data


def test_writer_reproduces_bytes_and_skips_high_zoom_payload_reads(tmp_path):
    entries = [
        (zxy_to_tileid(0, 0, 0), sample_tile()),
        (zxy_to_tileid(13, 0, 0), sample_tile() + b"\x80\x06\x01"),
    ]
    for name in ["first", "second"]:
        archive(tmp_path / name, entries)
    assert (tmp_path / "first").read_bytes() == (tmp_path / "second").read_bytes()
    content = (tmp_path / "first").read_bytes()
    source = MemorySource(content)
    reader = Reader(source)
    high_payload = list(all_tiles(source))[1][1]
    requested = []

    def checked(offset, length):
        payload = source(offset, length)
        requested.append(payload)
        return payload

    selected = list(bounded_tiles(checked, reader.header(), 12))
    assert [identifier for identifier, _ in selected] == [0]
    assert high_payload not in requested


def test_laptop_tile_set_deduplicates_overlap_and_rejects_different_source_tiles(tmp_path):
    from ck.catalog import load_catalog
    from ck.generated import generation_manifest

    items = load_catalog(ROOT)
    generated = tmp_path / "generated"
    folder = generated / "protomaps_us"
    (folder / "files").mkdir(parents=True)
    for state in ["RI", "DE"]:
        archive(folder / "files" / f"{state}.pmtiles", [(0, sample_tile())])
    measured = generation_manifest(
        folder,
        "synthetic-fixture",
        {"protomaps_planet": items["protomaps_planet"].sha256},
        complete=True,
        epoch=946684800,
    )
    items["protomaps_us"] = items["protomaps_us"].model_copy(
        update={
            "inputs": ["protomaps_planet"],
            **measured,
        }
    )
    for name in ["first", "second"]:
        result = build_laptop_tiles(ROOT, items, generated, tmp_path / name, 946684800)
        assert result["tiles"] == 1
    assert (tmp_path / "first/generation.json").read_bytes() == (
        tmp_path / "second/generation.json"
    ).read_bytes()
    payload = tmp_path / "first/files/2_US_ROADS.pmtiles"
    reader = Reader(MemorySource(payload.read_bytes()))
    assert reader.metadata()["ck_dataset"] == settings_for(ROOT).dataset_id
    assert b"SECRET" not in gzip.decompress(reader.get(0, 0, 0))
    modified = mvt.tile()
    modified.ParseFromString(sample_tile())
    modified.layers[0].features[0].geometry[-1] = 22
    archive(folder / "files/RI.pmtiles", [(0, modified.SerializeToString(deterministic=True))])
    measured = generation_manifest(
        folder,
        "synthetic-fixture",
        {"protomaps_planet": items["protomaps_planet"].sha256},
        complete=True,
        epoch=946684800,
    )
    items["protomaps_us"] = items["protomaps_us"].model_copy(update=measured)
    with pytest.raises(ValueError, match="different source tiles"):
        build_laptop_tiles(ROOT, items, generated, tmp_path / "different", 946684800)
    assert not (tmp_path / "different").exists()
