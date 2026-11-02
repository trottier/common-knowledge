"""Static export preserves real cargo and keeps executable content inert."""

import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from bs4 import BeautifulSoup

from ck.drive_export import export_preview

ASSETS = Path(__file__).resolve().parents[1] / "pipelines/drive_preview"


def put(root, relative, payload):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


@pytest.fixture
def drive(tmp_path):
    root = tmp_path / "private-source-drive"
    put(root, "VERIFY.TXT", b"Variant: 1\nProfile: sample\nSource: " + b"a" * 40 + b"\n")
    put(root, "README.TXT", b"Incomplete development inspection tree.\n")
    put(root, "3_MAPS_AND_PLACES/RI/Bristol County/Bristol 02806,02809,02885.pdf", b"%PDF-map\x00")
    put(root, "3_MAPS_AND_PLACES/RI/Bristol County/0_OVERVIEW.pdf", b"%PDF-overview\x00")
    put(root, "1_START/Español/Guía rápida.pdf", b"%PDF-guide\xff")
    put(root, "3_MAPS_AND_PLACES/RI/Notes.txt", b"A real text file, not a map download.\n")
    put(root, "BACKUP/3_MAPS_AND_PLACES/RI/backup.pdf", b"%PDF-backup")
    return root


def exported(drive, tmp_path):
    output = tmp_path / "public-export"
    result = export_preview(
        drive, ASSETS, output, label="Actual drive", notice="Incomplete; unreviewed"
    )
    return output, result, json.loads((output / "drive.json").read_text())


def resolve_export_url(output, url, download=False):
    parsed = urlsplit(url)
    assert not parsed.scheme and not parsed.netloc
    relative = unquote(parsed.path)
    if download:
        assert relative.startswith("downloads/")
        relative = "files/" + relative.removeprefix("downloads/")
    assert not relative.startswith("/") and ".." not in Path(relative).parts
    path = output / relative
    assert path.resolve().is_relative_to(output.resolve())
    return path


def test_unicode_names_original_bytes_checksums_and_manifest_privacy(drive, tmp_path):
    originals = {
        path.relative_to(drive).as_posix(): path.read_bytes()
        for path in drive.rglob("*")
        if path.is_file()
    }
    output, result, inventory = exported(drive, tmp_path)
    manifest = (output / "drive.json").read_text()
    assert str(drive) not in manifest and str(output) not in manifest
    assert inventory["root"] == "/"
    assert inventory["variant"] == 1 and inventory["profile"] == "sample"
    assert inventory["status"] == "Incomplete; unreviewed"
    entries = {entry["path"]: entry for entry in inventory["files"] if entry["kind"] == "file"}
    assert set(entries) == set(originals)
    recorded = {entry["path"]: entry for entry in result["files"]}
    for relative, payload in originals.items():
        entry = entries[relative]
        assert (drive / relative).read_bytes() == payload
        assert resolve_export_url(output, entry["url"]).read_bytes() == payload
        assert (
            resolve_export_url(output, entry["download_url"], download=True).read_bytes() == payload
        )
        assert (
            entry["sha256"] == hashlib.sha256(payload).hexdigest() == recorded[relative]["sha256"]
        )
        assert entry["size_bytes"] == len(payload) == recorded[relative]["size_bytes"]
    spanish = entries["1_START/Español/Guía rápida.pdf"]
    assert "%C3%B1" in spanish["url"] and "%20" in spanish["url"]
    document = BeautifulSoup((output / "index.html").read_text(), "html.parser")
    assert document.find("meta", attrs={"name": "ck-drive-manifest"})["content"] == "drive.json"
    for name in ("app.js", "app.css"):
        assert (output / "static" / name).read_bytes() == (ASSETS / name).read_bytes()


@pytest.mark.parametrize("suffix", ["html", "js", "svg", "sh", "apk", "exe"])
def test_active_documents_and_programs_use_inert_transport(drive, tmp_path, suffix):
    relative = f"7_LAPTOP/payload.{suffix}"
    payload = b'<script>throw new Error("must not execute")</script>'
    put(drive, relative, payload)
    output, _, inventory = exported(drive, tmp_path)
    entry = next(entry for entry in inventory["files"] if entry["path"] == relative)
    assert entry["url"].endswith(f"payload.{suffix}.download")
    assert entry["download_url"].endswith(f"payload.{suffix}.download")
    assert not (output / "files" / relative).exists()
    assert resolve_export_url(output, entry["url"]).read_bytes() == payload
    assert (drive / relative).read_bytes() == payload
    configuration = json.loads((output / "vercel.json").read_text())
    inert = next(rule for rule in configuration["headers"] if ".download" in rule["source"])
    headers = {header["key"].lower(): header["value"] for header in inert["headers"]}
    assert headers["content-type"] == "application/octet-stream"
    assert headers["content-disposition"] == "attachment"


def test_download_cards_resolve_only_actual_visible_map_pdfs(drive, tmp_path):
    put(drive, "3_MAPS_AND_PLACES/RI/BACKUP/hidden.pdf", b"%PDF-hidden")
    put(drive, "3_MAPS_AND_PLACES/RI/map-preview.png", b"PNG fixture")
    output, result, inventory = exported(drive, tmp_path)
    paths = {entry["path"] for entry in inventory["downloads"]}
    assert paths == {
        "3_MAPS_AND_PLACES/RI/Bristol County/Bristol 02806,02809,02885.pdf",
        "3_MAPS_AND_PLACES/RI/Bristol County/0_OVERVIEW.pdf",
    }
    assert result["downloads"] == inventory["downloads"]
    entries = {entry["path"]: entry for entry in inventory["files"]}
    for relative in paths:
        entry = entries[relative]
        assert entry["kind"] == "file" and not entry["hidden"]
        assert (
            resolve_export_url(output, entry["download_url"], download=True).read_bytes()
            == (drive / relative).read_bytes()
        )
    config = json.loads((output / "vercel.json").read_text())
    assert {"source": "/downloads/:path*", "destination": "/files/:path*"} in config["rewrites"]
    download_rule = next(
        rule for rule in config["headers"] if rule["source"] == "/downloads/:path*"
    )
    assert {header["key"].lower(): header["value"] for header in download_rule["headers"]}[
        "content-disposition"
    ] == "attachment"


def test_dotfiles_and_symlink_targets_are_not_published(drive, tmp_path):
    put(drive, ".secret", b"private dotfile")
    put(drive, ".private/hidden.pdf", b"private nested dotfile")
    outside = put(tmp_path, "outside/secret.txt", b"private external target")
    (drive / "linked-file.txt").symlink_to(outside)
    (drive / "linked-directory").symlink_to(outside.parent, target_is_directory=True)
    output, _, inventory = exported(drive, tmp_path)
    paths = {entry["path"] for entry in inventory["files"]}
    assert not {".secret", ".private", "linked-file.txt", "linked-directory"} & paths
    published = [path for path in (output / "files").rglob("*") if path.is_file()]
    assert all(not path.is_symlink() for path in published)
    assert not any(path.read_bytes().startswith(b"private") for path in published)
    assert outside.read_bytes() == b"private external target"


@pytest.mark.parametrize("location", ["inside_source", "source_parent", "same_source"])
def test_export_rejects_source_output_containment(drive, tmp_path, location):
    output = {"inside_source": drive / "site", "source_parent": tmp_path, "same_source": drive}[
        location
    ]
    original = (drive / "README.TXT").read_bytes()
    with pytest.raises(ValueError, match="contain"):
        export_preview(drive, ASSETS, output, label="Drive", notice="Draft")
    assert (drive / "README.TXT").read_bytes() == original
    assert not (drive / "site").exists()


def test_nonempty_output_is_rejected_without_overwriting_it(drive, tmp_path):
    output = tmp_path / "occupied"
    sentinel = put(output, "keep.txt", b"existing output")
    with pytest.raises(ValueError, match="empty"):
        export_preview(drive, ASSETS, output, label="Drive", notice="Draft")
    assert sentinel.read_bytes() == b"existing output"
    assert not (output / "drive.json").exists()
