"""Pinned, immutable SQLite road geometry cache; an RTree narrows exact clipping."""

import hashlib
import inspect
import json
import platform
import sqlite3
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from pyproj import CRS, Transformer
from shapely import from_wkb, to_wkb
from shapely.geometry import Point

from ck.catalog import Item
from ck.directory import EXCLUDED, excluded
from ck.generated import generation_manifest, verified_generated_files
from ck.roadsource import PLACE_VALUES, clipped_road, source_features


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def binding(root: Path, source: Item, allowed: set[str], crs: str) -> dict:
    paths = [
        "src/ck/roadsource.py",
        "src/ck/roadcache.py",
        "tools/prepare_road_cache.py",
        "src/ck/generated.py",
        "Dockerfile.build",
        "config/debian.sources",
        "pyproject.toml",
        "uv.lock",
    ]
    return {
        "algorithm": "state-road-cache-v1",
        "source": {
            key: getattr(source, key)
            for key in [
                "id",
                "sha256",
                "size_bytes",
                "url",
                "version",
                "license",
                "attribution",
                "license_proof_url",
            ]
        },
        "crs": CRS.from_user_input(crs).to_string(),
        "allowed_highways": sorted(allowed),
        "allowed_places": sorted(PLACE_VALUES),
        "excluded_tags": {
            key: None if values is None else sorted(values)
            for key, values in sorted(EXCLUDED.items())
        },
        "excluded_function_sha256": hashlib.sha256(
            inspect.getsource(excluded).encode()
        ).hexdigest(),
        "source_files": {name: digest(root / name) for name in paths},
        "tools": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            **{name: version(name) for name in ("osmium", "shapely", "pyproj")},
        },
    }


def recipe_version(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return "state-road-cache-v1-" + hashlib.sha256(raw).hexdigest()


def create_database(path: Path, source: Path, project, allowed: set[str]) -> dict:
    counts = Counter()
    places = 0
    with sqlite3.connect(path) as connection:
        connection.executescript("""
          PRAGMA page_size=4096;
          PRAGMA journal_mode=DELETE;
          CREATE TABLE roads(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
            ref TEXT NOT NULL, access TEXT NOT NULL, geometry BLOB NOT NULL,
            minx REAL NOT NULL, maxx REAL NOT NULL, miny REAL NOT NULL, maxy REAL NOT NULL);
          CREATE TABLE places(id INTEGER PRIMARY KEY, name TEXT NOT NULL, x REAL NOT NULL,
            y REAL NOT NULL);
          CREATE VIRTUAL TABLE road_index USING rtree(id,minx,maxx,miny,maxy);
          CREATE VIRTUAL TABLE place_index USING rtree(id,minx,maxx,miny,maxy);
        """)

        def road(record, geometry):
            west, south, east, north = geometry.bounds
            connection.execute(
                "INSERT INTO roads VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    record["id"],
                    record["kind"],
                    record["name"],
                    record["ref"],
                    record["access"],
                    to_wkb(geometry),
                    west,
                    east,
                    south,
                    north,
                ),
            )
            counts[record["kind"]] += 1

        def place(record):
            nonlocal places
            connection.execute(
                "INSERT INTO places VALUES(?,?,?,?)",
                (int(record["id"][1:]), record["name"], record["x"], record["y"]),
            )
            places += 1

        source_features(source, project, allowed, road, place)
        connection.execute(
            "INSERT INTO road_index SELECT id,minx,maxx,miny,maxy FROM roads ORDER BY id"
        )
        connection.execute("INSERT INTO place_index SELECT id,x,x,y,y FROM places ORDER BY id")
        connection.commit()
        connection.execute("VACUUM")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Road cache SQLite integrity check failed")
        for table in ("road_index", "place_index"):
            if connection.execute("SELECT rtreecheck(?)", (table,)).fetchone() != ("ok",):
                raise ValueError("Road cache RTree integrity check failed")
    return {
        "road_count": sum(counts.values()),
        "road_classes": dict(sorted(counts.items())),
        "place_count": places,
    }


def build_cache(
    root: Path, source: Path, item: Item, allowed: set[str], crs: str, epoch: int, output: Path
) -> dict:
    if output.exists():
        raise ValueError("Choose a fresh road-cache output; no overwrite")
    if (
        source.is_symlink()
        or source.stat().st_size != item.size_bytes
        or digest(source) != item.sha256
    ):
        raise ValueError("Road cache input differs from its actual source pin")
    record = binding(root, item, allowed, crs)
    project = Transformer.from_crs(4326, record["crs"], always_xy=True).transform
    (output / "files").mkdir(parents=True)
    audit = create_database(output / "files/roads.sqlite", source, project, allowed)
    (output / "binding.json").write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    (output / "source-counts.json").write_text(json.dumps(audit, sort_keys=True, indent=2) + "\n")
    result = generation_manifest(
        output,
        recipe_version(record),
        {item.id: item.sha256},
        complete=True,
        epoch=epoch,
        intermediates=["binding.json", "source-counts.json"],
    )
    return {**result, **audit}


def query_database(database: Path, extent, maximum: int, selection_allowed: set[str]):
    roads, places = [], []
    counts = Counter()
    west, south, east, north = extent.bounds
    # SQLite rounds RTree stored bounds outward. Overlap yields conservative candidates;
    # the same full-precision geometry intersection used by the direct path decides selection.
    uri = database.resolve().as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        placeholders = ",".join("?" for _ in selection_allowed)
        sql = (
            "SELECT r.id,r.kind,r.name,r.ref,r.access,r.geometry FROM road_index i "
            "JOIN roads r ON r.id=i.id WHERE i.minx<=? AND i.maxx>=? AND "
            f"i.miny<=? AND i.maxy>=? AND r.kind IN ({placeholders}) ORDER BY r.id"
        )
        for row in connection.execute(sql, (east, west, north, south, *sorted(selection_allowed))):
            record = dict(zip(("id", "kind", "name", "ref", "access"), row[:5], strict=True))
            selected = clipped_road(record, from_wkb(row[5]), extent)
            if selected is None:
                continue
            if len(roads) >= maximum:
                raise ValueError("Prototype source-way guard reached; no ways silently dropped")
            roads.append(selected)
            counts[selected["kind"]] += 1
        for identifier, name, x, y in connection.execute(
            "SELECT p.id,p.name,p.x,p.y FROM place_index i JOIN places p ON p.id=i.id "
            "WHERE i.minx<=? AND i.maxx>=? AND i.miny<=? AND i.maxy>=? ORDER BY p.id",
            (east, west, north, south),
        ):
            if extent.covers(Point(x, y)):
                places.append({"id": f"n{identifier}", "name": name, "x": x, "y": y})
    return roads, sorted(places, key=lambda x: x["id"]), dict(sorted(counts.items()))


def read_cached_roads(
    root: Path,
    catalog: dict[str, Item],
    folder: Path,
    extent,
    allowed: set[str],
    crs: str,
    maximum: int,
    epoch: int,
    selection_allowed: set[str] | None = None,
):
    item = catalog.get("road_cache_ri")
    if item is None:
        raise ValueError("Road cache requires its measured, pinned generated catalog item")
    metadata, payloads = verified_generated_files(item, folder, catalog)
    if set(payloads) != {"roads.sqlite"} or metadata["source_date_epoch"] != epoch:
        raise ValueError("Road cache payload inventory or epoch differs")
    if item.inputs != ["geofabrik_ri"]:
        raise ValueError("Road cache does not bind the selected Rhode Island source input")
    expected = binding(root, catalog[item.inputs[0]], allowed, crs)
    if metadata["pipeline_version"] != recipe_version(expected):
        raise ValueError("Road cache producer/input/filter/CRS binding differs")
    if {row["path"] for row in metadata["intermediates"]} != {"binding.json", "source-counts.json"}:
        raise ValueError("Road cache audit inventory differs")
    for row in metadata["intermediates"]:
        path = folder / row["path"]
        if (
            path.is_symlink()
            or path.stat().st_size != row["size_bytes"]
            or digest(path) != row["sha256"]
        ):
            raise ValueError("Road cache audit bytes changed")
    if json.loads((folder / "binding.json").read_text()) != expected:
        raise ValueError("Road cache source binding changed")
    selected = allowed if selection_allowed is None else selection_allowed
    if not selected or not selected <= allowed:
        raise ValueError("Road display selection is not covered by the cache source filter")
    result = query_database(payloads["roads.sqlite"], extent, maximum, selected)
    return (
        *result,
        {"manifest": metadata, "raw_manifest_sha256": digest(folder / "generation.json")},
    )
