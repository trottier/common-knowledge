"""HTTP behavior of the local, read-only drive explorer."""

import http.client
import json
import threading
from urllib.parse import quote

import pytest

from ck.drive_preview import DriveFolder, PreviewServer


@pytest.fixture
def preview(tmp_path):
    root = tmp_path / "drive"
    root.mkdir()
    (root / "VERIFY.TXT").write_text("Variant: 1\nProfile: sample\n")
    (root / "README.TXT").write_bytes(b"0123456789")
    (root / "empty.txt").write_bytes(b"")
    unicode_path = root / "1_START" / "简体中文" / "Read #1%.pdf"
    unicode_path.parent.mkdir(parents=True)
    unicode_path.write_bytes(b"%PDF-original-test-bytes")
    county = root / "3_MAPS_AND_PLACES" / "RI" / "Bristol County"
    county.mkdir(parents=True)
    (county / "Bristol County 02806,02809,02885.pdf").write_bytes(b"%PDF-county-fixture")
    (root / "BACKUP").mkdir()
    (root / "BACKUP" / "README.TXT").write_text("Backup fixture")
    (root / ".private").write_text("hidden fixture")
    (root / ".DS_Store").write_text("not drive content")
    for name in ("page.html", "script.js", "image.svg", "app.apk", "launch.command"):
        (root / name).write_bytes(b"Unexecuted original fixture")
    outside = tmp_path / "outside.txt"
    outside.write_text("Outside-root sentinel")
    (root / "escape.txt").symlink_to(outside)
    (root / "escape-dir").symlink_to(tmp_path, target_is_directory=True)
    (root / "internal-link.txt").symlink_to(root / "README.TXT")
    assets = tmp_path / "assets"
    assets.mkdir()
    for name in ("index.html", "app.css", "app.js"):
        (assets / name).write_text(f"Original application asset {name}")
    server = PreviewServer(("127.0.0.1", 0), DriveFolder(root, "EMERGENCY"), assets)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        yield server, root, assets
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        assert not thread.is_alive()


def request(preview, path, method="GET", headers=None, body=None):
    server = preview[0]
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_inventory_lists_actual_unicode_zip_paths_and_hidden_backup_without_host_root(preview):
    status, headers, payload = request(preview, "/api/drive")
    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    data = json.loads(payload)
    assert (data["label"], data["variant"], data["profile"], data["root"]) == (
        "EMERGENCY",
        1,
        "sample",
        "/",
    )
    assert str(preview[1]).encode() not in payload
    entries = {entry["path"]: entry for entry in data["files"]}
    assert "1_START/简体中文/Read #1%.pdf" in entries
    leaf = "3_MAPS_AND_PLACES/RI/Bristol County/Bristol County 02806,02809,02885.pdf"
    assert entries[leaf]["size_bytes"] == len(b"%PDF-county-fixture")
    assert entries[leaf]["name"] == "Bristol County 02806,02809,02885.pdf"
    assert entries["1_START/简体中文"]["kind"] == "directory"
    assert entries["BACKUP"]["hidden"] is True
    assert entries["BACKUP/README.TXT"]["hidden"] is True
    assert not any(
        path.startswith(".") or "escape" in path or path == "internal-link.txt" for path in entries
    )
    assert entries["README.TXT"]["size_bytes"] == 10
    before = dict(entries)
    (preview[1] / "new.txt").write_bytes(b"new actual file")
    refreshed = json.loads(request(preview, "/api/drive")[2])
    assert "new.txt" not in before
    assert any(entry["path"] == "new.txt" for entry in refreshed["files"])


def test_unicode_file_and_application_assets_are_original_bytes(preview):
    relative = "1_START/简体中文/Read #1%.pdf"
    path = "/files/" + quote(relative, safe="/")
    status, headers, payload = request(preview, path)
    assert status == 200
    assert payload == (preview[1] / relative).read_bytes()
    assert headers["Content-Type"] == "application/pdf"
    assert "Content-Disposition" not in headers
    for route, name, mime in (
        ("/", "index.html", "text/html"),
        ("/static/app.css", "app.css", "text/css"),
        ("/static/app.js", "app.js", "text/javascript"),
    ):
        status, headers, payload = request(preview, route)
        assert status == 200
        assert payload == (preview[2] / name).read_bytes()
        assert headers["Content-Type"].startswith(mime)
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "SAMEORIGIN"
        assert headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "range_header,expected,content_range",
    [
        ("bytes=2-5", b"2345", "bytes 2-5/10"),
        ("bytes=7-", b"789", "bytes 7-9/10"),
        ("bytes=-3", b"789", "bytes 7-9/10"),
        ("bytes=8-999", b"89", "bytes 8-9/10"),
        ("bytes=-999", b"0123456789", "bytes 0-9/10"),
    ],
)
def test_real_http_byte_ranges_preserve_exact_source_bytes(
    preview, range_header, expected, content_range
):
    status, headers, payload = request(
        preview, "/files/README.TXT", headers={"Range": range_header}
    )
    assert status == 206
    assert payload == expected
    assert headers["Content-Range"] == content_range
    assert headers["Content-Length"] == str(len(expected))
    assert headers["Accept-Ranges"] == "bytes"


@pytest.mark.parametrize(
    "range_header", ["bytes=10-", "bytes=8-2", "bytes=-0", "bytes=-", "bytes=0-1,3-4", "items=0-1"]
)
def test_unsatisfiable_or_unsupported_ranges_return_416_without_body(preview, range_header):
    status, headers, payload = request(
        preview, "/files/README.TXT", headers={"Range": range_header}
    )
    assert status == 416
    assert headers["Content-Range"] == "bytes */10"
    assert headers["Content-Length"] == "0"
    assert payload == b""


def test_head_and_empty_files_have_correct_lengths_without_payload(preview):
    for path in ("/api/drive", "/files/README.TXT", "/", "/static/app.js"):
        get_status, get_headers, get_body = request(preview, path)
        status, headers, payload = request(preview, path, "HEAD")
        assert status == get_status == 200
        assert headers["Content-Length"] == get_headers["Content-Length"] == str(len(get_body))
        assert payload == b""
    status, headers, payload = request(preview, "/files/README.TXT", "HEAD", {"Range": "bytes=2-5"})
    assert status == 206 and payload == b""
    assert headers["Content-Length"] == "4"
    assert headers["Content-Range"] == "bytes 2-5/10"
    assert request(preview, "/files/empty.txt")[2] == b""
    assert request(preview, "/files/empty.txt", headers={"Range": "bytes=0-"})[0] == 416


@pytest.mark.parametrize(
    "name", ["page.html", "script.js", "image.svg", "app.apk", "launch.command"]
)
def test_drive_programs_and_active_documents_are_inert_downloads(preview, name):
    status, headers, payload = request(preview, "/files/" + name)
    assert status == 200 and payload == b"Unexecuted original fixture"
    assert headers["Content-Type"] == "application/octet-stream"
    assert headers["Content-Disposition"].startswith("attachment;")
    assert headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "path",
    [
        "/files/../outside.txt",
        "/files/%2e%2e/outside.txt",
        "/files/%2fetc/passwd",
        "/files/..%5coutside.txt",
        "/files/%00README.TXT",
        "/files/.private",
        "/files/.DS_Store",
        "/files/escape.txt",
        "/files/escape-dir/outside.txt",
        "/files/internal-link.txt",
        "/static/../outside.txt",
        "/files/not-present.txt",
        "/files/1_START",
    ],
)
def test_http_traversal_symlinks_hidden_files_and_unlisted_assets_cannot_escape(preview, path):
    status, _, payload = request(preview, path)
    assert status == 404
    assert b"Outside-root sentinel" not in payload
    assert str(preview[1]).encode() not in payload


def test_post_cannot_modify_drive_files(preview):
    before = (preview[1] / "README.TXT").read_bytes()
    for route in ("/api/drive", "/files/README.TXT", "/"):
        assert request(preview, route, "POST", body=b"overwrite attempt")[0] == 405
    assert (preview[1] / "README.TXT").read_bytes() == before
