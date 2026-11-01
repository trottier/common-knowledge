import hashlib

import pytest

from ck.catalog import Collection, Item
from ck.licenses import parse_license_expression
from ck.publication import release_sources, ships_gpl


def fixture_item(**updates):
    value = {
        "id": "fixture",
        "family": "docs",
        "title": "Synthetic license fixture; never shipped",
        "url": "https://example.invalid/source.tar.gz",
        "version": "test",
        "size_bytes": 1,
        "sha256": hashlib.sha256(b"x").hexdigest(),
        "license": "MIT",
        "attribution": "Synthetic test fixture",
        "license_proof_url": "https://example.invalid/license",
        "placement": "universal",
        "dest": "7_LAPTOP/fixture",
        "profiles": ["sample"],
    }
    value.update(updates)
    return Item.model_validate(value)


@pytest.mark.parametrize(
    ("value", "supported"),
    [
        ("MIT", True),
        ("CC-BY-3.0 AND CC0-1.0", True),
        ("CC-BY-3.0 AND CC-BY-ND-3.0", False),
        ("mit OR apache-2.0", True),
        ("MIT/Apache-2.0", True),
        ("Apache-2.0 / MIT", True),
        ("(MIT OR Apache-2.0) AND Unicode-3.0", True),
        ("MIT AND (Apache-2.0 OR Unknown)", True),
        ("MIT OR Unknown AND Unknown", True),
        ("(MIT OR Unknown) AND Unknown", False),
        ("Unknown OR MIT AND Unknown", False),
        ("Unknown AND MIT", False),
        ("Unknown", False),
        ("(MIT OR (Unknown AND (Zlib OR Unlicense)))", True),
        ("Apache-2.0 WITH LLVM-exception", False),
        ("Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT", True),
        ("MIT WITH Unknown-exception OR Unlicense", True),
        ("(MIT OR Apache-2.0) AND LGPL-3.0-only", True),
        ("LGPL-3.0-or-later OR MPL-2.0", True),
        ("GPL-2.0+", False),
        ("GPL-2.0+ OR MIT", True),
        ("GPL-2.0-or-later", True),
        ("GPL-2.0-or-later AND OLDAP-2.8", True),
        ("Apache-2.0 WITH Swift-exception", True),
        ("apache-2.0 WITH swift-exception", True),
        ("GPL-3.0-only WITH Swift-exception", False),
        ("MIT WITH Swift-exception", False),
        ("Apache-2.0 WITH Unknown-exception", False),
        ("Apache-2.0 WITH Swift-exception AND Unknown", False),
        ("Apache-2.0 WITH Swift-exception OR Unknown", True),
    ],
)
def test_license_expression_choices_and_precedence(value, supported):
    assert parse_license_expression(value).supported is supported


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "()",
        "(MIT",
        "MIT)",
        "MIT OR",
        "OR MIT",
        "MIT AND AND Apache-2.0",
        "MIT Apache-2.0",
        "MIT and Apache-2.0",
        "MIT XOR Apache-2.0",
        "MIT OR (MIT AND)",
        "MIT OR Apache-2.0 WITH",
        "MIT OR Apache-2.0 WITH (LLVM-exception)",
        "MIT OR (Apache-2.0) WITH LLVM-exception",
        "MIT WITH LLVM-exception WITH Other-exception",
        "MIT OR Apache-2.0 WITH LLVM-exception+",
        "MIT OR Apache-2.0;Unknown",
        "MIT // Apache-2.0",
        "MIT OR [[VERIFY: license]]",
        "MIT OR DocumentRef-x:LicenseRef-y",
        "MIT OR GPL-2.0 +",
        "(" * 65 + "MIT" + ")" * 65,
        "MIT OR " * 300 + "MIT",
        "x" * 4097,
    ],
)
def test_malformed_or_unsupported_syntax_never_uses_a_known_or_arm(value):
    with pytest.raises(ValueError):
        parse_license_expression(value)
    assert any(
        "redistribution review" in issue for issue in fixture_item(license=value or " ").blockers()
    )


def test_all_license_ids_are_retained_for_contextual_gates_without_rewriting():
    declaration = "mit / (MPL-2.0 OR Apache-2.0 WITH LLVM-exception)"
    result = parse_license_expression(declaration)
    assert result.identifiers == {"MIT", "MPL-2.0", "Apache-2.0"}
    assert result.requires_source is True
    item = fixture_item(license=declaration, review="[[VERIFY: human pin and license review]]")
    before = item.model_dump()
    assert any("human pin and license review" in issue for issue in item.blockers())
    assert item.model_dump() == before


@pytest.mark.parametrize(
    "license",
    [
        "MIT OR (CC-BY-NC-SA-3.0)",
        "(cc-by-nc-sa-3.0 OR MIT)",
        "MIT OR CC-BY-NC-ND-4.0",
    ],
)
def test_permissive_choice_never_bypasses_existing_noncommercial_permission_gate(license):
    item = fixture_item(license=license)
    assert any("written emergency-use license" in issue for issue in item.blockers())
    assert any("named human" in issue for issue in item.blockers())
    item.permission_proof_url = "https://example.invalid/synthetic-grant"
    assert any("named human" in issue for issue in item.blockers())
    item.requires_legal = True
    assert any("named legal sign-off" in issue for issue in item.blockers())


def test_named_legal_and_verify_proof_holds_survive_supported_expressions():
    item = fixture_item(
        license="MIT OR Apache-2.0",
        requires_legal=True,
        license_proof_url="[[VERIFY: exact per-file proof]]",
    )
    problems = item.blockers(release=True)
    assert any("exact per-file proof" in issue for issue in problems)
    assert any("named legal sign-off" in issue for issue in problems)


def test_grouped_ready_reprint_alternative_cannot_escape_its_original_document_scope():
    item = fixture_item(license="(MIT OR LicenseRef-FEMA-Ready-Reprint)")
    assert any("Ready reprint terms" in issue for issue in item.blockers())
    item.url = "https://www.ready.gov/sites/default/files/synthetic.pdf"
    item.license_proof_url = "https://www.ready.gov/publications"
    assert item.blockers() == []
    item.placement = Collection(collection="school")
    assert any("Ready reprint terms" in issue for issue in item.blockers())


@pytest.mark.parametrize(
    "license",
    [
        "(GPL-3.0-only OR MIT)",
        "Apache-2.0 OR (GPL-3.0-or-later AND MIT)",
        "MPL-2.0",
        "(MPL-2.0 OR MIT)",
        "LGPL-3.0-only",
        "Apache-2.0 OR LGPL-3.0-or-later",
        "GPL-2.0-or-later",
        "Apache-2.0 WITH Swift-exception AND GPL-2.0-or-later",
    ],
)
def test_copyleft_app_alternatives_require_and_collect_corresponding_sources(
    monkeypatch, tmp_path, license
):
    app = fixture_item(id="application", family="binaries", license=license)
    assert any("source archive" in issue for issue in app.blockers(release=True))
    assert ships_gpl(app) is True
    source = fixture_item(id="application_source", placement="hub_only", inputs=["dependency"])
    dependency = fixture_item(id="dependency", placement="hub_only")
    app.source_id = source.id
    app.source_url = source.url
    source.source_for = app.id
    assert app.blockers(release=True) == []
    events = []
    monkeypatch.setattr("ck.publication.require_release_ready", lambda root: events.append("gate"))
    monkeypatch.setattr("ck.publication.load_config", lambda root: None)
    monkeypatch.setattr(
        "ck.publication.load_catalog",
        lambda *args: {item.id: item for item in (app, source, dependency)},
    )
    monkeypatch.setattr("ck.fetch.fetch", lambda item, cache: events.append(item.id))
    release_sources(tmp_path, tmp_path / "cache")
    assert events == ["gate", "application_source", "dependency"]
    app.placement = "hub_only"
    assert ships_gpl(app) is False


def test_malformed_binary_declaration_cannot_silently_skip_source_collection():
    item = fixture_item(family="binaries", license="MIT OR (GPL-3.0-only")
    with pytest.raises(ValueError):
        ships_gpl(item)


@pytest.mark.parametrize(
    "declaration", ["OLDAP-2.8", "GPL-2.0-or-later", "Apache-2.0 WITH Swift-exception"]
)
def test_recognized_source_terms_preserve_original_declarations_and_review_holds(declaration):
    item = fixture_item(
        license=declaration,
        review="[[VERIFY: exact source notices and correspondence]]",
        requires_legal=True,
    )
    before = item.model_dump()
    assert parse_license_expression(declaration).supported
    problems = item.blockers(release=True)
    assert any("exact source notices and correspondence" in issue for issue in problems)
    assert any("named legal sign-off" in issue for issue in problems)
    assert item.model_dump() == before
