"""Offline conversion and strict archive placement are separate gates."""

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from ck.catalog import Item
from ck.config import load_config, read_yaml
from ck.fetch import fetch, verify_zim
from ck.zim2pdf import ReferenceFetcher, Topics, article, ensure_glyphs, render_article

ROOT = Path(__file__).resolve().parents[1]


def source(body="<p>Fixture quantity: 2.5 mg; 12–18 hours.</p>"):
    # Synthetic data for numeric preservation, never clinical guidance.
    return f"""<div id="mw-content-text"><div class="mw-parser-output">{body}</div></div>
      <div class="zim-footer"><a title="Last edited on 2026-10-01"
      href="https://en.wikipedia.org/w/index.php?oldid=123">Wikipedia</a>
      <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.en">License</a></div>"""


def test_conversion_preserves_text_and_table_cells_without_active_resources():
    html = source("""<p onclick="bad()">Fixture: 2.5 mg; 12–18 hours.</p>
      <table style="display:none"><tr><th>Label</th><th>Fixture number</th></tr>
      <tr><td rowspan="2">Synthetic</td><td>0.05</td></tr><tr><td>100</td></tr></table>
      <img src="https://example.invalid/track" alt="Figure description">
      <script>bad()</script><iframe src="https://example.invalid/embed"></iframe>
      <a href="javascript:bad()">Unsafe</a><a href="#note">Footnote</a>""")
    data = article(html, "CC-BY-SA-4.0")
    soup = BeautifulSoup(data["html"], "html.parser")
    assert "2.5 mg; 12–18 hours." in soup.get_text()
    cells = [cell.get_text(" ") for cell in soup.select(".source-cell")]
    assert any("Synthetic" in cell and "continues through row 3" in cell for cell in cells)
    assert any("Row 3, column 2" in cell and "100" in cell for cell in cells)
    assert any("0.05" in cell for cell in cells)
    assert not soup.select("table, td, th")
    assert not soup.select("script, iframe, img, [src], [style], [onclick]")
    assert "Figure description" in soup.get_text()
    assert not soup.find("a", string="Unsafe").get("href")
    assert soup.find("a", string="Footnote")["href"] == "#note"
    assert data["modified"] == "2026-10-01"
    assert data["url"].endswith("oldid=123")


@pytest.mark.parametrize(
    "html",
    [
        source().replace("2026-10-01", "unknown"),
        source().replace("by-sa/4.0", "by-sa/3.0"),
        "<p>No provenance</p>",
    ],
)
def test_article_rejects_missing_or_mismatched_provenance(html):
    with pytest.raises(ValueError):
        article(html, "CC-BY-SA-4.0")


def test_disambiguation_pages_cannot_enter_the_medical_selection():
    with pytest.raises(ValueError, match="disambiguation"):
        article(
            source('<meta property="mw:PageProp/disambiguation"><p>Fixture may refer to</p>'),
            "CC-BY-SA-4.0",
        )


def report(check="url_external"):
    return {
        "checks": [
            "checksum",
            "integrity",
            "empty",
            "metadata",
            "favicon",
            "main_page",
            "redundant",
            "url_internal",
            "url_external",
            "redirect",
        ],
        "status": False,
        "file_name": "/temporary/path",
        "logs": [{"check": check, "level": "ERROR", "message": "Fixture failure"}],
    }


def test_zim_with_external_dependency_is_input_only(monkeypatch):
    monkeypatch.setattr(
        "ck.fetch.subprocess.run",
        lambda *a, **k: SimpleNamespace(stdout=json.dumps(report()), stderr="", returncode=1),
    )
    with pytest.raises(ValueError, match="Fixture failure"):
        verify_zim(Path("fixture.zim"))
    audit = verify_zim(Path("fixture.zim"), regeneration_only=True)
    assert audit["status"] is False and audit["regeneration_only"] is True
    assert "file_name" not in audit


@pytest.mark.parametrize("check", ["checksum", "integrity", "url_internal", "redirect"])
def test_regeneration_cannot_bypass_other_archive_errors(monkeypatch, check):
    monkeypatch.setattr(
        "ck.fetch.subprocess.run",
        lambda *a, **k: SimpleNamespace(stdout=json.dumps(report(check)), stderr="", returncode=1),
    )
    with pytest.raises(ValueError):
        verify_zim(Path("fixture.zim"), regeneration_only=True)


def test_unreported_checker_diagnostic_blocks_regeneration(monkeypatch):
    monkeypatch.setattr(
        "ck.fetch.subprocess.run",
        lambda *a, **k: SimpleNamespace(
            stdout=json.dumps(report()), stderr="Unsupported title index", returncode=1
        ),
    )
    with pytest.raises(ValueError, match="unexpected diagnostic"):
        verify_zim(Path("fixture.zim"), regeneration_only=True)


def test_failed_format_retains_verified_bytes_and_does_not_redownload(tmp_path):
    class Response(io.BytesIO):
        url = "https://example.invalid/fixture.txt"

    item = Item.model_validate(
        {
            "id": "fixture",
            "family": "docs",
            "title": "Synthetic fixture, never shipped",
            "url": Response.url,
            "version": "test",
            "size_bytes": 7,
            "sha256": hashlib.sha256(b"fixture").hexdigest(),
            "license": "CC0-1.0",
            "attribution": "Test fixture",
            "license_proof_url": "https://example.invalid/license",
            "placement": "universal",
            "dest": "4_PHONE_PACK/fixture.txt",
            "profiles": ["dev"],
        }
    )
    calls = []

    def check(*args):
        raise ValueError("Fixture format error")

    def download(*args, **kwargs):
        calls.append(1)
        return Response(b"fixture")

    with pytest.raises(ValueError, match="retained"):
        fetch(item, tmp_path, opener=download, format_check=check)
    assert (tmp_path / "quarantine" / item.sha256).read_bytes() == b"fixture"
    with pytest.raises(ValueError, match="Fixture format"):
        fetch(item, tmp_path, opener=download, format_check=check)
    assert len(calls) == 1


def test_draft_selection_has_150_unique_articles():
    selection = Topics.model_validate(read_yaml(ROOT / "catalog/medpdf_topics.yaml"))
    assert len(selection.topics) == 150
    assert len({topic.id for topic in selection.topics}) == 150
    assert len({(topic.source, topic.title) for topic in selection.topics}) == 150


def test_reference_resources_are_limited_to_cataloged_font_aliases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("font").write_bytes(b"Synthetic font resource")
    fetcher = ReferenceFetcher({"ck-font:///fixture": Path("font")})
    response = fetcher.fetch("ck-font:///fixture")
    assert response.read() == b"Synthetic font resource"
    response.close()
    with pytest.raises(ValueError, match="Unexpected reference resource"):
        fetcher.fetch("https://example.invalid/tracker")


def test_missing_symbols_cannot_silently_disappear():
    with pytest.raises(ValueError, match="U\\+2264"):
        ensure_glyphs("Fixture ≤ 5", set(map(ord, "Fixture 5")))


def test_attributed_phone_pdf_retains_numbers_links_and_repeat_hash(tmp_path):
    from jinja2 import Environment, FileSystemLoader
    from markupsafe import Markup
    from pypdf import PdfReader

    from ck.render import font_files

    fonts = {"ck-font:///fixture": font_files(ROOT, load_config(ROOT).languages[0])[0]}
    data = article(
        source('<h2 id="fixture">Synthetic test</h2><p>2.5 mg; 12–18 hours.</p>'), "CC-BY-SA-4.0"
    )
    document = (
        Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
        .get_template("reference.html.j2")
        .render(
            **data,
            title="Synthetic test, never medical guidance",
            body=Markup(data["html"]),
            fonts=list(fonts),
            reviewed=False,
            timestamp="2000-01-01T00:00:00+00:00",
            source_version="synthetic",
            css=(ROOT / "templates/document.css").read_text(),
        )
    )
    first, second = tmp_path / "a.pdf", tmp_path / "b.pdf"
    for output in (first, second):
        render_article((document, output, fonts, 946684800))
    assert first.read_bytes() == second.read_bytes()
    pdf = PdfReader(first)
    text = " ".join(page.extract_text() for page in pdf.pages)
    assert "2.5 mg; 12–18 hours." in text
    assert "Article last edited: 2026-10-01" in text
    assert pdf.outline and any(page.get("/Annots") for page in pdf.pages)
    assert pdf.trailer["/Root"]["/MarkInfo"]["/Marked"]
    assert float(pdf.pages[0].mediabox.width) == pytest.approx(90 / 25.4 * 72, abs=0.02)
    assert float(pdf.pages[0].mediabox.height) == pytest.approx(160 / 25.4 * 72, abs=0.02)


def test_clipped_source_table_fails_conversion(tmp_path):
    document = (
        "<style>@page{size:90mm 160mm} td{white-space:pre}</style><table><tr><td>"
        + ("Synthetic-long-table-cell " * 20)
        + "</td></tr></table>"
    )
    with pytest.raises(ValueError, match="exceeds page"):
        render_article((document, tmp_path / "clipped.pdf", {}, 946684800))
    assert not (tmp_path / "clipped.pdf").exists()
