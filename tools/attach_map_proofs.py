"""Attach audited local county-place and partial-map packets to a fresh inspection tree."""

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from pypdf import PdfReader

from ck.assemble import check_manifest, copy_exact, write_manifest
from ck.catalog import load_catalog, safe_path
from ck.config import load_config
from ck.directory import Place
from ck.drive_safety import is_executable, validate_tree
from ck.fetch import digest
from tools.assemble_inspection_preview import authenticated_receipt, confined_file
from tools.extend_inspection_preview import records

STALE = {"3_MAPS_AND_PLACES/0_FIND_A_MAP.pdf", "4_PHONE_PACK/0_WHAT_TO_COPY.pdf"}
PLACES = "3_MAPS_AND_PLACES/RI/Bristol County/"


def source_pins(items, pins):
    """Release-date/review holds remain visible; unresolved rights and input pins do not pass."""
    pending, admitted = list(pins), {}
    while pending:
        key = pending.pop()
        if key in admitted:
            continue
        item = items[key]
        expected = pins.get(key)
        expected = expected.get("sha256") if isinstance(expected, dict) else expected
        if expected is not None and expected != item.sha256:
            raise ValueError("Source pin changed: " + key)
        allowed_holds = tuple(
            key + "." + field + ":"
            for field in ("review", "release_date", "release_date_source_url")
        )
        hard = [issue for issue in item.blockers() if not issue.startswith(allowed_holds)]
        rights = re.search(
            r"(?:unknown|unconfirmed|unclear|unresolved|missing).{0,35}(?:licens|rights|permission)"
            r"|(?:licens|rights|permission).{0,35}(?:unknown|unconfirmed|unclear|unresolved|missing)",
            item.review or "",
            re.I,
        )
        if (
            hard
            or rights
            or item.family not in {"geodata", "fonts", "maps", "generated", "binaries"}
        ):
            raise ValueError("Unresolved map source rights or pins: " + key)
        admitted[key] = item.model_dump(mode="json")
        pending.extend(item.inputs)
    return admitted


def historical(items, metadata):
    from hashlib import sha256

    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    candidates = [
        item
        for item in items.values()
        if item.family == "generated" and item.sha256 == sha256(encoded).hexdigest()
    ]
    if len(candidates) != 1:
        raise ValueError("Historical map/directory manifest is not a unique catalog pin")
    item = candidates[0]
    if (
        metadata["pipeline_version"] != item.pipeline_version
        or metadata["inputs"] != {key: items[key].sha256 for key in item.inputs}
        or sum(row["size_bytes"] for row in metadata["files"]) != item.size_bytes
    ):
        raise ValueError("Historical map/directory recipe or inputs changed")
    return source_pins(items, {item.id: item.sha256, **metadata["inputs"]})


def payloads(folder, entries, maximum):
    found = records(folder, entries)
    for relative in found:
        path = confined_file(folder, relative)
        if is_executable(path) or path.suffix.lower() not in {".pdf", ".txt", ".json"}:
            raise ValueError("Executable or unsupported map attachment")
        if path.suffix.lower() == ".pdf":
            if path.stat().st_size > maximum:
                raise ValueError("Map attachment exceeds the shared PDF cap")
            PdfReader(path)
    return found


def admit_places(base, folder, checksum, items, maximum, epoch):
    receipt_path = confined_file(folder, "receipt.json")
    receipt = authenticated_receipt(receipt_path, checksum)
    if receipt["complete"] is not False or receipt["epoch"] != epoch:
        raise ValueError("Places packet must retain its incomplete historical scope and epoch")
    expected = {
        PLACES + name
        for name in (
            "Bristol County - Places.pdf",
            "SOURCE.TXT",
            "SOURCE/Bristol County SOURCE_DATA.json",
        )
    }
    if {row["path"] for row in receipt["files"]} != expected:
        raise ValueError("Places packet contains unapproved or full-state cargo")
    found = payloads(folder / "files", receipt["files"], maximum)
    source = json.loads(
        confined_file(
            folder / "files", PLACES + "SOURCE/Bristol County SOURCE_DATA.json"
        ).read_text()
    )
    places = receipt["places"]
    if len(places) != 33 or [row["number"] for row in places] != list(range(1, 34)):
        raise ValueError("The audited Bristol packet must retain all 33 source records")
    parsed = [Place.model_validate(row["record"]) for row in places]
    derived = [Place.model_validate(row) for row in source["places"]]
    if (
        len({row.id for row in parsed}) != 33
        or any(row.county != "44001" for row in parsed)
        or [row.model_dump(exclude={"tags"}) for row in parsed]
        != [row.model_dump(exclude={"tags"}) for row in derived]
        or source["original_historical_source_sha256"] != receipt["source_payload_sha256"]
    ):
        raise ValueError("County-only place source differs or contains another county")
    for row in receipt["map_files"]:
        path = confined_file(base, row["path"])
        if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
            raise ValueError("Places refer to another map payload")
    for row in places:
        ref = row["map_reference"]
        path = confined_file(base, PLACES + ref["file"])
        if not 1 <= ref["page"] <= len(PdfReader(path).pages) or not re.fullmatch(
            r"[A-E][1-6]", ref["grid"]
        ):
            raise ValueError("Place map page or grid does not resolve")
    sources = historical(items, receipt["historical_directory_generation"])
    return found, {
        "kind": "county_places",
        "receipt_path": str(receipt_path),
        "receipt_sha256": checksum,
        "recipe": receipt["recipe"],
        "complete": False,
        "source_payload_sha256": receipt["source_payload_sha256"],
        "source_records": 33,
        "source_holds": sources,
    }


def admit_map(folder, checksum, wrapper_checksum, items, maximum, epoch):
    path = confined_file(folder, "prototype.json")
    proof = authenticated_receipt(path, checksum)
    wrapper_path = confined_file(folder.parent, "receipt.json")
    wrapper = authenticated_receipt(wrapper_path, wrapper_checksum)
    if wrapper["prototype_sha256"] != checksum or wrapper["prototype"] != proof:
        raise ValueError("Map wrapper and actual prototype differ")
    policy, scope = proof["policy"], proof["coverage_scope"]
    if policy["epoch"] != epoch or policy["state"] != "RI" or scope["whole_county"] is not False:
        raise ValueError("Map packet must retain its explicit partial RI scope and epoch")
    prefix = "3_MAPS_AND_PLACES/RI/" + policy["county_name"] + "/"
    names = {proof["detail_pdf"], policy["overview_filename"]}
    if "0_OVERVIEW.pdf" in names or len(names) != 2:
        raise ValueError("Partial area needs its own named overview")
    if {row["path"] for row in proof["files"]} != {prefix + name for name in names}:
        raise ValueError("Area map files must remain directly in their county folder")
    for name in names:
        if len(safe_path(name).parts) != 1:
            raise ValueError("Area map filename is not a safe leaf")
    expected = {row["path"]: row for row in proof["files"]}
    actual = {
        file.relative_to(folder).as_posix() for file in validate_tree(folder / "3_MAPS_AND_PLACES")
    }
    if actual != set(expected):
        raise ValueError("Area map directory has unlisted or missing cargo")
    for relative, row in expected.items():
        file = confined_file(folder, relative)
        if (
            file.suffix.lower() != ".pdf"
            or is_executable(file)
            or file.stat().st_size > maximum
            or file.stat().st_size != row["size_bytes"]
            or digest(file) != row["sha256"]
        ):
            raise ValueError("Area map payload differs, is oversized, or is not an inert PDF")
        PdfReader(file)
    coverage = proof["street_name_coverage"]
    if (
        coverage["complete"] is not True
        or coverage["missing_way_ids"]
        or coverage["expected_way_ids"] != coverage["labeled_way_ids"]
    ):
        raise ValueError("Area map street coverage is incomplete")
    sources = source_pins(items, proof["inputs"])
    for font in proof["fonts"]:
        sources.update(source_pins(items, {font["id"]: font["sha256"]}))
    sources.update(historical(items, proof["historical_basemap"]["manifest"]))
    sources.update(historical(items, proof["historical_points"]["manifest"]))
    return expected, {
        "kind": "partial_county_map",
        "prototype_path": str(path),
        "prototype_sha256": checksum,
        "receipt_path": str(wrapper_path),
        "receipt_sha256": wrapper_checksum,
        "producer": proof["producer"],
        "coverage_scope": scope,
        "status": proof["status"],
        "source_holds": sources,
    }


def lineage(base, provenance):
    """Check only the existing inspection ancestry formats, including actual preserved manifests."""
    available = {digest(path): path.parent for path in base.parent.glob("*/MANIFEST.SHA256")}
    available[digest(base / "MANIFEST.SHA256")] = base
    checked, seen = [], set()
    node = provenance
    while node is not None:
        checksum = node["manifest_sha256"]
        if checksum in seen:
            raise ValueError("Cyclic inspection ancestry")
        seen.add(checksum)
        if checksum not in available:
            raise ValueError("Preserved ancestor tree is missing")
        check_manifest(available[checksum])
        checked.append({"manifest_sha256": checksum, "tree": str(available[checksum])})
        child, expected = None, None
        for child_key, expected_key in (
            ("base_provenance", "base_manifest_sha256"),
            ("parent_provenance", "parent_manifest_sha256"),
        ):
            if isinstance(node.get(child_key), dict):
                child, expected = node[child_key], node[expected_key]
                break
        reference = node.get("base", {})
        if child is None and isinstance(reference, dict):
            child = reference.get("provenance")
            if reference.get("provenance_path"):
                child = authenticated_receipt(
                    Path(reference["provenance_path"]), reference["provenance_sha256"]
                )
            if child is not None:
                expected = reference.get("manifest_sha256", child["manifest_sha256"])
        if child is not None and child["manifest_sha256"] != expected:
            raise ValueError("Inspection ancestry manifest link differs")
        node = child
    return checked


def attach(*, root, base, base_provenance, base_sha256, places, places_sha256, maps, output, epoch):
    external = output.with_name(output.name + ".provenance.json")
    if any(path.exists() or path.is_symlink() for path in (output, external)):
        raise ValueError("Choose fresh output/provenance paths; no overwrite")
    for source in (root, base, places, *(row[0] for row in maps)):
        if output.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(
            output.resolve()
        ):
            raise ValueError("Output overlaps an input")
    config = load_config(root)
    if config.variants.offline_ai_enabled:
        raise ValueError("Offline AI remains disabled for this local milestone")
    prior = authenticated_receipt(base_provenance, base_sha256)
    if digest(confined_file(base, "MANIFEST.SHA256")) != prior["manifest_sha256"]:
        raise ValueError("Base manifest and pinned provenance differ")
    originals = records(base, prior["files"])
    ancestors = lineage(base, prior)
    items = load_catalog(root, config)
    admitted, descriptor = admit_places(
        base, places, places_sha256, items, config.build.pdf.max_file_bytes, epoch
    )
    layers = [(places / "files", admitted)]
    descriptors = [descriptor]
    for folder, checksum, wrapper_checksum in maps:
        admitted, descriptor = admit_map(
            folder, checksum, wrapper_checksum, items, config.build.pdf.max_file_bytes, epoch
        )
        layers.append((folder, admitted))
        descriptors.append(descriptor)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-map-attach-", dir=output.parent) as temporary:
        tree = Path(temporary) / "tree"
        tree.mkdir()
        for relative, row in originals.items():
            if relative == "MANIFEST.SHA256" or relative.startswith("BACKUP/") or relative in STALE:
                continue
            copy_exact(confined_file(base, relative), tree / relative, row["sha256"])
        for folder, entries in layers:
            for relative, row in entries.items():
                if (tree / relative).exists():
                    raise ValueError("Map attachment collides with existing cargo")
                copy_exact(confined_file(folder, relative), tree / relative, row["sha256"])
        with (tree / "README.TXT").open("a") as stream:
            stream.write(
                "\nMaps and public places: 3_MAPS_AND_PLACES/RI/.\n"
                "Kent maps cover selected areas only; other areas remain absent.\n"
            )
        for directory in ("1_START", "4_PHONE_PACK"):
            shutil.copytree(tree / directory, tree / "BACKUP" / directory)
        for file in validate_tree(tree):
            if (
                file.suffix.lower() == ".pdf"
                and file.stat().st_size > config.build.pdf.max_file_bytes
            ):
                raise ValueError("PDF exceeds configured byte budget")
        manifest = write_manifest(tree)
        check_manifest(tree)
        check_manifest(base)
        if digest(base / "MANIFEST.SHA256") != prior["manifest_sha256"]:
            raise ValueError("Base changed during map attachment")
        result = {
            "status": "Incomplete local map inspection; no release or human approval",
            "variant": 1,
            "profile": "local-inspection",
            "epoch": epoch,
            "normal_assembly_gates_changed": False,
            "base": {
                "manifest_sha256": prior["manifest_sha256"],
                "provenance_path": str(base_provenance),
                "provenance_sha256": base_sha256,
            },
            "ancestor_manifests_checked": ancestors,
            "attached_proofs": descriptors,
            "removed_stale_indexes": sorted(STALE),
            "next_steps": ["Rebuild and attach map finder", "Rebuild and attach copy index"],
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
        if output.exists() or external.exists():
            raise ValueError("Output appeared during attachment")
        tree.rename(output)
        with external.open("x") as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "base", "base-provenance", "places", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--base-sha256", required=True)
    parser.add_argument("--places-sha256", required=True)
    parser.add_argument(
        "--maps",
        nargs=3,
        action="append",
        required=True,
        metavar=("PROOF_DIR", "PROTOTYPE_SHA256", "RECEIPT_SHA256"),
    )
    parser.add_argument("--epoch", type=int, required=True)
    args = vars(parser.parse_args())
    args["maps"] = [(Path(folder), checksum, wrapper) for folder, checksum, wrapper in args["maps"]]
    result = attach(**args)
    print(
        json.dumps(
            {"manifest_sha256": result["manifest_sha256"], "files": len(result["files"])}, indent=2
        )
    )


if __name__ == "__main__":
    main()
