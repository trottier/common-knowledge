"""Regenerate a publisher ZIM after removing audited external embeds."""

import hashlib
import json
import mmap
import struct
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from bs4 import BeautifulSoup
from libzim.reader import Archive
from libzim.writer import Creator, Hint, StringProvider
from libzim.writer import Item as WriterItem

from ck.catalog import Item
from ck.fetch import digest, verify_zim
from ck.generated import cached_input, generation_manifest


def remove_embeds(raw: bytes, broken_links: set[str] | None = None) -> bytes:
    document = BeautifulSoup(raw.decode("utf-8"), "html.parser")
    removed = 0
    for link in document.find_all("a", href=True):
        if link["href"] in (broken_links or set()):
            del link["href"]
            removed += 1
    for element in list(document.find_all(True)):
        if element.attrs is None or element.name == "a":
            continue
        values = [element.get(key, "") for key in ("src", "srcset", "poster", "data")]
        if element.name == "link" and set(element.get("rel", [])) & {
            "stylesheet",
            "preload",
            "prefetch",
            "preconnect",
            "dns-prefetch",
        }:
            values.append(element.get("href", ""))
        if any(
            str(value).strip().lower().startswith(("https:", "http:", "//")) for value in values
        ):
            note = document.new_tag("span")
            note.string = "[External embedded resource omitted for offline use.]"
            if element.get("alt"):
                note.string += " " + element["alt"]
            element.replace_with(note)
            removed += 1
    if not removed:
        raise ValueError(
            "Audited dependency was not found; do not silently pass an unchanged article"
        )
    note = document.new_tag("p")
    note.string = (
        "Common Knowledge offline adaptation: external embeds or malformed navigation links "
        "were omitted; their visible article text is retained. "
        "The original article's attribution and revision notice remain below."
    )
    if document.body is None:
        raise ValueError("Archive article has no body for an adaptation notice")
    document.body.insert(0, note)
    return str(document).encode("utf-8")


def normalize_uuid(path: Path, identity: bytes) -> None:
    """Normalize our generated header and its format-mandated internal MD5.

    Header layout: openzim/libzim src/fileheader.cpp; only ZIM 6.3 is supported.
    The publisher source is never modified.
    """
    archive = Archive(path)
    with path.open("r+b") as stream, mmap.mmap(stream.fileno(), 0) as mapped:
        for number in range(archive.entry_count, archive.all_entry_count):
            entry = archive.get_entry_by_id(number)
            if entry.is_redirect:
                continue
            item = entry.get_item()
            if item.mimetype != "application/octet-stream+xapian":
                continue
            raw = bytes(item.content)
            # Xapian Glass header: 14-byte magic, 2-byte format, then UUID.
            # xapian-core/backends/glass/glass_version.cc (1.4 format).
            if not raw.startswith(b"\x0f\x0dXapian Glass\x04\x6e"):
                raise ValueError("Unsupported generated search-index format")
            offset = mapped.find(raw)
            if offset < 0 or mapped.find(raw, offset + 1) >= 0:
                raise ValueError("Generated search index must be uniquely stored uncompressed")
            mapped[offset + 16 : offset + 32] = hashlib.sha256(
                identity + b":" + item.path.encode()
            ).digest()[:16]
        mapped.flush()
        header = stream.read(80)
        if len(header) != 80 or struct.unpack_from("<IHH", header) != (0x044D495A, 6, 3):
            raise ValueError("Unsupported generated ZIM header")
        checksum_position = struct.unpack_from("<Q", header, 72)[0]
        if checksum_position + 16 != path.stat().st_size:
            raise ValueError("Invalid generated ZIM checksum position")
        stream.seek(8)
        stream.write(hashlib.sha256(identity).digest()[:16])
        stream.seek(0)
        checksum = hashlib.md5(usedforsecurity=False)
        remaining = checksum_position
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("Truncated generated ZIM")
            checksum.update(chunk)
            remaining -= len(chunk)
        stream.write(checksum.digest())


class ArchiveItem(WriterItem):
    def __init__(self, archive: Archive, entry, changed: dict[str, bytes]):
        self.archive, self.path, self.title = archive, entry.path, entry.title
        self.mimetype = entry.get_item().mimetype
        self.changed = changed

    def get_path(self):
        return self.path

    def get_title(self):
        return self.title

    def get_mimetype(self):
        return self.mimetype

    def get_hints(self):
        return {Hint.FRONT_ARTICLE: int(self.mimetype == "text/html")}

    def get_contentprovider(self):
        content = self.changed.get(self.path)
        if content is None:
            content = bytes(self.archive.get_entry_by_path(self.path).get_item().content)
        return StringProvider(content)


def regenerate(source: Path, output: Path, epoch: int, identity: bytes) -> dict:
    if output.exists() or source.resolve() == output.resolve():
        raise ValueError("Regenerated archive must have a new output path")
    audit = verify_zim(source, regeneration_only=True, allow_broken_links=True)
    failures = {entry["path"] for entry in audit["logs"] if entry["level"] == "ERROR"}
    archive = Archive(source)
    changed = {}
    for path in sorted(failures):
        links = {
            link
            for entry in audit["logs"]
            if entry.get("path") == path and entry["check"] == "url_internal"
            for link in entry["links"]
        }
        changed[path] = remove_embeds(
            bytes(archive.get_entry_by_path(path).get_item().content), links
        )
    creator = Creator(output).config_nbworkers(1).config_indexing(False, "eng")
    with creator:
        for key in archive.metadata_keys:
            if key != "Counter" and not key.startswith("Illustration_"):
                value = archive.get_metadata(key)
                if key == "Date":
                    value = datetime.fromtimestamp(epoch, UTC).date().isoformat().encode()
                elif key == "Publisher":
                    value = b"Common Knowledge; regenerated from the Kiwix publisher archive"
                creator.add_metadata(key, value)
        creator.add_illustration(bytes(archive.get_illustration_item().content), 48)
        creator.set_mainpath(archive.main_entry.get_item().path)
        for number in range(archive.entry_count):
            entry = archive.get_entry_by_id(number)
            if entry.is_redirect:
                creator.add_redirection(
                    entry.path, entry.title, entry.get_redirect_entry().path, {}
                )
            else:
                creator.add_item(ArchiveItem(archive, entry, changed))
            if number and number % 10000 == 0:
                print(
                    f"Copied {number}/{archive.entry_count} archive entries",
                    file=sys.stderr,
                    flush=True,
                )
    normalize_uuid(output, identity)
    generated = Archive(output)
    if generated.entry_count != archive.entry_count:
        raise ValueError("Regeneration changed the archive entry count")
    for number in range(archive.entry_count):
        before = archive.get_entry_by_id(number)
        after = generated.get_entry_by_path(before.path)
        if before.title != after.title or before.is_redirect != after.is_redirect:
            raise ValueError("Regeneration changed an entry title or redirect")
        if before.is_redirect:
            if before.get_redirect_entry().path != after.get_redirect_entry().path:
                raise ValueError("Regeneration changed a redirect target")
        else:
            original = before.get_item()
            rebuilt = after.get_item()
            expected = changed.get(before.path)
            if expected is None:
                expected = bytes(original.content)
            if original.mimetype != rebuilt.mimetype or expected != bytes(rebuilt.content):
                raise ValueError(f"Regeneration changed unexpected content: {before.path}")
    final_audit = verify_zim(output)
    return {
        "source_audit": audit,
        "output_audit": final_audit,
        "entry_count": archive.entry_count,
        "full_text_index": False,
        "changed": [
            {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}
            for path, raw in changed.items()
        ],
    }


def build_offline_zim(root: Path, item: Item, cache: Path, output: Path, epoch: int) -> dict:
    if output.exists():
        raise ValueError("Offline ZIM output must be new")
    source_cache = cache if (cache / item.sha256).is_file() else cache / "quarantine"
    source = cached_input(item, source_cache)
    recipe = hashlib.sha256()
    for relative in (
        "src/ck/zimclean.py",
        "src/ck/fetch.py",
        "src/ck/generated.py",
        "pyproject.toml",
        "uv.lock",
        "Dockerfile.build",
        "catalog/buildtools.yaml",
        "tools/bootstrap_zim.py",
        "config/debian.sources",
    ):
        recipe.update(relative.encode() + b"\0" + (root / relative).read_bytes())
    pipeline = "zim-offline-v1-" + recipe.hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-zim-offline-") as temporary:
        stage = Path(temporary)
        (stage / "files").mkdir()
        report = regenerate(
            source,
            stage / "files/WikiMed-offline.zim",
            epoch,
            f"{item.sha256}:{pipeline}:{epoch}".encode(),
        )
        (stage / "audit.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        (stage / "files/SOURCE.TXT").write_text(
            f"Source: {item.title}, {item.version}\n{item.url}\nSHA-256: {digest(source)}\n"
            f"{item.attribution}\n{item.license}: {item.license_proof_url}\n"
            "Regenerated by Common Knowledge; malformed links or external embeds omitted in the "
            "articles named in the generation audit. Other entry contents and redirects were "
            "verified against the original archive.\nTitle search is available; the original "
            "full-text index is not included in this regenerated edition.\n"
        )
        result = generation_manifest(
            stage,
            pipeline,
            {item.id: item.sha256},
            complete=True,
            epoch=epoch,
            intermediates=["audit.json"],
            tool_versions=Path("/opt/ck-tool-versions.txt").read_text(),
        )
        stage.rename(output)
    return result
