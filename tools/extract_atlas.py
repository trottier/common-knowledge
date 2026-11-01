"""Extract bounded PMTiles inputs, verifying one local planet once per batch.

Remote range extracts remain incomplete. Complete derivatives require the exact
checksum-verified whole input; no network is needed when --source-file is used.
"""

import argparse
import hashlib
import json
import os
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
    parser.add_argument("--jobs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-id", default="protomaps_planet")
    parser.add_argument("--source-file", type=Path)
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
    if args.source_file is not None and (
        args.source_file.is_symlink()
        or not args.source_file.is_file()
        or args.source_file.stat().st_size != source["size_bytes"]
        or sha(args.source_file) != source["sha256"]
    ):
        raise ValueError("Local planet differs from its pinned whole-file size or SHA-256")
    if args.source_file is not None:
        with args.source_file.open("rb") as stream:
            if stream.read(8) != b"PMTiles\x03":
                raise ValueError("Local planet has an unsupported PMTiles header")
    states = [json.loads(path.read_text())["state"] for path in args.jobs]
    if len(states) != len(set(states)) or any(
        not isinstance(state, str) or len(state) != 2 or not state.isascii() or not state.isalpha()
        for state in states
    ):
        raise ValueError("Choose distinct two-letter state extraction jobs")
    # Validate the whole source once, then extract states without rehashing a
    # 139 GB planet for every county or state.
    for jobs_path, state in zip(args.jobs, states, strict=True):
        extract(
            args,
            catalog,
            source,
            jobs_path,
            args.output / state if len(states) > 1 else args.output,
        )
    if len(states) > 1:
        print(json.dumps(batch_manifest(args.output, states)))


def batch_manifest(output: Path, states: list[str]) -> dict:
    """Bind every extracted state as one catalog input without duplicating bytes."""
    inputs, files, intermediates, epochs = {}, [], [], set()
    complete = True
    payloads = []
    for state in sorted(states):
        folder = output / state
        metadata = json.loads((folder / "generation.json").read_text())
        epochs.add(metadata["source_date_epoch"])
        complete = complete and metadata["complete"] is True
        for identifier, value in metadata["inputs"].items():
            if identifier in inputs and inputs[identifier] != value:
                raise ValueError("Batch extraction has conflicting source pins")
            inputs[identifier] = value
        if len(metadata["files"]) != 1 or metadata["files"][0]["path"] != f"{state}.pmtiles":
            raise ValueError("Batch extraction has an unexpected state payload")
        entry = metadata["files"][0]
        payload = folder / "files" / entry["path"]
        if (
            payload.is_symlink()
            or payload.stat().st_size != entry["size_bytes"]
            or sha(payload) != entry["sha256"]
        ):
            raise ValueError("Batch extraction payload changed")
        files.append(entry)
        payloads.append(payload)
        for name in ("generation.json", "source.json", "region.geojson"):
            path = folder / name
            intermediates.append(
                {"path": f"{state}/{name}", "sha256": sha(path), "size_bytes": path.stat().st_size}
            )
    if len(epochs) != 1:
        raise ValueError("Batch extraction epochs disagree")
    (output / "files").mkdir()
    for payload in payloads:
        os.link(payload, output / "files" / payload.name)
    metadata = {
        "pipeline_version": "pmtiles-extract-v1-" + sha(Path(__file__)),
        "inputs": inputs,
        "complete": complete,
        "source_date_epoch": epochs.pop(),
        "files": files,
        "intermediates": intermediates,
    }
    payload = encoded(metadata)
    (output / "generation.json").write_bytes(payload + b"\n")
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": sum(entry["size_bytes"] for entry in files),
        "pipeline_version": metadata["pipeline_version"],
    }


def extract(args, catalog, source, jobs_path: Path, output: Path):
    architecture = {"aarch64": "arm64", "x86_64": "x64"}[platform.machine()]
    tool_id = "pmtiles_" + architecture
    jobs = json.loads(jobs_path.read_text())
    region = jobs_path.parent / "region.geojson"
    if not jobs["pages"] or not region.is_file():
        raise ValueError("Prepare the county viewports before extracting")
    settings = (args.root / "pipelines/atlas/settings.yaml").read_text()
    maxzoom = next(
        int(line.split(":", 1)[1]) for line in settings.splitlines() if line.startswith("maxzoom:")
    )
    files = output / "files"
    files.mkdir(parents=True)
    target = files / f"{jobs['state']}.pmtiles"
    command = [
        "pmtiles",
        "extract",
        str(args.source_file.resolve()) if args.source_file is not None else source["url"],
        str(target),
        "--region=" + str(region),
        "--maxzoom=" + str(maxzoom),
        "--download-threads=2",
    ]
    subprocess.run(command, check=True)
    subprocess.run(["pmtiles", "verify", str(target)], check=True)
    (output / "region.geojson").write_bytes(region.read_bytes())
    provenance = {
        "source": source,
        "region_sha256": sha(region),
        "maxzoom": maxzoom,
        "tool_id": tool_id,
        "tool_sha256": catalog[tool_id]["sha256"],
        "command": [
            part.replace(str(region), "region.geojson")
            .replace(str(target), target.name)
            .replace(str(args.source_file.resolve()), "source.pmtiles")
            if args.source_file is not None
            else part.replace(str(region), "region.geojson").replace(str(target), target.name)
            for part in command
        ],
    }
    (output / "source.json").write_bytes(encoded(provenance) + b"\n")
    metadata = {
        "pipeline_version": "pmtiles-extract-v1-" + sha(Path(__file__)),
        "inputs": {
            args.source_id: source["sha256"],
            tool_id: catalog[tool_id]["sha256"],
            **{key: value for key, value in jobs["inputs"].items() if key != "noto_sans"},
        },
        "complete": args.source_file is not None,
        "source_date_epoch": jobs["epoch"],
        "files": [
            {"path": target.name, "sha256": sha(target), "size_bytes": target.stat().st_size}
        ],
        "intermediates": [
            {
                "path": name,
                "sha256": sha(output / name),
                "size_bytes": (output / name).stat().st_size,
            }
            for name in ("source.json", "region.geojson")
        ],
    }
    payload = encoded(metadata)
    (output / "generation.json").write_bytes(payload + b"\n")
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
