"""Selected book references keep revision attribution and safe offline PDF paths."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from ck.catalog import load_catalog, safe_path
from ck.referencepacks import Pack, build_reference_pack, filename, selections

ROOT = Path(__file__).resolve().parents[1]


def test_selection_needs_canonical_unique_archive_paths_and_named_review():
    values = selections(ROOT)["reference_howto_1"].model_dump()
    for changes in (
        {"paths": ["Article", "Article"]},
        {"paths": ["../Article"]},
        {"paths": ["/Article"]},
        {"status": "reviewed"},
    ):
        with pytest.raises(ValidationError):
            Pack.model_validate({**values, **changes})


def test_long_non_latin_titles_get_distinct_fat_safe_names():
    first = filename(1, "Book/" + "中文:?<>" * 100 + "a")
    second = filename(1, "Book/" + "中文:?<>" * 100 + "b")
    assert first != second
    assert len(first) < 90
    safe_path(first)
    safe_path(second)


def test_release_checks_reference_selection_even_if_catalog_markers_are_cleared(monkeypatch):
    from ck.catalog import Item
    from ck.review import release_blockers

    monkeypatch.setattr("ck.review.markers", lambda root: [])
    monkeypatch.setattr(Item, "blockers", lambda *args, **kwargs: [])
    blockers = release_blockers(ROOT)
    for identifier in selections(ROOT):
        assert any(identifier in line and "named human" in line for line in blockers)


def fixture_archive(monkeypatch, *, redirect=False, provenance=True):
    import libzim.reader

    footer = """<div class="zim-footer"><a title="Last edited on 2026-10-01"
    href="https://en.wikibooks.org/w/index.php?oldid=123">Wikibooks</a>
    <a href="https://creativecommons.org/licenses/by-sa/4.0/">License</a></div>"""
    raw = (
        '<div id="mw-content-text"><div class="mw-parser-output">'
        '<h2 id="example">Synthetic background</h2><p>Fixture value: 12.5.</p>'
        '<img src="https://example.invalid/track" alt="Synthetic missing figure">'
        "</div></div>" + (footer if provenance else "")
    ).encode()
    source = SimpleNamespace(
        title="Synthetic reference, never shipped", mimetype="text/html", content=raw
    )
    entry = SimpleNamespace(is_redirect=redirect, get_item=lambda: source)
    monkeypatch.setattr(
        libzim.reader, "Archive", lambda path: SimpleNamespace(get_entry_by_path=lambda path: entry)
    )
    monkeypatch.setattr(
        "ck.referencepacks.archive_source", lambda *args: (Path("fixture.zim"), {"synthetic": True})
    )


def pack_fixture(monkeypatch):
    from contextlib import nullcontext

    from ck.config import load_config
    from ck.render import font_files

    monkeypatch.setattr(
        "ck.referencepacks.MathRenderer",
        lambda *args: nullcontext(
            SimpleNamespace(
                versions="\nSynthetic unused math renderer",
                notice="Synthetic renderer notice; never shipped",
            )
        ),
    )
    catalog = load_catalog(ROOT)
    pack = selections(ROOT)["reference_med_lib"].model_copy(update={"paths": ["Synthetic"]})
    monkeypatch.setattr("ck.referencepacks.selections", lambda root: {"reference_med_lib": pack})
    monkeypatch.setattr("ck.referencepacks.read_yaml", lambda path: {"fonts": ["noto_sans"]})
    catalog["reference_med_lib"].inputs = [pack.source, "noto_sans", "mathjax_mml_svg"]
    font = font_files(ROOT, load_config(ROOT).languages[0])[0]
    monkeypatch.setattr("ck.referencepacks.cached_input", lambda *args: font)
    return catalog


def test_real_phone_pdf_repeat_keeps_attribution_and_omission_notice(tmp_path, monkeypatch):
    from pypdf import PdfReader

    fixture_archive(monkeypatch)
    catalog = pack_fixture(monkeypatch)
    results = []
    for suffix in ("a", "b"):
        results.append(
            build_reference_pack(
                ROOT, catalog, tmp_path, tmp_path / suffix, 946684800, "reference_med_lib"
            )
        )
    assert results[0] == results[1]
    first = next((tmp_path / "a/files").glob("*.pdf"))
    second = next((tmp_path / "b/files").glob("*.pdf"))
    assert first.read_bytes() == second.read_bytes()
    pdf = PdfReader(first)
    text = " ".join(" ".join(page.extract_text() for page in pdf.pages).split())
    assert "12.5" in text and "2026-10-01" in text and "Creative Commons" in text
    assert "Synthetic missing figure" in text and "If 911 does not answer" in text
    assert "review pending" in text and pdf.outline
    assert float(pdf.pages[0].mediabox.width) == pytest.approx(90 / 25.4 * 72, abs=0.02)


@pytest.mark.parametrize("redirect,provenance", [(True, True), (False, False)])
def test_bad_source_cannot_publish_a_partial_reference_pack(
    tmp_path, monkeypatch, redirect, provenance
):
    fixture_archive(monkeypatch, redirect=redirect, provenance=provenance)
    catalog = pack_fixture(monkeypatch)
    with pytest.raises(ValueError):
        build_reference_pack(
            ROOT, catalog, tmp_path, tmp_path / "output", 946684800, "reference_med_lib"
        )
    assert not (tmp_path / "output").exists()
