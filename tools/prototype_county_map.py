"""Run the isolated, unreviewed county/area vector-map proof; never updates catalog pins."""

import argparse
from pathlib import Path

from ck.countyproof import run

parser = argparse.ArgumentParser(description=__doc__)
for name in ["root", "cache", "basemap", "points", "zip-source", "output", "pdf-budget-config"]:
    parser.add_argument("--" + name, type=Path, required=True)
parser.add_argument("--policy", type=Path)
parser.add_argument("--road-cache", type=Path)
parser.add_argument("--counts-only", action="store_true")
args = parser.parse_args()
run(
    args.root,
    args.cache,
    args.basemap,
    args.points,
    args.zip_source,
    args.output,
    args.pdf_budget_config,
    args.policy,
    args.counts_only,
    args.road_cache,
)
