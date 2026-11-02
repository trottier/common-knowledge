"""Extend an authenticated local draft tree; run as python -m tools.extend_inspection_preview."""

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from ck.assemble import check_manifest, copy_exact, write_manifest
from ck.catalog import Collection, Topics, load_catalog, safe_path
from ck.config import load_config
from ck.core import recipe_fingerprint
from ck.drive_safety import validate_tree
from ck.fetch import digest
from ck.render import content_file
from tools.assemble_inspection_preview import authenticated_receipt, confined_file


def records(root, entries):
    """Authenticate exact membership, including files subsequently omitted from copying."""
    expected = {}
    for entry in entries:
        name = entry["path"]
        path = confined_file(root, name)
        if name in expected or path.stat().st_size != entry["size_bytes"]:
            raise ValueError("Duplicate or wrong-sized layer file")
        if digest(path) != entry["sha256"]:
            raise ValueError("Layer payload checksum mismatch")
        expected[name] = entry
    if set(expected) != {p.relative_to(root).as_posix() for p in validate_tree(root)}:
        raise ValueError("Layer has missing or extra files")
    return expected


def admit_additions(config, items, receipt):
    if receipt.get("variant") != 1 or receipt.get("normal_sample_selection_changed") is not False:
        raise ValueError("Additional layer must retain its Variant 1 local scope")
    selected = receipt["selected_ids"]
    components = {row["id"]: row for row in receipt["components"]}
    if len(components) != len(receipt["components"]) or sorted(components) != sorted(selected):
        raise ValueError("Additional component selection differs")
    source_rows = {row["catalog"]["id"]: row["catalog"] for row in receipt["source_closure"]}
    if len(source_rows) != len(receipt["source_closure"]):
        raise ValueError("Duplicate source closure record")
    pending, seen, expected = list(selected), set(), {}
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        item = items[key]
        if source_rows.get(key) != item.model_dump(mode="json"):
            raise ValueError(f"Source catalog changed: {key}")
        hard = [p for p in item.blockers() if not p.startswith(key + ".review:")]
        if hard or re.search(
            r"unknown|unconfirmed|unclear|unresolved|missing permission|written permission|"
            r"license compatibility|per-file license inventory",
            item.review or "",
            re.I,
        ):
            raise ValueError(f"Unresolved source rights or pins: {key}")
        pending.extend(item.inputs)
        if item.source_id:
            pending.append(item.source_id)
    if seen != set(source_rows):
        raise ValueError("Additional source closure differs")
    variant = config.variants.variants[1]
    for key, component in components.items():
        item = items[key]
        if component["catalog"] != item.model_dump(mode="json"):
            raise ValueError(f"Component catalog changed: {key}")
        if item.family not in {"docs", "generated", "phrasebooks"} or item.placement == "hub_only":
            raise ValueError("Held or executable component")
        if (
            isinstance(item.placement, Collection)
            and item.placement.collection != variant.collection
        ):
            raise ValueError("Another variant's collection")
        if isinstance(item.placement, Topics) and not set(item.placement.topics) & set(
            variant.topics
        ):
            raise ValueError("Another variant's topics")
        if item.family == "generated":
            metadata = component["historical_generation"]["metadata"]
            encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
            if (
                hashlib.sha256(encoded).hexdigest() != item.sha256
                or metadata.get("complete") is not True
                or metadata["pipeline_version"] != item.pipeline_version
                or metadata["inputs"] != {k: items[k].sha256 for k in item.inputs}
                or sum(row["size_bytes"] for row in metadata["files"]) != item.size_bytes
            ):
                raise ValueError("Historical generation binding differs")
            bindings = [(str(Path(item.dest) / safe_path(r["path"])), r) for r in metadata["files"]]
        else:
            bindings = [(item.dest, {"sha256": item.sha256, "size_bytes": item.size_bytes})]
        if set(component["files"]) != {name for name, _ in bindings}:
            raise ValueError("Component destination binding differs")
        for name, row in bindings:
            if name in expected:
                raise ValueError("Component destination collision")
            expected[name] = {"sha256": row["sha256"], "size_bytes": row["size_bytes"]}
    payloads = {r["path"]: r for r in receipt["files"]}
    if len(payloads) != len(receipt["files"]) or set(payloads) != set(expected) | {
        "00_LOCAL_DRAFT_STATUS.TXT"
    }:
        raise ValueError("Unexpected additional layer destination")
    for name, row in expected.items():
        if any(payloads[name][k] != v for k, v in row.items()):
            raise ValueError("Additional payload differs from catalog generation")


def admit_guides(root, receipt, items):
    if receipt.get("profile") != "local-inspection":
        raise ValueError("Quick guides are local drafts")
    if (
        recipe_fingerprint(root, receipt["epoch"], ["en", "es"], "sample")
        != receipt["render_source_snapshot_sha256"]
    ):
        raise ValueError("Quick-guide original source snapshot differs")
    expected = {}
    for section in receipt["sections"]:
        source = confined_file(root, section["source_path"])
        header, body = content_file(source)
        if (
            digest(source) != section["source_file_sha256"]
            or hashlib.sha256(body.encode()).hexdigest() != section["source_body_sha256"]
            or header.source_inputs != section["source_input_bindings"]
            or any(
                getattr(header, k) != section[k]
                for k in ("title", "status", "reviewer", "reviewed_on")
            )
            or header.status not in {"draft", "machine"}
        ):
            raise ValueError("Quick-guide content, status, or bindings differ")
        for font in section["fonts"]:
            if (
                font["sha256"] != items[font["id"]].sha256
                or font["size_bytes"] != items[font["id"]].size_bytes
            ):
                raise ValueError("Quick-guide font pin differs")
        for destination in section["destinations"]:
            if destination in expected or not destination.startswith(
                ("1_START/", "4_PHONE_PACK/", "5_MEDICAL_REFERENCE/")
            ):
                raise ValueError("Unexpected quick-guide destination")
            expected[destination] = {
                "sha256": section["pdf_sha256"],
                "size_bytes": section["size_bytes"],
            }
    actual = {r["path"]: {k: r[k] for k in ("sha256", "size_bytes")} for r in receipt["files"]}
    if len(actual) != len(receipt["files"]) or actual != expected:
        raise ValueError("Quick-guide artifact bindings differ")


def extend_preview(
    *,
    root,
    base,
    base_manifest_sha256,
    additions,
    additions_receipt,
    additions_sha256,
    guides,
    guides_receipt,
    guides_sha256,
    output,
    epoch,
    base_provenance=None,
    base_provenance_sha256=None,
):
    provenance = output.with_name(output.name + ".provenance.json")
    for path in (output, provenance):
        if path.exists() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("Choose fresh output/provenance paths; no overwrite or symlinks")
    for source in (root, base, additions, guides):
        if output.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(
            output.resolve()
        ):
            raise ValueError("Output overlaps an input")
    config = load_config(root)
    if config.variants.offline_ai_enabled:
        raise ValueError("Offline AI is disabled for this milestone")
    manifest = confined_file(base, "MANIFEST.SHA256")
    if digest(manifest) != base_manifest_sha256:
        raise ValueError("Base manifest checksum mismatch")
    check_manifest(base)
    prior = None
    if base_provenance is not None:
        prior = authenticated_receipt(base_provenance, base_provenance_sha256)
        if prior.get("manifest_sha256") != base_manifest_sha256:
            raise ValueError("Base provenance does not bind the base manifest")
    elif base_provenance_sha256:
        raise ValueError("Base provenance path required")
    extra = authenticated_receipt(additions_receipt, additions_sha256)
    quick = authenticated_receipt(guides_receipt, guides_sha256)
    items = load_catalog(root, config)
    admit_additions(config, items, extra)
    admit_guides(root, quick, items)
    layers = [
        (additions, records(additions, extra["files"])),
        (guides, records(guides, quick["files"])),
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-extend-", dir=output.parent) as temporary:
        tree = Path(temporary) / "tree"
        tree.mkdir()
        for path in validate_tree(base):
            relative = path.relative_to(base)
            if relative.parts[0] not in {"BACKUP", "MANIFEST.SHA256"}:
                copy_exact(path, tree / relative, digest(path))
        for source, entries in layers:
            for relative, row in entries.items():
                copy_exact(confined_file(source, relative), tree / relative, row["sha256"])
        readme = tree / "README.TXT"
        previous = readme.read_text()
        retained = previous.split("\nMaps:", 1)[0]
        readme.write_text(
            retained + "\n\nQuick guides: 1_START/English/00_Quick guides/\n"
            "and 1_START/Español/00_Guías rápidas/\n"
            "Phone copies and official preparedness guides: 4_PHONE_PACK/\n"
            "Draft medical PDFs and offline WikEM/WikiMed archives: 5_MEDICAL_REFERENCE/\n"
            "Bristol County proof and RI Android map data with ODbL source: 3_MAPS_AND_PLACES/\n"
            "Automobile references: 6_VIDEOS_AND_IN_DEPTH/in_depth/howto_1/phone/\n\n"
            "Incomplete local draft inspection. Added references are full-profile supplements.\n"
            "RI Android data is sample-only.\n"
            "Still missing: Android and laptop reader apps, mesh apps, videos,\n"
            "remaining counties,\n"
            "complete places coverage, and remaining selected cargo.\n"
            "Medical, language, safety, pin, and physical-device reviews remain pending.\n"
            "Use BACKUP for second copies of START and the phone pack.\n"
        )
        with (tree / "VERIFY.TXT").open("a") as stream:
            stream.write(
                "\nExtension: local draft only.\n"
                f"Additional catalog source: {extra['source_catalog_commit']}\n"
                f"Quick-guide source: {quick['source_commit']}\n"
                "External provenance retains exact receipts, historical epochs, and holds.\n"
            )
        for directory in ("1_START", "4_PHONE_PACK"):
            shutil.copytree(tree / directory, tree / "BACKUP" / directory)
        for path in validate_tree(tree):
            if path.relative_to(tree).parts[0] in {"9_LOCAL_LLM", "9_OFFLINE_AI"}:
                raise ValueError("No offline AI in this milestone")
            if (
                path.suffix.lower() == ".pdf"
                and path.stat().st_size > config.build.pdf.max_file_bytes
            ):
                raise ValueError("PDF exceeds configured byte budget")
        final_manifest = write_manifest(tree)
        check_manifest(tree)
        result = {
            "status": "Incomplete local draft inspection; not normal assembly or release",
            "variant": 1,
            "profile": "local-inspection",
            "epoch": epoch,
            "normal_assembly_gates_changed": False,
            "extension_tool_sha256": digest(Path(__file__)),
            "base": {
                "manifest_sha256": base_manifest_sha256,
                "provenance_sha256": base_provenance_sha256,
                "provenance": prior,
            },
            "additional_cargo": {"receipt_sha256": additions_sha256, "receipt": extra},
            "quick_guides": {"receipt_sha256": guides_sha256, "receipt": quick},
            "copy_index": "Not appended; subsequent indexed clone must bind this actual tree",
            "manifest_sha256": final_manifest,
            "files": [
                {
                    "path": p.relative_to(tree).as_posix(),
                    "sha256": digest(p),
                    "size_bytes": p.stat().st_size,
                }
                for p in validate_tree(tree)
            ],
        }
        for path in [*tree.rglob("*"), tree]:
            os.utime(path, (epoch, epoch), follow_symlinks=False)
        if output.exists() or provenance.exists():
            raise ValueError("Output appeared; no overwrite")
        tree.rename(output)
        with provenance.open("x") as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "root",
        "base",
        "additions",
        "additions-receipt",
        "guides",
        "guides-receipt",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("base-manifest-sha256", "additions-sha256", "guides-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--base-provenance", type=Path)
    parser.add_argument("--base-provenance-sha256")
    parser.add_argument("--epoch", type=int, required=True)
    result = extend_preview(**vars(parser.parse_args()))
    print(
        json.dumps(
            {"manifest_sha256": result["manifest_sha256"], "files": len(result["files"])}, indent=2
        )
    )


if __name__ == "__main__":
    main()
