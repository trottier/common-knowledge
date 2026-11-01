import hashlib
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from libzim.reader import Archive

from ck.catalog import Item
from ck.wikem import (
    Snapshot,
    build_archive,
    clean_html,
    load_snapshot,
    local_link,
    page_document,
    redirect_target,
)
from ck.zim2pdf import archive_source, article

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "source",
    [
        "#REDIRECT [[Article#Section|Label]]",
        "#Redirect:[[Article#Section|Label]]",
        "#REDIRECT: [[Article#Section|Label]]",
        " \n#redirect : [[ Article#Section |Label]]",
    ],
)
def test_redirect_colon_forms_preserve_the_actual_target(source):
    assert redirect_target(source) == "Article#Section"
    with pytest.raises(ValueError, match="Unsupported"):
        redirect_target("Ordinary article text [[Article]]")


def pages():
    return {
        "Alpha": {"pageid": 1, "ns": 0, "title": "Alpha", "lastrevid": 10},
        "Beta": {"pageid": 2, "ns": 0, "title": "Beta", "lastrevid": 20, "redirect": ""},
    }


def test_snapshot_requires_complete_pagination_and_accounts_for_publisher_denials(tmp_path):
    root, cache = tmp_path / "repo", tmp_path / "cache"
    (root / "pipelines/wikem").mkdir(parents=True)
    (root / "config").mkdir()
    cache.mkdir()
    (root / "pipelines/wikem/settings.yaml").write_bytes(
        (ROOT / "pipelines/wikem/settings.yaml").read_bytes()
    )
    scope = root / "config/wikem-scope.yaml"
    scope.write_text(
        json.dumps(
            {
                "pages": [
                    {"pageid": 2, "title": "Beta", "reason": "Publisher denied anonymous access"}
                ]
            }
        )
    )

    def source(identifier, url, value):
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        sha256 = hashlib.sha256(raw).hexdigest()
        (cache / sha256).write_bytes(raw)
        return Item(
            id=identifier,
            family="docs",
            title="Synthetic API fixture",
            url=url,
            version="synthetic",
            size_bytes=len(raw),
            sha256=sha256,
            license="CC-BY-SA-4.0",
            attribution="Synthetic contributors",
            license_proof_url="https://wikem.org/wiki/Creative_Commons",
            placement="hub_only",
            dest="build/inputs/",
            profiles=["sample"],
        )

    api = "https://wikem.org/w/api.php?"
    listing = {"query": {"pages": {str(p["pageid"]): p for p in pages().values()}}}
    items = {
        "wikem_license_snapshot": source(
            "wikem_license_snapshot",
            "https://wikem.org/wiki/Creative_Commons",
            b"https://creativecommons.org/licenses/by-sa/4.0/",
        ),
        "wikem_listing_0000": source(
            "wikem_listing_0000", api + "generator=allpages&gapnamespace=0", listing
        ),
        "wikem_revisions_0000": source(
            "wikem_revisions_0000",
            api + "revids=10",
            {
                "query": {
                    "pages": {
                        "1": {
                            "pageid": 1,
                            "revisions": [{"revid": 10, "timestamp": "2000-01-01T00:00:00Z"}],
                        }
                    }
                }
            },
        ),
        "wikem_article_1": source(
            "wikem_article_1",
            api + "oldid=10",
            {
                "parse": {
                    "pageid": 1,
                    "revid": 10,
                    "text": {"*": '<div class="mw-parser-output">Synthetic article</div>'},
                }
            },
        ),
    }
    loaded = load_snapshot(root, items, cache)
    assert set(loaded.pages) == {"Alpha"} and len(loaded.exclusions) == 1
    assert set(loaded.inputs) == set(items)
    listing["continue"] = {"gapcontinue": "Gamma", "continue": "gapcontinue||"}
    items["wikem_listing_0000"] = source(
        "wikem_listing_0000", api + "generator=allpages&gapnamespace=0", listing
    )
    with pytest.raises(ValueError, match="stopped before the final"):
        load_snapshot(root, items, cache)


def test_offline_article_keeps_table_structure_and_removes_automatic_remote_resources():
    source = """<div class="mw-parser-output" onclick="bad()" style="background:url(https://bad.invalid)">
      <h2 id="section">Synthetic heading</h2><table><tr><th rowspan="2">Synthetic header</th>
      <td>Synthetic first cell</td></tr><tr><td>Synthetic second cell</td></tr></table>
      <img src="https://bad.invalid/pixel" alt="Synthetic figure">
      <script>bad()</script><script type="math/tex">SYNTHETIC-FORMULA</script>
      <style>@import 'https://bad.invalid';</style>
      <a href="/wiki/Beta">Internal alias</a><a href="javascript:bad()">Visible unsafe link text</a>
      <a href="#missing">Visible missing fragment text</a><form action="https://bad.invalid">
      <button>Visible control words</button><p>Visible form words</p></form></div>"""
    content, audit = clean_html(source, pages(), "https://wikem.org")
    soup = BeautifulSoup(content, "html.parser")
    assert len(soup.select("table tr")) == 2 and soup.th["rowspan"] == "2"
    assert not soup.select("script, style, img, form, button, [src], [onclick], [style]")
    assert soup.find("a", string="Internal alias")["href"] == "2.html"
    assert not soup.find("a", string="Visible unsafe link text").has_attr("href")
    assert "Visible form words" in soup.get_text() and "Visible control words" in soup.get_text()
    assert "Synthetic figure" in soup.get_text()
    assert "SYNTHETIC-FORMULA" in soup.get_text()
    assert audit == {"omitted_media": 1, "disabled_controls": 2, "unavailable_links": 2}
    document = page_document(
        pages()["Alpha"],
        {"revid": 10, "timestamp": "2000-01-01T00:00:00Z"},
        content,
        "https://wikem.org",
    )
    converted = article(document.decode(), "CC-BY-SA-4.0")
    assert converted["modified"] == "2000-01-01"
    assert "Synthetic first cell" in converted["html"]
    assert "Synthetic second cell" in converted["html"]


def test_internal_link_resolution_handles_encoded_titles_fragments_and_unsafe_urls():
    assert (
        local_link("https://wikem.org/wiki/Alpha#section", pages(), "https://wikem.org")
        == "1.html#section"
    )
    assert local_link("/w/index.php?title=Beta", pages(), "https://wikem.org") == "2.html"
    assert local_link("/wiki/Missing", pages(), "https://wikem.org") is None
    assert local_link("//bad.invalid/remote", pages(), "https://wikem.org") is None
    assert local_link("javascript:bad()", pages(), "https://wikem.org") is None


def test_generated_wikem_archive_repeats_with_title_search_aliases_and_source_dates(
    tmp_path, monkeypatch
):
    sources = Snapshot(
        pages(),
        {
            10: {"pageid": 1, "revid": 10, "timestamp": "2000-01-01T00:00:00Z"},
            20: {
                "pageid": 2,
                "revid": 20,
                "timestamp": "2000-01-01T00:00:00Z",
                "slots": {"main": {"*": "#REDIRECT [[Alpha]]"}},
            },
        },
        {
            1: {
                "revision": 10,
                "html": (
                    '<div class="mw-parser-output"><h2 id="section">Synthetic reference</h2>'
                    "<table><tr><td>Synthetic cell</td></tr></table>"
                    '<a href="/wiki/Beta">Beta</a></div>'
                ),
            }
        },
        {"synthetic_source": "0" * 64},
        "https://wikem.org/wiki/Creative_Commons",
        "https://wikem.org",
    )
    monkeypatch.setattr("ck.wikem.load_snapshot", lambda *args: sources)
    first = build_archive(ROOT, {}, tmp_path, tmp_path / "a", 946684800)
    second = build_archive(ROOT, {}, tmp_path, tmp_path / "b", 946684800)
    assert first == second and first["articles"] == first["redirects"] == 1
    path = tmp_path / "a/files/WikEM-offline.zim"
    assert path.read_bytes() == (tmp_path / "b/files/WikEM-offline.zim").read_bytes()
    archive = Archive(path)
    assert archive.entry_count == 3 and archive.has_title_index
    assert b"2000-01-01" in bytes(archive.get_entry_by_path("A/1.html").get_item().content)
    alias = BeautifulSoup(
        bytes(archive.get_entry_by_path("A/2.html").get_item().content), "html.parser"
    )
    assert alias.find("a", string="Alpha")["href"] == "1.html"
    with pytest.raises(ValueError, match="source redirect"):
        article(str(alias), "CC-BY-SA-4.0")
    source_item = Item(
        id="synthetic_source",
        family="docs",
        title="Synthetic source fixture",
        url="https://example.invalid/source",
        version="synthetic",
        size_bytes=1,
        sha256="0" * 64,
        license="CC0-1.0",
        attribution="Synthetic fixture",
        license_proof_url="https://example.invalid/license",
        placement="hub_only",
        dest="build/inputs/",
        profiles=["sample"],
    )
    generated_item = source_item.model_copy(
        update={
            "id": "a",
            "family": "generated",
            "url": None,
            "inputs": ["synthetic_source"],
            **{key: first[key] for key in ("size_bytes", "sha256", "pipeline_version")},
        }
    )
    catalog = {"synthetic_source": source_item, "a": generated_item}
    selected, audit = archive_source(generated_item, catalog, tmp_path, tmp_path, 946684800)
    assert selected == path and audit["status"] is True
    with pytest.raises(ValueError, match="at this epoch"):
        archive_source(generated_item, catalog, tmp_path, tmp_path, 946684801)
