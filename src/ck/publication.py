"""Build reviewable release assets and a static, tracker-free verification site."""

import json
import re
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ck.catalog import load_catalog, safe_path
from ck.config import load_config
from ck.fetch import digest
from ck.generated import cached_input
from ck.review import require_release_ready

GITHUB_ASSET_LIMIT = 2_000_000_000


def release_sources(root: Path, cache: Path) -> None:
    """Fetch corresponding sources only after all release review gates pass."""
    from ck.fetch import fetch

    require_release_ready(root)
    items = load_catalog(root, load_config(root))
    for app in items.values():
        if ships_gpl(app):
            for source in corresponding_sources(items, app):
                fetch(source, cache)


def corresponding_sources(items, app):
    seen = set()

    def visit(identifier, ancestors):
        if identifier in ancestors:
            raise ValueError("Corresponding source dependency cycle")
        if identifier in seen:
            return
        if identifier not in items:
            raise ValueError("Missing corresponding source dependency")
        seen.add(identifier)
        source = items[identifier]
        yield source
        for dependency in source.inputs:
            yield from visit(dependency, ancestors | {identifier})

    yield from visit(app.source_id, set())


def source_archive_extension(path: Path) -> str:
    # GitHub/GitLab archive APIs often end in a commit or query, not an extension.
    with path.open("rb") as stream:
        header = stream.read(6)
    if zipfile.is_zipfile(path):
        extension = ".zip"
    elif header.startswith(b"\x1f\x8b"):
        extension = ".tar.gz"
    elif header == b"\xfd7zXZ\x00":
        extension = ".tar.xz"
    else:
        raise ValueError("Unsupported corresponding source archive format")
    check_source_archive(path, extension)
    return extension


def ships_gpl(item) -> bool:
    return (
        item.family in {"apk", "binaries"}
        and item.placement != "hub_only"
        and any(part.startswith("GPL-") for part in item.license.split(" AND "))
    )


def check_source_archive(path: Path, extension: str) -> None:
    # Inspect without extracting: HTML error responses must never become sources.
    if extension == ".zip":
        with zipfile.ZipFile(path) as archive:
            if not archive.namelist() or archive.testzip() is not None:
                raise ValueError("Corresponding source ZIP is empty or corrupt")
    elif extension in {".tar.gz", ".tar.xz"}:
        with tarfile.open(path, "r:*") as archive:
            if not any(member.isfile() for member in archive):
                raise ValueError("Corresponding source TAR contains no files")
    else:
        raise ValueError("Unsupported corresponding source archive format")


def write_catalog_lock(root: Path, target: Path, epoch: int) -> None:
    config = load_config(root)
    items = load_catalog(root, config)
    data = {
        "version": config.build.version,
        "source_date_epoch": epoch,
        "config_sha256": {
            str(path.relative_to(root)): digest(path)
            for path in sorted((root / "config").glob("*.yaml"))
        },
        "items": [items[key].model_dump(mode="json") for key in sorted(items)],
    }
    target.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")


def prepare_release(
    root: Path, core: Path, images: Path, cache: Path, output: Path, epoch: int, commit: str
) -> dict:
    require_release_ready(root)
    config = load_config(root)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A release needs the exact source commit")
    if config.build.source_date_epoch != epoch:
        raise ValueError("Release epoch must match confirmed configuration")
    if output.exists():
        raise ValueError("Release output must be new")
    from ck.core import verify_core

    verify_core(root, core, epoch, "dev")
    metadata = json.loads((core / "core-manifest.json").read_text())
    if set(metadata["languages"]) != {language.code for language in config.languages}:
        raise ValueError("Release PDFs must include all fifteen editions")
    built = json.loads((images.parent / "build-manifest.json").read_text())
    if (
        built.get("profile") != "dev"
        or built.get("commit") != commit
        or built.get("source_date_epoch") != epoch
        or built.get("version") != config.build.version
        or built.get("variants") != list(range(1, 9))
        or built.get("core_manifest_sha256") != digest(core / "core-manifest.json")
        or [entry.get("variant") for entry in built.get("images", [])] != list(range(1, 9))
    ):
        raise ValueError("Release images do not match this core, epoch, version and source commit")
    items = load_catalog(root, config)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-release-") as temporary:
        stage = Path(temporary)
        kinds = {}

        def copy(source: Path, name: str, kind: str) -> None:
            if len(safe_path(name).parts) != 1 or (stage / name).exists():
                raise ValueError("Release asset names must be unique plain filenames")
            if source.is_symlink() or not source.is_file():
                raise ValueError("Release inputs must be regular files")
            if source.stat().st_size >= GITHUB_ASSET_LIMIT:
                raise ValueError(f"GitHub release asset must be under 2 GB: {name}")
            shutil.copyfile(source, stage / name)
            kinds[name] = kind

        for source in sorted(core.glob("*/*.pdf")):
            copy(source, source.parent.name + "-" + source.name, "pdf")
        if not kinds:
            raise ValueError("No release PDFs were built")
        for number in range(1, 9):
            name = f"common-knowledge-{config.build.version}-variant-{number}-dev.img.zst"
            source = images / name
            expected = (images / (name + ".sha256")).read_text().split()[0]
            if digest(source) != expected:
                raise ValueError("Compressed development image differs from its hash")
            record = built["images"][number - 1]
            if record["compressed"] != name or record["compressed_sha256"] != expected:
                raise ValueError("Development image differs from its build manifest")
            manifest_name = name.removesuffix(".img.zst") + ".MANIFEST.SHA256"
            for filename, checksum in (
                (name, record["compressed_sha256"]),
                (name.removesuffix(".zst"), record["sha256"]),
                (manifest_name, record["manifest_sha256"]),
            ):
                if (images / (filename + ".sha256")).read_text() != f"{checksum}  {filename}\n":
                    raise ValueError("Image verification sidecar differs from its build manifest")
            if digest(images / manifest_name) != record["manifest_sha256"]:
                raise ValueError("File manifest differs from its build manifest")
            copy(source, name, "dev-image")
            for suffix in (
                ".img.sha256",
                ".img.zst.sha256",
                ".MANIFEST.SHA256",
                ".MANIFEST.SHA256.sha256",
            ):
                sidecar = images / name.removesuffix(".img.zst")
                sidecar = sidecar.with_name(sidecar.name + suffix)
                copy(sidecar, sidecar.name, "verification")
        for app in sorted(items.values(), key=lambda item: item.id):
            if not ships_gpl(app):
                continue
            if not app.source_id:
                raise ValueError(f"Missing corresponding source: {app.id}")
            for source in corresponding_sources(items, app):
                path = cached_input(source, cache)
                extension = source_archive_extension(path)
                name = "source-" + app.id
                if source.id != app.source_id:
                    name += "-" + source.id
                copy(path, name + extension, "gpl-source")
        if "wikem_en_nopic" in items and items["wikem_en_nopic"].family == "generated":
            from ck.sourcebundle import pack_sources

            name = "source-data-wikem.tar.gz"
            bundle = pack_sources(items, ["wikem_en_nopic"], cache, stage / name, epoch)
            if bundle["size_bytes"] >= GITHUB_ASSET_LIMIT:
                raise ValueError(f"GitHub release asset must be under 2 GB: {name}")
            kinds[name] = "source-data"
        write_catalog_lock(root, stage / "catalog.lock.json", epoch)
        kinds["catalog.lock.json"] = "catalog"
        files = [
            {
                "name": name,
                "kind": kinds[name],
                "size_bytes": (stage / name).stat().st_size,
                "sha256": digest(stage / name),
            }
            for name in sorted(kinds)
        ]
        manifest = {
            "version": config.build.version,
            "profile": "dev",
            "commit": commit,
            "source_date_epoch": epoch,
            "files": files,
        }
        (stage / "release-manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n"
        )
        (stage / "SHA256SUMS").write_text(
            "".join(
                f"{digest(path)}  {path.name}\n"
                for path in sorted(stage.iterdir())
                if path.is_file()
            )
        )
        stage.rename(output)
    return manifest


def build_site(
    root: Path,
    manifests: list[Path],
    output: Path,
    repository: str,
    full_manifests: list[Path] | None = None,
) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GitHub repository")
    if output.exists():
        raise ValueError("Site output must be new")
    config = load_config(root)
    catalog = load_catalog(root, config)
    releases = []
    for path in sorted(manifests):
        release = json.loads(path.read_text())
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", release["version"]):
            raise ValueError("Invalid release version")
        if not re.fullmatch(r"[0-9a-f]{40}", release["commit"]):
            raise ValueError("Invalid release commit")
        for file in release["files"]:
            if (
                len(safe_path(file["name"]).parts) != 1
                or not re.fullmatch(r"[0-9a-f]{64}", file["sha256"])
                or type(file["size_bytes"]) is not int
                or file["size_bytes"] <= 0
            ):
                raise ValueError("Invalid published file metadata")
            from urllib.parse import quote

            file["url"] = (
                f"https://github.com/{repository}/releases/download/v{release['version']}/"
                + quote(file["name"])
            )
        releases.append(release)
    full_builds = []
    for path in sorted(full_manifests or []):
        build = json.loads(path.read_text())
        if (
            build.get("profile") != "full"
            or build.get("reproduced") is not True
            or build.get("variants") != list(range(1, 9))
            or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", build.get("version", ""))
            or not re.fullmatch(r"[0-9a-f]{40}", build.get("commit", ""))
            or len(build.get("images", [])) != 8
            or [entry.get("variant") for entry in build["images"]] != list(range(1, 9))
        ):
            raise ValueError("Full-image publication needs all eight reproducible variants")
        for image in build["images"]:
            for name in ("image", "compressed", "manifest"):
                if len(safe_path(image[name]).parts) != 1:
                    raise ValueError("Invalid full-image filename")
            for checksum in ("sha256", "compressed_sha256", "manifest_sha256"):
                if not re.fullmatch(r"[0-9a-f]{64}", image[checksum]):
                    raise ValueError("Invalid full-image checksum")
            for size in ("image_size_bytes", "compressed_size_bytes"):
                if type(image[size]) is not int or image[size] <= 0:
                    raise ValueError("Invalid full-image size")
        full_builds.append(build)
    items = [
        {
            **item.model_dump(),
            "proof": item.license_proof_url
            if item.license_proof_url.startswith("https://")
            else None,
        }
        for item in sorted(catalog.values(), key=lambda item: item.id)
    ]
    from ck.cardlinks import PAGES

    environment = Environment(
        loader=FileSystemLoader(root / "templates"), autoescape=True, undefined=StrictUndefined
    )
    document = environment.get_template("verification.html.j2").render(
        releases=releases,
        full_builds=full_builds,
        items=items,
        draft=not releases and not full_builds,
        card_pages=PAGES,
    )
    output.mkdir(parents=True)
    (output / PAGES[2]).write_text(document)
    videos = [
        item
        for item in catalog.values()
        if item.family == "video"
        and item.url
        and item.url.startswith("https://")
        and isinstance(item.size_bytes, int)
        and "[[VERIFY" not in item.sha256
        and not item.requires_legal
        and "[[VERIFY" not in item.license
    ]
    agencies = catalog.get("state_emergency_agencies")
    agency_url = (
        agencies.url if agencies and agencies.url and agencies.url.startswith("https://") else None
    )
    for number, kind in enumerate(("videos", "agencies")):
        (output / PAGES[number]).write_text(
            environment.get_template("card-page.html.j2").render(
                kind=kind,
                card_pages=PAGES,
                videos=videos,
                agency_url=agency_url,
                draft=not releases and not full_builds,
            )
        )
    (output / ".nojekyll").write_text("")
