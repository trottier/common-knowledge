"""Measure the actual bounded named-street plan from an authenticated prepared scene."""

import argparse
import json
import resource
import time
from pathlib import Path

from ck.countyproof import svg_map
from ck.fetch import digest
from ck.streetcoverage import complete_detail_sheets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.prepared.is_symlink() or digest(args.prepared) != args.sha256:
        raise ValueError("Choose a fresh result and the exact authenticated prepared scene")
    data = json.loads(args.prepared.read_text())
    for font in data["fonts"]:
        if digest(Path(font["path"])) != font["sha256"]:
            raise ValueError("Prepared font changed")
    result = {
        "prepared_sha256": args.sha256,
        "preparation_producer": data["producer"],
        "tool_sha256": digest(Path(__file__)),
        "base_sheets": len(data["sheets"]),
        "status": "Unreviewed bounded label-plan diagnostic; no PDF rendered",
    }
    started = time.monotonic()
    try:
        sheets, coverage = complete_detail_sheets(data, svg_map)
        result.update(cap_failure=False, total_sheets=len(sheets), coverage=coverage)
    except ValueError as error:
        message = str(error)
        if not message.startswith("Street coverage incomplete: max_pages="):
            raise
        result.update(cap_failure=True, actual_failure=message)
    result.update(
        wall_seconds=time.monotonic() - started,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: result.get(key)
                for key in (
                    "base_sheets",
                    "cap_failure",
                    "total_sheets",
                    "wall_seconds",
                    "peak_rss_kib",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
