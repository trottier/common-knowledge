"""Regenerate OsmAnd maps from a narrow roads-and-public-places OSM input."""

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pydantic import Field

from ck.catalog import Item, safe_path
from ck.config import Identifier, Model, Text, read_yaml
from ck.directory import AMENITIES, excluded, osm_category
from ck.generated import cached_input, generation_manifest


class Settings(Model):
    place_values: list[Text]
    sources: dict[Text, Identifier]
    supplements: dict[Text, list[Identifier]]
    road_values: list[Text]
    road_node_values: list[Text]
    tags: list[Text]
    max_heap_mib: int = Field(ge=256)


def pipeline_version(root: Path) -> str:
    recipe = hashlib.sha256()
    for relative in (
        "src/ck/androidmaps.py",
        "src/ck/mapextract.py",
        "src/ck/directory.py",
        "src/ck/generated.py",
        "pipelines/androidmaps/settings.yaml",
        "pipelines/androidmaps/national.yaml",
        "Dockerfile.build",
        "uv.lock",
        "config/debian.sources",
    ):
        recipe.update(relative.encode() + b"\0" + (root / relative).read_bytes())
    return "androidmaps-v1-" + recipe.hexdigest()


def filtered_tags(kind: str, tags: dict[str, str], settings: Settings) -> dict[str, str]:
    if excluded(tags):
        return {}
    road = kind == "way" and tags.get("highway") in settings.road_values
    road_node = kind == "node" and tags.get("highway") in settings.road_node_values
    restriction = kind == "relation" and tags.get("type") == "restriction"
    place = tags.get("place") in settings.place_values
    public = all(tags.get(key) not in {"no", "private"} for key in ("access", "public"))
    civic = (
        tags.get("amenity") in {"school", "library"}
        and public
        and (
            tags.get("operator:type") in {"public", "government"}
            or tags.get("ownership") == "public"
        )
    )
    poi = civic or osm_category(tags)
    if tags.get("office") == "government" and not poi:
        return {}
    if not (road or road_node or place or poi or restriction):
        return {}
    result = {key: value for key, value in tags.items() if key in settings.tags}
    if not poi:
        result = {
            key: value
            for key, value in result.items()
            if key not in {"amenity", "healthcare", "healthcare:speciality"}
            and not key.startswith("addr:")
        }
    result.update(
        {
            key: value
            for key, value in tags.items()
            if key.endswith(":conditional") and key.removesuffix(":conditional") in settings.tags
        }
    )
    # Names in other languages are source data, not generated translations.
    result.update({key: value for key, value in tags.items() if key.startswith("name:")})
    return dict(sorted(result.items()))


def filter_roads(
    source: Path, output: Path, settings: Settings, supplements: tuple[Path, ...] = ()
) -> dict:
    import osmium

    counts = Counter()
    with tempfile.TemporaryDirectory(prefix=".ck-osm-filter-", dir=output.parent) as temporary:
        if supplements:
            merged = Path(temporary) / "merged.osm.pbf"
            subprocess.run(
                [
                    "osmium",
                    "apply-changes",
                    "-F",
                    "pbf",
                    "--change-file-format",
                    "osm",
                    str(source),
                    *map(str, supplements),
                    "--output",
                    str(merged),
                ],
                check=True,
            )
            source = merged
        selected = Path(temporary) / "selected.osm.pbf"
        subprocess.run(
            [
                "osmium",
                "tags-filter",
                "-F",
                "pbf",
                str(source),
                "nwr/highway",
                "nwr/place=" + ",".join(settings.place_values),
                "nwr/amenity=" + ",".join(sorted({*AMENITIES, "school", "library"})),
                "nwr/healthcare=clinic",
                "r/type=restriction",
                "--remove-tags",
                "--output",
                str(selected),
            ],
            check=True,
        )
        with osmium.SimpleWriter(str(output)) as writer:

            class Cleaner(osmium.SimpleHandler):
                def write(self, kind, obj):
                    raw = dict(obj.tags)
                    tags = filtered_tags(kind, raw, settings)
                    if tags:
                        counts[kind + "_tagged"] += 1
                    if excluded(raw):
                        counts["excluded_tags_removed"] += 1
                    # Keep untagged reference geometry so roads and areas stay
                    # connected. The generated PBF does not keep source users.
                    getattr(writer, "add_" + kind)(
                        obj.replace(
                            tags=tags,
                            uid=0,
                            user="",
                            changeset=0,
                        )
                    )

                def node(self, node):
                    self.write("node", node)

                def way(self, way):
                    self.write("way", way)

                def relation(self, relation):
                    self.write("relation", relation)

            Cleaner().apply_file(str(selected))
    check = subprocess.run(
        ["osmium", "check-refs", "--check-relations", str(output)],
        capture_output=True,
        text=True,
    )
    if check.returncode:
        raise ValueError("Filtered map has incomplete references: " + check.stderr + check.stdout)
    return dict(sorted(counts.items()))


def unpack_tool(source: Path, output: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        seen = set()
        for member in archive.infolist():
            name = member.filename
            while name.startswith("./"):
                name = name[2:]
            if not name or member.is_dir():
                continue
            relative = safe_path(name)
            if stat.S_ISLNK(member.external_attr >> 16) or relative in seen:
                raise ValueError("Invalid map creator archive entry")
            seen.add(relative)
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))


def build_android_map(
    root: Path,
    catalog: dict[str, Item],
    cache: Path,
    output: Path,
    state: str,
    osm_id: str,
    epoch: int,
    prepared: Path | None = None,
    prepared_id: str | None = None,
) -> dict:
    if output.exists():
        raise ValueError("Android map output must be new")
    if len(state) != 2 or not state.isascii() or not state.isalpha():
        raise ValueError("State must be a two-letter code")
    settings_path = root / "pipelines/androidmaps/settings.yaml"
    settings = Settings.model_validate(read_yaml(settings_path))
    if bool(prepared) != bool(prepared_id):
        raise ValueError("Prepared state source needs both a directory and catalog ID")
    state = state.upper()
    if prepared:
        from ck.mapextract import policy, prepared_state_source

        osm = prepared_state_source(root, catalog, prepared, prepared_id, state, osm_id, epoch)
        supplement_ids = []
        heap_mib = policy(root).max_heap_mib
    else:
        if settings.sources.get(state) != osm_id:
            raise ValueError("State and confirmed OSM source mapping disagree")
        osm = cached_input(catalog[osm_id], cache)
        supplement_ids = settings.supplements.get(state, [])
        heap_mib = settings.max_heap_mib
    tool = cached_input(catalog["osmand_creator"], cache)
    supplements = tuple(cached_input(catalog[key], cache) for key in supplement_ids)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-android-map-") as temporary:
        stage = Path(temporary)
        work = stage / "work"
        work.mkdir()
        source = work / f"{state.upper()}_roads_places.osm.pbf"
        counts = filter_roads(osm, source, settings, supplements)
        if not counts.get("way_tagged"):
            raise ValueError("Road filter produced no tagged ways")
        os.utime(source, (epoch, epoch))
        creator = stage / "creator"
        unpack_tool(tool, creator)
        java = [
            "java",
            "-Djava.awt.headless=true",
            "-Duser.timezone=UTC",
            "-Duser.language=en",
            "-Duser.country=US",
            f"-Xmx{heap_mib}m",
            "-cp",
            str(creator / "OsmAndMapCreator.jar") + ":" + str(creator / "lib/*"),
            "net.osmand.MainUtilities",
        ]
        # The publisher derives the OBF creation date from the input file mtime.
        # Call the original JARs directly; no publisher files are patched.
        with (stage / "creator.log").open("w") as log:
            subprocess.run(
                [*java, "generate-obf", str(source.resolve()), "--no-address", "--no-transport"],
                cwd=work,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        maps = list(work.glob("*.obf"))
        if len(maps) != 1:
            raise ValueError("Map creator did not produce exactly one OBF")
        inspection = subprocess.run(
            [*java, "inspector", str(maps[0].resolve())], check=True, capture_output=True, text=True
        )
        # stderr has wall-clock log dates and timing measurements. Keep it for
        # diagnosis without binding those transient logs into the output pin.
        (stage / "inspection.txt").write_text(inspection.stdout)
        (stage / "inspection-stderr.log").write_text(inspection.stderr)
        if not all(
            section in inspection.stdout for section in ("Map data", "Routing data", "POI data")
        ):
            raise ValueError("OBF inspection did not find map, routing and POI indexes")
        date = re.search(r"edition = (.+)", inspection.stdout)
        if (
            not date
            or datetime.strptime(date[1], "%a %b %d %H:%M:%S UTC %Y")
            .replace(tzinfo=UTC)
            .timestamp()
            != epoch
        ):
            raise ValueError("OBF creation date is not the fixed build epoch")
        files = stage / "files"
        files.mkdir()
        maps[0].rename(files / f"{state.upper()}_roads_places.obf")
        data = files / "data"
        data.mkdir()
        source.rename(data / source.name)
        (files / f"{state.upper()}_SOURCE.txt").write_text(
            "Map data: © OpenStreetMap contributors, under the Open Database License.\n"
            "https://www.openstreetmap.org/copyright\n"
            "https://opendatacommons.org/licenses/odbl/1-0/\n"
            "The data/ folder contains the modified source database for this map.\n"
            f"Source: {catalog[osm_id].url}\nVersion: {catalog[osm_id].version}\n"
            f"Source SHA-256: {catalog[osm_id].sha256}\n"
            + "".join(
                f"Supplement: {catalog[key].url}\nVersion: {catalog[key].version}\n"
                f"SHA-256: {catalog[key].sha256}\n"
                for key in supplement_ids
            )
            + (
                f"Prepared state source: {prepared_id}\n"
                f"Prepared manifest SHA-256: {catalog[prepared_id].sha256}\n"
                "State extraction boundaries: U.S. Census Bureau TIGER/Line; "
                "statistical boundaries, not legal land descriptions.\n"
                if prepared_id
                else ""
            )
        )
        (stage / "filter.json").write_text(json.dumps(counts, indent=2) + "\n")
        versions = subprocess.run(["java", "-version"], check=True, capture_output=True, text=True)
        measurements = generation_manifest(
            stage,
            pipeline_version(root),
            {
                key: catalog[key].sha256
                for key in (
                    osm_id,
                    "osmand_creator",
                    *supplement_ids,
                    *([prepared_id] if prepared_id else []),
                )
            },
            complete=True,
            epoch=epoch,
            intermediates=["filter.json", "inspection.txt"],
            tool_versions=versions.stdout
            + versions.stderr
            + "\nOsmAnd creator: "
            + catalog["osmand_creator"].version,
        )
        # Keep the small audit files; cached source/tool archives remain outside
        # the placed payload. Temporary databases and extracted JARs are removed.
        shutil.rmtree(work)
        shutil.rmtree(creator)
        stage.rename(output)
    return {**measurements, "filter": counts}
