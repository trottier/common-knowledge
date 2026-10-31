"""Regeneration retains entries and resolves the original offline audit errors."""

import struct
import zlib

import pytest
from libzim.reader import Archive
from libzim.suggestion import SuggestionSearcher
from libzim.writer import Creator, Hint, Item, StringProvider

from ck.zimclean import regenerate, remove_embeds


class FixtureItem(Item):
    def __init__(self, path, content):
        self.path, self.content = path, content

    def get_path(self):
        return self.path

    def get_title(self):
        return self.path

    def get_mimetype(self):
        return "text/html"

    def get_contentprovider(self):
        return StringProvider(self.content)

    def get_hints(self):
        return {Hint.FRONT_ARTICLE: 1}


def png():
    # Original synthetic transparent fixture; no external image asset.
    def chunk(name, payload):
        data = name + payload
        return struct.pack(">I", len(payload)) + data + struct.pack(">I", zlib.crc32(data))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 48, 48, 8, 6, 0, 0, 0))
        + (chunk(b"IDAT", zlib.compress((b"\x00" + b"\x00" * 48 * 4) * 48)) + chunk(b"IEND", b""))
    )


def test_archive_rebuild_is_offline_complete_and_repeatable(tmp_path):
    source = tmp_path / "source.zim"
    with Creator(source).config_indexing(False, "eng").config_nbworkers(1) as creator:
        for key, value in {
            "Name": "fixture",
            "Title": "Synthetic test fixture",
            "Description": "Original fixture, never shipped",
            "Creator": "Test fixture",
            "Publisher": "Test fixture",
            "Date": "2000-01-01",
            "Language": "eng",
        }.items():
            creator.add_metadata(key, value.encode())
        creator.add_illustration(png(), 48)
        creator.add_item(
            FixtureItem(
                "index.html", b'<html><body><a href="article.html">Article</a></body></html>'
            )
        )
        creator.add_item(
            FixtureItem(
                "article.html",
                b"<html><body><p>Original words 2.5.</p>"
                b'<iframe src="https://example.invalid/embed"></iframe>'
                b'<a href="./missing">Original label</a>'
                b'<a href="https://example.invalid/source">Attribution</a></body></html>',
            )
        )
        creator.add_redirection("alias", "Alias", "article.html", {})
        creator.set_mainpath("index.html")
    first, second = tmp_path / "first.zim", tmp_path / "second.zim"
    for output in (first, second):
        report = regenerate(source, output, 946684800, b"fixed synthetic identity")
        assert report["entry_count"] == 3
        assert report["output_audit"]["status"] is True
        assert [entry["path"] for entry in report["changed"]] == ["article.html"]
        rebuilt = Archive(output)
        text = bytes(rebuilt.get_entry_by_path("article.html").get_item().content)
        assert b"Original words 2.5." in text
        assert b"https://example.invalid/source" in text
        assert b"Original label" in text and b'href="./missing"' not in text
        assert b"iframe" not in text and b"offline adaptation" in text
        assert rebuilt.get_entry_by_path("alias").is_redirect
        assert "article.html" in list(
            SuggestionSearcher(rebuilt).suggest("article").get_results(0, 10)
        )
    assert first.read_bytes() == second.read_bytes()


def test_declared_external_dependency_must_actually_be_removed():
    with pytest.raises(ValueError, match="dependency was not found"):
        remove_embeds(b"<html><body>Original text only</body></html>")
