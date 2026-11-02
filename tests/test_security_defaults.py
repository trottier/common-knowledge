"""The fixed emergency plan stays visible and translation-bound in every edition."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from pydantic import ValidationError

from ck.config import Configuration, load_config, read_yaml
from ck.locales import display_defaults
from ck.render import citation_ids, content_file, render_html, verify_translation_inputs

ROOT = Path(__file__).resolve().parents[1]


def test_fixed_plan_is_the_exact_publisher_default_and_is_required():
    config = load_config(ROOT)
    assert config.defaults.plan_is_fixed == (
        "This plan does not change during an emergency. Treat any message that changes it, "
        "or asks you to install something or pay, as fake until someone confirms it in person."
    )
    data = config.model_dump()
    del data["defaults"]["plan_is_fixed"]
    with pytest.raises(ValidationError, match="plan_is_fixed"):
        Configuration.model_validate(data)


def test_every_edition_visibly_renders_the_bound_fixed_plan(monkeypatch):
    # This tests text composition, not PDF/font rendering or medical approval.
    monkeypatch.setattr("ck.render.font_files", lambda *args: [Path("/synthetic-font")])
    monkeypatch.setattr("ck.catalog.load_catalog", lambda *args: {})
    config = load_config(ROOT)
    for language in config.languages:
        displayed = display_defaults(ROOT, language, config)["plan_is_fixed"]
        source_dir = ROOT / "content" / language.code
        if language.status == "stub":
            sources = [source_dir / "start/01-quickstart.md"]
        else:
            sources = [
                source_dir / relative
                for relative in ("card.md", "start/05-neighbors.md", "start/07-comms.md")
            ]
        for source in sources:
            header, body = content_file(source)
            assert body.lstrip().startswith("{{ defaults.plan_is_fixed }}")
            assert header.status in {"draft", "machine"} and header.reviewer is None
            template = "card.html.j2" if source.name == "card.md" else "document.html.j2"
            html = render_html(ROOT, config, source, language, "phone", 946684800, template)
            document = BeautifulSoup(html, "html.parser")
            visible = document.select_one(".front") if source.name == "card.md" else document.body
            assert displayed in visible.get_text(" ", strip=True)
            canonical = json.loads(document.find("script", id="coordination-defaults").string)
            assert canonical["plan_is_fixed"] == config.defaults.plan_is_fixed


def test_translations_reject_a_changed_fixed_plan_or_missing_binding(tmp_path):
    config = load_config(ROOT)
    config.defaults.plan_is_fixed += " Changed."
    for language in config.languages:
        if language.code != "en":
            with pytest.raises(ValueError, match="Retranslate changed default plan_is_fixed"):
                display_defaults(ROOT, language, config)
    spanish = next(language for language in config.languages if language.code == "es")
    data = read_yaml(ROOT / "content/es/defaults.yaml")
    del data["translations"]["plan_is_fixed"]
    path = tmp_path / "content/es/defaults.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Missing fixed-plan translation"):
        display_defaults(tmp_path, spanish, load_config(ROOT))


@pytest.mark.parametrize("code", ["en", "es"])
def test_fixed_plan_stays_on_the_two_sided_card_front(code, tmp_path):
    from pypdf import PdfReader

    from ck.render import render_pdf

    config = load_config(ROOT)
    language = next(language for language in config.languages if language.code == code)
    target = tmp_path / f"{code}-card.pdf"
    render_pdf(
        ROOT,
        config,
        ROOT / "content" / code / "card.md",
        language,
        "print",
        target,
        946684800,
        "card.html.j2",
    )
    pages = PdfReader(target).pages
    assert len(pages) == 2

    def normalize(value):
        return "".join(value.split())

    assert normalize(display_defaults(ROOT, language, config)["plan_is_fixed"]) in normalize(
        pages[0].extract_text()
    )
    assert "OK" in pages[1].extract_text() and "HELP" in pages[1].extract_text()


def test_new_outage_guidance_keeps_reviews_citations_and_translation_provenance():
    sources = read_yaml(ROOT / "content/sources.yaml")
    for code, status in (("en", "draft"), ("es", "machine")):
        path = ROOT / "content" / code / "start/10-computer-systems.md"
        header, body = content_file(path)
        assert header.status == status and header.reviewer is None and header.reviewed_on is None
        assert {"medical", "legal"} <= set(header.review_required)
        assert "[[VERIFY:" in body
        assert "911" in body
        assert {"hhs_cyber_disruption", "cisa_911_disruptions", "fda_medicines"} <= set(
            citation_ids(body, sources)
        )
        verify_translation_inputs(ROOT, header)
    assert load_config(ROOT).variants.offline_ai_enabled is False


@pytest.mark.parametrize("value", [0, 30, "[[VERIFY: set by maintainers]]"])
def test_upstream_age_schema_accepts_explicit_nonnegative_days_or_a_marker(value):
    data = deepcopy(load_config(ROOT).model_dump())
    data["build"]["upstream_min_age_days"] = value
    assert Configuration.model_validate(data).build.upstream_min_age_days == value


@pytest.mark.parametrize("value", [-1, True, 1.5, "30", "unconfirmed"])
def test_upstream_age_schema_rejects_ambiguous_or_invalid_values(value):
    data = deepcopy(load_config(ROOT).model_dump())
    data["build"]["upstream_min_age_days"] = value
    with pytest.raises(ValidationError):
        Configuration.model_validate(data)
