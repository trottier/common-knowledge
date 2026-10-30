import json
import re
from pathlib import Path

from pypdf import PdfReader

from ck.config import load_config, read_yaml
from ck.core import build_core
from ck.render import content_file

ROOT = Path(__file__).resolve().parents[1]


def test_all_original_citations_resolve_and_review_status_is_explicit():
    sources = read_yaml(ROOT / "content/sources.yaml")
    sections = sorted((ROOT / "content/en/start").glob("*.md"))
    assert len(sections) == 13
    for path in (ROOT / "content").rglob("*.md"):
        header, body = content_file(path)
        if header.status == "reviewed":
            assert header.reviewer and header.reviewed_on
        assert set(re.findall(r"\[@([a-z0-9_]+)\]", body)) <= sources.keys()


def test_core_layout_and_canonical_defaults(tmp_path):
    config = load_config(ROOT)
    files = build_core(ROOT, config, tmp_path, 946684800)
    assert len(files) == 6
    card = tmp_path / "en/02_CARD.pdf"
    assert len(PdfReader(card).pages) == 2
    assert len(PdfReader(tmp_path / "en/03_TAGS.pdf").pages) == 1
    for name in ("01_START_phone.html", "02_CARD.html"):
        text = (tmp_path / "en" / name).read_text()
        encoded = re.search(r'id="coordination-defaults">(.*?)</script>', text, re.S).group(1)
        assert json.loads(encoded) == config.defaults.model_dump()
    card_html = card.with_suffix(".html").read_text()
    assert 'href="#source-' not in card_html
    assert 'href="https://www.ecfr.gov/' in card_html
    outline = PdfReader(tmp_path / "en/01_START_phone.pdf").outline
    assert outline
