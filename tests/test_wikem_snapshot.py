import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("snapshot_wikem", ROOT / "tools/snapshot_wikem.py")
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


def test_capture_binds_cached_response_to_request_and_exact_bytes(tmp_path):
    target = tmp_path / "response.json"
    raw = b'{"synthetic": true}'
    target.write_bytes(raw)
    target.with_suffix(".json.request.json").write_text(
        json.dumps(
            {
                "url": snapshot.API + "?synthetic",
                "sha256": snapshot.checksum(raw),
            }
        )
    )
    assert snapshot.capture(snapshot.API + "?synthetic", target, 1) == raw
    with pytest.raises(ValueError, match="different request"):
        snapshot.capture(snapshot.API + "?other", target, 1)
    target.write_bytes(b'{"changed": true}')
    with pytest.raises(ValueError, match="different request"):
        snapshot.capture(snapshot.API + "?synthetic", target, 1)


def test_publisher_denial_excludes_only_the_named_page_without_trying_other_endpoints(tmp_path):
    raw = json.dumps(
        {
            "error": {
                "code": "accessdenied",
                "info": "You are not allowed to view Synthetic restricted page.",
            }
        }
    ).encode()
    error = snapshot.AccessDenied(snapshot.API + "?action=query&revids=20", raw)
    candidates = [
        {"pageid": 1, "title": "Synthetic public page"},
        {"pageid": 2, "title": "Synthetic restricted page"},
    ]
    exclusions = {}
    snapshot.record_denial(error, candidates, exclusions, tmp_path / "denials.json")
    assert set(exclusions) == {2}
    assert exclusions[2]["response_sha256"] == snapshot.checksum(raw)
    with pytest.raises(ValueError, match="does not identify one"):
        snapshot.record_denial(error, candidates[:1], {}, tmp_path / "ambiguous.json")
    assert not (tmp_path / "ambiguous.json").exists()


def test_listing_acquisition_follows_publisher_continuation_and_pins_each_response(
    tmp_path, monkeypatch
):
    urls = []

    def capture(url, target, delay):
        urls.append(url)
        result = {"query": {"pages": {}}}
        if len(urls) == 1:
            result["continue"] = {"gapcontinue": "Beta", "continue": "gapcontinue||"}
        raw = json.dumps(result).encode()
        target.write_bytes(raw)
        return raw

    monkeypatch.setattr(snapshot, "capture", capture)
    snapshot.collect_listings(tmp_path / "listings", 1)
    pins = json.loads((tmp_path / "listings/pins.json").read_text())
    assert len(pins) == len(urls) == 2 and "gapcontinue=Beta" in urls[1]
    for pin in pins:
        raw = (tmp_path / "listings" / pin["file"]).read_bytes()
        assert pin["sha256"] == snapshot.checksum(raw) and pin["size_bytes"] == len(raw)


def test_snapshot_keeps_publisher_tables_and_pins_exact_revision_responses(tmp_path, monkeypatch):
    listing = tmp_path / "listing"
    listing.mkdir()
    raw = json.dumps(
        {
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "ns": 0,
                        "contentmodel": "wikitext",
                        "title": "Synthetic article",
                        "lastrevid": 10,
                    }
                }
            }
        }
    ).encode()
    (listing / "0000.json").write_bytes(raw)
    (listing / "pins.json").write_text(
        json.dumps(
            [
                {
                    "file": "/acquisition/0000.json",
                    "url": snapshot.API + "?action=query",
                    "size_bytes": len(raw),
                    "sha256": snapshot.checksum(raw),
                }
            ]
        )
    )
    table = '<div class="mw-parser-output"><table><tr><td>Synthetic cell</td></tr></table></div>'

    def response(url, target, delay):
        if url == snapshot.LICENSE:
            return b"License: https://creativecommons.org/licenses/by-sa/4.0/"
        if "action=query" in url:
            return json.dumps(
                {
                    "query": {
                        "pages": {
                            "1": {
                                "pageid": 1,
                                "revisions": [
                                    {
                                        "revid": 10,
                                        "timestamp": "2000-01-01T00:00:00Z",
                                        "slots": {"main": {"*": "Synthetic source"}},
                                    }
                                ],
                            }
                        }
                    }
                }
            ).encode()
        return json.dumps({"parse": {"pageid": 1, "revid": 10, "text": {"*": table}}}).encode()

    monkeypatch.setattr(snapshot, "capture", response)
    snapshot.snapshot(listing, tmp_path / "out", tmp_path / "cache", 1, "2000-01-01")
    items = json.loads((tmp_path / "out/catalog.json").read_text())
    article = next(item for item in items if item["id"] == "wikem_article_1")
    stored = (tmp_path / "cache" / article["sha256"]).read_bytes()
    assert json.loads(stored)["parse"]["text"]["*"] == table
    assert "oldid=10" in article["url"] and article["placement"] == "hub_only"
    assert snapshot.checksum(stored) == article["sha256"]
    assert "[[VERIFY" in article["review"]
    report = json.loads((tmp_path / "out/report.json").read_text())
    assert report["articles"] == 1 and report["redirects"] == 0


def test_wikem_cli_dispatches_with_the_selected_cache_and_epoch(monkeypatch, tmp_path, capsys):
    from ck.cli import main

    calls = []

    def build(root, items, cache, output, epoch):
        calls.append((root, cache, output, epoch))
        return {"fixture": True}

    monkeypatch.setattr("ck.wikem.build_archive", build)
    assert (
        main(
            [
                "--root",
                str(ROOT),
                "wikem",
                "--cache",
                str(tmp_path / "cache"),
                "--output",
                str(tmp_path / "out"),
                "--epoch",
                "946684800",
            ]
        )
        == 0
    )
    assert calls == [(ROOT, tmp_path / "cache", tmp_path / "out", 946684800)]
    assert json.loads(capsys.readouterr().out) == {"fixture": True}
