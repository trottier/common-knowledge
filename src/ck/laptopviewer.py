"""Package unchanged browser SDK releases with a local-file-only laptop viewer."""

import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pmtiles.reader import Reader

from ck.catalog import Item, safe_path
from ck.config import Identifier, Model, read_yaml
from ck.generated import cached_input, generation_manifest, verified_generated_files
from ck.laptopmap import settings_for


class Member(Model):
    member: str
    dest: str


class Archive(Model):
    id: Identifier
    files: list[Member]
    notices: list[str]


class SDK(Model):
    data_id: Identifier
    basemap_id: Identifier
    archives: list[Archive]
    extra_notices: list[Identifier]
    lock_ids: list[Identifier]


def copy_member(archive: tarfile.TarFile, name: str, target: Path) -> None:
    matches = [member for member in archive.getmembers() if member.name == name]
    if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 32_000_000:
        raise ValueError(f"Missing, duplicated or unsafe SDK archive member: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with archive.extractfile(matches[0]) as source, target.open("xb") as destination:
        shutil.copyfileobj(source, destination)


def region_bounds(payloads: dict[str, Path]) -> list[dict]:
    result = []
    for name, path in sorted(payloads.items()):
        if path.suffix != ".pmtiles" or len(Path(name).stem) != 2:
            raise ValueError("Viewer regions need state PMTiles inputs")
        with path.open("rb") as stream:

            def get_bytes(offset, length):
                stream.seek(offset)
                return stream.read(length)

            header = Reader(get_bytes).header()
        result.append(
            {
                "id": Path(name).stem,
                "bounds": [
                    [header["min_lon_e7"] / 1e7, header["min_lat_e7"] / 1e7],
                    [header["max_lon_e7"] / 1e7, header["max_lat_e7"] / 1e7],
                ],
            }
        )
    return result


def build_viewer(
    root: Path, items: dict[str, Item], cache: Path, generated: Path, output: Path, epoch: int
) -> dict:
    if output.exists():
        raise ValueError("Laptop viewer output must be new")
    policy = SDK.model_validate(read_yaml(root / "pipelines/laptopmap/sdk.yaml"))
    settings = settings_for(root)
    data, payloads = verified_generated_files(
        items[policy.data_id], generated / policy.data_id, items
    )
    basemap, regions = verified_generated_files(
        items[policy.basemap_id], generated / policy.basemap_id, items
    )
    if (
        data["source_date_epoch"] != epoch
        or basemap["source_date_epoch"] != epoch
        or set(payloads) != {settings.archive_filename}
        or data["inputs"] != {policy.basemap_id: items[policy.basemap_id].sha256}
    ):
        raise ValueError("Viewer requires this epoch's checked narrow dataset and basemap")
    identifiers = [archive.id for archive in policy.archives]
    identifiers += policy.extra_notices + policy.lock_ids
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate laptop SDK input")
    paths = {identifier: cached_input(items[identifier], cache) for identifier in identifiers}
    inputs = {identifier: items[identifier].sha256 for identifier in identifiers}
    inputs.update(
        {
            policy.data_id: items[policy.data_id].sha256,
            policy.basemap_id: items[policy.basemap_id].sha256,
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-laptop-viewer-") as temporary:
        stage = Path(temporary)
        files = stage / "files"
        licenses = files / "LICENSES"
        licenses.mkdir(parents=True)
        for archive in policy.archives:
            with tarfile.open(paths[archive.id], "r:gz") as source:
                for member in archive.files:
                    copy_member(source, member.member, files / str(safe_path(member.dest)))
                for number, name in enumerate(archive.notices, 1):
                    copy_member(source, name, licenses / f"{archive.id}_{number}.txt")
        for identifier in policy.extra_notices:
            shutil.copyfile(paths[identifier], licenses / f"{identifier}.txt")
        shutil.copyfile(root / "LICENSE", licenses / "Common-Knowledge-Apache-2.0.txt")
        shutil.copyfile(root / "LICENSE-CONTENT", licenses / "Original-content-CC0.txt")
        source = payloads[settings.archive_filename]
        shutil.copyfile(source, files / settings.archive_filename)
        context = {
            **settings.model_dump(),
            "source_date_epoch": epoch,
            "source_version": items[policy.basemap_id].version,
            "archive_size_bytes": source.stat().st_size,
            "regions": region_bounds(regions),
        }
        encoded = (
            json.dumps(context, ensure_ascii=True, sort_keys=True)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
        )
        templates = Environment(
            loader=FileSystemLoader(root / "pipelines/laptopmap"),
            autoescape=True,
            undefined=StrictUndefined,
        )
        (files / "1_OPEN_MAP.html").write_text(
            templates.get_template("index.html.j2").render(
                archive_filename=settings.archive_filename, settings_json=encoded
            )
        )
        shutil.copyfile(root / "pipelines/laptopmap/style.css", files / "style.css")
        subprocess.run(
            [
                "bun",
                "build",
                str(root / "pipelines/laptopmap/app.js"),
                "--format=iife",
                "--target=browser",
                "--outfile",
                str(files / "app.js"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        lines = [
            "Common Knowledge laptop map",
            "",
            f"Open 1_OPEN_MAP.html. Choose {settings.archive_filename} in the same folder.",
            "Use the atlas PDFs if this viewer does not open.",
            "",
            "© OpenStreetMap contributors; Protomaps. Open Database License 1.0.",
            "Source: https://www.openstreetmap.org/copyright",
            "",
            "The vector database was regenerated: roads, settlements and water only.",
            "POI and infrastructure layers were removed. No live closures or availability.",
            "Publisher browser JavaScript, CSS and notices are copied without modification.",
            "MapLibre uses the computer's installed fonts; some scripts may lack glyphs.",
            "This viewer does not verify the map's SHA-256. Use the drive manifest.",
            "",
        ]
        for identifier in sorted(inputs):
            item = items[identifier]
            lines += [
                f"{identifier}: {item.version}",
                f"SHA-256: {item.sha256}",
                f"License: {item.license}",
                f"Source: {item.url or item.pipeline_version}",
                f"License proof: {item.license_proof_url}",
                item.attribution,
                "",
            ]
        (files / "SOURCE.TXT").write_text("\n".join(lines))
        recipe = hashlib.sha256()
        recipe_paths = [
            root / "src/ck/laptopviewer.py",
            root / "src/ck/laptopmap.py",
            root / "src/ck/generated.py",
            root / "uv.lock",
            root / "Dockerfile.build",
        ]
        recipe_paths += [
            root / "pipelines/laptopmap" / name
            for name in (
                "sdk.yaml",
                "settings.yaml",
                "index.html.j2",
                "app.js",
                "model.js",
                "style.css",
            )
        ]
        for path in recipe_paths:
            recipe.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
        measured = generation_manifest(
            stage, "laptop-viewer-v1-" + recipe.hexdigest(), inputs, complete=True, epoch=epoch
        )
        stage.rename(output)
    return measured
