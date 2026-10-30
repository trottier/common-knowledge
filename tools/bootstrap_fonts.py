"""Fetch the JSON-compatible YAML font catalog before Python dependencies exist.

This tiny bootstrap uses only the standard library. Fonts stay outside git.
"""

import hashlib
import json
import sys
import tempfile
import urllib.request
from pathlib import Path


def bootstrap(catalog: Path, cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for item in json.loads(catalog.read_text(encoding="utf-8")):
        target = cache / item["sha256"]
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == item["sha256"]:
            continue
        if not item["url"].startswith("https://"):
            raise ValueError("Fonts require publisher HTTPS URLs")
        request = urllib.request.Request(
            item["url"], headers={"User-Agent": "CommonKnowledge-build"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            if not response.url.startswith("https://"):
                raise ValueError("Font download redirected outside HTTPS")
            data = response.read(item["size_bytes"] + 1)
        if len(data) != item["size_bytes"]:
            raise ValueError(f"Wrong font size: {item['id']}")
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Wrong font checksum: {item['id']}")
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.replace(target)


if __name__ == "__main__":
    bootstrap(Path(sys.argv[1]), Path(sys.argv[2]))
