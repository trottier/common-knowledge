from pathlib import Path

import pytest

from ck.config import load_config, read_yaml
from ck.render import citation_ids, content_file, render_html
from ck.review import release_blockers, write_release_review

ROOT = Path(__file__).resolve().parents[1]


def test_every_original_edition_has_resolvable_citation_syntax():
    sources = read_yaml(ROOT / "content/sources.yaml")
    for source in (ROOT / "content").rglob("*.md"):
        _, body = content_file(source)
        citation_ids(body, sources)


@pytest.mark.parametrize("reference", ["[@]", "[@source", "[@ONE]", "[@one; @two]"])
def test_malformed_citations_cannot_render(tmp_path, reference):
    source = tmp_path / "draft.md"
    source.write_text(
        "---\ntitle: Citation fixture\nstatus: draft\nreviewer: null\nreviewed_on: null\n"
        "---\n\nA claim. " + reference + "\n"
    )
    config = load_config(ROOT)
    with pytest.raises(ValueError, match="Malformed citation"):
        render_html(ROOT, config, source, config.languages[0], "phone", 946684800)


def test_separate_references_become_real_source_links(tmp_path):
    source = tmp_path / "draft.md"
    source.write_text(
        "---\ntitle: Citation fixture\nstatus: draft\nreviewer: null\nreviewed_on: null\n"
        "---\n\nA claim. [@cdc_generator] [@fema_utilities]\n"
    )
    config = load_config(ROOT)
    html = render_html(ROOT, config, source, config.languages[0], "phone", 946684800)
    assert 'href="#source-cdc_generator"' in html
    assert 'href="#source-fema_utilities"' in html
    assert "[@" not in html


@pytest.mark.parametrize("reference", ["[@unknown_source]", "[@one; @two]"])
def test_release_and_review_inventory_check_translated_citations(tmp_path, monkeypatch, reference):
    from ck import review

    monkeypatch.setattr(review, "load_config", lambda root: None)
    monkeypatch.setattr(review, "load_catalog", lambda root, config: {})
    source = tmp_path / "content/es/start/fixture.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "---\ntitle: Fuente de prueba\nstatus: machine\nreviewer: null\nreviewed_on: null\n"
        "---\n\nUna afirmación. " + reference + "\n"
    )
    problems = release_blockers(tmp_path)
    assert any("content/es/start/fixture.md: citations:" in problem for problem in problems)
    output = tmp_path / "report.md"
    write_release_review(tmp_path, output)
    assert "content/es/start/fixture.md: citations:" in output.read_text()
