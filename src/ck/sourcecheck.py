"""Cross-check a publisher's BLAKE3 input and report the catalog SHA-256."""

import hashlib
import re
from pathlib import Path

from ck.catalog import Item


def verify_publisher_input(item: Item, path: Path) -> dict:
    import blake3

    if not item.publisher_blake3 or not re.fullmatch(r"[0-9a-f]{64}", item.publisher_blake3):
        raise ValueError("A confirmed publisher BLAKE3 checksum is required")
    if (
        path.is_symlink()
        or not path.is_file()
        or not isinstance(item.size_bytes, int)
        or path.stat().st_size != item.size_bytes
    ):
        raise ValueError("Publisher input is missing, linked or the wrong size")
    sha, publisher, size = hashlib.sha256(), blake3.blake3(), 0
    with path.open("rb") as stream:
        if (item.url or "").endswith(".pmtiles") and stream.read(8) != b"PMTiles\x03":
            raise ValueError("Publisher PMTiles input has an unsupported header")
        stream.seek(0)
        while chunk := stream.read(16 * 1024 * 1024):
            sha.update(chunk)
            publisher.update(chunk)
            size += len(chunk)
    if size != item.size_bytes or publisher.hexdigest() != item.publisher_blake3:
        raise ValueError("Publisher BLAKE3 or input size does not match")
    if not item.sha256.startswith("[[VERIFY") and sha.hexdigest() != item.sha256:
        raise ValueError("Input differs from the existing catalog SHA-256")
    return {
        "id": item.id,
        "version": item.version,
        "url": item.url,
        "size_bytes": size,
        "sha256": sha.hexdigest(),
        "publisher_blake3": publisher.hexdigest(),
    }
