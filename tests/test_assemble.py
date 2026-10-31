import os
from pathlib import Path

import pytest

from ck.assemble import assemble, check_manifest, write_manifest
from ck.config import load_config
from ck.core import verify_core, write_core_manifest
from ck.drive_safety import executable_allowed, validate_tree
from ck.image import build_image, run
from ck.planner import plan_variants

ROOT = Path(__file__).resolve().parents[1]
EPOCH = 946684800


@pytest.mark.parametrize(
    "path,allowed",
    [
        ("9_LOCAL_LLM/Start Local LLM - Windows.bat", True),
        ("9_AI_ASSISTANT/Start AI.bat", False),
        ("6_VIDEOS_AND_IN_DEPTH/in_depth/repair/laptop/tool.exe", True),
        ("6_VIDEOS_AND_IN_DEPTH/topics/medical/tool.exe", False),
        ("2_VIDEOS/android/VLC.apk", True),
    ],
)
def test_revised_executable_layout(path, allowed):
    assert executable_allowed(path) is allowed


def test_planner_fails_on_overflow_and_unconfirmed_capacity():
    config = load_config(ROOT)
    plans = plan_variants(config, {}, "dev", 1024)
    assert len(plans) == 8 and all(plan.fits for plan in plans)
    assert not any(plan.fits for plan in plan_variants(config, {}, "dev", 1024**3))
    with pytest.raises(ValueError, match="unconfirmed"):
        plan_variants(config, {}, "full", 1024)


def test_manifest_detects_tampering_and_extra_files(tmp_path):
    (tmp_path / "README.TXT").write_text("Fixture")
    write_manifest(tmp_path)
    check_manifest(tmp_path)
    (tmp_path / "README.TXT").write_text("Changed")
    with pytest.raises(ValueError, match="checksum"):
        check_manifest(tmp_path)
    write_manifest(tmp_path)
    (tmp_path / "EXTRA.TXT").write_text("Extra")
    with pytest.raises(ValueError, match="file set"):
        check_manifest(tmp_path)


def test_disguised_executable_rejected(tmp_path):
    folder = tmp_path / "4_PHONE_PACK"
    folder.mkdir()
    (folder / "document.pdf").write_bytes(b"MZfixture")
    with pytest.raises(ValueError, match="Executable"):
        validate_tree(tmp_path)


def test_fat_case_collision_rejected(tmp_path):
    (tmp_path / "File.txt").write_text("one")
    (tmp_path / "file.txt").write_text("two")
    with pytest.raises(ValueError, match="collision"):
        validate_tree(tmp_path)


def test_core_cache_cannot_hide_stale_sources_or_changed_output(tmp_path):
    folder = tmp_path / "en"
    folder.mkdir()
    pdf = folder / "01_START_phone.pdf"
    pdf.write_bytes(b"PDF payload fixture; not a rendering test")
    write_core_manifest(ROOT, tmp_path, EPOCH, ["en"], "dev")
    verify_core(ROOT, tmp_path, EPOCH, "dev")
    pdf.write_bytes(b"Modified")
    with pytest.raises(ValueError, match="changed"):
        verify_core(ROOT, tmp_path, EPOCH, "dev")


def test_assemble_dev_backup_and_manifest(tmp_path):
    core = tmp_path / "core"
    (core / "en").mkdir(parents=True)
    for name in ("01_START_phone.pdf", "01_START_print.pdf", "02_CARD.pdf", "03_TAGS.pdf"):
        (core / "en" / name).write_bytes(b"File payload fixture; not a PDF rendering test")
    write_core_manifest(ROOT, core, EPOCH, ["en"], "dev")
    tree = assemble(
        ROOT,
        load_config(ROOT),
        core,
        tmp_path / "tree",
        1,
        "dev",
        tmp_path / "cache",
        tmp_path / "generated",
        EPOCH,
    )
    check_manifest(tree)
    primary = tree / "1_START/English/01_START_phone.pdf"
    backup = tree / "BACKUP/1_START/English/01_START_phone.pdf"
    assert primary.read_bytes() == backup.read_bytes()
    assert "DEVELOPMENT" in (tree / "README.TXT").read_text()
    assert all(path.stat().st_mtime == EPOCH for path in tree.rglob("*"))


def test_image_roundtrip_hidden_backup_and_reproducibility(tmp_path):
    tree = tmp_path / "tree"
    files = {
        "README.TXT": "Filesystem test fixture",
        "1_START/Español/01_START_phone.pdf": "Unicode path payload",
        "BACKUP/1_START/العربية/01_START_phone.pdf": "Arabic folder payload",
    }
    for name, text in files.items():
        path = tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    write_manifest(tree)
    config = load_config(ROOT)
    first = build_image(tree, tmp_path / "first", config, 1, "dev", EPOCH)
    for path in tree.rglob("*"):
        os.utime(path, (EPOCH + 100, EPOCH + 100))
    second = build_image(tree, tmp_path / "second", config, 1, "dev", EPOCH)
    assert first["sha256"] == second["sha256"]
    assert first["compressed_sha256"] == second["compressed_sha256"]
    attributes = run(["mattrib", "-i", first["image"], "::/BACKUP"], EPOCH).stdout
    assert "H" in attributes.split("::")[0]
