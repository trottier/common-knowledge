"""Regenerate a narrow offline laptop basemap without hidden POI/infrastructure layers."""

import gzip
import hashlib
import json
import mmap
import shutil
import sqlite3
import tempfile
from pathlib import Path

from mapbox_vector_tile.Mapbox import vector_tile_pb2
from pmtiles.reader import Reader
from pmtiles.tile import (
    Compression,
    Entry,
    TileType,
    deserialize_directory,
    zxy_to_tileid,
)
from pmtiles.writer import finalize_header
from pydantic import Field

from ck.catalog import Item, safe_path
from ck.config import Identifier, Model, read_yaml
from ck.directory import excluded
from ck.generated import generation_manifest, verified_generated_files


class View(Model):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-85, le=85)
    zoom: int = Field(ge=0, le=14)


class Settings(Model):
    basemap_id: Identifier
    dataset_id: Identifier
    archive_filename: str
    max_zoom: int = Field(ge=0, le=14)
    max_archive_bytes: int = Field(gt=0, le=0xFFFFFFFF)
    default_view: View
    view_max_zoom: int = Field(ge=0, le=22)
    worker_count: int = Field(ge=1, le=8)
    fields: dict[str, list[str]]
    kinds: dict[str, list[str]]
    excluded_details: list[str]


def settings_for(root: Path) -> Settings:
    settings = Settings.model_validate(read_yaml(root / "pipelines/laptopmap/settings.yaml"))
    relative = safe_path(settings.archive_filename)
    if len(relative.parts) != 1 or relative.suffix != ".pmtiles":
        raise ValueError("Laptop map archive needs one FAT-safe PMTiles filename")
    if (
        set(settings.fields) != {"roads", "places", "water"}
        or settings.kinds.keys() != settings.fields.keys()
    ):
        raise ValueError("Laptop map policy permits only roads, places and water")
    return settings


def properties(layer, feature) -> dict:
    if len(feature.tags) % 2:
        raise ValueError("Malformed vector feature tag pairs")
    result = {}
    for index in range(0, len(feature.tags), 2):
        key = layer.keys[feature.tags[index]]
        value = layer.values[feature.tags[index + 1]]
        fields = value.ListFields()
        if len(fields) != 1 or key in result:
            raise ValueError("Vector feature has ambiguous property values")
        result[key] = (fields[0][1], fields[0][0].name)
    return result


def narrow_tile(payload: bytes, settings: Settings) -> bytes:
    original = vector_tile_pb2.tile()
    original.ParseFromString(payload)
    if not original.IsInitialized():
        raise ValueError("Vector tile omits required schema fields")
    result = vector_tile_pb2.tile()
    for layer in original.layers:
        if layer.name not in settings.fields:
            continue
        target = result.layers.add()
        target.name, target.version, target.extent = layer.name, layer.version, layer.extent
        keys, values = {}, {}
        for feature in layer.features:
            props = properties(layer, feature)
            plain = {key: value[0] for key, value in props.items()}
            if (
                plain.get("kind") not in settings.kinds[layer.name]
                or plain.get("kind_detail") in settings.excluded_details
                or excluded(plain)
            ):
                continue
            if layer.name == "water" and feature.type != vector_tile_pb2.tile.Polygon:
                continue
            output = target.features.add()
            if feature.HasField("id"):
                output.id = feature.id
            output.type = feature.type
            output.geometry.extend(feature.geometry)
            for key in sorted(props.keys() & set(settings.fields[layer.name])):
                value = vector_tile_pb2.tile.value()
                setattr(value, props[key][1], props[key][0])
                encoded = value.SerializeToString(deterministic=True)
                if key not in keys:
                    keys[key] = len(target.keys)
                    target.keys.append(key)
                if encoded not in values:
                    values[encoded] = len(target.values)
                    target.values.add().CopyFrom(value)
                output.tags.extend([keys[key], values[encoded]])
        if not target.features:
            del result.layers[-1]
    # Rebuilding dictionaries removes unused original values, including names
    # from rejected features. Geometry integers of retained features stay exact.
    return result.SerializeToString(deterministic=True)


def bounded_tiles(get_bytes, header, maximum, offset=None, length=None):
    """Skip high-zoom payloads before reading them from a large input archive."""
    entries = deserialize_directory(
        get_bytes(
            header["root_offset"] if offset is None else offset,
            header["root_length"] if length is None else length,
        )
    )
    cutoff = zxy_to_tileid(maximum + 1, 0, 0)
    for entry in entries:
        if entry.tile_id >= cutoff:
            break
        if entry.run_length == 0:
            yield from bounded_tiles(
                get_bytes,
                header,
                maximum,
                header["leaf_directory_offset"] + entry.offset,
                entry.length,
            )
        else:
            data = None
            for identifier in range(entry.tile_id, min(entry.tile_id + entry.run_length, cutoff)):
                if data is None:
                    data = get_bytes(header["tile_data_offset"] + entry.offset, entry.length)
                yield identifier, data


class TileWriter:
    """Use exact-content deduplication rather than Python's randomized bytes hash."""

    def __init__(self, output, temporary):
        self.output, self.data = output, temporary
        self.entries, self.seen = [], {}
        self.count, self.offset = 0, 0

    def add(self, identifier: int, payload: bytes):
        if (
            self.entries
            and identifier <= self.entries[-1].tile_id + self.entries[-1].run_length - 1
        ):
            raise ValueError("Write laptop tiles in strictly increasing order")
        checksum = hashlib.sha256(payload).digest()
        previous = self.seen.get(checksum)
        if previous is None:
            offset = self.offset
            self.data.seek(offset)
            self.data.write(payload)
            self.seen[checksum] = (offset, len(payload))
            self.offset += len(payload)
        else:
            offset, length = previous
            self.data.seek(offset)
            if length != len(payload) or self.data.read(length) != payload:
                raise ValueError("Tile checksum collision; refusing an ambiguous archive")
        if (
            self.entries
            and self.entries[-1].offset == offset
            and identifier == self.entries[-1].tile_id + self.entries[-1].run_length
        ):
            self.entries[-1].run_length += 1
        else:
            self.entries.append(Entry(identifier, offset, len(payload), 1))
        self.count += 1

    def finish(self, header, metadata):
        if not self.entries:
            raise ValueError("Laptop basemap contains no retained tiles")
        blocks = finalize_header(
            header, self.count, self.entries, len(self.seen), metadata, True, self.offset
        )
        for block in blocks:
            self.output.write(block)
        self.data.seek(0)
        shutil.copyfileobj(self.data, self.output)


def build_laptop_tiles(
    root: Path, items: dict[str, Item], generated: Path, output: Path, epoch: int
) -> dict:
    if output.exists():
        raise ValueError("Laptop basemap output must be new")
    settings = settings_for(root)
    source = items[settings.basemap_id]
    manifest, payloads = verified_generated_files(source, generated / source.id, items)
    if manifest["source_date_epoch"] != epoch or any(
        not name.endswith(".pmtiles") for name in payloads
    ):
        raise ValueError("Laptop map requires matching-epoch checked PMTiles inputs")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-laptop-tiles-") as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        database = sqlite3.connect(stage / "tiles.sqlite")
        database.execute(
            "CREATE TABLE tiles (id INTEGER PRIMARY KEY, source_sha BLOB NOT NULL, payload BLOB)"
        )
        bounds, input_tiles = [], 0
        try:
            for _name, path in sorted(payloads.items()):
                with (
                    path.open("rb") as stream,
                    mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mapped,
                ):

                    def get_bytes(offset, length):
                        return mapped[offset : offset + length]

                    reader = Reader(get_bytes)
                    header = reader.header()
                    if header["tile_type"] != TileType.MVT or header["tile_compression"] not in {
                        Compression.GZIP,
                        Compression.NONE,
                    }:
                        raise ValueError("Unsupported laptop basemap tile encoding")
                    bounds.append(header)
                    for identifier, data in bounded_tiles(get_bytes, header, settings.max_zoom):
                        row = database.execute(
                            "SELECT source_sha FROM tiles WHERE id=?", (identifier,)
                        ).fetchone()
                        if row is not None:
                            if hashlib.sha256(data).digest() != row[0]:
                                raise ValueError(
                                    "Overlapping atlas extracts contain different source tiles"
                                )
                            continue
                        raw = (
                            gzip.decompress(data)
                            if header["tile_compression"] == Compression.GZIP
                            else data
                        )
                        filtered = narrow_tile(raw, settings)
                        encoded = gzip.compress(filtered, mtime=0) if filtered else b""
                        database.execute(
                            "INSERT INTO tiles VALUES (?,?,?)",
                            (identifier, hashlib.sha256(data).digest(), encoded),
                        )
                        input_tiles += 1
                database.commit()
            target = stage / "files" / settings.archive_filename
            header = {
                "tile_type": TileType.MVT,
                "tile_compression": Compression.GZIP,
                "min_lon_e7": min(h["min_lon_e7"] for h in bounds),
                "min_lat_e7": min(h["min_lat_e7"] for h in bounds),
                "max_lon_e7": max(h["max_lon_e7"] for h in bounds),
                "max_lat_e7": max(h["max_lat_e7"] for h in bounds),
                "center_lon_e7": round(settings.default_view.longitude * 10_000_000),
                "center_lat_e7": round(settings.default_view.latitude * 10_000_000),
                "center_zoom": settings.default_view.zoom,
            }
            metadata = {
                "name": "Common Knowledge roads and places",
                "format": "pbf",
                "attribution": "© OpenStreetMap contributors; Protomaps",
                "license": "ODbL-1.0",
                "ck_dataset": settings.dataset_id,
                "ck_source_version": source.version,
                "source_date_epoch": epoch,
                "vector_layers": [{"id": name, "fields": {}} for name in sorted(settings.fields)],
            }
            with target.open("wb") as result, tempfile.TemporaryFile() as data:
                writer = TileWriter(result, data)
                for identifier, payload in database.execute(
                    "SELECT id,payload FROM tiles WHERE length(payload)>0 ORDER BY id"
                ):
                    writer.add(identifier, payload)
                writer.finish(header, metadata)
            if target.stat().st_size > settings.max_archive_bytes:
                raise ValueError(
                    "Laptop map exceeds its explicit size budget; change policy and rebuild"
                )
        finally:
            database.close()
        (stage / "tiles.sqlite").unlink()
        (stage / "filter.json").write_text(
            json.dumps(
                {
                    "input_archives": sorted(payloads),
                    "unique_input_tiles": input_tiles,
                    "max_zoom": settings.max_zoom,
                    "retained_tiles": writer.count,
                    "layers": sorted(settings.fields),
                },
                sort_keys=True,
            )
            + "\n"
        )
        recipe = hashlib.sha256()
        for name in [
            "src/ck/laptopmap.py",
            "src/ck/directory.py",
            "src/ck/generated.py",
            "pipelines/laptopmap/settings.yaml",
            "pyproject.toml",
            "uv.lock",
            "Dockerfile.build",
        ]:
            recipe.update(name.encode() + b"\0" + (root / name).read_bytes())
        measured = generation_manifest(
            stage,
            "laptop-tiles-v1-" + recipe.hexdigest(),
            {source.id: source.sha256},
            complete=True,
            epoch=epoch,
            intermediates=["filter.json"],
        )
        stage.rename(output)
    return {**measured, "tiles": writer.count}
