"""Exercise authenticated local inspection assembly without changing release gates."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfWriter

from ck.assemble import check_manifest
from ck.config import load_config
from ck.core import write_core_manifest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "inspection_tool", ROOT / "tools/assemble_inspection_preview.py"
)
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
EPOCH = 1793404800


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(path)


def record(root, relative):
    path = root / relative
    return {"path": relative, "size_bytes": path.stat().st_size, "sha256": checksum(path)}


@pytest.fixture
def inputs(tmp_path):
    root, core, maps, supplements = [
        tmp_path / name for name in ("root", "core", "maps", "supplements")
    ]
    root.mkdir()
    for name in ("config", "content"):
        shutil.copytree(ROOT / name, root / name)
    for name in ("Dockerfile.build", "pyproject.toml", "uv.lock"):
        shutil.copyfile(ROOT / name, root / name)
    config = load_config(root)
    for lang in config.languages:
        for name in ("01_START_phone.pdf", "01_START_print.pdf"):
            pdf(core / lang.code / name)
    (core / "en/01_START_phone.html").write_text(
        "<style>@font-face {src:url(file:/font)}</style><p>Fixture</p>"
    )
    map_path = "3_MAPS_AND_PLACES/RI/Bristol County/0_OVERVIEW.pdf"
    pdf(maps / map_path)
    (maps / "prototype.json").write_text(
        json.dumps({"status": "unreviewed fixture", "files": [record(maps, map_path)]})
    )
    guide = "4_PHONE_PACK/fixture.pdf"
    pdf(supplements / guide)
    (supplements / "SUPPLEMENTARY_DRAFTS.TXT").write_text("Synthetic draft inspection fixture\n")
    item = {
        "id": "fixture_guide",
        "family": "docs",
        "title": "Synthetic test guide",
        "url": "https://example.invalid/fixture.pdf",
        "version": "test fixture",
        "license": "CC0-1.0",
        "attribution": "Original synthetic test fixture",
        "license_proof_url": "https://example.invalid/license",
        "placement": "universal",
        "dest": guide,
        "profiles": ["full"],
        "sha256": checksum(supplements / guide),
        "size_bytes": (supplements / guide).stat().st_size,
        "review": "[[VERIFY: synthetic human review fixture]]",
    }
    (root / "catalog").mkdir()
    (root / "catalog/docs.yaml").write_text(json.dumps([item]))
    receipt = {
        "variant": 1,
        "normal_sample_selection_changed": False,
        "selected_ids": [item["id"]],
        "components": [{"id": item["id"], "catalog": item}],
        "source_closure": [item],
        "files": [record(supplements, guide), record(supplements, "SUPPLEMENTARY_DRAFTS.TXT")],
    }
    receipt_path = tmp_path / "supplements.json"
    receipt_path.write_text(json.dumps(receipt))
    languages = [lang.code for lang in config.languages]
    write_core_manifest(root, core, EPOCH, languages, "sample")
    return {
        "root": root,
        "core": core,
        "maps": maps,
        "map_sha256": checksum(maps / "prototype.json"),
        "supplements": supplements,
        "supplements_receipt": receipt_path,
        "supplements_sha256": checksum(receipt_path),
        "output": tmp_path / "output",
        "epoch": EPOCH,
        "core_source": "synthetic fixture",
        "map_source": "synthetic fixture",
    }


def reseal_core(inputs):
    write_core_manifest(
        inputs["root"],
        inputs["core"],
        EPOCH,
        [lang.code for lang in load_config(inputs["root"]).languages],
        "sample",
    )


def test_actual_copy_manifest_backups_editions_and_historical_scope(inputs):
    result = preview.assemble_preview(**inputs)
    output = inputs["output"]
    assert result["profile"] == "local-inspection"
    assert result["normal_assembly_gates_changed"] is False
    assert result["supplements"]["receipt"]["components"][0]["catalog"]["profiles"] == ["full"]
    assert "[[VERIFY" in result["supplements"]["receipt"]["source_closure"][0]["review"]
    readme = (output / "README.TXT").read_text()
    for lang in load_config(inputs["root"]).languages:
        assert (output / "1_START" / lang.name / "01_START_phone.pdf").is_file()
        assert lang.name in readme
    assert "incomplete local inspection" in readme and "Missing:" in readme
    assert "Profile: local inspection" in (output / "VERIFY.TXT").read_text()
    assert "@font-face" not in (output / "7_LAPTOP/English/01_START.html").read_text()
    assert (output / "4_PHONE_PACK/fixture.pdf").read_bytes() == (
        inputs["supplements"] / "4_PHONE_PACK/fixture.pdf"
    ).read_bytes()
    for directory in ("1_START", "4_PHONE_PACK"):
        for path in (output / directory).rglob("*"):
            if path.is_file():
                assert (
                    path.read_bytes() == (output / "BACKUP" / path.relative_to(output)).read_bytes()
                )
    check_manifest(output)
    assert checksum(output / "MANIFEST.SHA256") == result["manifest_sha256"]
    assert "MANIFEST.SHA256" not in [
        line.split("  ", 1)[1] for line in (output / "MANIFEST.SHA256").read_text().splitlines()
    ]
    assert output.with_name("output.provenance.json").is_file()


@pytest.mark.parametrize(
    "mutation", ["receipt", "payload", "symlink", "parent-symlink", "traversal", "duplicate"]
)
def test_untrusted_components_fail_before_publication(inputs, mutation):
    maps = inputs["maps"]
    manifest_path = maps / "prototype.json"
    metadata = json.loads(manifest_path.read_text())
    payload = maps / metadata["files"][0]["path"]
    if mutation == "receipt":
        manifest_path.write_text("{}")
    elif mutation == "payload":
        payload.write_bytes(b"changed")
    elif mutation == "symlink":
        original = payload.with_suffix(".original")
        payload.rename(original)
        payload.symlink_to(original)
    elif mutation == "parent-symlink":
        directory = payload.parent
        original = directory.with_name("original")
        directory.rename(original)
        directory.symlink_to(original, target_is_directory=True)
    else:
        if mutation == "traversal":
            metadata["files"][0]["path"] = "../escape.pdf"
        else:
            metadata["files"].append(metadata["files"][0])
        manifest_path.write_text(json.dumps(metadata))
        inputs["map_sha256"] = checksum(manifest_path)
    with pytest.raises(ValueError):
        preview.assemble_preview(**inputs)
    assert not inputs["output"].exists()


def test_stale_core_is_not_waived(inputs):
    (inputs["core"] / "en/01_START_phone.pdf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Core output changed"):
        preview.assemble_preview(**inputs)
    assert not inputs["output"].exists()


def test_collision_does_not_replace_core_file(inputs):
    target = inputs["supplements"] / "README.TXT"
    target.write_text("Must not overwrite generated practical README")
    receipt = json.loads(inputs["supplements_receipt"].read_text())
    receipt["files"].append(record(inputs["supplements"], "README.TXT"))
    inputs["supplements_receipt"].write_text(json.dumps(receipt))
    inputs["supplements_sha256"] = checksum(inputs["supplements_receipt"])
    with pytest.raises(ValueError, match="Notice collides"):
        preview.assemble_preview(**inputs)
    assert not inputs["output"].exists()


def test_existing_output_is_untouched(inputs):
    inputs["output"].mkdir()
    marker = inputs["output"] / "keep"
    marker.write_text("existing")
    with pytest.raises(ValueError, match="no overwrite"):
        preview.assemble_preview(**inputs)
    assert marker.read_text() == "existing"


def test_configured_pdf_budget_is_enforced_on_copied_artifacts(inputs):
    config_path = inputs["root"] / "config/build.yaml"
    from ck.config import read_yaml

    data = read_yaml(config_path)
    data["pdf"]["max_file_mb"] = 1
    config_path.write_text(json.dumps(data))
    manifest_path = inputs["maps"] / "prototype.json"
    manifest = json.loads(manifest_path.read_text())
    path = inputs["maps"] / manifest["files"][0]["path"]
    with path.open("ab") as stream:
        stream.write(b" " * 1_000_001)
    manifest["files"][0] = record(inputs["maps"], manifest["files"][0]["path"])
    manifest_path.write_text(json.dumps(manifest))
    inputs["map_sha256"] = checksum(manifest_path)
    reseal_core(inputs)
    with pytest.raises(ValueError, match="PDF exceeds configured"):
        preview.assemble_preview(**inputs)
    assert not inputs["output"].exists()


def test_missing_edition_is_not_silently_skipped(inputs):
    path = inputs["core"] / "ar/01_START_phone.pdf"
    path.unlink()
    reseal_core(inputs)
    with pytest.raises(ValueError, match="Missing"):
        preview.assemble_preview(**inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize(
    "license_text", ["[[VERIFY: unknown redistribution rights]]", "MIT OR CC-BY-NC-SA-4.0"]
)
def test_unknown_or_restricted_rights_are_not_a_draft_review_exception(inputs, license_text):
    catalog_path = inputs["root"] / "catalog/docs.yaml"
    item = json.loads(catalog_path.read_text())[0]
    item["license"] = license_text
    catalog_path.write_text(json.dumps([item]))
    receipt = json.loads(inputs["supplements_receipt"].read_text())
    receipt["components"][0]["catalog"] = item
    receipt["source_closure"] = [item]
    inputs["supplements_receipt"].write_text(json.dumps(receipt))
    inputs["supplements_sha256"] = checksum(inputs["supplements_receipt"])
    reseal_core(inputs)
    with pytest.raises(ValueError):
        preview.assemble_preview(**inputs)
    assert not inputs["output"].exists()
