"""Clone a pinned local preview, moving unchanged Ready PDFs into configured language folders."""

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from ck.assemble import check_manifest, copy_exact, destination, write_manifest
from ck.catalog import Item, load_catalog
from ck.config import load_config
from ck.drive_safety import validate_tree
from ck.fetch import digest
from tools.assemble_inspection_preview import authenticated_receipt, confined_file


def guide_moves(config, items, originals, admission, base):
    """Re-admit the original grant and bytes, permitting only edition/path metadata changes."""
    components = {r["id"]: r for r in admission["components"]}
    closure = {r["catalog"]["id"]: r["catalog"] for r in admission["source_closure"]}
    original_ids, moves, held = set(), [], []
    for raw in originals:
        old = Item.model_validate(raw)
        if old.id in original_ids or not old.id.startswith("ready_") or old.family != "docs":
            raise ValueError("Unexpected original official-guide family")
        original_ids.add(old.id)
        current = items[old.id]
        before, after = old.model_dump(mode="json"), current.model_dump(mode="json")
        if {k: v for k, v in before.items() if k not in {"language", "dest"}} != {
            k: v for k, v in after.items() if k not in {"language", "dest"}
        }:
            raise ValueError(
                f"Publisher bytes, rights, or other catalog metadata changed: {old.id}"
            )
        if (
            current.language != Path(old.dest).parts[2]
            or current.license != "LicenseRef-FEMA-Ready-Reprint"
            or current.license_proof_url != "https://www.ready.gov/publications"
            or current.inputs
            or current.source_id
            or current.requires_legal
            or any(not p.startswith(current.id + ".review:") for p in current.blockers())
            or re.search(
                r"unknown|unconfirmed|unresolved|missing permission", current.review or "", re.I
            )
        ):
            raise ValueError(f"Unresolved official-guide rights or language binding: {old.id}")
        target = destination(current, config, 1)
        if old.id not in components:
            if current.size_bytes <= config.build.pdf.max_file_bytes:
                raise ValueError(f"Eligible original unexpectedly absent from admission: {old.id}")
            if (base / old.dest).exists() or (base / target).exists():
                raise ValueError("Oversized held PDF must not be present")
            held.append(
                {
                    "id": old.id,
                    "size_bytes": current.size_bytes,
                    "sha256": current.sha256,
                    "reason": "Original exceeds configured PDF byte cap; not split or altered",
                }
            )
            continue
        if Item.model_validate(components[old.id]["catalog"]).model_dump(mode="json") != before:
            raise ValueError("Original admission catalog differs")
        if Item.model_validate(closure[old.id]).model_dump(mode="json") != before:
            raise ValueError("Original admission source record differs")
        source = confined_file(base, old.dest)
        if source.stat().st_size != current.size_bytes or digest(source) != current.sha256:
            raise ValueError("Original PDF bytes differ")
        if (base / target).exists() or target == old.dest:
            raise ValueError("Guide destination collision or unchanged code path")
        moves.append(
            {
                "id": old.id,
                "from": old.dest,
                "to": target,
                "sha256": current.sha256,
                "size_bytes": current.size_bytes,
                "catalog": after,
            }
        )
    current_ids = {key for key in items if key.startswith("ready_")}
    if original_ids != current_ids or len({r["to"] for r in moves}) != len(moves):
        raise ValueError("Official-guide family or destinations differ")
    return moves, held


def reorganize(
    *,
    root,
    base,
    base_manifest_sha256,
    base_provenance,
    base_provenance_sha256,
    original_catalog,
    admission_receipt,
    admission_sha256,
    output,
    epoch,
):
    provenance = output.with_name(output.name + ".provenance.json")
    for path in (output, provenance):
        if path.exists() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("Choose fresh output/provenance paths; no overwrite or symlinks")
    if output.resolve().is_relative_to(base.resolve()) or base.resolve().is_relative_to(
        output.resolve()
    ):
        raise ValueError("Output overlaps the base")
    if digest(confined_file(base, "MANIFEST.SHA256")) != base_manifest_sha256:
        raise ValueError("Parent manifest checksum mismatch")
    check_manifest(base)
    parent = authenticated_receipt(base_provenance, base_provenance_sha256)
    if parent["manifest_sha256"] != base_manifest_sha256:
        raise ValueError("Parent provenance does not bind manifest")
    admission = authenticated_receipt(admission_receipt, admission_sha256)
    originals = authenticated_receipt(
        original_catalog, admission["catalog_file_sha256"]["catalog/official_guides.yaml"]
    )
    config = load_config(root)
    moves, held = guide_moves(config, load_catalog(root, config), originals, admission, base)
    by_source = {row["from"]: row for row in moves}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-guide-folders-", dir=output.parent) as temporary:
        tree = Path(temporary) / "tree"
        tree.mkdir()
        for source in validate_tree(base):
            relative = source.relative_to(base).as_posix()
            if relative.split("/")[0] in {"BACKUP", "MANIFEST.SHA256"}:
                continue
            target = by_source.get(relative, {}).get("to", relative)
            copy_exact(source, tree / target, digest(source))
        with (tree / "README.TXT").open("a") as stream:
            stream.write(
                "\nOfficial preparedness guides: open your language folder in 4_PHONE_PACK,\n"
                "then Official guides. Original FEMA PDFs are unchanged and remain unreviewed.\n"
            )
        with (tree / "VERIFY.TXT").open("a") as stream:
            stream.write(
                "\nOfficial guides reorganized by configured edition name; PDF bytes unchanged.\n"
                "External provenance retains original grants, holds, epochs, and path mapping.\n"
            )
        for name in ("1_START", "4_PHONE_PACK"):
            shutil.copytree(tree / name, tree / "BACKUP" / name)
        for path in validate_tree(tree):
            if (
                path.suffix.lower() == ".pdf"
                and path.stat().st_size > config.build.pdf.max_file_bytes
            ):
                raise ValueError("PDF exceeds configured byte budget")
        manifest = write_manifest(tree)
        check_manifest(tree)
        result = {
            "status": "Incomplete local draft inspection; original official PDFs unchanged",
            "variant": 1,
            "profile": "local-inspection",
            "epoch": epoch,
            "normal_assembly_gates_changed": False,
            "tool_sha256": digest(Path(__file__)),
            "parent_manifest_sha256": base_manifest_sha256,
            "parent_provenance_sha256": base_provenance_sha256,
            "parent_provenance": parent,
            "original_admission_sha256": admission_sha256,
            "original_admission": admission,
            "original_catalog_sha256": digest(original_catalog),
            "current_catalog_sha256": digest(root / "catalog/official_guides.yaml"),
            "language_config_sha256": digest(root / "config/languages.yaml"),
            "placement_code_sha256": digest(root / "src/ck/assemble.py"),
            "path_mapping": moves,
            "held_originals": held,
            "manifest_sha256": manifest,
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
        "base-provenance",
        "original-catalog",
        "admission-receipt",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("base-manifest-sha256", "base-provenance-sha256", "admission-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--epoch", type=int, required=True)
    result = reorganize(**vars(parser.parse_args()))
    print(
        json.dumps(
            {
                "manifest_sha256": result["manifest_sha256"],
                "moved_guides": len(result["path_mapping"]),
                "files": len(result["files"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
