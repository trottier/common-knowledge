"""Prepare checked road sources and reference-complete Census jurisdiction extracts."""

import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pydantic import Field
from shapely import box
from shapely.geometry import mapping
from shapely.ops import unary_union

from ck.androidmaps import Settings, filter_roads
from ck.catalog import Item
from ck.config import Identifier, Model, read_yaml
from ck.directory import read_boundaries
from ck.generated import cached_input, generation_manifest, verified_generated_files


class NationalSettings(Model):
    source_inputs: dict[str, Identifier]
    pacific_states: list[str]
    boundary_padding_degrees: float = Field(gt=0, le=0.01)
    max_heap_mib: int = Field(ge=256)

    def source_for(self, state: str) -> str:
        return self.source_inputs["oceania" if state in self.pacific_states else "us"]


def policy(root: Path) -> NationalSettings:
    return NationalSettings.model_validate(read_yaml(root / "pipelines/androidmaps/national.yaml"))


def recipe_version(root: Path, prefix: str) -> str:
    recipe = hashlib.sha256()
    for name in (
        "src/ck/mapextract.py",
        "src/ck/androidmaps.py",
        "src/ck/directory.py",
        "src/ck/generated.py",
        "pipelines/androidmaps/settings.yaml",
        "pipelines/androidmaps/national.yaml",
        "Dockerfile.build",
        "uv.lock",
        "config/debian.sources",
    ):
        recipe.update(name.encode() + b"\0" + (root / name).read_bytes())
    return prefix + "-" + recipe.hexdigest()


def build_road_source(
    root: Path, items: dict[str, Item], cache: Path, output: Path, osm_id: str, epoch: int
) -> dict:
    if output.exists():
        raise ValueError("Prepared road source output must be new")
    if osm_id not in policy(root).source_inputs.values():
        raise ValueError("Choose a configured national parent OSM source")
    source = cached_input(items[osm_id], cache)
    settings = Settings.model_validate(read_yaml(root / "pipelines/androidmaps/settings.yaml"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-road-source-") as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        counts = filter_roads(source, stage / "files/roads_places.osm.pbf", settings)
        if not counts.get("way_tagged"):
            raise ValueError("National road filter produced no tagged ways")
        (stage / "filter.json").write_text(json.dumps(counts, sort_keys=True) + "\n")
        measured = generation_manifest(
            stage,
            recipe_version(root, "android-source-v1"),
            {osm_id: items[osm_id].sha256},
            complete=True,
            epoch=epoch,
            intermediates=["filter.json"],
        )
        stage.rename(output)
    return {**measured, "filter": counts}


def extraction_regions(geometry, padding: float):
    """Split antimeridian extents before invoking Osmium's polygon extractor."""
    west, _, east, _ = geometry.bounds
    parts = [geometry]
    if east - west > 180:
        parts = [
            geometry.intersection(box(-180, -90, 0, 90)),
            geometry.intersection(box(0, -90, 180, 90)),
        ]
    for part in parts:
        if part.is_empty:
            continue
        buffered = part.simplify(padding / 4, preserve_topology=True).buffer(padding)
        # A simplified boundary must not remove source territory geometry.
        if not buffered.covers(part):
            buffered = part.buffer(padding)
        buffered = buffered.intersection(box(-180, -90, 180, 90))
        if buffered.geom_type not in {"Polygon", "MultiPolygon"} or buffered.is_empty:
            raise ValueError("No usable Census extraction geometry")
        yield buffered


def extract_roads(source: Path, geometry, output: Path, padding: float) -> None:
    """Keep complete ways and all retained relation members, including turn restrictions."""
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-map-extract-") as temporary:
        stage = Path(temporary)
        parts = []
        for number, region in enumerate(extraction_regions(geometry, padding)):
            polygon = stage / f"part-{number}.geojson"
            polygon.write_text(
                json.dumps({"type": "Feature", "properties": {}, "geometry": mapping(region)})
                + "\n"
            )
            target = stage / f"part-{number}.osm.pbf"
            subprocess.run(
                [
                    "osmium",
                    "extract",
                    "-F",
                    "pbf",
                    str(source),
                    "--strategy",
                    "smart",
                    "-S",
                    "types=any",
                    "--polygon",
                    str(polygon),
                    "--output",
                    str(target),
                ],
                check=True,
            )
            parts.append(target)
        if not parts:
            raise ValueError("Census extraction geometry is empty")
        if len(parts) == 1:
            parts[0].rename(output)
        else:
            subprocess.run(
                ["osmium", "merge", *map(str, parts), "--output", str(output)], check=True
            )
    subprocess.run(["osmium", "check-refs", "--check-relations", str(output)], check=True)


def build_state_extracts(
    root: Path,
    items: dict[str, Item],
    cache: Path,
    prepared: Path,
    prepared_id: str,
    output: Path,
    epoch: int,
    states: list[str],
) -> dict:
    if output.exists():
        raise ValueError("State map extraction output must be new")
    settings = policy(root)
    source_item = items[prepared_id]
    manifest, payloads = verified_generated_files(source_item, prepared, items)
    if manifest["source_date_epoch"] != epoch or manifest["pipeline_version"] != recipe_version(
        root, "android-source-v1"
    ):
        raise ValueError("Prepared road source epoch or recipe changed")
    if set(payloads) != {"roads_places.osm.pbf"}:
        raise ValueError("Expected one checked national road-source payload")
    counties = read_boundaries(cached_input(items["census_county_analysis"], cache))
    with cached_input(items["census_states"], cache).open() as stream:
        codes = {row["STUSAB"]: row["STATE"] for row in csv.DictReader(stream, delimiter="|")}
    valid_states = {code for code, fips in codes.items() if fips in set(counties.STATEFP)}
    if not states or len(set(states)) != len(states) or not set(states) <= valid_states:
        raise ValueError("Choose distinct confirmed Census jurisdictions")
    for state in states:
        if manifest["inputs"] != {
            settings.source_for(state): items[settings.source_for(state)].sha256
        }:
            raise ValueError("State and prepared parent OSM source disagree")
    inputs = {
        identifier: items[identifier].sha256
        for identifier in [prepared_id, "census_county_analysis", "census_states"]
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-state-extracts-") as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        for state in sorted(states):
            geometry = unary_union(counties[counties.STATEFP == codes[state]].geometry)
            extract_roads(
                payloads["roads_places.osm.pbf"],
                geometry,
                stage / "files" / f"{state}_roads_places.osm.pbf",
                settings.boundary_padding_degrees,
            )
        (stage / "states.json").write_text(
            json.dumps(
                {
                    "states": {state: codes[state] for state in sorted(states)},
                    "parent_sources": {
                        state: settings.source_for(state) for state in sorted(states)
                    },
                    "boundary_padding_degrees": settings.boundary_padding_degrees,
                },
                sort_keys=True,
            )
            + "\n"
        )
        measured = generation_manifest(
            stage,
            recipe_version(root, "android-extract-v1"),
            inputs,
            complete=True,
            epoch=epoch,
            intermediates=["states.json"],
        )
        stage.rename(output)
    return {**measured, "states": sorted(states)}


def prepared_state_source(
    root: Path,
    items: dict[str, Item],
    prepared: Path,
    prepared_id: str,
    state: str,
    osm_id: str,
    epoch: int,
) -> Path:
    from ck.fetch import digest

    manifest, payloads = verified_generated_files(items[prepared_id], prepared, items)
    if manifest["source_date_epoch"] != epoch or manifest["pipeline_version"] != recipe_version(
        root, "android-extract-v1"
    ):
        raise ValueError("Prepared state map source epoch or recipe changed")
    data_path = prepared / "states.json"
    binding = next(
        (entry for entry in manifest["intermediates"] if entry["path"] == "states.json"), None
    )
    if data_path.is_symlink() or binding is None or digest(data_path) != binding["sha256"]:
        raise ValueError("Prepared state mapping changed or is unbound")
    data = json.loads(data_path.read_text())
    if (
        state not in data["states"]
        or data["parent_sources"].get(state) != osm_id
        or policy(root).source_for(state) != osm_id
    ):
        raise ValueError("Prepared map state and parent source disagree")
    if set(payloads) != {f"{code}_roads_places.osm.pbf" for code in data["states"]}:
        raise ValueError("Prepared state mapping and source files disagree")
    return payloads[f"{state}_roads_places.osm.pbf"]


def collect_android_maps(
    root: Path, items: dict[str, Item], cache: Path, outputs: list[Path], output: Path, epoch: int
) -> dict:
    from ck.androidmaps import pipeline_version
    from ck.fetch import digest

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
        names = [
            entry["path"]
            for entry in metadata["files"]
            if re.fullmatch(r"[A-Z]{2}_roads_places\.obf", entry["path"])
        ]
        if len(names) != 1:
            raise ValueError("State map output needs exactly one OBF")
        state = names[0][:2]
        if state not in states or state in selected:
            raise ValueError("Unexpected or duplicate Android map jurisdiction")
        identifier = "android_map_" + state.lower()
        metadata, payloads = verified_generated_files(items[identifier], folder, items)
        if metadata["source_date_epoch"] != epoch or metadata[
            "pipeline_version"
        ] != pipeline_version(root):
            raise ValueError("State map epoch or recipe changed")
        if set(payloads) != {names[0], f"data/{state}_roads_places.osm.pbf", f"{state}_SOURCE.txt"}:
            raise ValueError("State map source database or attribution is missing")
        for name in ("inspection.txt", "filter.json"):
            path = folder / name
            binding = next(
                (entry for entry in metadata["intermediates"] if entry["path"] == name), None
            )
            if path.is_symlink() or binding is None or digest(path) != binding["sha256"]:
                raise ValueError("State map inspection or filter audit changed")
        if any(entry["size_bytes"] > 0xFFFFFFFF for entry in metadata["files"]):
            raise ValueError("State map payload exceeds FAT32 file limits; split the state")
        selected[state] = (folder, payloads, identifier)
    if selected.keys() != states.keys():
        raise ValueError(
            "Missing Android map jurisdictions: "
            + ", ".join(sorted(states.keys() - selected.keys()))
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-android-set-") as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        (stage / "states").mkdir()
        intermediates = ["jurisdictions.json"]
        for state, (folder, payloads, _) in sorted(selected.items()):
            for relative, source in payloads.items():
                target = stage / "files" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            for name in ("generation.json", "inspection.txt", "filter.json"):
                relative = f"states/{state}.{name}"
                shutil.copyfile(folder / name, stage / relative)
                intermediates.append(relative)
        (stage / "jurisdictions.json").write_text(json.dumps(states, sort_keys=True) + "\n")
        result = generation_manifest(
            stage,
            recipe_version(root, "android-set-v1"),
            {identifier: items[identifier].sha256 for _, _, identifier in selected.values()},
            complete=True,
            epoch=epoch,
            intermediates=intermediates,
        )
        stage.rename(output)
    return {**result, "jurisdictions": len(selected)}
