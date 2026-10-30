import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont
from pypdf import PdfReader
from weasyprint.urls import FatalURLFetchingError

from ck.config import load_config
from ck.render import OfflineFetcher, font_files, render_html, render_pdf

ROOT = Path(__file__).resolve().parents[1]
EPOCH = int(datetime(2000, 1, 1, tzinfo=UTC).timestamp())


@pytest.mark.parametrize(
    ("page_format", "width", "height"),
    [("phone", 90 / 25.4 * 72, 160 / 25.4 * 72), ("print", 612, 792)],
)
def test_pdf_dimensions_links_bookmarks_and_dates(tmp_path, page_format, width, height):
    config = load_config(ROOT)
    language = next(x for x in config.languages if x.code == "en")
    output = tmp_path / f"{page_format}.pdf"
    render_pdf(
        ROOT, config, ROOT / "content/en/start/01-use.md", language, page_format, output, EPOCH
    )
    pdf = PdfReader(output)
    assert float(pdf.pages[0].mediabox.width) == pytest.approx(width, abs=0.02)
    assert float(pdf.pages[0].mediabox.height) == pytest.approx(height, abs=0.02)
    assert pdf.outline
    assert any(page.get("/Annots") for page in pdf.pages)
    assert pdf.metadata.creation_date.year == 2000
    assert pdf.trailer["/Root"]["/MarkInfo"]["/Marked"]
    embedded = {
        str(font.get_object()["/BaseFont"])
        for page in pdf.pages
        for font in page["/Resources"]["/Font"].values()
    }
    assert embedded and all("+CK" in name for name in embedded)


def test_pdf_reproducible_and_verify_highlighted(tmp_path):
    config = load_config(ROOT)
    language = config.languages[0]
    source = ROOT / "content/en/start/01-use.md"
    hashes = []
    for name in ("a.pdf", "b.pdf"):
        output = render_pdf(ROOT, config, source, language, "phone", tmp_path / name, EPOCH)
        hashes.append(hashlib.sha256(output.read_bytes()).hexdigest())
    assert hashes[0] == hashes[1]
    assert '<mark class="verify">' in render_html(ROOT, config, source, language, "phone", EPOCH)


def test_rtl_shaping_and_pdf(tmp_path):
    config = load_config(ROOT)
    arabic = next(x for x in config.languages if x.code == "ar")
    text = "مرحبا بالعالم"
    font_path = font_files(ROOT, arabic)[0]
    result = subprocess.run(
        ["hb-shape", str(font_path), text, "--no-glyph-names", "--output-format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    glyphs = [glyph["g"] for glyph in json.loads(result.stdout)]
    assert all(glyph != 0 for glyph in glyphs)
    font = TTFont(font_path)
    naive = [font.getGlyphID(font.getBestCmap()[ord(c)]) for c in text][::-1]
    assert glyphs != naive
    output = render_pdf(
        ROOT, config, ROOT / "tests/fixtures/rtl.md", arabic, "phone", tmp_path / "rtl.pdf", EPOCH
    )
    assert 'dir="rtl"' in output.with_suffix(".html").read_text()
    assert PdfReader(output).trailer["/Root"]["/Lang"] == "ar"


@pytest.mark.parametrize("url", ["https://example.com/image.png", "file:///etc/passwd"])
def test_renderer_cannot_fetch_network_or_unrelated_files(tmp_path, url):
    with pytest.raises(FatalURLFetchingError):
        OfflineFetcher([tmp_path]).fetch(url)
