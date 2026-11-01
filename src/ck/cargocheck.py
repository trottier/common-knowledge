"""Audit a locked Rust source set without granting application release approval."""

import hashlib
import stat
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

from ck.catalog import Item, safe_path
from ck.generated import cached_input

CRATES_IO = "registry+https://github.com/rust-lang/crates.io-index"


def archive_text(archive: tarfile.TarFile, relative: str) -> bytes:
    """Read one regular file beneath an archive's top-level directory."""
    safe_path(relative)
    matches = []
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.parts[1:] != PurePosixPath(relative).parts:
            continue
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe source archive path")
        matches.append(member)
    if len(matches) != 1 or not matches[0].isfile():
        raise ValueError(f"Expected one regular source file: {relative}")
    with archive.extractfile(matches[0]) as stream:
        return stream.read()


def package_manifests(path: Path):
    """Inspect local Rust manifests, including ZIPs in mixed-language source graphs."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                name = PurePosixPath(member.filename)
                if member.is_dir() or name.name != "Cargo.toml":
                    continue
                if (
                    name.is_absolute()
                    or ".." in name.parts
                    or stat.S_ISLNK(member.external_attr >> 16)
                ):
                    raise ValueError("Unsafe local Cargo manifest")
                yield (
                    member.filename,
                    tomllib.loads(archive.read(member).decode("utf-8")).get("package", {}),
                )
    else:
        with tarfile.open(path) as archive:
            for member in archive.getmembers():
                name = PurePosixPath(member.name)
                if name.name != "Cargo.toml":
                    continue
                if name.is_absolute() or ".." in name.parts or not member.isfile():
                    raise ValueError("Unsafe local Cargo manifest")
                with archive.extractfile(member) as stream:
                    yield (
                        member.name,
                        tomllib.loads(stream.read().decode("utf-8")).get("package", {}),
                    )


def audit_cargo_sources(
    items: dict[str, Item], source_id: str, lock_path: str, cache: Path
) -> dict:
    """Bind every locked package to cataloged, checksum-verified source bytes."""
    sources = {}
    active = set()

    def visit(identifier):
        if identifier in active:
            raise ValueError("Corresponding source dependency cycle")
        if identifier in sources:
            return
        if identifier not in items:
            raise ValueError(f"Missing corresponding source: {identifier}")
        active.add(identifier)
        item = items[identifier]
        for dependency in item.inputs:
            visit(dependency)
        active.remove(identifier)
        sources[identifier] = item

    visit(source_id)
    with tarfile.open(cached_input(sources[source_id], cache)) as archive:
        lock_bytes = archive_text(archive, lock_path)
    lock = tomllib.loads(lock_bytes.decode("utf-8"))
    packages = lock.get("package", [])
    if not packages:
        raise ValueError("Cargo lockfile contains no packages")
    identities = [(package["name"], package["version"]) for package in packages]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate locked package identity")
    registry_hashes = set()
    for package in packages:
        if "source" in package:
            if package["source"] != CRATES_IO or "checksum" not in package:
                raise ValueError("Unsupported or unchecked Cargo package source")
            registry_hashes.add(package["checksum"])

    # The remaining archives contain the wrapper and upstream path dependencies.
    local = {}
    for identifier, item in sources.items():
        if item.sha256 in registry_hashes:
            continue
        for path, package in package_manifests(cached_input(item, cache)):
            name, version = package.get("name"), package.get("version")
            if isinstance(name, str) and isinstance(version, str):
                local.setdefault((name, version), []).append(
                    {"source_id": identifier, "path": path}
                )

    registry_records, local_records = [], []
    for package in packages:
        name, version = package["name"], package["version"]
        if "source" not in package:
            matches = local.get((name, version), [])
            if len(matches) != 1:
                raise ValueError(f"Missing or ambiguous local package source: {name} {version}")
            local_records.append({"name": name, "version": version, **matches[0]})
            continue
        candidates = [item for item in sources.values() if item.sha256 == package["checksum"]]
        if len(candidates) != 1:
            raise ValueError(f"Missing or ambiguous registry source: {name} {version}")
        item = candidates[0]
        if item.version != version:
            raise ValueError(f"Registry source catalog version mismatch: {name}")
        with tarfile.open(cached_input(item, cache)) as archive:
            manifest = tomllib.loads(archive_text(archive, "Cargo.toml").decode("utf-8"))["package"]
        if manifest.get("name") != name or manifest.get("version") != version:
            raise ValueError(f"Registry source package identity mismatch: {name} {version}")
        if manifest.get("license") != item.license:
            raise ValueError(f"Registry source license metadata mismatch: {name} {version}")
        registry_records.append(
            {"name": name, "version": version, "source_id": item.id, "sha256": item.sha256}
        )
    return {
        "source_id": source_id,
        "lock_path": lock_path,
        "lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "registry_packages": sorted(
            registry_records, key=lambda item: (item["name"], item["version"])
        ),
        "local_packages": sorted(local_records, key=lambda item: (item["name"], item["version"])),
        "complete_cargo_lock_sources": True,
        "complete_application_source_closure": False,
        "human_license_or_pin_approval": False,
    }
