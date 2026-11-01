"""Verify selected VLC APK native members against the pinned publisher AARs."""

import argparse
import json
from pathlib import Path

from ck.catalog import load_catalog
from ck.nativecheck import audit_native_libraries

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", type=Path, default=Path.cwd())
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = audit_native_libraries(
    load_catalog(args.root),
    ["vlc_android", "vlc_android_older"],
    ["vlc_libvlc_aar", "vlc_medialibrary_aar"],
    args.cache,
)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(
    json.dumps(
        {
            "applications": len(result["applications"]),
            "native_members": sum(len(item["native_members"]) for item in result["applications"]),
            "complete_application_source_closure": False,
        }
    )
)
