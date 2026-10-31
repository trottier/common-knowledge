import json
from pathlib import Path

import pytest

from ck.build import build_profile, check_profile
from ck.core import write_core_manifest

ROOT = Path(__file__).resolve().parents[1]
EPOCH = 946684800


def test_sample_preflight_lists_unresolved_inputs_before_writing(tmp_path):
    with pytest.raises(ValueError, match="not ready"):
        build_profile(ROOT, tmp_path / "sample", tmp_path, tmp_path, "sample", [1, 3], EPOCH)
    assert not (tmp_path / "sample").exists()
    assert len(check_profile(ROOT, "dev")) == 8


def test_profile_build_repeats_document_and_filesystem_builds(tmp_path, monkeypatch):
    calls = []

    def fixture_core(root, config, output, epoch, profile):
        calls.append(output)
        (output / "en").mkdir(parents=True)
        (output / "en/01_START_phone.pdf").write_bytes(b"Synthetic filesystem payload")
        write_core_manifest(root, output, epoch, ["en"], profile)

    monkeypatch.setattr("ck.build.build_core", fixture_core)
    result = build_profile(
        ROOT,
        tmp_path / "dev",
        tmp_path / "cache",
        tmp_path / "generated",
        "dev",
        [3, 1],
        EPOCH,
        reproduce=True,
    )
    assert len(calls) == 2 and calls[0] != calls[1]
    assert result["reproduced"] and result["variants"] == [1, 3]
    for image in result["images"]:
        assert not (tmp_path / "dev/images" / image["image"]).exists()
        assert (tmp_path / "dev/images" / image["compressed"]).stat().st_size == image[
            "compressed_size_bytes"
        ]
    assert json.loads((tmp_path / "dev/build-manifest.json").read_text()) == result
    assert not list((tmp_path / "dev").glob(".ck-variant-*"))


def test_profile_build_never_reports_mismatched_repeated_images(tmp_path, monkeypatch):
    def fixture_core(root, config, output, epoch, profile):
        (output / "en").mkdir(parents=True)
        (output / "en/01_START_phone.pdf").write_bytes(output.name.encode())
        write_core_manifest(root, output, epoch, ["en"], profile)

    monkeypatch.setattr("ck.build.build_core", fixture_core)
    with pytest.raises(ValueError, match="not reproducible"):
        build_profile(ROOT, tmp_path / "dev", tmp_path, tmp_path, "dev", [1], EPOCH, reproduce=True)
    assert not (tmp_path / "dev/build-manifest.json").exists()
