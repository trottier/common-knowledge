"""Index attachment admission must preserve the base and reject stale inventories."""

import importlib.util
import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

from ck.assemble import check_manifest, write_manifest
from ck.fetch import digest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("attach_index", ROOT / "tools/attach_copy_index.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def pdf(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    writer.add_blank_page(width=90 * 72 / 25.4, height=160 * 72 / 25.4)
    writer.write(path)


@pytest.fixture
def inputs(tmp_path):
    base = tmp_path / "base"
    relative = "1_START/English/01_START_phone.pdf"
    pdf(base / relative)
    (base / "README.TXT").write_text("Synthetic incomplete local fixture")
    manifest = write_manifest(base)
    index = tmp_path / "index.pdf"
    pdf(index)
    metadata = {
        "target_path": tool.INDEX_PATH,
        "source_manifest_sha256": manifest,
        "epoch": 1793404800,
        "pages": 1,
        "pdf": {"sha256": digest(index), "size_bytes": index.stat().st_size},
        "indexed_files": [
            {
                "path": relative,
                "sha256": digest(base / relative),
                "size_bytes": (base / relative).stat().st_size,
            }
        ],
    }
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(metadata))
    provenance = tmp_path / "base-provenance.json"
    provenance.write_text(json.dumps({"manifest_sha256": manifest, "status": "draft fixture"}))
    return {
        "base": base,
        "index": index,
        "receipt": receipt,
        "receipt_sha256": digest(receipt),
        "output": tmp_path / "out",
        "base_provenance": provenance,
        "base_provenance_sha256": digest(provenance),
    }


def test_fresh_clone_keeps_payloads_backups_self_hash_rule_and_original_provenance(inputs):
    original = digest(inputs["base"] / "MANIFEST.SHA256")
    result = tool.attach(**inputs)
    out = inputs["output"]
    assert (out / tool.INDEX_PATH).read_bytes() == inputs["index"].read_bytes()
    assert (out / "BACKUP" / tool.INDEX_PATH).read_bytes() == inputs["index"].read_bytes()
    assert not (inputs["base"] / tool.INDEX_PATH).exists()
    assert digest(inputs["base"] / "MANIFEST.SHA256") == original
    assert result["base_provenance"]["status"] == "draft fixture"
    assert result["manifest_sha256"] == digest(out / "MANIFEST.SHA256")
    assert (out / "README.TXT").read_bytes() == (inputs["base"] / "README.TXT").read_bytes()
    check_manifest(out)
    assert "MANIFEST.SHA256" not in [
        line.split("  ", 1)[1] for line in (out / "MANIFEST.SHA256").read_text().splitlines()
    ]


@pytest.mark.parametrize(
    "mutation",
    ["manifest", "missing", "orphan", "duplicate", "index", "base", "receipt", "collision"],
)
def test_stale_or_inconsistent_inputs_never_publish(inputs, mutation):
    metadata = json.loads(inputs["receipt"].read_text())
    if mutation == "manifest":
        metadata["source_manifest_sha256"] = "0" * 64
    elif mutation == "missing":
        metadata["indexed_files"] = []
    elif mutation == "orphan":
        metadata["indexed_files"][0]["path"] = "missing.pdf"
    elif mutation == "duplicate":
        metadata["indexed_files"] *= 2
    elif mutation == "index":
        inputs["index"].write_bytes(b"changed")
    elif mutation == "base":
        (inputs["base"] / "README.TXT").write_text("changed")
    elif mutation == "collision":
        pdf(inputs["base"] / tool.INDEX_PATH)
        metadata["source_manifest_sha256"] = write_manifest(inputs["base"])
    inputs["receipt"].write_text(json.dumps(metadata))
    inputs["receipt_sha256"] = digest(inputs["receipt"]) if mutation != "receipt" else "0" * 64
    with pytest.raises(ValueError):
        tool.attach(**inputs)
    assert not inputs["output"].exists()


def test_existing_output_and_its_content_are_never_replaced(inputs):
    inputs["output"].mkdir()
    marker = inputs["output"] / "keep"
    marker.write_text("keep")
    with pytest.raises(ValueError, match="no overwrite"):
        tool.attach(**inputs)
    assert marker.read_text() == "keep"


def test_new_optional_format_policy_matches_index_and_preserves_companions(inputs):
    from tools.build_copy_index import inventory

    for name in [
        "5_MEDICAL_REFERENCE/book.zim",
        "3_MAPS_AND_PLACES/map.obf",
        "3_MAPS_AND_PLACES/source.osm.pbf",
        "3_MAPS_AND_PLACES/SOURCE.TXT",
    ]:
        path = inputs["base"] / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic")
    manifest = write_manifest(inputs["base"])
    metadata = json.loads(inputs["receipt"].read_text())
    metadata["source_manifest_sha256"] = manifest
    metadata["indexed_files"] = inventory(inputs["base"], manifest)
    inputs["receipt"].write_text(json.dumps(metadata))
    inputs["receipt_sha256"] = digest(inputs["receipt"])
    inputs["base_provenance"].write_text(
        json.dumps({"manifest_sha256": manifest, "status": "draft"})
    )
    inputs["base_provenance_sha256"] = digest(inputs["base_provenance"])
    result = tool.attach(**inputs)
    assert len(metadata["indexed_files"]) == 3
    for name in ["3_MAPS_AND_PLACES/source.osm.pbf", "3_MAPS_AND_PLACES/SOURCE.TXT"]:
        assert (inputs["output"] / name).read_bytes() == (inputs["base"] / name).read_bytes()
    check_manifest(inputs["output"])
    assert result["normal_assembly_gates_changed"] is False


def map_receipt(inputs):
    names = [
        "3_MAPS_AND_PLACES/RI/Bristol County/0_OVERVIEW.pdf",
        "3_MAPS_AND_PLACES/RI/Bristol County/Bristol County.pdf",
    ]
    for name in names:
        pdf(inputs["base"] / name)
    manifest = write_manifest(inputs["base"])
    metadata = json.loads(inputs["receipt"].read_text())
    metadata["target_path"] = tool.MAP_INDEX_PATH
    metadata["source_manifest_sha256"] = manifest
    metadata["indexed_maps"] = [
        {
            "path": name,
            "sha256": digest(inputs["base"] / name),
            "size_bytes": (inputs["base"] / name).stat().st_size,
        }
        for name in names
    ]
    del metadata["indexed_files"]
    inputs["receipt"].write_text(json.dumps(metadata))
    inputs["receipt_sha256"] = digest(inputs["receipt"])
    inputs["base_provenance"].write_text(
        json.dumps({"manifest_sha256": manifest, "status": "draft"})
    )
    inputs["base_provenance_sha256"] = digest(inputs["base_provenance"])
    return metadata


def test_exact_map_finder_target_is_admitted_without_a_map_backup(inputs):
    map_receipt(inputs)
    result = tool.attach(**inputs)
    assert (inputs["output"] / tool.MAP_INDEX_PATH).read_bytes() == inputs["index"].read_bytes()
    assert not (inputs["output"] / "BACKUP" / tool.MAP_INDEX_PATH).exists()
    assert result["index_kind"] == "map_finder"
    check_manifest(inputs["output"])


@pytest.mark.parametrize("kind", ["target", "orphan", "collision"])
def test_map_finder_cannot_become_an_arbitrary_overlay(inputs, kind):
    metadata = map_receipt(inputs)
    if kind == "target":
        metadata["target_path"] = "7_LAPTOP/anything.pdf"
    elif kind == "orphan":
        metadata["indexed_maps"][0]["path"] = "3_MAPS_AND_PLACES/RI/missing/none.pdf"
    else:
        pdf(inputs["base"] / tool.MAP_INDEX_PATH)
        metadata["source_manifest_sha256"] = write_manifest(inputs["base"])
    inputs["receipt"].write_text(json.dumps(metadata))
    inputs["receipt_sha256"] = digest(inputs["receipt"])
    with pytest.raises(ValueError):
        tool.attach(**inputs)
    assert not inputs["output"].exists()
