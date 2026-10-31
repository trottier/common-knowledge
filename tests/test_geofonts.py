from pathlib import Path

import pytest
from pypdf import PdfReader

from ck.config import load_config
from ck.geofonts import font_ids, require_glyphs
from ck.render import font_files, render_pdf

ROOT = Path(__file__).resolve().parents[1]


def test_geographic_fonts_cover_source_scripts_and_fail_on_missing_characters():
    language = load_config(ROOT).languages[0]
    latin = font_files(ROOT, language)
    names = ["ᏣᎳᎩ", "利达快递", "صيدلية"]
    with pytest.raises(ValueError, match="additional pinned font coverage"):
        require_glyphs(names, latin)
    fonts = font_files(ROOT, language, tuple(font_ids(ROOT)))
    require_glyphs(names, fonts)
    # Deliberately use an unassigned code point: no silent tofu substitution.
    with pytest.raises(ValueError, match=r"U\+0378"):
        require_glyphs(["Missing \u0378"], fonts)


def test_geographic_scripts_are_embedded_and_extractable_in_a_phone_pdf(tmp_path):
    source = tmp_path / "fixture.md"
    names = ["ᏣᎳᎩ", "利达快递", "صيدلية"]
    source.write_text(
        "---\ntitle: Synthetic multilingual place-name fixture\nstatus: draft\n"
        "reviewer: null\nreviewed_on: null\n---\n# Synthetic places\n\n" + "\n\n".join(names)
    )
    config = load_config(ROOT)
    output = tmp_path / "fixture.pdf"
    render_pdf(
        ROOT,
        config,
        source,
        config.languages[0],
        "phone",
        output,
        946684800,
        fallback_ids=tuple(font_ids(ROOT)),
    )
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert all(name in text for name in names[:2])
    # RTL extractors can reverse Arabic runs. Require every source letter.
    assert set(names[2]) <= set(text)
    resources = [
        font.get_object() for page in reader.pages for font in page["/Resources"]["/Font"].values()
    ]
    assert len(resources) >= 4
