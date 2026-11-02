"""Catalog edition names are resolved from configuration without altering publisher PDFs."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ck.assemble import destination
from ck.catalog import Item, load_catalog, safe_path
from ck.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return {
        "id": "fixture",
        "family": "docs",
        "title": "Synthetic test fixture",
        "url": "https://example.invalid/test.pdf",
        "version": "test",
        "size_bytes": 1,
        "sha256": "0" * 64,
        "license": "CC0-1.0",
        "attribution": "Synthetic fixture",
        "license_proof_url": "https://example.invalid/license",
        "placement": "universal",
        "dest": "4_PHONE_PACK/{edition}/Official guides/Test - {edition}.pdf",
        "language": "ar",
        "profiles": ["full"],
    }


@pytest.mark.parametrize("code", ["ar", "zh-Hant", "en", "es"])
def test_edition_paths_follow_configuration_names_in_folder_and_filename(code):
    config = load_config(ROOT).model_copy(deep=True)
    language = next(language for language in config.languages if language.code == code)
    language.name += " — configured test name"
    item = Item.model_validate({**sample(), "language": code})
    expected = f"4_PHONE_PACK/{language.name}/Official guides/Test - {language.name}.pdf"
    assert destination(item, config, 1) == expected
    safe_path(expected)


def test_language_is_optional_for_existing_items_but_required_for_edition_placeholder():
    value = sample()
    value.pop("language")
    with pytest.raises(ValidationError, match="require a language"):
        Item.model_validate(value)
    value["dest"] = "4_PHONE_PACK/original.pdf"
    assert Item.model_validate(value).language is None


@pytest.mark.parametrize("code", ["../ar", "", "ar Arabic"])
def test_malformed_language_code_is_rejected(code):
    with pytest.raises(ValidationError):
        Item.model_validate({**sample(), "language": code})


def test_unknown_configured_edition_fails_catalog_load_and_destination(tmp_path):
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog/docs.yaml").write_text(json.dumps([{**sample(), "language": "zz"}]))
    config = load_config(ROOT).model_copy(update={"local_llm": None})
    with pytest.raises(ValueError, match="unknown language edition"):
        load_catalog(tmp_path, config)
    with pytest.raises(ValueError, match="unknown language edition"):
        destination(Item.model_validate({**sample(), "language": "zz"}), config, 1)


def test_all_forty_original_ready_guides_resolve_safely_with_preserved_grant():
    config = load_config(ROOT)
    family = json.loads((ROOT / "catalog/official_guides.yaml").read_text())
    assert len(family) == 40
    languages = {language.code: language.name for language in config.languages}
    paths = []
    for raw in family:
        item = Item.model_validate(raw)
        path = destination(item, config, 1)
        assert path.startswith(f"4_PHONE_PACK/{languages[item.language]}/Official guides/FEMA - ")
        assert path.endswith(f" - {languages[item.language]}.pdf")
        assert item.license == "LicenseRef-FEMA-Ready-Reprint"
        assert item.url.startswith("https://www.ready.gov/sites/default/files/")
        assert not [p for p in item.blockers() if not p.startswith(item.id + ".review:")]
        safe_path(path)
        paths.append(path)
    assert len(paths) == len(set(paths))
