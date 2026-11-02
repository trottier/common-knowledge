"""Export an actual development drive tree for static mobile-test hosting."""

import hashlib
import json
import mimetypes
import shutil
from pathlib import Path
from urllib.parse import quote

from ck.drive_preview import INLINE_TYPES, TEXT_EXTENSIONS, DriveFolder


def export_preview(drive: Path, assets: Path, output: Path, *, label: str, notice: str) -> dict:
    folder = DriveFolder(drive, label, notice)
    target = output.resolve()
    if target.is_relative_to(folder.root) or folder.root.is_relative_to(target):
        raise ValueError("Export output and source drive must not contain one another")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("Choose an empty static preview output directory")
    inventory = folder.inventory()
    target.mkdir(parents=True, exist_ok=True)
    static = target / "static"
    static.mkdir()
    for name in ("app.css", "app.js"):
        shutil.copyfile(assets / name, static / name)
    document = (assets / "index.html").read_text()
    document = document.replace(
        "<head>", '<head>\n  <meta name="ck-drive-manifest" content="drive.json">', 1
    )
    (target / "index.html").write_text(document)
    copied = []
    for entry in inventory["files"]:
        if entry["kind"] != "file":
            continue
        source = folder.file(entry["path"])
        mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        inert = mime not in INLINE_TYPES and source.suffix.lower() not in TEXT_EXTENSIONS
        transport_path = entry["path"] + (".download" if inert else "")
        destination = target / "files" / transport_path
        if destination.exists():
            raise ValueError("Static transport filename collision: " + transport_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        with source.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        with destination.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != checksum:
                raise ValueError("Source changed during static preview export: " + entry["path"])
        size = destination.stat().st_size
        entry.update(
            size_bytes=size,
            sha256=checksum,
            url="files/" + quote(transport_path, safe="/"),
            download_url="downloads/" + quote(transport_path, safe="/"),
        )
        copied.append({"path": entry["path"], "size_bytes": size, "sha256": checksum})
    inventory["downloads"] = [
        {"path": entry["path"]}
        for entry in sorted(
            inventory["files"], key=lambda entry: (entry["name"].startswith("0_"), entry["path"])
        )
        if entry["kind"] == "file"
        and entry["path"].startswith("3_MAPS_AND_PLACES/")
        and entry["path"].lower().endswith(".pdf")
        and not entry["hidden"]
    ]
    (target / "drive.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n")
    configuration = {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "version": 2,
        "framework": None,
        "buildCommand": "",
        "outputDirectory": ".",
        "headers": [
            {
                "source": "/(.*)",
                "headers": [
                    {"key": "X-Content-Type-Options", "value": "nosniff"},
                    {"key": "Referrer-Policy", "value": "no-referrer"},
                ],
            },
            {
                "source": "/downloads/:path*",
                "headers": [
                    {"key": "Content-Disposition", "value": "attachment"},
                ],
            },
            {
                "source": r"/files/(.*\.download)",
                "headers": [
                    {"key": "Content-Type", "value": "application/octet-stream"},
                    {"key": "Content-Disposition", "value": "attachment"},
                ],
            },
        ],
        "rewrites": [{"source": "/downloads/:path*", "destination": "/files/:path*"}],
    }
    (target / "vercel.json").write_text(json.dumps(configuration, indent=2) + "\n")
    return {"files": copied, "downloads": inventory["downloads"], "output": str(target)}
