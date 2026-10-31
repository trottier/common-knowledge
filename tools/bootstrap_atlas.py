"""Install the publisher-checksummed native addon without package install hooks."""

import hashlib
import io
import json
import platform
import subprocess
import sys
import tarfile
from pathlib import Path
from urllib.request import urlopen

items = json.loads(Path(sys.argv[1]).read_text())
architecture = {"aarch64": "arm64", "x86_64": "x64"}[platform.machine()]
item = next(item for item in items if item["id"] == "maplibre_native_" + architecture)
with urlopen(item["url"], timeout=60) as response:
    payload = response.read(item["size_bytes"] + 1)
if len(payload) != item["size_bytes"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
    raise ValueError("Native renderer publisher checksum mismatch")
abi = subprocess.check_output(["node", "-p", "process.versions.modules"], text=True).strip()
with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
    member = archive.getmember(f"node-v{abi}/mbgl.node")
    destination = Path(sys.argv[2]) / "@maplibre/maplibre-gl-native/lib" / f"node-v{abi}"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "mbgl.node").write_bytes(archive.extractfile(member).read())

item = next(item for item in items if item["id"] == "pmtiles_" + architecture)
with urlopen(item["url"], timeout=60) as response:
    payload = response.read(item["size_bytes"] + 1)
if len(payload) != item["size_bytes"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
    raise ValueError("PMTiles publisher checksum mismatch")
with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
    destination = Path("/usr/local/bin/pmtiles")
    destination.write_bytes(archive.extractfile("pmtiles").read())
    destination.chmod(0o755)

fonts = json.loads(Path(sys.argv[3]).read_text())
item = next(item for item in fonts if item["id"] == "noto_sans")
with urlopen(item["url"], timeout=60) as response:
    payload = response.read(item["size_bytes"] + 1)
if len(payload) != item["size_bytes"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
    raise ValueError("Atlas test font checksum mismatch")
Path("/opt/ck-atlas-test-font.ttf").write_bytes(payload)
