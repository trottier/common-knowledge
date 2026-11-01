"""Bind Android native members to exact publisher artifacts without source approval."""

import hashlib
import re
import stat
import zipfile
from collections import defaultdict
from pathlib import Path

from ck.catalog import Item
from ck.generated import cached_input


def native_members(path: Path, prefix: str) -> dict[tuple[str, str], dict]:
    result = {}
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            name = member.filename
            if not name.startswith(prefix + "/") or not name.endswith(".so"):
                continue
            match = re.fullmatch(re.escape(prefix) + r"/([A-Za-z0-9_-]+)/([^/]+\.so)", name)
            if not match or member.is_dir() or stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError("Invalid native library archive member")
            identity = (match[1], match[2])
            if identity in result:
                raise ValueError("Duplicate native library archive member")
            with archive.open(member) as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            result[identity] = {"path": name, "sha256": sha, "size_bytes": member.file_size}
    return result


def audit_native_libraries(
    items: dict[str, Item], app_ids: list[str], artifact_ids: list[str], cache: Path
) -> dict:
    if not app_ids or not artifact_ids or len(app_ids) != len(set(app_ids)):
        raise ValueError("Choose distinct applications and a nonempty publisher artifact set")
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ValueError("Duplicate publisher artifact selection")
    artifacts = defaultdict(list)
    for identifier in artifact_ids:
        item = items[identifier]
        for identity, member in native_members(cached_input(item, cache), "jni").items():
            artifacts[identity].append({"artifact_id": identifier, **member})
    applications = []
    for identifier in app_ids:
        item = items[identifier]
        members = native_members(cached_input(item, cache), "lib")
        if not members:
            raise ValueError(f"Application contains no standard native libraries: {identifier}")
        bindings = []
        for identity, member in sorted(members.items()):
            matches = [
                candidate
                for candidate in artifacts[identity]
                if candidate["sha256"] == member["sha256"]
                and candidate["size_bytes"] == member["size_bytes"]
            ]
            if not matches:
                raise ValueError(
                    f"Native library has no exact publisher artifact: {member['path']}"
                )
            bindings.append(
                {"abi": identity[0], "library": identity[1], **member, "matches": matches}
            )
        applications.append({"id": identifier, "sha256": item.sha256, "native_members": bindings})
    return {
        "applications": applications,
        "publisher_artifacts": {
            identifier: items[identifier].sha256 for identifier in artifact_ids
        },
        "all_standard_native_members_match": True,
        "complete_application_source_closure": False,
        "human_license_or_pin_approval": False,
    }
