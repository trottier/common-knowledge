"""Standalone source references must not create citation-only body pages."""

import re
from pathlib import Path

import pytest
from pypdf import PdfReader

from ck.config import load_config
from ck.core import bundle_sections
from ck.render import render_pdf

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("page_format", ["phone", "print"])
def test_vietnamese_quickstart_keeps_citation_with_its_list(page_format, tmp_path):
    config = load_config(ROOT)
    language = next(item for item in config.languages if item.code == "vi")
    source = ROOT / "content/vi/start/01-quickstart.md"
    bundle = tmp_path / "START.md"
    bundle_sections([source], bundle)
    target = tmp_path / f"quickstart-{page_format}.pdf"
    render_pdf(ROOT, config, bundle, language, page_format, target, 1793404800, profile="sample")
    reader = PdfReader(target)
    texts = [page.extract_text() for page in reader.pages]
    # Learn the PDF's extracted footer once: complex-script glyph mappings do
    # not always round-trip to the original Unicode, even when visibly correct.
    footer = re.sub(r"\s+\d+\s*$", "", texts[0].strip().splitlines()[-1])
    assert footer
    for number, text in enumerate(texts, 1):
        assert footer in text
        body = text.replace(footer, "")
        body = re.sub(r"\s*\d+\s*$", "", body).strip()
        assert body, f"Empty body on page {number}"
        assert not re.fullmatch(r"(?:\s*\[[a-z0-9_]+\]\s*)+", body), (
            f"Citation-only body on page {number}: {body!r}"
        )
    assert "source-project_spec" in reader.named_destinations
    titles, pending = [], list(reader.outline)
    while pending:
        entry = pending.pop()
        if isinstance(entry, list):
            pending.extend(entry)
        else:
            titles.append(entry.title)
    assert "Hướng dẫn bắt đầu nhanh" in titles
    html = target.with_suffix(".html").read_text()
    assert 'id="source-project_spec"' in html
    assert "Common Knowledge specification" in html
