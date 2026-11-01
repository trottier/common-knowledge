"""Install the catalog-pinned, static ZIM checker for the build architecture."""

import hashlib
import io
import json
import platform
import subprocess
import sys
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath


def checker(archive: bytes) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as source:
        matches = [
            member
            for member in source.getmembers()
            if PurePosixPath(member.name).name == "zimcheck"
        ]
        if len(matches) != 1 or not matches[0].isfile():
            raise ValueError("ZIM tools archive must contain one regular zimcheck file")
        member = matches[0]
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe ZIM checker archive path")
        return source.extractfile(member).read()


def main():
    catalog_path, output = map(Path, sys.argv[1:])
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}[platform.machine()]
    item = next(
        item
        for item in json.loads(catalog_path.read_text())
        if item["id"] == f"zim_tools_{architecture}"
    )
    with urllib.request.urlopen(
        urllib.request.Request(item["url"], method="HEAD"), timeout=60
    ) as response:
        if not response.url.startswith("https://"):
            raise ValueError("ZIM tools redirect outside HTTPS")
        etag = response.headers["ETag"]

    def part(start):
        end = min(start + 4 * 1024 * 1024, item["size_bytes"]) - 1
        request = urllib.request.Request(
            item["url"],
            headers={
                "Range": f"bytes={start}-{end}",
                "If-Match": etag,
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            if (
                not response.url.startswith("https://")
                or response.status != 206
                or response.headers.get("ETag") != etag
                or response.headers.get("Content-Range")
                != f"bytes {start}-{end}/{item['size_bytes']}"
            ):
                raise ValueError("Invalid ZIM tools publisher byte range")
            data = response.read(end - start + 2)
        if len(data) != end - start + 1:
            raise ValueError("Incomplete ZIM tools publisher byte range")
        return data

    with ThreadPoolExecutor(max_workers=8) as pool:
        raw = b"".join(pool.map(part, range(0, item["size_bytes"], 4 * 1024 * 1024)))
    if len(raw) != item["size_bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError("ZIM tools download does not match the catalog")
    output.write_bytes(checker(raw))
    output.chmod(0o755)
    subprocess.run([str(output), "--version"], check=True)


if __name__ == "__main__":
    main()
