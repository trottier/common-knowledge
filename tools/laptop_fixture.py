"""Build a synthetic browser test map with the real, checksum-checked SDKs.

This is a test fixture. It never updates production catalog pins.
Run inside the build container: python tools/laptop_fixture.py OUTPUT --cache CACHE.
"""

import argparse
import gzip
import io
from pathlib import Path

import mapbox_vector_tile
from pmtiles.tile import Compression, TileType

from ck.catalog import load_catalog
from ck.generated import generation_manifest
from ck.laptopmap import TileWriter, settings_for
from ck.laptopviewer import build_viewer


def fixture(root: Path, output: Path, cache: Path):
    items = load_catalog(root)
    settings = settings_for(root)
    epoch = 946684800
    generated = output / "generated"
    base = generated / "protomaps_us"
    data = generated / "laptop_roads_places"
    for folder in (base, data):
        (folder / "files").mkdir(parents=True)
    tile = mapbox_vector_tile.encode(
        [
            {
                "name": "places",
                "features": [
                    {
                        "geometry": {"type": "Point", "coordinates": [0, 0]},
                        "properties": {"kind": "locality", "name": "Synthetic test town"},
                    }
                ],
            },
            {
                "name": "roads",
                "features": [
                    {
                        "geometry": {"type": "LineString", "coordinates": [[-45, -20], [45, 20]]},
                        "properties": {"kind": "major_road", "name": "Synthetic test road"},
                    }
                ],
            },
        ],
        default_options={"quantize_bounds": (-180, -85, 180, 85)},
    )
    metadata = {
        "ck_dataset": settings.dataset_id,
        "ck_source_version": "synthetic-fixture",
        "source_date_epoch": epoch,
    }
    with (data / "files" / settings.archive_filename).open("wb") as stream:
        writer = TileWriter(stream, io.BytesIO())
        writer.add(0, gzip.compress(tile, mtime=0))
        writer.finish(
            {
                "tile_type": TileType.MVT,
                "tile_compression": Compression.GZIP,
                "min_lon_e7": -1800000000,
                "max_lon_e7": 1800000000,
                "min_lat_e7": -850000000,
                "max_lat_e7": 850000000,
            },
            metadata,
        )
    (base / "files/RI.pmtiles").write_bytes(
        (data / "files" / settings.archive_filename).read_bytes()
    )
    measured = generation_manifest(
        base,
        "synthetic-fixture",
        {"protomaps_planet": items["protomaps_planet"].sha256},
        complete=True,
        epoch=epoch,
    )
    items["protomaps_us"] = items["protomaps_us"].model_copy(
        update={**measured, "inputs": ["protomaps_planet"], "version": "synthetic-fixture"}
    )
    measured = generation_manifest(
        data,
        "synthetic-fixture",
        {"protomaps_us": items["protomaps_us"].sha256},
        complete=True,
        epoch=epoch,
    )
    items["laptop_roads_places"] = items["laptop_roads_places"].model_copy(update=measured)
    build_viewer(root, items, cache, generated, output / "viewer", epoch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    fixture(Path(__file__).resolve().parents[1], args.output, args.cache)
