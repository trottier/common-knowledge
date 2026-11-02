"""Guard actual authenticated local intake without weakening ordinary release gates."""

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from ck.assemble import check_manifest, write_manifest
from ck.config import load_config
from ck.core import recipe_fingerprint
from ck.render import content_file

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "extend_tool", ROOT / "tools/extend_inspection_preview.py"
)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(path, value):
    path.write_text(json.dumps(value))
    return sha(path)


def file_record(folder, relative):
    path = folder / relative
    return {"path": relative, "sha256": sha(path), "size_bytes": path.stat().st_size}


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    for name in ("config", "content"):
        shutil.copytree(ROOT / name, root / name)
    for name in ("Dockerfile.build", "pyproject.toml", "uv.lock"):
        shutil.copyfile(ROOT / name, root / name)
    base, extra, guides = [tmp_path / name for name in ("base", "extra", "guides")]
    for directory in (base, extra, guides):
        directory.mkdir()
    for name in ("1_START/English/start.txt", "4_PHONE_PACK/English/card.txt"):
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Original synthetic fixture")
    shutil.copytree(base / "4_PHONE_PACK", base / "BACKUP/4_PHONE_PACK")
    (base / "README.TXT").write_text(
        "COMMON KNOWLEDGE\nEnglish\nMaps: fixture\nMissing: archives\n"
    )
    (base / "VERIFY.TXT").write_text("Variant: 1\nSource: synthetic fixture\n")
    base_hash = write_manifest(base)
    name = "4_PHONE_PACK/official/en/fixture.pdf"
    path = extra / name
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF synthetic unchanged test fixture")
    (extra / "00_LOCAL_DRAFT_STATUS.TXT").write_text("Local draft fixture")
    catalog = {
        "id": "fixture",
        "family": "docs",
        "title": "Synthetic fixture",
        "url": "https://example.invalid/fixture.pdf",
        "version": "test",
        "size_bytes": path.stat().st_size,
        "sha256": sha(path),
        "license": "CC0-1.0",
        "attribution": "Original test fixture",
        "license_proof_url": "https://example.invalid/license",
        "placement": "universal",
        "dest": name,
        "profiles": ["full"],
        "review": "[[VERIFY: human pin review]]",
    }
    (root / "catalog").mkdir()
    seal(root / "catalog/docs.yaml", [catalog])
    from ck.catalog import load_catalog

    item = load_catalog(root, load_config(root))["fixture"].model_dump(mode="json")
    extra_receipt = tmp_path / "extra.json"
    extra_data = {
        "variant": 1,
        "normal_sample_selection_changed": False,
        "source_catalog_commit": "synthetic",
        "selected_ids": ["fixture"],
        "components": [{"id": "fixture", "catalog": item, "files": [name]}],
        "source_closure": [{"catalog": item}],
        "files": [file_record(extra, name), file_record(extra, "00_LOCAL_DRAFT_STATUS.TXT")],
    }
    source = root / "content/en/start/02-first-hour.md"
    header, body = content_file(source)
    destination = "1_START/English/00_Quick guides/fixture.pdf"
    path = guides / destination
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF unchanged synthetic quick-guide fixture")
    quick = {
        "profile": "local-inspection",
        "epoch": 1793404800,
        "source_commit": "synthetic",
        "render_source_snapshot_sha256": recipe_fingerprint(
            root, 1793404800, ["en", "es"], "sample"
        ),
        "sections": [
            {
                "source_path": str(source.relative_to(root)),
                "source_file_sha256": sha(source),
                "source_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "source_input_bindings": header.source_inputs,
                "title": header.title,
                "status": header.status,
                "reviewer": header.reviewer,
                "reviewed_on": header.reviewed_on,
                "fonts": [],
                "destinations": [destination],
                "pdf_sha256": sha(path),
                "size_bytes": path.stat().st_size,
            }
        ],
        "files": [file_record(guides, destination)],
    }
    quick_receipt = tmp_path / "quick.json"
    return {
        "root": root,
        "base": base,
        "base_manifest_sha256": base_hash,
        "additions": extra,
        "additions_receipt": extra_receipt,
        "additions_sha256": seal(extra_receipt, extra_data),
        "guides": guides,
        "guides_receipt": quick_receipt,
        "guides_sha256": seal(quick_receipt, quick),
        "output": tmp_path / "output",
        "epoch": 1793404800,
    }


def test_extension_preserves_bytes_rebuilds_backup_and_manifest(inputs):
    original = {
        p.relative_to(inputs["base"]): p.read_bytes()
        for p in inputs["base"].rglob("*")
        if p.is_file()
    }
    result = tool.extend_preview(**inputs)
    output = inputs["output"]
    for source in (inputs["additions"], inputs["guides"]):
        for path in source.rglob("*"):
            if path.is_file():
                assert (output / path.relative_to(source)).read_bytes() == path.read_bytes()
    for directory in ("1_START", "4_PHONE_PACK"):
        for path in (output / directory).rglob("*"):
            if path.is_file():
                assert (
                    output / "BACKUP" / path.relative_to(output)
                ).read_bytes() == path.read_bytes()
    assert all((inputs["base"] / p).read_bytes() == value for p, value in original.items())
    assert "offline WikEM/WikiMed archives" in (output / "README.TXT").read_text()
    assert "Missing: archives" not in (output / "README.TXT").read_text()
    assert result["normal_assembly_gates_changed"] is False
    assert result["additional_cargo"]["receipt"]["components"][0]["catalog"]["review"].startswith(
        "[[VERIFY"
    )
    assert all(int(p.stat().st_mtime) == inputs["epoch"] for p in output.rglob("*"))
    check_manifest(output)
    assert result["manifest_sha256"] == sha(output / "MANIFEST.SHA256")
    assert "  MANIFEST.SHA256" not in (output / "MANIFEST.SHA256").read_text()


@pytest.mark.parametrize(
    "mutation",
    [
        "base-extra",
        "layer-extra",
        "symlink",
        "traversal",
        "collision",
        "payload",
        "receipt",
        "nonempty",
        "nested",
    ],
)
def test_untrusted_inputs_never_publish(inputs, mutation):
    if mutation == "base-extra":
        (inputs["base"] / "extra.txt").write_text("unlisted")
    elif mutation == "layer-extra":
        (inputs["guides"] / "extra.txt").write_text("unlisted")
    elif mutation == "symlink":
        p = inputs["additions"] / "00_LOCAL_DRAFT_STATUS.TXT"
        p.unlink()
        p.symlink_to(inputs["base"] / "README.TXT")
    elif mutation == "payload":
        (inputs["additions"] / "00_LOCAL_DRAFT_STATUS.TXT").write_text("changed")
    elif mutation == "receipt":
        inputs["guides_receipt"].write_text("{}")
    elif mutation == "nonempty":
        inputs["output"].mkdir()
        (inputs["output"] / "keep.txt").write_text("keep")
    elif mutation == "nested":
        inputs["output"] = inputs["base"] / "nested"
    elif mutation == "traversal":
        receipt = json.loads(inputs["guides_receipt"].read_text())
        receipt["files"][0]["path"] = "../escape.pdf"
        inputs["guides_sha256"] = seal(inputs["guides_receipt"], receipt)
    else:
        path = inputs["base"] / "00_LOCAL_DRAFT_STATUS.TXT"
        path.write_text("existing; must not replace")
        inputs["base_manifest_sha256"] = write_manifest(inputs["base"])
    with pytest.raises(ValueError):
        tool.extend_preview(**inputs)
    assert not inputs["output"].exists() or mutation == "nonempty"


@pytest.mark.parametrize(
    "field,value",
    [
        ("license", "[[VERIFY: unknown rights]]"),
        ("review", "[[VERIFY: unknown bundled rights]]"),
        ("requires_legal", True),
    ],
)
def test_review_exception_does_not_waive_rights_or_named_legal_holds(inputs, field, value):
    path = inputs["root"] / "catalog/docs.yaml"
    rows = json.loads(path.read_text())
    rows[0][field] = value
    seal(path, rows)
    from ck.catalog import load_catalog

    item = load_catalog(inputs["root"], load_config(inputs["root"]))["fixture"]
    receipt = json.loads(inputs["additions_receipt"].read_text())
    receipt["components"][0]["catalog"] = item.model_dump(mode="json")
    receipt["source_closure"][0]["catalog"] = item.model_dump(mode="json")
    inputs["additions_sha256"] = seal(inputs["additions_receipt"], receipt)
    with pytest.raises(ValueError, match="Unresolved source rights or pins"):
        tool.extend_preview(**inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "reviewed"),
        ("source_input_bindings", {"invented": "binding"}),
        ("source_body_sha256", "0" * 64),
    ],
)
def test_quick_guides_must_retain_original_content_and_review_status(inputs, field, value):
    path = inputs["guides_receipt"]
    receipt = json.loads(path.read_text())
    receipt["sections"][0][field] = value
    inputs["guides_sha256"] = seal(path, receipt)
    with pytest.raises(ValueError, match="content, status, or bindings"):
        tool.extend_preview(**inputs)
    assert not inputs["output"].exists()


def test_pdf_cap_remains_hard_even_for_authenticated_base(inputs):
    path = inputs["base"] / "4_PHONE_PACK/oversized.pdf"
    limit = load_config(inputs["root"]).build.pdf.max_file_bytes
    with path.open("wb") as stream:
        stream.truncate(limit + 1)
    inputs["base_manifest_sha256"] = write_manifest(inputs["base"])
    with pytest.raises(ValueError, match="PDF exceeds configured byte budget"):
        tool.extend_preview(**inputs)
    assert not inputs["output"].exists()
