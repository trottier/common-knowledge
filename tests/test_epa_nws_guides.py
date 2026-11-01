"""Bind the guide intake to its measured files and unresolved rights gates."""

import json
from pathlib import Path

from ck.catalog import load_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_guide_catalog_matches_individual_pdf_intake_and_preserves_review_holds():
    catalog = load_catalog(ROOT)
    evidence = json.loads((ROOT / "docs/evidence/epa-nws-guide-intake.json").read_text())
    for identifier, measured in evidence["pdfs"].items():
        item = catalog[identifier]
        assert (item.url, item.sha256, item.size_bytes) == (
            measured["url"],
            measured["sha256"],
            measured["size_bytes"],
        )
        assert measured["page_count"] == len(measured["page_dimensions_pt"])
        assert not measured["encrypted"]
        assert not measured["root_open_action"]
        assert not measured["embedded_attachments"]
        assert not measured["sensitive_dictionary_keys"]
        assert item.blockers(release=True)
        assert "[[VERIFY:" in item.review
    assert evidence["source_content_rewritten"] is False
    assert evidence["rendered_review"]["physical_phone_readability_approved"] is False


def test_epa_illustration_rights_gap_keeps_both_different_editions_unplaced():
    catalog = load_catalog(ROOT)
    english = catalog["epa_emergency_disinfection_en_2017"]
    spanish = catalog["epa_emergency_disinfection_es_2015"]
    assert english.version != spanish.version
    assert english.sha256 != spanish.sha256
    for item in [english, spanish]:
        assert item.placement == "hub_only"
        assert item.requires_legal
        assert item.legal_reviewer is None
        assert "[[VERIFY:" in item.license
        assert "[[VERIFY:" in item.license_proof_url
        assert any("named legal sign-off" in blocker for blocker in item.blockers())


def test_nws_placeholder_replacement_keeps_epa_gap_and_prior_retirements_explicit():
    catalog = load_catalog(ROOT)
    history = json.loads((ROOT / "docs/proposals/retired-intake-placeholders.yaml").read_text())
    retired = {entry["placeholder"]["id"]: entry for entry in history["retired"]}
    prior = {
        "fema_guides",
        "ready_guides",
        "radio_question_pools",
        "howto_documents_1",
        "howto_documents_2",
        "education",
    }
    assert prior <= retired.keys()
    assert not (prior | {"nws_guides"}) & catalog.keys()
    assert "epa_guides" in catalog
    assert "epa_guides" not in retired
    assert set(retired["nws_guides"]["concrete_replacements"]) == {
        "nws_thunderstorm_safety_en_2018",
        "nws_weather_radio_quadfold_en_2025",
    }
    for identifier in retired["nws_guides"]["concrete_replacements"]:
        item = catalog[identifier]
        assert item.license == "US-PD"
        assert item.license_proof_url == "https://www.weather.gov/owlie/publication_brochures"
        assert item.blockers(release=True)
