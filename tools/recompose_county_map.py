"""Recompose the pinned county proof's cached vectors; never reads geodata."""

import argparse
import json
from pathlib import Path

from ck.map_recompose import recompose

parser = argparse.ArgumentParser(description=__doc__)
for name in ["root", "prepared", "output"]:
    parser.add_argument("--" + name, type=Path, required=True)
args = parser.parse_args()
result = recompose(args.root, args.prepared, args.output)
print(
    json.dumps(
        {
            "producer": result["producer"]["version"],
            "files": result["files"],
            "elapsed_seconds": result["elapsed_seconds"],
        },
        indent=2,
    )
)
