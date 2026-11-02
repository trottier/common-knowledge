"""Reframe authenticated cached medical HTML; no source archives are opened."""

import argparse
import json
from pathlib import Path

from ck.reference_recompose import recompose_medical

parser = argparse.ArgumentParser(description=__doc__)
for name in ["root", "prepared", "cache", "output"]:
    parser.add_argument("--" + name, type=Path, required=True)
selection = parser.add_mutually_exclusive_group(required=True)
selection.add_argument("--topic", action="append")
selection.add_argument("--all", action="store_true")
args = parser.parse_args()
result = recompose_medical(args.root, args.prepared, args.cache, args.output, args.topic)
print(
    json.dumps(
        {key: result[key] for key in ["sha256", "size_bytes", "pipeline_version", "articles"]},
        indent=2,
    )
)
