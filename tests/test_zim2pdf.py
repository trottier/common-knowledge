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
from ck.fetch import canonical_zim_logs, fetch, verify_zim
from ck.zim2pdf import ReferenceFetcher, Topics, article, ensure_glyphs, render_article

ROOT = Path(__file__).resolve().parents[1]


def test_duplicate_content_audits_do_not_depend_on_worker_order():
    def warning(first, second):
        return {
            "check": "redundant",
            "level": "WARNING",
            "path1": first,
            "path2": second,
            "message": first + " and " + second,
        }

    error = {"check": "checksum", "level": "ERROR", "message": "Synthetic error"}
    first = [warning("a", "b"), warning("a", "c"), error]
    second = [error, warning("c", "b"), warning("b", "a")]
    assert canonical_zim_logs(first) == canonical_zim_logs(second)
    assert error in canonical_zim_logs(first)


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
      <a href="javascript:bad()">Unsafe</a><a href="#note">Footnote</a><p id="note">Note</p>""")
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


def test_publisher_revision_dates_are_read_from_localized_footers():
    html = source().replace("Last edited on ", "Esta página se editó por última vez el ")
    assert article(html, "CC-BY-SA-4.0")["modified"] == "2026-10-01"


def test_source_equations_need_a_verified_renderer_and_preserve_its_vector_paths():
    html = source(
        '<span class="mwe-math-element"><math id="ratio" alttext="2.5 / 0.05">'
        "<mfrac><mn>2.5</mn><mn>0.05</mn></mfrac></math>"
        '<img class="mwe-math-fallback-image-inline" src="fallback.svg" alt="Equation fallback">'
        '</span><img src="figure.svg" alt="Other figure">'
    )
    with pytest.raises(ValueError, match="verified offline equation renderer"):
        article(html, "CC-BY-SA-4.0")
    received = []
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0L10 0"/></svg>'

    def render(mathml):
        received.append(mathml)
        return svg

    data = article(html, "CC-BY-SA-4.0", render)
    soup = BeautifulSoup(data["html"], "html.parser")
    assert "<mfrac><mn>2.5</mn><mn>0.05</mn></mfrac>" in received[0]
    assert soup.find(id="ratio") and soup.path["d"] == "M0 0L10 0"
    assert not soup.find("math") and len(data["rendered_equations"]) == 1
    assert soup.svg["aria-label"] == "2.5 / 0.05"
    assert data["rendered_equations"][0]["replaced_math_fallbacks"] == 1
    assert data["omitted_media"] == 1 and "Other figure" in soup.get_text()


def test_original_cc0_navigation_does_not_obscure_the_article_license():
    for expected in ("CC-BY-SA-4.0 AND CC0-1.0", "CC0-1.0 AND CC-BY-SA-4.0"):
        assert article(source(), expected)["url"].endswith("oldid=123")
    for expected in ("CC0-1.0", "Unknown AND CC-BY-SA-4.0", "CC-BY-SA-3.0 AND CC0-1.0"):
        with pytest.raises(ValueError, match="license"):
            article(source(), expected)


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
    def run(arguments, **kwargs):
        data = report()
        failed = "--all" in arguments or "--url_external" in arguments
        if not failed:
            data.update(status=True, logs=[])
        return SimpleNamespace(stdout=json.dumps(data), stderr="", returncode=int(failed))

    monkeypatch.setattr(
        "ck.fetch.subprocess.run",
        run,
    )
    with pytest.raises(ValueError, match="Fixture failure"):
        verify_zim(Path("fixture.zim"))
    audit = verify_zim(Path("fixture.zim"), regeneration_only=True)
    assert audit["status"] is False and audit["regeneration_only"] is True
    assert "file_name" not in audit


def test_repair_allowance_cannot_mask_a_later_structural_failure(monkeypatch):
    def run(arguments, **kwargs):
        data = report("url_external" if "--all" in arguments else "checksum")
        return SimpleNamespace(stdout=json.dumps(data), stderr="", returncode=1)

    monkeypatch.setattr("ck.fetch.subprocess.run", run)
    with pytest.raises(ValueError, match="structural checks failed"):
        verify_zim(Path("fixture.zim"), regeneration_only=True, allow_broken_links=True)


def test_broken_links_cannot_be_allowed_for_shipped_archives():
    with pytest.raises(ValueError, match="restricted to regeneration"):
        verify_zim(Path("fixture.zim"), allow_broken_links=True)


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


def test_draft_selection_has_about_150_unique_articles_from_both_references():
    selection = Topics.model_validate(read_yaml(ROOT / "catalog/medpdf_topics.yaml"))
    count = len(selection.topics)
    assert count >= 150
    assert len({topic.id for topic in selection.topics}) == count
    assert len({(topic.source, topic.title) for topic in selection.topics}) == count
    assert {topic.source for topic in selection.topics} == {"wikimed_en_nopic", "wikem_en_nopic"}


def test_medical_selection_cannot_claim_review_without_a_named_reviewer_and_date():
    data = read_yaml(ROOT / "catalog/medpdf_topics.yaml")
    with pytest.raises(ValueError, match="named reviewer and date"):
        Topics.model_validate({**data, "status": "reviewed"})


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
