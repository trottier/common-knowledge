"""Prepare one pinned source's immutable projected road/place cache; no downloads."""

import argparse
import json
from pathlib import Path

from ck.catalog import load_catalog
from ck.config import read_yaml
from ck.generated import cached_input
from ck.roadcache import build_cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "cache", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-item", required=True)
    parser.add_argument("--crs", required=True)
    parser.add_argument("--epoch", type=int, required=True)
    args = parser.parse_args()
    item = load_catalog(args.root)[args.source_item]
    allowed = set(read_yaml(args.root / "pipelines/androidmaps/settings.yaml")["road_values"])
    print(
        json.dumps(
            build_cache(
                args.root,
                cached_input(item, args.cache),
                item,
                allowed,
                args.crs,
                args.epoch,
                args.output,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
