"""Preserve exact downloaded inputs for offline rebuilds without committing cargo."""

import gzip
import io
import json
import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path

from ck.catalog import Item
from ck.fetch import digest
from ck.generated import cached_input


def source_records(items: dict[str, Item], selected: list[str]) -> dict:
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("Select distinct catalog items")
    leaves, visiting = {}, set()

    def visit(identifier):
        if identifier not in items or identifier in visiting:
            raise ValueError(f"Missing or cyclic source dependency: {identifier}")
        item = items[identifier]
        if item.family != "generated":
            if not isinstance(item.size_bytes, int) or not re.fullmatch(
                r"[0-9a-f]{64}", item.sha256
            ):
                raise ValueError(f"Unpinned bundle input: {identifier}")
            leaves[identifier] = item.model_dump(mode="json")
            return
        visiting.add(identifier)
        for dependency in item.inputs:
            visit(dependency)
        visiting.remove(identifier)

    for identifier in selected:
        visit(identifier)
    return {
        "format": "ck-source-bundle-v1",
        "selected": sorted(selected),
        "sources": dict(sorted(leaves.items())),
    }


def pack_sources(
    items: dict[str, Item], selected: list[str], cache: Path, output: Path, epoch: int
) -> dict:
    if output.exists() or epoch < 0:
        raise ValueError("Source bundle needs a new output path and nonnegative epoch")
    record = source_records(items, selected)
    paths = {}
    for identifier in record["sources"]:
        item = items[identifier]
        path = cached_input(item, cache)
        if item.sha256 in paths and paths[item.sha256].stat().st_size != item.size_bytes:
            raise ValueError("Conflicting sizes for one source hash")
        paths[item.sha256] = path
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-source-pack-") as temporary:
        staged = Path(temporary) / "sources.tar.gz"
        with (
            staged.open("wb") as stream,
            gzip.GzipFile(
                filename="", fileobj=stream, mode="wb", mtime=0, compresslevel=9
            ) as zipped,
            tarfile.open(fileobj=zipped, mode="w|", format=tarfile.USTAR_FORMAT) as archive,
        ):

            def add(name, size, content):
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.mode = size, epoch, 0o644
                archive.addfile(info, content)

            raw = (
                json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
            ).encode()
            add("sources.json", len(raw), io.BytesIO(raw))
            for checksum, path in sorted(paths.items()):
                with path.open("rb") as source:
                    add("cache/" + checksum, path.stat().st_size, source)
        result = {
            "sha256": digest(staged),
            "size_bytes": staged.stat().st_size,
            "source_items": len(record["sources"]),
            "unique_payloads": len(paths),
            "source_date_epoch": epoch,
        }
        # This packaging step does not grant permission or review to any input.
        staged.rename(output)
    return result


def restore_sources(
    items: dict[str, Item], selected: list[str], bundle: Path, cache: Path, sha256: str
) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", sha256) or bundle.is_symlink() or digest(bundle) != sha256:
        raise ValueError("Source bundle checksum mismatch")
    expected = source_records(items, selected)
    payloads = {entry["sha256"]: entry["size_bytes"] for entry in expected["sources"].values()}
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache, prefix=".ck-source-restore-") as temporary:
        staging = Path(temporary)
        seen = set()
        with tarfile.open(bundle, "r|gz") as archive:
            for number, member in enumerate(archive):
                if not member.isfile() or member.name in seen:
                    raise ValueError("Bundle contains duplicate or nonregular members")
                seen.add(member.name)
                content = archive.extractfile(member)
                if number == 0:
                    raw = (
                        json.dumps(
                            expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                        )
                        + "\n"
                    ).encode()
                    if (
                        member.name != "sources.json"
                        or member.size != len(raw)
                        or content.read() != raw
                    ):
                        raise ValueError("Source bundle catalog records changed")
                    continue
                checksum = member.name.removeprefix("cache/")
                if (
                    member.name != "cache/" + checksum
                    or checksum not in payloads
                    or member.size != payloads[checksum]
                ):
                    raise ValueError("Unexpected source bundle member")
                target = staging / checksum
                with target.open("xb") as stream:
                    shutil.copyfileobj(content, stream)
                if digest(target) != checksum:
                    raise ValueError("Source bundle payload checksum mismatch")
        if seen != {"sources.json", *("cache/" + key for key in payloads)}:
            raise ValueError("Source bundle is incomplete")
        for checksum, size in payloads.items():
            target = cache / checksum
            if target.exists() or target.is_symlink():
                if (
                    target.is_symlink()
                    or not target.is_file()
                    or target.stat().st_size != size
                    or digest(target) != checksum
                ):
                    raise ValueError("Existing cache entry is invalid; refusing to replace it")
        for checksum in payloads:
            target = cache / checksum
            if not target.exists():
                # Linking publishes a complete verified file and never overwrites.
                os.link(staging / checksum, target)
    return {
        "sha256": sha256,
        "source_items": len(expected["sources"]),
        "unique_payloads": len(payloads),
    }
