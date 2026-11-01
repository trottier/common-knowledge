"""Fetch a held APK with the pinned modern verifier; grant no release approval."""

import argparse
import json
from pathlib import Path

from ck.apkverifier import build_tool_archive, verifier_jar, verify_apk
from ck.catalog import load_catalog
from ck.config import read_yaml
from ck.fetch import fetch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", type=Path, default=Path.cwd())
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--tool-cache", type=Path, required=True)
parser.add_argument("--item", default="offlinellm_android_candidate")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
items = load_catalog(args.root)
spec = read_yaml(args.root / "pipelines/apk_verifier/settings.yaml")
jar_item = items[spec["jar_id"]]
spec = {**spec, "jar_sha256": jar_item.sha256, "jar_size_bytes": jar_item.size_bytes}
archive_item = items[spec["archive_id"]]
archive = build_tool_archive(archive_item, args.cache)
jar = verifier_jar(archive, archive_item, spec, args.tool_cache)
reports = []


def modern_format_check(item, path):
    reports.append(verify_apk(item, path, jar, spec))


fetch(items[args.item], args.cache, format_check=modern_format_check)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(reports[-1], sort_keys=True, indent=2) + "\n")
print(json.dumps({"item": args.item, "signature_verified": True, "release_approved": False}))
