"""Extract a bounded PMTiles input with the pinned CLI in the atlas container.

The planet SHA-256 must be confirmed before this derivative can be complete.
Range downloads alone do not verify the publisher's whole-planet checksum.
"""

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-id", default="protomaps_planet")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new extraction output directory")
    catalog = {}
    # These two catalog families use JSON, a subset of YAML, so the build-tool
    # stage needs no second Python dependency environment.
    for family in ("geodata", "buildtools"):
        catalog.update(
            {
                item["id"]: item
                for item in json.loads((args.root / f"catalog/{family}.yaml").read_text())
            }
        )
    source = catalog[args.source_id]
    if not source["url"].startswith("https://") or "[[VERIFY" in source["url"]:
        raise ValueError("The planet URL must be confirmed")
    architecture = {"aarch64": "arm64", "x86_64": "x64"}[platform.machine()]
    tool_id = "pmtiles_" + architecture
    jobs = json.loads(args.jobs.read_text())
    region = args.jobs.parent / "region.geojson"
    if not jobs["pages"] or not region.is_file():
        raise ValueError("Prepare the county viewports before extracting")
    settings = (args.root / "pipelines/atlas/settings.yaml").read_text()
    maxzoom = next(
        int(line.split(":", 1)[1]) for line in settings.splitlines() if line.startswith("maxzoom:")
    )
    files = args.output / "files"
    files.mkdir(parents=True)
    target = files / f"{jobs['state']}.pmtiles"
    command = [
        "pmtiles",
        "extract",
        source["url"],
        str(target),
        "--region=" + str(region),
        "--maxzoom=" + str(maxzoom),
        "--download-threads=2",
    ]
    subprocess.run(command, check=True)
    subprocess.run(["pmtiles", "verify", str(target)], check=True)
    (args.output / "region.geojson").write_bytes(region.read_bytes())
    provenance = {
        "source": source,
        "region_sha256": sha(region),
        "maxzoom": maxzoom,
        "tool_id": tool_id,
        "tool_sha256": catalog[tool_id]["sha256"],
        "command": [
            part.replace(str(region), "region.geojson").replace(str(target), target.name)
            for part in command
        ],
    }
    (args.output / "source.json").write_bytes(encoded(provenance) + b"\n")
    metadata = {
        "pipeline_version": "pmtiles-extract-v1-" + sha(Path(__file__)),
        "inputs": {
            args.source_id: source["sha256"],
            tool_id: catalog[tool_id]["sha256"],
            **{key: value for key, value in jobs["inputs"].items() if key != "noto_sans"},
        },
        # This pipeline downloads ranges, so it deliberately cannot certify a
        # whole-source checksum. A separately verified source is still needed.
        "complete": False,
        "source_date_epoch": jobs["epoch"],
        "files": [
            {"path": target.name, "sha256": sha(target), "size_bytes": target.stat().st_size}
        ],
        "intermediates": [
            {
                "path": name,
                "sha256": sha(args.output / name),
                "size_bytes": (args.output / name).stat().st_size,
            }
            for name in ("source.json", "region.geojson")
        ],
    }
    payload = encoded(metadata)
    (args.output / "generation.json").write_bytes(payload + b"\n")
    print(
        json.dumps(
            {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": target.stat().st_size,
                "pipeline_version": metadata["pipeline_version"],
            }
        )
    )


if __name__ == "__main__":
    main()
