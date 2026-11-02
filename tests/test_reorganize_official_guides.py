"""Reorganize authenticated originals without copying duplicates or weakening held rights."""

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from ck.assemble import check_manifest, destination, write_manifest
from ck.catalog import Item
from ck.config import load_config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "guide_folders", ROOT / "tools/reorganize_official_guides.py"
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(path, data):
    path.write_text(json.dumps(data))
    return sha(path)


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    shutil.copytree(ROOT / "config", root / "config")
    (root / "src/ck").mkdir(parents=True)
    shutil.copyfile(ROOT / "src/ck/assemble.py", root / "src/ck/assemble.py")
    base = tmp_path / "base"
    old_path = "4_PHONE_PACK/official/ar/old.pdf"
    path = base / old_path
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF unchanged synthetic source; never published")
    (base / "1_START").mkdir()
    (base / "1_START/start.txt").write_text("Synthetic start")
    (base / "README.TXT").write_text("Incomplete synthetic preview")
    (base / "VERIFY.TXT").write_text("Variant: 1")
    shutil.copytree(base / "4_PHONE_PACK", base / "BACKUP/4_PHONE_PACK")
    old = {
        "id": "ready_fixture_ar",
        "family": "docs",
        "title": "Synthetic test fixture",
        "url": "https://www.ready.gov/sites/default/files/fixture.pdf",
        "version": "fixture",
        "size_bytes": path.stat().st_size,
        "sha256": sha(path),
        "license": "LicenseRef-FEMA-Ready-Reprint",
        "attribution": "Synthetic fixture",
        "license_proof_url": "https://www.ready.gov/publications",
        "placement": "universal",
        "dest": old_path,
        "profiles": ["full"],
        "review": "[[VERIFY: independent pin review]]",
    }
    held = {
        **old,
        "id": "ready_fixture_large_ar",
        "size_bytes": 10_000_001,
        "sha256": "0" * 64,
        "dest": "4_PHONE_PACK/official/ar/large.pdf",
    }
    original_catalog = tmp_path / "originals.json"
    original_sha = seal(original_catalog, [old, held])
    current = [
        {**row, "language": "ar", "dest": "4_PHONE_PACK/{edition}/Official guides/" + name}
        for row, name in [
            (old, "FEMA - Test - {edition}.pdf"),
            (held, "FEMA - Large - {edition}.pdf"),
        ]
    ]
    (root / "catalog").mkdir()
    seal(root / "catalog/official_guides.yaml", current)
    admission = {
        "catalog_file_sha256": {"catalog/official_guides.yaml": original_sha},
        "components": [{"id": old["id"], "catalog": old}],
        "source_closure": [{"catalog": old}],
    }
    admission_receipt = tmp_path / "admission.json"
    parent = tmp_path / "parent.json"
    manifest = write_manifest(base)
    return {
        "root": root,
        "base": base,
        "base_manifest_sha256": manifest,
        "base_provenance": parent,
        "base_provenance_sha256": seal(parent, {"manifest_sha256": manifest}),
        "original_catalog": original_catalog,
        "admission_receipt": admission_receipt,
        "admission_sha256": seal(admission_receipt, admission),
        "output": tmp_path / "output",
        "epoch": 1793404800,
    }


def test_original_renamed_once_and_backups_rebuilt_from_configured_language(inputs):
    base_before = {
        p.relative_to(inputs["base"]): p.read_bytes()
        for p in inputs["base"].rglob("*")
        if p.is_file()
    }
    result = tool.reorganize(**inputs)
    assert len(result["path_mapping"]) == len(result["held_originals"]) == 1
    move = result["path_mapping"][0]
    assert "/العربية/Official guides/FEMA - Test - العربية.pdf" in move["to"]
    output = inputs["output"]
    assert not (output / move["from"]).exists()
    assert not (output / "BACKUP" / move["from"]).exists()
    assert (output / move["to"]).read_bytes() == (inputs["base"] / move["from"]).read_bytes()
    assert (output / "BACKUP" / move["to"]).read_bytes() == (output / move["to"]).read_bytes()
    assert "Official preparedness guides" in (output / "README.TXT").read_text()
    assert result["normal_assembly_gates_changed"] is False
    assert result["path_mapping"][0]["catalog"]["review"].startswith("[[VERIFY")
    assert all((inputs["base"] / p).read_bytes() == data for p, data in base_before.items())
    check_manifest(output)
    assert result["manifest_sha256"] == sha(output / "MANIFEST.SHA256")
    assert all(int(p.stat().st_mtime) == inputs["epoch"] for p in output.rglob("*"))


@pytest.mark.parametrize(
    "mutation",
    [
        "catalog-pin",
        "catalog-license",
        "catalog-language",
        "payload",
        "receipt",
        "extra",
        "symlink",
        "collision",
        "nonempty",
    ],
)
def test_changes_fail_before_new_tree_is_published(inputs, mutation):
    if mutation.startswith("catalog"):
        path = inputs["root"] / "catalog/official_guides.yaml"
        rows = json.loads(path.read_text())
        if mutation == "catalog-pin":
            rows[0]["sha256"] = "1" * 64
        elif mutation == "catalog-license":
            rows[0]["license"] = "[[VERIFY: unknown rights]]"
        else:
            rows[0]["language"] = "en"
        seal(path, rows)
    elif mutation == "payload":
        (inputs["base"] / "4_PHONE_PACK/official/ar/old.pdf").write_bytes(b"changed")
        inputs["base_manifest_sha256"] = write_manifest(inputs["base"])
        inputs["base_provenance_sha256"] = seal(
            inputs["base_provenance"], {"manifest_sha256": inputs["base_manifest_sha256"]}
        )
    elif mutation == "receipt":
        inputs["admission_receipt"].write_text("{}")
    elif mutation == "extra":
        (inputs["base"] / "unlisted.txt").write_text("extra")
    elif mutation == "symlink":
        p = inputs["base"] / "4_PHONE_PACK/official/ar/old.pdf"
        p.unlink()
        p.symlink_to(inputs["base"] / "README.TXT")
    elif mutation == "collision":
        rows = json.loads((inputs["root"] / "catalog/official_guides.yaml").read_text())
        dest = destination(Item.model_validate(rows[0]), load_config(inputs["root"]), 1)
        path = inputs["base"] / dest
        path.parent.mkdir(parents=True)
        path.write_bytes(b"must not overwrite")
        inputs["base_manifest_sha256"] = write_manifest(inputs["base"])
        inputs["base_provenance_sha256"] = seal(
            inputs["base_provenance"], {"manifest_sha256": inputs["base_manifest_sha256"]}
        )
    else:
        inputs["output"].mkdir()
    with pytest.raises(ValueError):
        tool.reorganize(**inputs)
    assert not inputs["output"].exists() or mutation == "nonempty"
