import os
from pathlib import Path

import pytest

from ck.assemble import assemble, check_manifest, core_size, write_manifest
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
        ("9_OFFLINE_AI/Start Offline AI - Windows.bat", True),
        ("9_LOCAL_LLM/Start Local LLM - Windows.bat", False),
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


def test_planner_checks_source_pins_without_shipping_build_inputs():
    from ck.catalog import Item

    common = dict(
        version="fixture",
        license="US-PD",
        attribution="Synthetic test input",
        license_proof_url="https://example.org/license",
        profiles=["sample"],
    )
    source = Item(
        id="source",
        family="geodata",
        title="Unconfirmed source",
        url="https://example.org/source",
        size_bytes=5000,
        sha256="[[VERIFY: synthetic unconfirmed checksum]]",
        placement="hub_only",
        dest="build/input/",
        **common,
    )
    output = Item(
        id="output",
        family="generated",
        title="Derived output",
        size_bytes=100,
        sha256="0" * 64,
        placement="universal",
        dest="3_MAPS_AND_PLACES/atlas/",
        inputs=["source"],
        pipeline_version="fixture",
        **common,
    )
    plans = plan_variants(load_config(ROOT), {"source": source, "output": output}, "sample", 10)
    assert all(plan.known_total_bytes == 110 and plan.items == ["output"] for plan in plans)
    assert all(
        not plan.fits and any("source.sha256" in issue for issue in plan.blockers) for plan in plans
    )


def test_map_policy_switches_all_variants_before_other_capacity_changes():
    from ck.catalog import Item, Topics

    def item(identifier, size):
        return Item(
            id=identifier,
            family="docs",
            title="Synthetic map policy fixture",
            version="fixture",
            url="https://example.org/fixture",
            size_bytes=size,
            sha256="0" * 64,
            license="US-PD",
            attribution="Synthetic fixture",
            license_proof_url="https://example.org/license",
            placement="universal",
            dest="3_MAPS_AND_PLACES/",
            profiles=["full"],
        )

    config = load_config(ROOT)
    items = {
        key: item(key, size)
        for key, size in {
            "national_atlas": 10,
            "national_directory": 10,
            "osmand_prebuilt": 500,
            "android_roads_places": 100,
        }.items()
    }
    plans = plan_variants(config, items, "full", 10, 1000)
    assert all(plan.map_path == "prebuilt" and plan.fits for plan in plans)
    depth = item("medical_depth", 500)
    depth.placement = Topics(topics=["medical"])
    items[depth.id] = depth
    plans = plan_variants(config, items, "full", 10, 1000)
    assert all(plan.map_path == "roads_places" and plan.fits for plan in plans)
    assert all(
        "osmand_prebuilt" not in plan.items and "android_roads_places" in plan.items
        for plan in plans
    )
    items["osmand_prebuilt"].license = "[[VERIFY: synthetic unconfirmed terms]]"
    plans = plan_variants(config, items, "full", 10, 10000)
    assert all(plan.map_path == "roads_places" and plan.fits for plan in plans)


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


def test_imported_phone_pack_files_are_backed_up_and_counted_twice(tmp_path, monkeypatch):
    import hashlib

    from ck.catalog import Item

    core = tmp_path / "core"
    (core / "en").mkdir(parents=True)
    (core / "en/01_START_phone.pdf").write_bytes(b"Synthetic core payload, never shipped")
    write_core_manifest(ROOT, core, EPOCH, ["en"], "sample")
    payload = b"Synthetic imported document, never shipped"
    checksum = hashlib.sha256(payload).hexdigest()
    imported = Item(
        id="guide",
        family="docs",
        title="Synthetic guide",
        version="fixture",
        url="https://example.invalid/guide.pdf",
        size_bytes=len(payload),
        sha256=checksum,
        license="CC0-1.0",
        attribution="Synthetic fixture",
        license_proof_url="https://example.invalid/license",
        placement="universal",
        dest="4_PHONE_PACK/official/Guide.pdf",
        profiles=["sample"],
    )
    monkeypatch.setattr("ck.assemble.load_catalog", lambda *args: {imported.id: imported})
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / checksum).write_bytes(payload)
    config = load_config(ROOT)
    plan = plan_variants(config, {imported.id: imported}, "sample", core_size(core))[0]
    assert plan.known_total_bytes == core_size(core) + 2 * len(payload)
    tree = assemble(
        ROOT, config, core, tmp_path / "tree", 1, "sample", cache, tmp_path / "generated", EPOCH
    )
    assert (tree / "4_PHONE_PACK/official/Guide.pdf").read_bytes() == payload
    assert (tree / "BACKUP/4_PHONE_PACK/official/Guide.pdf").read_bytes() == payload
    check_manifest(tree)
