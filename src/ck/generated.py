"""Measured generated outputs and their pinned input provenance."""

import hashlib
import json
from pathlib import Path

from ck.catalog import Item, safe_path
from ck.fetch import digest


def verified_generated_files(
    item: Item, output: Path, catalog: dict[str, Item], *, allow_incomplete: bool = False
) -> tuple[dict, dict[str, Path]]:
    metadata = json.loads((output / "generation.json").read_text())
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != item.sha256:
        raise ValueError(f"Generated manifest checksum mismatch: {item.id}")
    if metadata["pipeline_version"] != item.pipeline_version:
        raise ValueError(f"Generated pipeline version changed: {item.id}")
    if not allow_incomplete and metadata.get("complete") is not True:
        raise ValueError(f"Generated content is incomplete: {item.id}")
    if metadata.get("inputs") != {key: catalog[key].sha256 for key in item.inputs}:
        raise ValueError(f"Generated input pins changed: {item.id}")
    if sum(entry["size_bytes"] for entry in metadata["files"]) != item.size_bytes:
        raise ValueError(f"Generated size mismatch: {item.id}")
    result = {}
    for entry in metadata["files"]:
        relative = str(safe_path(entry["path"]))
        source = output / "files" / relative
        if relative in result or source.is_symlink() or not source.is_file():
            raise ValueError(f"Invalid generated file: {relative}")
        if not source.resolve().is_relative_to((output / "files").resolve()):
            raise ValueError("Generated input escapes its build directory")
        if source.stat().st_size != entry["size_bytes"] or digest(source) != entry["sha256"]:
            raise ValueError(f"Generated payload changed: {relative}")
        result[relative] = source
    return metadata, result


def cached_input(item: Item, cache: Path) -> Path:
    if not isinstance(item.size_bytes, int) or "[[VERIFY" in item.sha256:
        raise ValueError(f"Unpinned pipeline input: {item.id}")
    path = cache / item.sha256
    if path.is_symlink() or not path.is_file() or path.stat().st_size != item.size_bytes:
        raise ValueError(f"Missing or wrong-sized input: {item.id}; run ck fetch")
    if digest(path) != item.sha256:
        raise ValueError(f"Pipeline input checksum mismatch: {item.id}")
    return path


def generation_manifest(
    output: Path,
    pipeline_version: str,
    inputs: dict[str, str],
    *,
    complete: bool,
    epoch: int | None = None,
    intermediates: list[str] | None = None,
    tool_versions: str | None = None,
) -> dict:
    files = []
    for path in sorted((output / "files").rglob("*")):
        if path.is_symlink():
            raise ValueError("Generated outputs cannot contain symlinks")
        if path.is_file():
            relative = path.relative_to(output / "files").as_posix()
            safe_path(relative)
            files.append(
                {"path": relative, "size_bytes": path.stat().st_size, "sha256": digest(path)}
            )
    if not files:
        raise ValueError("Generated pipeline produced no files")
    metadata = {
        "pipeline_version": pipeline_version,
        "inputs": inputs,
        "complete": complete,
        "source_date_epoch": epoch,
        "files": files,
        "intermediates": [
            {
                "path": str(safe_path(name)),
                "sha256": digest(output / name),
                "size_bytes": (output / name).stat().st_size,
            }
            for name in intermediates or []
        ],
    }
    if tool_versions is not None:
        metadata["tool_versions"] = tool_versions
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    (output / "generation.json").write_bytes(encoded + b"\n")
    return {
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "size_bytes": sum(entry["size_bytes"] for entry in files),
        "pipeline_version": pipeline_version,
    }
