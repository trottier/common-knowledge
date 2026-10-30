import hashlib
import io
from pathlib import Path

import pytest
from pydantic import ValidationError

from ck.catalog import Item, load_catalog, safe_path
from ck.config import load_config
from ck.fetch import HttpsRedirects, fetch, verify_format
from ck.review import release_blockers, require_release_ready

ROOT = Path(__file__).resolve().parents[1]


def item_for(data=b"fixture"):
    return Item.model_validate(
        {
            "id": "fixture",
            "family": "docs",
            "title": "Test fixture, never shipped",
            "url": "https://example.invalid/fixture.txt",
            "version": "test",
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "license": "CC0-1.0",
            "attribution": "Test fixture",
            "license_proof_url": "https://example.invalid/license",
            "placement": "universal",
            "dest": "4_PHONE_PACK/fixture.txt",
            "profiles": ["dev"],
        }
    )


class Response(io.BytesIO):
    url = "https://example.invalid/fixture.txt"


def test_catalog_valid_but_release_fails_closed():
    items = load_catalog(ROOT, load_config(ROOT))
    assert {item.family for item in items.values()} >= {
        "fonts",
        "zim",
        "apk",
        "generated",
        "geodata",
    }
    assert {"bitchat_android", "briar_android", "wikem_en_nopic", "national_atlas"} <= items.keys()
    assert items["wikimed_en_nopic"].checksum_source_url.endswith(".meta4")
    assert release_blockers(ROOT)
    with pytest.raises(ValueError, match="Release blocked"):
        require_release_ready(ROOT)


@pytest.mark.parametrize(
    "path",
    [
        "../file",
        "x/../file",
        "/file",
        "C:/file",
        "x\\file",
        "x/CON.txt",
        "x/autorun.INF",
        "x/trailing.",
    ],
)
def test_unsafe_paths_rejected(path):
    with pytest.raises(ValueError):
        safe_path(path)


@pytest.mark.parametrize("field", ["sha256", "size_bytes", "placement", "license_proof_url"])
def test_catalog_missing_required_field_rejected(field):
    data = item_for().model_dump()
    del data[field]
    with pytest.raises(ValidationError):
        Item.model_validate(data)


def test_fetch_checks_bytes_and_repairs_corrupted_cache(tmp_path):
    item = item_for()
    checks = []

    def opener(*args, **kwargs):
        return Response(b"fixture")

    path = fetch(item, tmp_path, opener=opener, format_check=lambda i, p: checks.append(p))
    assert path.name == item.sha256
    path.write_bytes(b"corrupt")
    assert (
        fetch(item, tmp_path, opener=opener, format_check=lambda i, p: None).read_bytes()
        == b"fixture"
    )
    assert checks


@pytest.mark.parametrize("payload", [b"short", b"too-long-fixture", b"wrong!!"])
def test_bad_download_never_enters_cache(tmp_path, payload):
    with pytest.raises(ValueError):
        fetch(
            item_for(),
            tmp_path,
            opener=lambda *a, **k: Response(payload),
            format_check=lambda i, p: None,
        )
    assert list(tmp_path.iterdir()) == []


def test_unconfirmed_download_is_rejected_before_network(tmp_path):
    item = item_for().model_copy(update={"sha256": "[[VERIFY: checksum]]"})

    def opener(*args, **kwargs):
        pytest.fail("Unconfirmed item attempted network access")

    with pytest.raises(ValueError, match="unconfirmed"):
        fetch(item, tmp_path, opener=opener)


def test_https_redirect_cannot_downgrade():
    with pytest.raises(ValueError, match="outside HTTPS"):
        HttpsRedirects().redirect_request(None, None, 302, "", {}, "http://example.invalid/file")


def test_apk_wrong_signer_rejected(monkeypatch, tmp_path):
    from types import SimpleNamespace

    item = item_for().model_copy(update={"family": "apk", "signer_cert_sha256": "a" * 64})
    monkeypatch.setattr(
        "ck.fetch.subprocess.run",
        lambda *a, **k: SimpleNamespace(
            stdout="Signer #1 certificate SHA-256 digest: " + "b" * 64 + "\n"
        ),
    )
    with pytest.raises(ValueError, match="signer"):
        verify_format(item, tmp_path / "fixture.apk")
