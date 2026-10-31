import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("extract_atlas", ROOT / "tools/extract_atlas.py")
extract_atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_atlas)


def test_local_batch_verifies_whole_input_once_and_rejects_tampering(tmp_path, monkeypatch):
    root = tmp_path / "recipe"
    (root / "catalog").mkdir(parents=True)
    (root / "pipelines/atlas").mkdir(parents=True)
    (root / "pipelines/atlas/settings.yaml").write_text("maxzoom: 14\n")
    source = tmp_path / "source.pmtiles"
    source.write_bytes(b"PMTiles\x03Synthetic source")
    catalog = [
        {
            "id": "protomaps_planet",
            "url": "https://example.invalid/planet.pmtiles",
            "size_bytes": source.stat().st_size,
            "sha256": extract_atlas.sha(source),
        }
    ]
    (root / "catalog/geodata.yaml").write_text(json.dumps(catalog))
    (root / "catalog/buildtools.yaml").write_text(
        json.dumps([{"id": "pmtiles_x64", "sha256": "0" * 64}])
    )
    jobs = []
    for state in ("RI", "DE"):
        directory = tmp_path / state
        directory.mkdir()
        (directory / "region.geojson").write_text('{"type":"FeatureCollection","features":[]}')
        path = directory / "jobs.json"
        path.write_text(
            json.dumps({"state": state, "epoch": 946684800, "pages": [{}], "inputs": {}})
        )
        jobs.append(path)
    calls = []
    real_sha = extract_atlas.sha

    def hashed(path):
        calls.append(path)
        return real_sha(path)

    def run(command, **kwargs):
        if command[1] == "extract":
            assert Path(command[2]) == source
            Path(command[3]).write_bytes(b"Synthetic bounded PMTiles output")

    monkeypatch.setattr(extract_atlas, "sha", hashed)
    monkeypatch.setattr(extract_atlas.subprocess, "run", run)
    monkeypatch.setattr(extract_atlas.platform, "machine", lambda: "x86_64")
    argv = [
        "extract_atlas",
        "--root",
        str(root),
        "--jobs",
        *map(str, jobs),
        "--source-file",
        str(source),
        "--output",
        str(tmp_path / "outputs"),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    extract_atlas.main()
    assert calls.count(source) == 1
    for state in ("RI", "DE"):
        metadata = json.loads((tmp_path / "outputs" / state / "generation.json").read_text())
        assert metadata["complete"] is True
        assert str(tmp_path) not in (tmp_path / "outputs" / state / "source.json").read_text()
    batch = json.loads((tmp_path / "outputs/generation.json").read_text())
    assert batch["complete"] is True
    assert {entry["path"] for entry in batch["files"]} == {"DE.pmtiles", "RI.pmtiles"}
    assert batch["inputs"] == {"protomaps_planet": catalog[0]["sha256"], "pmtiles_x64": "0" * 64}
    for entry in batch["files"]:
        assert real_sha(tmp_path / "outputs/files" / entry["path"]) == entry["sha256"]
    source.write_bytes(source.read_bytes()[:-1] + b"!")
    monkeypatch.setattr(sys, "argv", [*argv[:-1], str(tmp_path / "bad")])
    with pytest.raises(ValueError, match="whole-file"):
        extract_atlas.main()
    assert not (tmp_path / "bad").exists()
