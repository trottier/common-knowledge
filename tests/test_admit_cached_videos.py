"""Admission is a fresh, auditable clone; it cannot overwrite cargo or release holds."""

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from ck.assemble import check_manifest, write_manifest
from ck.catalog import load_catalog
from ck.config import load_config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "cached_video_tool", ROOT / "tools/admit_cached_videos.py"
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def admission(tmp_path, monkeypatch):
    base = tmp_path / "base"
    for name in ("1_START/English/start.txt", "4_PHONE_PACK/English/card.txt", tool.INDEX_PATH):
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Unchanged synthetic base")
        backup = base / "BACKUP" / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, backup)
    (base / "README.TXT").write_text(
        "English\nStill missing: Android and laptop reader apps, mesh apps, videos,\n"
        "remaining counties\n"
    )
    (base / "VERIFY.TXT").write_text("Local fixture")
    checksum = write_manifest(base)
    provenance = tmp_path / "base.json"
    provenance.write_text(
        json.dumps({"manifest_sha256": checksum, "unrelated_history": "retain by reference"})
    )
    source = tmp_path / "packets"
    source.mkdir()
    bindings = {}
    for name in (
        "2_VIDEOS/clip.mp4",
        "2_VIDEOS/clip_SOURCE.TXT",
        "6_VIDEOS_AND_IN_DEPTH/topics/convening/clip.mp4",
        "6_VIDEOS_AND_IN_DEPTH/topics/convening/clip_SOURCE.TXT",
    ):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Unchanged synthetic packet " + name)
        bindings[name] = path
    # Authenticate real cached bytes separately in the intake audit. These fixtures isolate
    # cloning, preservation, and collisions from FFmpeg and external cargo downloads.
    monkeypatch.setattr(
        tool,
        "packets",
        lambda *args: (
            load_config(ROOT),
            bindings,
            {"historical_recipe": "unchanged", "review": "[[VERIFY: human playback]]"},
        ),
    )
    return dict(
        root=ROOT,
        cache=tmp_path / "cache",
        outputs={"synthetic": source},
        base=base,
        base_manifest_sha256=checksum,
        base_provenance=provenance,
        base_provenance_sha256=sha(provenance),
        output=tmp_path / "output",
        epoch=1793404800,
    )


def test_clone_preserves_all_other_bytes_and_does_not_embed_ancestor(admission):
    before = {
        p.relative_to(admission["base"]).as_posix(): p.read_bytes()
        for p in admission["base"].rglob("*")
        if p.is_file()
    }
    result = tool.admit(**admission)
    tree = admission["output"]
    for name, data in before.items():
        assert (admission["base"] / name).read_bytes() == data
        if name not in {
            tool.INDEX_PATH,
            "BACKUP/" + tool.INDEX_PATH,
            "MANIFEST.SHA256",
            "README.TXT",
            "VERIFY.TXT",
        }:
            assert (tree / name).read_bytes() == data
    assert not (tree / tool.INDEX_PATH).exists()
    assert not (tree / "BACKUP" / tool.INDEX_PATH).exists()
    for path in next(iter(admission["outputs"].values())).rglob("*"):
        if path.is_file():
            assert (
                tree / path.relative_to(next(iter(admission["outputs"].values())))
            ).read_bytes() == path.read_bytes()
    assert "provenance_path" in result["base"] and "unrelated_history" not in result["base"]
    assert result["cached_videos"]["review"].startswith("[[VERIFY")
    assert result["normal_assembly_gates_changed"] is False
    assert all(int(p.stat().st_mtime) == admission["epoch"] for p in tree.rglob("*"))
    check_manifest(tree)


@pytest.mark.parametrize(
    "mutation",
    ["collision", "ancestor", "overwrite", "base-corrupt", "backup", "nested", "missing-index"],
)
def test_unsafe_clone_never_publishes(admission, mutation):
    base = admission["base"]
    if mutation == "collision":
        path = base / "2_VIDEOS/clip.mp4"
        path.parent.mkdir()
        path.write_text("Existing file")
    elif mutation == "ancestor":
        admission["base_provenance"].write_text("{}")
    elif mutation == "overwrite":
        admission["output"].mkdir()
    elif mutation == "base-corrupt":
        (base / "README.TXT").write_text("Changed")
    elif mutation == "backup":
        (base / "BACKUP/1_START/English/start.txt").write_text("Wrong backup")
    elif mutation == "nested":
        admission["output"] = base / "nested"
    else:
        (base / tool.INDEX_PATH).unlink()
    if mutation in {"collision", "backup", "missing-index"}:
        admission["base_manifest_sha256"] = write_manifest(base)
        admission["base_provenance"].write_text(
            json.dumps({"manifest_sha256": admission["base_manifest_sha256"]})
        )
        admission["base_provenance_sha256"] = sha(admission["base_provenance"])
    with pytest.raises(ValueError):
        tool.admit(**admission)
    assert not admission["output"].exists() or mutation == "overwrite"


@pytest.mark.parametrize(
    "field,value",
    [
        ("license", "[[VERIFY: redistribution rights]]"),
        ("requires_legal", True),
        ("review", "[[VERIFY: unknown per-file rights]]"),
    ],
)
def test_packet_review_exception_never_waives_rights(tmp_path, monkeypatch, field, value):
    config = load_config(ROOT)
    items = load_catalog(ROOT, config)
    for key in tool.SELECTED:
        items[key] = items[key].model_copy(update={field: value})
    monkeypatch.setattr(tool, "load_catalog", lambda *args: items)
    with pytest.raises(ValueError, match="Unresolved source rights or pins"):
        tool.packets(ROOT, tmp_path, {key: tmp_path for key in tool.SELECTED}, 1793404800)
