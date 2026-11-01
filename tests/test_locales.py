import hashlib
import json
import re
from pathlib import Path

import pytest
from pypdf import PdfReader

from ck.assemble import _copy_core
from ck.config import load_config
from ck.core import build_core
from ck.locales import display_defaults, edition_for
from ck.render import content_file, verify_translation_inputs

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def editions(tmp_path_factory):
    output = tmp_path_factory.mktemp("editions")
    files = build_core(ROOT, load_config(ROOT), output, 946684800)
    return output, files


def test_all_editions_have_phone_print_fonts_and_localized_readme(editions, tmp_path):
    output, files = editions
    config = load_config(ROOT)
    assert len(files) == 38
    lines = _copy_core(ROOT, config, output, tmp_path)
    assert len(lines) == 15
    for language in config.languages:
        edition = edition_for(ROOT, language, config)
        assert edition.readme.format(folder=language.name) in lines
        assert (tmp_path / "1_START" / language.name / "01_START_phone.pdf").is_file()
        html = (output / language.code / "01_START_phone.html").read_text()
        assert f'dir="{language.dir}"' in html
        assert edition.translation_footer in html
        encoded = re.search(r'id="coordination-defaults">(.*?)</script>', html, re.S).group(1)
        assert json.loads(encoded) == config.defaults.model_dump()
        pdf = PdfReader(output / language.code / "01_START_phone.pdf")
        assert pdf.trailer["/Root"]["/Lang"] == language.code
        for page in pdf.pages:
            assert page.extract_text().strip()
            for font in page["/Resources"]["/Font"].values():
                assert "+CK" in str(font.get_object()["/BaseFont"])


def test_spanish_full_edition_and_every_page_notice(editions):
    output, _ = editions
    assert len(PdfReader(output / "es/02_CARD.pdf").pages) == 2
    assert len(PdfReader(output / "es/03_TAGS.pdf").pages) == 1
    for path in (output / "es").glob("*.pdf"):
        for page in PdfReader(path).pages:
            assert "Traducciónautomáticasinrevisar." in "".join(page.extract_text().split())


def test_spanish_active_sections_match_english_without_the_future_section():
    sections = {
        code: {path.name for path in (ROOT / "content" / code / "start").glob("*.md")}
        for code in ("en", "es")
    }
    assert sections["es"] == sections["en"]
    assert len(sections["en"]) == 12
    assert not any(name.startswith("10-") for name in sections["en"])
    for code in sections:
        assert (ROOT / "content" / code / "future/10-offline-ai.md").is_file()


def test_translation_rejects_changed_coordination_default():
    config = load_config(ROOT)
    spanish = next(item for item in config.languages if item.code == "es")
    display_defaults(ROOT, spanish, config)
    config.defaults.meetings.if_nobody_there = "Changed original instruction"
    with pytest.raises(ValueError, match="Retranslate changed default"):
        display_defaults(ROOT, spanish, config)


def test_spanish_source_provenance_detects_changed_protocol(tmp_path):
    for path in (ROOT / "content/es").rglob("*.md"):
        header, _ = content_file(path)
        assert header.source_inputs
        verify_translation_inputs(ROOT, header)
    source = tmp_path / "content/en/protocol.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "---\ntitle: Test\nstatus: draft\nreviewer: null\nreviewed_on: null\n---\nOld"
    )
    header, _ = content_file(source)
    header.source_inputs = {"content/en/protocol.md": hashlib.sha256(b"Old").hexdigest()}
    verify_translation_inputs(tmp_path, header)
    source.write_text(source.read_text().replace("Old", "Changed clinical guidance"))
    with pytest.raises(ValueError, match="Retranslate changed source"):
        verify_translation_inputs(tmp_path, header)
