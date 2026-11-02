"""Combine authenticated components into an explicitly incomplete local inspection tree.

This tool does not invoke normal assembly, change profile selection, or grant reviews.
Run with the pinned build environment and the frozen source root used for the core.
"""

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from ck.assemble import _copy_core, check_manifest, copy_exact, write_manifest
from ck.catalog import Collection, Topics, load_catalog, safe_path
from ck.config import load_config
from ck.core import verify_core
from ck.drive_safety import validate_tree
from ck.fetch import digest


def confined_file(root: Path, relative: str) -> Path:
    normalized = str(safe_path(relative))
    if normalized != relative:
        raise ValueError(f"Noncanonical component path: {relative}")
    path = root / relative
    if root.is_symlink() or any(parent.is_symlink() for parent in [path, *path.parents]):
        raise ValueError(f"Symlink in component path: {relative}")
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Missing or escaping component file: {relative}")
    return path


def authenticated_receipt(path: Path, checksum: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("An exact receipt SHA-256 is required")
    if (
        any(p.is_symlink() for p in [path, *path.parents])
        or not path.is_file()
        or digest(path) != checksum
    ):
        raise ValueError(f"Receipt checksum mismatch: {path}")
    return json.loads(path.read_text())


def copy_records(source: Path, records: list[dict], target: Path) -> None:
    if not records:
        raise ValueError("Empty component inventory")
    expected = set()
    for record in records:
        relative = record["path"]
        if str(safe_path(relative)) != relative:
            raise ValueError(f"Noncanonical component path: {relative}")
        if relative in expected:
            raise ValueError(f"Duplicate component path: {relative}")
        expected.add(relative)
        path = confined_file(source, relative)
        if path.suffix.casefold() not in {".pdf", ".txt"}:
            raise ValueError(f"Unsupported inspection cargo: {relative}")
        if path.stat().st_size != record["size_bytes"]:
            raise ValueError(f"Component size mismatch: {relative}")
        copy_exact(path, target / relative, record["sha256"])
        if digest(target / relative) != record["sha256"]:
            raise ValueError(f"Copied component changed: {relative}")


def check_supplements(config, items, receipt: dict) -> None:
    if receipt.get("variant") != 1 or receipt.get("normal_sample_selection_changed") is not False:
        raise ValueError("Supplements must retain their separate Variant 1 inspection scope")
    selected = receipt["selected_ids"]
    if len(set(selected)) != len(selected):
        raise ValueError("Duplicate selected supplement")
    variant = config.variants.variants[1]
    component_ids = []
    for component in receipt["components"]:
        item = items[component["id"]]
        component_ids.append(item.id)
        original = component["catalog"]
        for key in (
            "sha256",
            "size_bytes",
            "pipeline_version",
            "inputs",
            "dest",
            "license",
            "license_proof_url",
            "profiles",
            "placement",
        ):
            if original.get(key, [] if key == "inputs" else None) != item.model_dump(
                mode="json"
            ).get(key):
                raise ValueError(f"Supplement catalog changed: {item.id}.{key}")
        if item.family not in {"generated", "docs", "phrasebooks"}:
            raise ValueError(f"Unsupported supplement family: {item.id}")
        if item.placement == "hub_only":
            raise ValueError(f"Held supplement cannot be placed: {item.id}")
        if (
            isinstance(item.placement, Collection)
            and item.placement.collection != variant.collection
        ):
            raise ValueError(f"Another variant's collection: {item.id}")
        if isinstance(item.placement, Topics) and not set(item.placement.topics) & set(
            variant.topics
        ):
            raise ValueError(f"Another variant's topics: {item.id}")
    if sorted(component_ids) != sorted(selected):
        raise ValueError("Supplement selected/component inventories differ")
    # Existing source records retain their review markers. Unknown rights still block.
    closure = set()
    pending = list(selected)
    recorded = {row["id"]: row for row in receipt["source_closure"]}
    if len(recorded) != len(receipt["source_closure"]):
        raise ValueError("Duplicate supplement source record")
    while pending:
        key = pending.pop()
        if key in closure:
            continue
        closure.add(key)
        item = items[key]
        pending.extend(item.inputs)
        row = recorded[key]
        if any(
            row.get(field) != getattr(item, field)
            for field in ("sha256", "license", "license_proof_url")
        ):
            raise ValueError(f"Supplement source pin or rights changed: {key}")
        blockers = [
            problem for problem in item.blockers() if not problem.startswith(f"{item.id}.review:")
        ]
        if blockers:
            raise ValueError(f"Unresolved source rights or pins: {key}: {blockers}")
    if closure != set(recorded):
        raise ValueError("Supplement source closure differs")


def assemble_preview(
    *,
    root: Path,
    core: Path,
    maps: Path,
    map_sha256: str,
    supplements: Path,
    supplements_receipt: Path,
    supplements_sha256: str,
    output: Path,
    epoch: int,
    core_source: str,
    map_source: str,
) -> dict:
    provenance = output.with_name(output.name + ".provenance.json")
    if output.exists() or provenance.exists() or output.is_symlink() or provenance.is_symlink():
        raise ValueError("Choose a fresh output and provenance path; no overwrite")
    config = load_config(root)
    if config.variants.offline_ai_enabled:
        raise ValueError("Inspection milestone requires offline AI disabled")
    for path in core.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlink in core input")
    verify_core(root, core, epoch, "sample")
    core_manifest_path = confined_file(core, "core-manifest.json")
    core_manifest = json.loads(core_manifest_path.read_text())
    if set(core_manifest["languages"]) != {lang.code for lang in config.languages}:
        raise ValueError("All fifteen actual core editions are required")
    for lang in config.languages:
        for name in ("01_START_phone.pdf", "01_START_print.pdf"):
            confined_file(core, f"{lang.code}/{name}")
    map_receipt = authenticated_receipt(confined_file(maps, "prototype.json"), map_sha256)
    if any(not row["path"].startswith("3_MAPS_AND_PLACES/") for row in map_receipt["files"]):
        raise ValueError("Map receipt contains non-map cargo")
    supplement_receipt = authenticated_receipt(supplements_receipt, supplements_sha256)
    items = load_catalog(root, config)
    check_supplements(config, items, supplement_receipt)
    actual_supplements = {p.relative_to(supplements).as_posix() for p in validate_tree(supplements)}
    if actual_supplements != {row["path"] for row in supplement_receipt["files"]}:
        raise ValueError("Supplement receipt does not cover the exact tree")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-inspection-", dir=output.parent) as temporary:
        tree = Path(temporary) / "tree"
        tree.mkdir()
        editions = _copy_core(root, config, core, tree)
        if len(editions) != len(config.languages):
            raise ValueError("Not all core editions were copied")
        copy_records(maps, map_receipt["files"], tree)
        copy_records(supplements, supplement_receipt["files"], tree)
        for name in ("1_START", "4_PHONE_PACK"):
            shutil.copytree(tree / name, tree / "BACKUP" / name)
        readme = [
            "COMMON KNOWLEDGE",
            "Variant 1 — incomplete local inspection",
            "",
            "Open 1_START for the instructions in your language.",
            *editions,
            "",
            "Maps: 3_MAPS_AND_PLACES/RI/Bristol County/",
            "Phone PDFs and phrasebooks: 4_PHONE_PACK/",
            "Draft medical references: 5_MEDICAL_REFERENCE/pdf/",
            "Draft automobile references: 6_VIDEOS_AND_IN_DEPTH/in_depth/howto_1/phone/",
            "",
            "These are draft inspection files. Human review and physical-phone tests are pending.",
            "The extra references are full-profile supplements, not normal sample-profile cargo.",
            "Missing: other counties, complete places coverage, Android maps and apps, videos,",
            "raw reference archives, and the remaining selected sample cargo.",
            "Backup copies of START and the phone pack are in BACKUP.",
        ]
        copy_exact_notice(tree / "README.TXT", "\n".join(readme) + "\n")
        copy_exact_notice(
            tree / "VERIFY.TXT",
            "\n".join(
                [
                    "Common Knowledge — development inspection only",
                    "Variant: 1",
                    "Profile: local inspection (core rendered with sample profile)",
                    f"Core source: {core_source}",
                    f"Map source: {map_source}",
                    "Supplement sources: historical matching49a artifacts; see external provenance",
                    f"SOURCE_DATE_EPOCH: {epoch}",
                    "Incomplete; draft/machine translations and human reviews pending.",
                    "Not a completed sample, image, release, or phone acceptance result.",
                ]
            )
            + "\n",
        )
        files = validate_tree(tree)
        for path in files:
            if (
                path.suffix.casefold() == ".pdf"
                and path.stat().st_size > config.build.pdf.max_file_bytes
            ):
                raise ValueError(f"PDF exceeds configured byte budget: {path.relative_to(tree)}")
            if path.relative_to(tree).parts[0] == "9_OFFLINE_AI":
                raise ValueError("Offline AI is absent from this milestone")
        manifest_sha256 = write_manifest(tree)
        check_manifest(tree)
        files = validate_tree(tree)
        result = {
            "status": "Incomplete local draft inspection; not sample assembly or release",
            "profile": "local-inspection",
            "variant": 1,
            "epoch": epoch,
            "sources": {"core": core_source, "map": map_source, "supplements": "historical49a"},
            "core": {
                "manifest_file_sha256": digest(core_manifest_path),
                "manifest": core_manifest,
                "laptop_html_transform": "Existing _copy_core removes @font-face and file fonts",
            },
            "maps": {"receipt_sha256": map_sha256, "receipt": map_receipt},
            "supplements": {"receipt_sha256": supplements_sha256, "receipt": supplement_receipt},
            "copy_index": "Not generated: no existing copy-ready-index generator is available",
            "human_status": "Draft English; machine translations; all named reviews remain pending",
            "omissions": [
                "remaining Rhode Island counties",
                "complete places directory",
                "Android maps and apps",
                "videos",
                "raw reference archives",
                "remaining selected sample cargo",
            ],
            "offline_ai_payloads": False,
            "normal_assembly_gates_changed": False,
            "pdf_max_bytes": config.build.pdf.max_file_bytes,
            "manifest_sha256": manifest_sha256,
            "files": [
                {
                    "path": p.relative_to(tree).as_posix(),
                    "size_bytes": p.stat().st_size,
                    "sha256": digest(p),
                }
                for p in files
            ],
        }
        result["file_count"] = len(files)
        result["pdf_count"] = sum(p.suffix.casefold() == ".pdf" for p in files)
        result["total_bytes"] = sum(p.stat().st_size for p in files)
        for path in [*tree.rglob("*"), tree]:
            os.utime(path, (epoch, epoch), follow_symlinks=False)
        if output.exists() or provenance.exists():
            raise ValueError("Output appeared during assembly; no overwrite")
        tree.rename(output)
        with provenance.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def copy_exact_notice(target: Path, text: str) -> None:
    if target.exists():
        raise ValueError(f"Notice collides with an input: {target.name}")
    target.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "core", "maps", "supplements", "supplements-receipt", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("map-sha256", "supplements-sha256", "core-source", "map-source"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--epoch", type=int, required=True)
    result = assemble_preview(**vars(parser.parse_args()))
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("status", "file_count", "pdf_count", "total_bytes", "manifest_sha256")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
