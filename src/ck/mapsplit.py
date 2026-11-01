"""Bound large-state conversions while proving complete source-object coverage."""

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import Field

from ck.androidmaps import Settings, filter_roads, pipeline_version, unpack_tool
from ck.catalog import Item, safe_path
from ck.config import Model, read_yaml
from ck.directory import read_boundaries
from ck.fetch import digest
from ck.generated import cached_input, generation_manifest, verified_generated_files
from ck.mapextract import prepared_state_source


class SplitSettings(Model):
    max_part_bytes: int = Field(ge=1024)
    max_parts: int = Field(ge=2, le=999)
    max_depth: int = Field(ge=1, le=24)
    overlap_degrees: float = Field(gt=0, le=0.01)
    max_heap_mib: int = Field(ge=256)


def settings_for(root: Path) -> SplitSettings:
    return SplitSettings.model_validate(read_yaml(root / "pipelines/androidmaps/split.yaml"))


def split_version(root: Path, prefix="android-split-v1") -> str:
    recipe = hashlib.sha256(pipeline_version(root).encode())
    for name in ("src/ck/mapsplit.py", "pipelines/androidmaps/split.yaml"):
        recipe.update(name.encode() + b"\0" + (root / name).read_bytes())
    return prefix + "-" + recipe.hexdigest()


def source_info(path: Path) -> dict:
    result = subprocess.run(
        ["osmium", "fileinfo", "--extended", "--json", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        # Osmium 1.15 cannot calculate an empty file's bounding box. Distinguish
        # that expected empty clip from a malformed or otherwise failed input.
        import osmium

        if next(iter(osmium.FileProcessor(str(path))), None) is None:
            return {"bbox": None, "count": {"nodes": 0, "ways": 0, "relations": 0}}
        raise ValueError("Cannot inspect regional source: " + result.stderr)
    data = json.loads(result.stdout)["data"]
    if data.get("multiple_versions") or not data.get("objects_ordered"):
        raise ValueError("Regional sources must be sorted with one version per object")
    return {
        "bbox": data["bbox"],
        "count": {k: data["count"][k] for k in ("nodes", "ways", "relations")},
    }


def child_bounds(bounds: list[float]) -> list[list[float]]:
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Cannot split a degenerate or out-of-range source extent")
    if east - west >= north - south:
        middle = (west + east) / 2
        return [[west, south, middle, north], [middle, south, east, north]]
    middle = (south + north) / 2
    return [[west, south, east, middle], [west, middle, east, north]]


def clip_source(source: Path, bounds: list[float], output: Path, overlap: float) -> dict:
    west, south, east, north = bounds
    expanded = [
        max(-180, west - overlap),
        max(-90, south - overlap),
        min(180, east + overlap),
        min(90, north + overlap),
    ]
    subprocess.run(
        [
            "osmium",
            "extract",
            str(source),
            "--strategy",
            "smart",
            "-S",
            "types=any",
            "--bbox",
            ",".join(format(value, ".17g") for value in expanded),
            "--output",
            str(output),
        ],
        check=True,
    )
    subprocess.run(["osmium", "check-refs", "--check-relations", str(output)], check=True)
    return source_info(output)


def verify_union(source: Path, parts: list[Path], temporary: Path) -> dict:
    if not parts or len(set(parts)) != len(parts):
        raise ValueError("Source coverage requires a distinct, nonempty part set")
    merged = temporary / "coverage-union.osm.pbf"
    subprocess.run(["osmium", "merge", *map(str, parts), "--output", str(merged)], check=True)
    try:
        result = subprocess.run(["osmium", "diff", "--quiet", str(source), str(merged)])
        if result.returncode:
            raise ValueError("Regional source union differs from the complete state source")
        return {
            "source_sha256": digest(source),
            "object_counts": source_info(source)["count"],
            "all_objects_and_attributes_equal": True,
        }
    finally:
        merged.unlink(missing_ok=True)


def split_sources(
    source: Path, stage: Path, state: str, settings: SplitSettings
) -> tuple[list[dict], dict]:
    regions = stage / "regions"
    regions.mkdir()
    source_bounds = source_info(source)["bbox"]
    if not source_bounds:
        raise ValueError("State source is empty")
    leaves, empty_bounds = [], []

    def divide(path, bounds, key, depth, info):
        if not info["count"]["nodes"]:
            empty_bounds.append(bounds)
            path.unlink()
            return
        if path.stat().st_size <= settings.max_part_bytes:
            if len(leaves) >= settings.max_parts:
                raise ValueError("Regional source set exceeds configured part limit")
            leaves.append(
                {
                    "path": path,
                    "core_bounds": bounds,
                    "tree_key": key,
                    "object_counts": info["count"],
                }
            )
            return
        if depth >= settings.max_depth:
            raise ValueError("Regional source exceeds byte bound at maximum split depth")
        for number, bounds_child in enumerate(child_bounds(bounds)):
            child = regions / f"candidate_{key}{number}.osm.pbf"
            child_info = clip_source(source, bounds_child, child, settings.overlap_degrees)
            divide(child, bounds_child, key + str(number), depth + 1, child_info)
        path.unlink()

    initial = regions / "candidate_root.osm.pbf"
    shutil.copyfile(source, initial)
    divide(initial, source_bounds, "p", 0, source_info(source))
    for number, part in enumerate(sorted(leaves, key=lambda part: part["tree_key"]), 1):
        target = regions / f"{state}_{number:03d}_roads_places.osm.pbf"
        part.pop("path").rename(target)
        part.update(
            source_path=target.relative_to(stage).as_posix(),
            source_sha256=digest(target),
            source_bytes=target.stat().st_size,
            name=f"{state}_{number:03d}_roads_places.obf",
        )
    leaves.sort(key=lambda part: part["name"])
    coverage = verify_union(source, [stage / part["source_path"] for part in leaves], stage)
    coverage.update(source_bounds=source_bounds, empty_core_bounds=empty_bounds)
    return leaves, coverage


def inspect_map(java: list[str], path: Path, epoch: int, target: Path) -> str:
    result = subprocess.run(
        [*java, "inspector", str(path.resolve())], check=True, capture_output=True, text=True
    )
    target.write_text(result.stdout)
    target.with_suffix(".stderr.log").write_text(result.stderr)
    date = re.search(r"edition = (.+)", result.stdout)
    if (
        not date
        or datetime.strptime(date[1], "%a %b %d %H:%M:%S UTC %Y").replace(tzinfo=UTC).timestamp()
        != epoch
    ):
        raise ValueError("Regional OBF creation date is not the fixed build epoch")
    if not any(section in result.stdout for section in ("Map data", "Routing data", "POI data")):
        raise ValueError("Regional OBF inspection found no map, routing, or POI index")
    return result.stdout


def preserve_failure(stage: Path, output: Path, error: Exception) -> None:
    failure = output.with_name(output.name + ".failure")
    try:
        failure.mkdir()
    except FileExistsError:
        failure = Path(tempfile.mkdtemp(prefix=output.name + ".failure-", dir=output.parent))
    for source in stage.rglob("*.log"):
        target = failure / source.relative_to(stage)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (failure / "failure.json").write_text(
        json.dumps(
            {"error_type": type(error).__name__, "error": str(error), "complete": False}, indent=2
        )
        + "\n"
    )
    error.add_note(f"Conversion diagnostics preserved at {failure}")


def build_split_map(
    root: Path,
    items: dict[str, Item],
    cache: Path,
    output: Path,
    state: str,
    osm_id: str,
    epoch: int,
    prepared: Path,
    prepared_id: str,
) -> dict:
    state = state.upper()
    if output.exists() or not re.fullmatch(r"[A-Z]{2}", state):
        raise ValueError("Split maps need a new output and a two-letter jurisdiction")
    source = prepared_state_source(root, items, prepared, prepared_id, state, osm_id, epoch)
    settings = settings_for(root)
    filters = Settings.model_validate(read_yaml(root / "pipelines/androidmaps/settings.yaml"))
    tool = cached_input(items["osmand_creator"], cache)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-split-map-") as temporary:
        stage = Path(temporary)
        try:
            files = stage / "files"
            (files / "data").mkdir(parents=True)
            original = files / "data" / f"{state}_roads_places.osm.pbf"
            counts = filter_roads(source, original, filters)
            if not counts.get("way_tagged"):
                raise ValueError("State filter produced no tagged roads")
            parts, coverage = split_sources(original, stage, state, settings)
            creator = stage / "creator"
            unpack_tool(tool, creator)
            java = [
                "java",
                "-Djava.awt.headless=true",
                "-Duser.timezone=UTC",
                "-Duser.language=en",
                "-Duser.country=US",
                "-XX:+UnlockExperimentalVMOptions",
                f"-XX:hashCode={filters.jvm_identity_hash}",
                f"-Xmx{settings.max_heap_mib}m",
                "-cp",
                str(creator / "OsmAndMapCreator.jar") + ":" + str(creator / "lib/*"),
                "net.osmand.MainUtilities",
            ]
            inspections = stage / "inspections"
            inspections.mkdir()
            all_inspections = []
            for part in parts:
                work = stage / "work"
                work.mkdir()
                leaf = work / (Path(part["name"]).stem + ".osm.pbf")
                shutil.copyfile(stage / part["source_path"], leaf)
                os.utime(leaf, (epoch, epoch))
                with (inspections / (part["name"] + ".creator.log")).open("w") as log:
                    subprocess.run(
                        [
                            *java,
                            "generate-obf",
                            str(leaf.resolve()),
                            "--no-address",
                            "--no-transport",
                        ],
                        cwd=work,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
                maps = list(work.glob("*.obf"))
                if len(maps) != 1:
                    raise ValueError("Regional converter did not produce exactly one OBF")
                maps[0].rename(files / part["name"])
                inspection_path = inspections / (part["name"] + ".txt")
                all_inspections.append(
                    inspect_map(java, files / part["name"], epoch, inspection_path)
                )
                part["inspection_path"] = inspection_path.relative_to(stage).as_posix()
                shutil.rmtree(work)
            combined = "\n".join(all_inspections)
            if not all(section in combined for section in ("Map data", "Routing data", "POI data")):
                raise ValueError("State parts do not contain all required index types")
            (files / f"{state}_SOURCE.txt").write_text(
                "Map data: © OpenStreetMap contributors, under the Open Database License.\n"
                "https://www.openstreetmap.org/copyright\n"
                "https://opendatacommons.org/licenses/odbl/1-0/\n"
                "The data/ folder contains the complete modified source database "
                "for these map parts.\n"
                f"Source: {items[osm_id].url}\nVersion: {items[osm_id].version}\n"
                f"Source SHA-256: {items[osm_id].sha256}\nPrepared source: {prepared_id}\n"
                f"Prepared manifest SHA-256: {items[prepared_id].sha256}\n"
            )
            (files / f"{state}_PARTS.txt").write_text(
                "Import every .obf file listed below. Keep all parts together.\n"
                "Importa todos los archivos .obf que aparecen abajo. "
                "Mantén juntas las partes.\nTraducción automática sin revisar.\n\n"
                + "\n".join(part["name"] for part in parts)
                + "\n"
            )
            (stage / "parts.json").write_text(
                json.dumps(
                    {"state": state, "settings": settings.model_dump(), "parts": parts},
                    sort_keys=True,
                    indent=2,
                )
                + "\n"
            )
            (stage / "coverage.json").write_text(
                json.dumps(coverage, sort_keys=True, indent=2) + "\n"
            )
            (stage / "filter.json").write_text(json.dumps(counts, sort_keys=True) + "\n")
            (stage / "inspection.txt").write_text(combined)
            if any(path.stat().st_size > 0xFFFFFFFF for path in files.rglob("*") if path.is_file()):
                raise ValueError("Split map payload exceeds a FAT32 file limit")
            versions = subprocess.run(
                ["java", "-version"], check=True, capture_output=True, text=True
            )
            intermediates = [
                "parts.json",
                "coverage.json",
                "filter.json",
                "inspection.txt",
                *[part[key] for part in parts for key in ("source_path", "inspection_path")],
            ]
            measured = generation_manifest(
                stage,
                split_version(root),
                {key: items[key].sha256 for key in (osm_id, "osmand_creator", prepared_id)},
                complete=True,
                epoch=epoch,
                intermediates=intermediates,
                tool_versions=versions.stdout
                + versions.stderr
                + "\nJVM options: "
                + json.dumps(java[1 : java.index("-cp")])
                + "\nOsmAnd creator: "
                + items["osmand_creator"].version,
            )
            shutil.rmtree(creator)
            stage.rename(output)
        except Exception as error:
            preserve_failure(stage, output, error)
            raise
    return {**measured, "parts": len(parts), "source_coverage_verified": True}


def checked_audits(folder: Path, metadata: dict) -> None:
    for entry in metadata["intermediates"]:
        relative = str(safe_path(entry["path"]))
        path = folder / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(folder.resolve())
            or path.stat().st_size != entry["size_bytes"]
            or digest(path) != entry["sha256"]
        ):
            raise ValueError("State map intermediate audit changed")


def validate_split_state(
    root: Path, state: str, folder: Path, payloads: dict[str, Path], metadata: dict, epoch: int
) -> None:
    if (
        metadata["pipeline_version"] != split_version(root)
        or metadata["source_date_epoch"] != epoch
    ):
        raise ValueError("Split state epoch or recipe changed")
    names = {entry["path"] for entry in metadata["intermediates"]}
    if not {"parts.json", "coverage.json", "filter.json", "inspection.txt"} <= names:
        raise ValueError("Split state lacks bound coverage and part audits")
    data = json.loads((folder / "parts.json").read_text())
    parts = data["parts"]
    if (
        data["state"] != state
        or not parts
        or len(parts) > settings_for(root).max_parts
        or data["settings"] != settings_for(root).model_dump()
    ):
        raise ValueError("Split state mapping or settings disagree")
    expected = {f"data/{state}_roads_places.osm.pbf", f"{state}_SOURCE.txt", f"{state}_PARTS.txt"}
    part_sources = []
    for number, part in enumerate(parts, 1):
        if part["name"] != f"{state}_{number:03d}_roads_places.obf":
            raise ValueError("Split state part sequence is incomplete or repeated")
        expected.add(part["name"])
        if part["source_path"] not in names or part["inspection_path"] not in names:
            raise ValueError("Split state lacks a bound regional source or inspection")
        source = folder / str(safe_path(part["source_path"]))
        if (
            digest(source) != part["source_sha256"]
            or source.stat().st_size != part["source_bytes"]
            or source.stat().st_size > settings_for(root).max_part_bytes
            or source_info(source)["count"] != part["object_counts"]
        ):
            raise ValueError("Split source exceeds its bound or changed")
        part_sources.append(source)
    if set(payloads) != expected:
        raise ValueError("Split state is missing a map part, source database, or attribution")
    with tempfile.TemporaryDirectory(prefix=".ck-split-coverage-") as temporary:
        actual = verify_union(
            payloads[f"data/{state}_roads_places.osm.pbf"], part_sources, Path(temporary)
        )
    expected_coverage = json.loads((folder / "coverage.json").read_text())
    if any(actual[key] != expected_coverage.get(key) for key in actual):
        raise ValueError("Split state source-coverage audit disagrees")


def collect_mixed_maps(
    root: Path, items: dict[str, Item], cache: Path, outputs: list[Path], output: Path, epoch: int
) -> dict:
    if output.exists():
        raise ValueError("National Android map collection output must be new")
    counties = read_boundaries(cached_input(items["census_county_analysis"], cache))
    with cached_input(items["census_states"], cache).open() as stream:
        states = {
            row["STUSAB"]: row["STATE"]
            for row in csv.DictReader(stream, delimiter="|")
            if row["STATE"] in set(counties.STATEFP)
        }
    selected = {}
    for folder in outputs:
        metadata = json.loads((folder / "generation.json").read_text())
        maps = [entry["path"] for entry in metadata["files"] if entry["path"].endswith(".obf")]
        codes = {
            name[:2]
            for name in maps
            if re.fullmatch(r"[A-Z]{2}(?:_[0-9]{3})?_roads_places\.obf", name)
        }
        if len(codes) != 1 or not all(
            re.fullmatch(r"[A-Z]{2}(?:_[0-9]{3})?_roads_places\.obf", name) for name in maps
        ):
            raise ValueError("State output needs one confirmed jurisdiction's OBF set")
        state = codes.pop()
        if state not in states or state in selected:
            raise ValueError("Unexpected or duplicate Android map jurisdiction")
        identifier = "android_map_" + state.lower()
        metadata, payloads = verified_generated_files(items[identifier], folder, items)
        checked_audits(folder, metadata)
        if metadata["pipeline_version"].startswith("android-split-v1-"):
            validate_split_state(root, state, folder, payloads, metadata, epoch)
        elif (
            metadata["pipeline_version"] == pipeline_version(root)
            and metadata["source_date_epoch"] == epoch
        ):
            if set(payloads) != {
                f"{state}_roads_places.obf",
                f"data/{state}_roads_places.osm.pbf",
                f"{state}_SOURCE.txt",
            } or not {"inspection.txt", "filter.json"} <= {
                entry["path"] for entry in metadata["intermediates"]
            }:
                raise ValueError("State map source database, attribution, or audit is missing")
        else:
            raise ValueError("State map epoch or recipe changed")
        if any(entry["size_bytes"] > 0xFFFFFFFF for entry in metadata["files"]):
            raise ValueError("State map payload exceeds FAT32 file limits")
        selected[state] = (folder, payloads, identifier)
    if selected.keys() != states.keys():
        raise ValueError(
            "Missing Android map jurisdictions: "
            + ", ".join(sorted(states.keys() - selected.keys()))
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-android-mixed-") as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        (stage / "states").mkdir()
        intermediates = ["jurisdictions.json"]
        for state, (folder, payloads, _) in sorted(selected.items()):
            for relative, source in payloads.items():
                target = stage / "files" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            audits = [
                "generation.json",
                *[
                    entry["path"]
                    for entry in json.loads((folder / "generation.json").read_text())[
                        "intermediates"
                    ]
                    if not entry["path"].endswith(".osm.pbf")
                ],
            ]
            for name in audits:
                relative = f"states/{state}/{name}"
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(folder / name, target)
                intermediates.append(relative)
        (stage / "jurisdictions.json").write_text(json.dumps(states, sort_keys=True) + "\n")
        result = generation_manifest(
            stage,
            split_version(root, "android-set-mixed-v1"),
            {identifier: items[identifier].sha256 for _, _, identifier in selected.values()},
            complete=True,
            epoch=epoch,
            intermediates=intermediates,
        )
        stage.rename(output)
    return {**result, "jurisdictions": len(selected)}
