"""Read-only development browser for a selected drive folder, not an image verifier."""

import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit

IGNORED = {".DS_Store", ".Spotlight-V100", ".Trashes", ".fseventsd"}
INLINE_TYPES = {"application/pdf", "video/mp4", "audio/mpeg", "image/png", "image/jpeg"}
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".sha256", ".log"}


class DriveFolder:
    def __init__(
        self, root: Path, label: str, notice: str = "Development preview; device tests pending."
    ):
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Choose a drive folder")
        self.label = label
        self.notice = notice

    def file(self, relative: str) -> Path:
        parts = PurePosixPath(relative).parts
        if (
            not relative
            or relative.startswith("/")
            or "\\" in relative
            or any(ord(character) < 32 for character in relative)
            or any(part in {".", ".."} or part.startswith(".") for part in parts)
        ):
            raise ValueError("Invalid drive path")
        path = self.root
        for part in parts:
            path = path / part
            if path.is_symlink():
                raise ValueError("Preview does not follow drive symlinks")
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise ValueError("Not a drive file")
        return resolved

    def inventory(self) -> dict:
        files = []

        def visit(directory: Path, hidden: bool = False) -> None:
            for path in sorted(directory.iterdir(), key=lambda item: item.name):
                if path.name in IGNORED or path.name.startswith(".") or path.is_symlink():
                    continue
                relative = path.relative_to(self.root).as_posix()
                inherited = hidden or path.name.upper() == "BACKUP"
                if path.is_dir():
                    files.append(
                        {
                            "path": relative,
                            "name": path.name,
                            "kind": "directory",
                            "size_bytes": None,
                            "hidden": inherited,
                        }
                    )
                    visit(path, inherited)
                elif path.is_file():
                    files.append(
                        {
                            "path": relative,
                            "name": path.name,
                            "kind": "file",
                            "size_bytes": path.stat().st_size,
                            "hidden": inherited,
                        }
                    )

        visit(self.root)
        metadata = ""
        verify = self.root / "VERIFY.TXT"
        if verify.is_file() and not verify.is_symlink():
            with verify.open(encoding="utf-8", errors="replace") as stream:
                metadata = stream.read(65536)
        variant = re.search(r"^Variant:\s*([1-8])\s*$", metadata, re.M | re.I)
        profile = re.search(r"^Profile:\s*(dev|sample|full)\s*$", metadata, re.M | re.I)
        source = re.search(r"^Source:\s*(.+)$", metadata, re.M | re.I)
        return {
            "label": self.label,
            "variant": int(variant[1]) if variant else None,
            "profile": profile[1].lower() if profile else "local preview",
            "root": "/",
            "status": self.notice,
            "source": source[1].strip() if source else None,
            "files": files,
        }


def byte_range(value: str | None, size: int) -> tuple[int, int]:
    if value is None:
        return 0, size - 1
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", value)
    if match is None or not size or not any(match.groups()):
        raise ValueError("Unsupported byte range")
    first, last = match.groups()
    if not first:
        suffix = int(last)
        if suffix <= 0:
            raise ValueError("Invalid suffix range")
        return max(0, size - suffix), size - 1
    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start >= size or start > end:
        raise ValueError("Unsatisfiable byte range")
    return start, end


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, drive: DriveFolder, assets: Path):
        self.drive = drive
        self.assets = assets.resolve(strict=True)
        for name in ("index.html", "app.css", "app.js"):
            if not (self.assets / name).is_file():
                raise ValueError("Missing development explorer asset: " + name)
        super().__init__(address, PreviewHandler)


class PreviewHandler(BaseHTTPRequestHandler):
    server: PreviewServer

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self):
        self.respond(body=True)

    def do_HEAD(self):
        self.respond(body=False)

    def do_POST(self):
        self.send_error(405, "Read-only development preview")

    def respond(self, *, body: bool):
        route = urlsplit(self.path).path
        try:
            if route == "/api/drive":
                payload = json.dumps(self.server.drive.inventory(), ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if body:
                    self.wfile.write(payload)
                return
            if route in {"/", "/index.html"}:
                self.send_file(self.server.assets / "index.html", "text/html; charset=utf-8", body)
                return
            if route in {"/static/app.css", "/static/app.js"}:
                name = route.rsplit("/", 1)[1]
                mime = "text/css" if name.endswith(".css") else "text/javascript"
                self.send_file(self.server.assets / name, mime + "; charset=utf-8", body)
                return
            if route.startswith("/files/"):
                path = self.server.drive.file(unquote(route.removeprefix("/files/")))
                guessed = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                if path.suffix.lower() in TEXT_EXTENSIONS:
                    mime = "text/plain; charset=utf-8"
                    attachment = False
                elif guessed in INLINE_TYPES:
                    mime, attachment = guessed, False
                else:
                    mime, attachment = "application/octet-stream", True
                self.send_file(path, mime, body, attachment=attachment)
                return
            self.send_error(404)
        except (FileNotFoundError, NotADirectoryError, ValueError):
            self.send_error(404, "File is not in this drive preview")
        except (BrokenPipeError, ConnectionResetError):
            return

    def send_file(self, path: Path, mime: str, body: bool, *, attachment: bool = False):
        with path.open("rb") as stream:
            size = path.stat().st_size
            try:
                start, end = byte_range(self.headers.get("Range"), size)
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            partial_response = self.headers.get("Range") is not None
            length = end - start + 1
            self.send_response(206 if partial_response else 200)
            self.send_header("Content-Type", mime)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            if partial_response:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            if attachment:
                self.send_header(
                    "Content-Disposition",
                    "attachment; filename*=UTF-8''" + quote(path.name, safe=""),
                )
            self.end_headers()
            if body and length:
                stream.seek(start)
                remaining = length
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)


def serve(
    drive: Path,
    assets: Path,
    *,
    label: str,
    port: int = 8766,
    notice: str = "Development preview; device tests pending.",
) -> None:
    with PreviewServer(("127.0.0.1", port), DriveFolder(drive, label, notice), assets) as server:
        print(f"Drive Explorer: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
