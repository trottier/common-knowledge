"""Measured generated outputs and their pinned input provenance."""

import hashlib
import json
from pathlib import Path

from ck.catalog import Item, safe_path
from ck.fetch import digest


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
    }
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    (output / "generation.json").write_bytes(encoded + b"\n")
    return {
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "size_bytes": sum(entry["size_bytes"] for entry in files),
        "pipeline_version": pipeline_version,
    }
