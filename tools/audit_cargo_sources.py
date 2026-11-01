"""Check one application's locked Cargo source set using only its verified cache."""

import argparse
import json
from pathlib import Path

from ck.cargocheck import audit_cargo_sources
from ck.catalog import load_catalog

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", type=Path, default=Path.cwd())
parser.add_argument("--source-id", required=True)
parser.add_argument("--lock-path", required=True)
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = audit_cargo_sources(load_catalog(args.root), args.source_id, args.lock_path, args.cache)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(
    json.dumps(
        {
            "registry_packages": len(result["registry_packages"]),
            "local_packages": len(result["local_packages"]),
            "complete_application_source_closure": False,
        }
    )
)
