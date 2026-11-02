"""Attach an authenticated copy index to a fresh clone of an actual inspection tree."""

import argparse
import json
import os
import tempfile
from pathlib import Path

from pypdf import PdfReader

from ck.assemble import check_manifest, copy_exact, write_manifest
from ck.drive_safety import validate_tree
from ck.fetch import digest

INDEX_PATH = "4_PHONE_PACK/0_WHAT_TO_COPY.pdf"
MAP_INDEX_PATH = "3_MAPS_AND_PLACES/0_FIND_A_MAP.pdf"


def attach(
    base: Path,
    index: Path,
    receipt: Path,
    receipt_sha256: str,
    output: Path,
    base_provenance: Path | None = None,
    base_provenance_sha256: str | None = None,
) -> dict:
    external = output.with_name(output.name + ".provenance.json")
    if output.exists() or output.is_symlink() or external.exists() or external.is_symlink():
        raise ValueError("Choose a fresh output and provenance; no overwrite")
    if receipt.is_symlink() or digest(receipt) != receipt_sha256:
        raise ValueError("Index receipt checksum differs")
    metadata = json.loads(receipt.read_text())
    if base.is_symlink():
        raise ValueError("Symlink base is not allowed")
    check_manifest(base)
    source_pins = {
        relative: checksum
        for checksum, relative in (
            line.split("  ", 1) for line in (base / "MANIFEST.SHA256").read_text().splitlines()
        )
    }
    source_manifest = digest(base / "MANIFEST.SHA256")
    if metadata["source_manifest_sha256"] != source_manifest:
        raise ValueError("Index belongs to another base manifest")
    target = metadata["target_path"]
    if target not in {INDEX_PATH, MAP_INDEX_PATH}:
        raise ValueError("Unexpected index target")
    is_copy = target == INDEX_PATH
    inventory_key = "indexed_files" if is_copy else "indexed_maps"
    if not isinstance(metadata.get(inventory_key), list):
        raise ValueError("Index receipt lacks the target-specific inventory")
    if (
        index.is_symlink()
        or index.stat().st_size != metadata["pdf"]["size_bytes"]
        or digest(index) != metadata["pdf"]["sha256"]
    ):
        raise ValueError("Index PDF checksum or size differs")
    if len(PdfReader(index).pages) != metadata["pages"]:
        raise ValueError("Index PDF page count differs")
    originals = validate_tree(base)
    selected = {}
    for path in originals:
        relative = path.relative_to(base).as_posix()
        if relative in {target, "BACKUP/" + target}:
            raise ValueError("Base already contains the target index; no overwrite")
        if not is_copy and relative in {INDEX_PATH, "BACKUP/" + INDEX_PATH}:
            raise ValueError("Attach the map finder before generating the copy index")
        parts = path.relative_to(base).parts
        eligible = (
            (
                parts[0].casefold() != "backup"
                and path.suffix.lower() in {".pdf", ".mp4", ".apk", ".zim", ".obf"}
            )
            if is_copy
            else (
                len(parts) == 4
                and parts[0] == "3_MAPS_AND_PLACES"
                and parts[1].casefold() != "android"
                and path.suffix.lower() == ".pdf"
            )
        )
        if eligible:
            selected[relative] = {"sha256": digest(path), "size_bytes": path.stat().st_size}
    expected = {
        row["path"]: {"sha256": row["sha256"], "size_bytes": row["size_bytes"]}
        for row in metadata[inventory_key]
    }
    if len(expected) != len(metadata[inventory_key]) or selected != expected:
        raise ValueError("Index inventory differs from actual eligible base files")
    ancestor = None
    if base_provenance is not None or base_provenance_sha256 is not None:
        if (
            base_provenance is None
            or base_provenance.is_symlink()
            or digest(base_provenance) != base_provenance_sha256
        ):
            raise ValueError("Base provenance checksum differs")
        ancestor = json.loads(base_provenance.read_text())
        if ancestor["manifest_sha256"] != source_manifest:
            raise ValueError("Base provenance belongs to another tree")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-index-attach-", dir=output.parent) as temporary:
        tree = Path(temporary) / "tree"
        tree.mkdir()
        for source in originals:
            relative = source.relative_to(base)
            if relative.as_posix() != "MANIFEST.SHA256":
                copy_exact(source, tree / relative, source_pins[relative.as_posix()])
        for relative in (target, "BACKUP/" + target) if is_copy else (target,):
            copy_exact(index, tree / relative, metadata["pdf"]["sha256"])
        checksum = write_manifest(tree)
        check_manifest(tree)
        check_manifest(base)
        if digest(base / "MANIFEST.SHA256") != source_manifest:
            raise ValueError("Base changed during attachment")
        files = validate_tree(tree)
        result = {
            "status": "Incomplete local inspection with draft index; no release approval",
            "target_path": target,
            "index_kind": "copy" if is_copy else "map_finder",
            "base_manifest_sha256": source_manifest,
            "base_provenance": ancestor,
            "index_receipt_sha256": receipt_sha256,
            "index_receipt": metadata,
            "manifest_sha256": checksum,
            "normal_assembly_gates_changed": False,
            "files": [
                {
                    "path": p.relative_to(tree).as_posix(),
                    "sha256": digest(p),
                    "size_bytes": p.stat().st_size,
                }
                for p in files
            ],
        }
        for path in [*tree.rglob("*"), tree]:
            os.utime(path, (metadata["epoch"], metadata["epoch"]), follow_symlinks=False)
        if output.exists() or external.exists():
            raise ValueError("Output appeared during attachment; no overwrite")
        tree.rename(output)
        with external.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "index", "receipt", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--base-provenance", type=Path)
    parser.add_argument("--base-provenance-sha256")
    result = attach(**vars(parser.parse_args()))
    print(
        json.dumps(
            {"manifest_sha256": result["manifest_sha256"], "files": len(result["files"])}, indent=2
        )
    )


if __name__ == "__main__":
    main()
