"""Collect published manifests using authenticated gh; never execute release data."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def collect(repository: str, output: Path) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository")
    output.mkdir(parents=True, exist_ok=False)
    pages = json.loads(
        subprocess.check_output(
            ["gh", "api", "--paginate", "--slurp", f"repos/{repository}/releases"], text=True
        )
    )
    for release in (release for page in pages for release in page):
        if release["draft"]:
            continue
        tag = release["tag_name"]
        if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", tag):
            raise ValueError("Unexpected published release tag")
        directory = output / tag
        directory.mkdir()
        subprocess.run(
            [
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                repository,
                "--pattern",
                "release-manifest.json",
                "--pattern",
                "SHA256SUMS",
                "--dir",
                str(directory),
            ],
            check=True,
        )
        path = directory / "release-manifest.json"
        expected = [
            line.split()[0]
            for line in (directory / "SHA256SUMS").read_text().splitlines()
            if line.split()[1:] == ["release-manifest.json"]
        ]
        if len(expected) != 1 or hashlib.sha256(path.read_bytes()).hexdigest() != expected[0]:
            raise ValueError("Published release manifest checksum differs")
        manifest = json.loads(path.read_text())
        if "v" + manifest["version"] != tag:
            raise ValueError("Published manifest version differs from release tag")
        path.rename(output / (tag + ".json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    collect(args.repository, args.output)
