import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from ck.publication import build_site, check_source_archive, prepare_release, write_catalog_lock

ROOT = Path(__file__).resolve().parents[1]


def test_archive_api_downloads_are_identified_by_content_and_sources_include_submodules(tmp_path):
    import io
    import tarfile
    from types import SimpleNamespace

    from ck.publication import corresponding_sources, source_archive_extension

    source = tmp_path / ("a" * 64)
    with tarfile.open(source, "w:gz") as archive:
        payload = b"Synthetic corresponding source"
        member = tarfile.TarInfo("project/source.txt")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    assert source_archive_extension(source) == ".tar.gz"
    items = {
        "project": SimpleNamespace(id="project", inputs=["submodule"]),
        "submodule": SimpleNamespace(id="submodule", inputs=[]),
    }
    app = SimpleNamespace(source_id="project")
    assert [item.id for item in corresponding_sources(items, app)] == ["project", "submodule"]
    items["submodule"].inputs = ["project"]
    with pytest.raises(ValueError, match="cycle"):
        list(corresponding_sources(items, app))


def test_release_review_reports_every_marker_and_never_changes_sources(tmp_path):
    from ck.fetch import digest
    from ck.review import markers, write_release_review

    source = ROOT / "content/en/start/09-medical.md"
    source = next((ROOT / "content/en/start").glob("*medical*")) if not source.exists() else source
    before = digest(source)
    output = tmp_path / "review.md"
    write_release_review(ROOT, output)
    report = output.read_text()
    for marker in markers(ROOT):
        assert marker["marker"] in report
        assert f"{marker['path']}:{marker['line']}" in report
    assert "v0.1.0 is incomplete" in report and "named human" in report
    assert digest(source) == before


def test_unreviewed_sources_cannot_create_release_assets(tmp_path):
    output = tmp_path / "release"
    with pytest.raises(ValueError, match="Release blocked"):
        prepare_release(
            ROOT,
            tmp_path / "core",
            tmp_path / "images",
            tmp_path / "cache",
            output,
            946684800,
            "0" * 40,
        )
    assert not output.exists()


def test_catalog_lock_is_stable_and_records_inputs(tmp_path):
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    write_catalog_lock(ROOT, first, 946684800)
    write_catalog_lock(ROOT, second, 946684800)
    assert first.read_bytes() == second.read_bytes()
    data = json.loads(first.read_text())
    assert data["config_sha256"]["config/defaults.yaml"]
    assert next(item for item in data["items"] if item["id"] == "base_model")["sha256"]


def test_verification_site_labels_unpublished_files_and_uses_no_active_resources(tmp_path):
    output = tmp_path / "site"
    build_site(ROOT, [], output, "trottier/common-knowledge")
    soup = BeautifulSoup((output / "index.html").read_text(), "html.parser")
    assert "No published release files" in soup.get_text()
    assert "sha256sum FILE" in soup.get_text()
    assert "certutil -hashfile FILE SHA256" in soup.get_text()
    assert not soup.select("script, iframe, img, video, audio, link[href], [src]")
    assert (output / ".nojekyll").exists()


def test_verification_downloads_are_built_from_validated_release_metadata(tmp_path):
    manifest = tmp_path / "release.json"
    data = {
        "version": "0.1.0",
        "profile": "dev",
        "commit": "0" * 40,
        "files": [{"name": "es-START.pdf", "size_bytes": 123, "sha256": "a" * 64}],
    }
    manifest.write_text(json.dumps(data))
    output = tmp_path / "site"
    build_site(ROOT, [manifest], output, "trottier/common-knowledge")
    soup = BeautifulSoup((output / "index.html").read_text(), "html.parser")
    anchor = soup.find("a", string="es-START.pdf")
    assert (
        anchor["href"]
        == "https://github.com/trottier/common-knowledge/releases/download/v0.1.0/es-START.pdf"
    )
    data["files"][0]["name"] = "../outside.pdf"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Unsafe"):
        build_site(ROOT, [manifest], tmp_path / "bad-site", "trottier/common-knowledge")


def test_source_archives_cannot_be_html_renamed_as_zip(tmp_path):
    import zipfile

    source = tmp_path / "source"
    source.write_text("<html>Permission denied</html>")
    with pytest.raises(zipfile.BadZipFile):
        check_source_archive(source, ".zip")
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("source/LICENSE", "Synthetic license fixture")
    check_source_archive(source, ".zip")


def test_full_site_rejects_partial_or_unrepeated_builds(tmp_path):
    image = {
        "image": "fixture.img",
        "compressed": "fixture.img.zst",
        "manifest": "fixture.MANIFEST.SHA256",
        "sha256": "a" * 64,
        "compressed_sha256": "b" * 64,
        "manifest_sha256": "c" * 64,
        "image_size_bytes": 1024,
        "compressed_size_bytes": 100,
    }
    data = {
        "version": "0.1.0",
        "profile": "full",
        "commit": "0" * 40,
        "reproduced": True,
        "variants": list(range(1, 9)),
        "images": [{**image, "variant": n} for n in range(1, 9)],
    }
    manifest = tmp_path / "full.json"
    manifest.write_text(json.dumps(data))
    build_site(ROOT, [], tmp_path / "site", "trottier/common-knowledge", [manifest])
    assert (
        "All eight variants matched independent builds"
        in (tmp_path / "site/index.html").read_text()
    )
    data["reproduced"] = False
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="all eight reproducible"):
        build_site(ROOT, [], tmp_path / "invalid", "trottier/common-knowledge", [manifest])


@pytest.mark.parametrize("include_snapshot", [False, True])
def test_release_assets_bind_images_to_core_and_check_every_sidecar(
    tmp_path, monkeypatch, include_snapshot
):
    from ck.catalog import Item
    from ck.config import load_config
    from ck.fetch import digest

    config = load_config(ROOT)
    config.build.source_date_epoch = 946684800
    monkeypatch.setattr("ck.publication.require_release_ready", lambda root: None)
    monkeypatch.setattr("ck.publication.load_config", lambda root: config)
    items = {}
    cache = tmp_path / "cache"
    if include_snapshot:
        cache.mkdir()
        payload = cache / "fixture"
        payload.write_bytes(b"Synthetic source snapshot; never shipped.")
        source_checksum = digest(payload)
        payload.rename(cache / source_checksum)
        common = dict(
            title="Synthetic fixture",
            version="1",
            size_bytes=(cache / source_checksum).stat().st_size,
            sha256=source_checksum,
            license="CC0-1.0",
            attribution="Original test fixture",
            license_proof_url="https://example.invalid/license",
            placement="hub_only",
            dest="build/fixture",
            profiles=["sample"],
        )
        items["source"] = Item(
            id="source", family="docs", url="https://example.invalid/source", **common
        )
        items["wikem_en_nopic"] = Item(
            id="wikem_en_nopic",
            family="generated",
            inputs=["source"],
            pipeline_version="fixture-v1",
            **common,
        )
    monkeypatch.setattr("ck.publication.load_catalog", lambda *args: items)
    monkeypatch.setattr("ck.core.verify_core", lambda *args: None)
    core, images = tmp_path / "core", tmp_path / "images"
    core.mkdir()
    images.mkdir()
    (core / "en").mkdir()
    (core / "en/fixture.pdf").write_bytes(b"Synthetic PDF payload for packaging, never shipped")
    (core / "core-manifest.json").write_text(
        json.dumps({"languages": [language.code for language in config.languages]})
    )
    built = {
        "profile": "dev",
        "commit": "0" * 40,
        "source_date_epoch": 946684800,
        "version": config.build.version,
        "variants": list(range(1, 9)),
        "core_manifest_sha256": digest(core / "core-manifest.json"),
        "images": [],
    }
    for number in range(1, 9):
        base = f"common-knowledge-{config.build.version}-variant-{number}-dev"
        compressed, manifest = base + ".img.zst", base + ".MANIFEST.SHA256"
        (images / compressed).write_bytes(b"Synthetic compressed image payload")
        (images / manifest).write_text("Synthetic file manifest")
        record = {
            "variant": number,
            "compressed": compressed,
            "compressed_sha256": digest(images / compressed),
            "sha256": "a" * 64,
            "manifest_sha256": digest(images / manifest),
        }
        built["images"].append(record)
        for filename, checksum in (
            (compressed, record["compressed_sha256"]),
            (base + ".img", record["sha256"]),
            (manifest, record["manifest_sha256"]),
        ):
            (images / (filename + ".sha256")).write_text(f"{checksum}  {filename}\n")
    (tmp_path / "build-manifest.json").write_text(json.dumps(built))
    output = tmp_path / "release"
    result = prepare_release(ROOT, core, images, tmp_path / "cache", output, 946684800, "0" * 40)
    assert sum(entry["kind"] == "dev-image" for entry in result["files"]) == 8
    if include_snapshot:
        from ck.sourcebundle import restore_sources

        bundle = next(entry for entry in result["files"] if entry["kind"] == "source-data")
        restored = tmp_path / "restored-sources"
        restore_sources(
            items, ["wikem_en_nopic"], output / bundle["name"], restored, bundle["sha256"]
        )
        assert (restored / source_checksum).read_bytes() == (cache / source_checksum).read_bytes()
    for line in (output / "SHA256SUMS").read_text().splitlines():
        checksum, filename = line.split("  ", 1)
        assert digest(output / filename) == checksum
    (images / (built["images"][0]["compressed"] + ".sha256")).write_text(
        "b" * 64 + "  stale.img.zst\n"
    )
    with pytest.raises(ValueError, match="differs from its hash"):
        prepare_release(
            ROOT, core, images, tmp_path / "cache", tmp_path / "bad", 946684800, "0" * 40
        )
    assert not (tmp_path / "bad").exists()
