"""Admit an authenticated medical-framing proof into a new local inspection clone."""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from pypdf import PdfReader

from ck.assemble import check_manifest, copy_exact, write_manifest
from ck.catalog import load_catalog
from ck.config import load_config
from ck.drive_safety import validate_tree
from ck.fetch import digest
from ck.generated import verified_generated_files
from ck.reference_recompose import exact_main
from tools.assemble_inspection_preview import authenticated_receipt, confined_file

INDEX = "4_PHONE_PACK/0_WHAT_TO_COPY.pdf"
PROJECT_NOTES = ("SUPPLEMENTARY_DRAFTS.TXT", "ADDITIONAL_DRAFTS.TXT")


def canonical(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def clinical_pair(old_html: Path, old_pdf: Path, new_html: Path, new_pdf: Path) -> str:
    bodies = []
    for html, pdf in ((old_html, old_pdf), (new_html, new_pdf)):
        text = html.read_bytes().decode("utf-8")
        identifiers = PdfReader(pdf).trailer.get("/ID")
        identity = getattr(identifiers[0], "original_bytes", None) if identifiers else None
        if identity != hashlib.sha256(text.encode()).hexdigest().encode("ascii"):
            raise ValueError("Clinical HTML is not bound to its actual PDF ID")
        bodies.append(exact_main(text).encode())
    if bodies[0] != bodies[1]:
        raise ValueError("Clinical main bytes changed")
    return hashlib.sha256(bodies[0]).hexdigest()


def medical_proof(
    root, parent, proof, generation_sha256, raw_generation_sha256, audit, audit_sha256, proof_source
):
    items = load_catalog(root)
    item = items["medical_phone_pdfs"]
    old, payloads = verified_generated_files(item, parent, items)
    for row in old["intermediates"]:
        path = confined_file(parent, row["path"])
        if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
            raise ValueError("Historical medical intermediate changed")
    new = authenticated_receipt(proof / "generation.json", raw_generation_sha256)
    if canonical(new) != generation_sha256 or new["complete"] is not True:
        raise ValueError("New proof generation identity or completeness differs")
    if new["source_date_epoch"] != old["source_date_epoch"]:
        raise ValueError("Medical proof epoch differs")
    if new["inputs"].get(item.id) != item.sha256:
        raise ValueError("Proof does not bind the current historical parent catalog pin")
    for key, pin in new["inputs"].items():
        if key != item.id and (items[key].family != "fonts" or items[key].sha256 != pin):
            raise ValueError("Proof font pin differs from current parent catalog")
    for row in new["intermediates"]:
        path = confined_file(proof, row["path"])
        if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
            raise ValueError("New proof intermediate changed")
    report = authenticated_receipt(audit, audit_sha256)
    if (
        report["canonical_generation_sha256"] != generation_sha256
        or report["raw_generation_sha256"] != raw_generation_sha256
        or report["original_review_holds"] != item.review
        or report["pdf_count"] != 158
        or any(
            report.get(key) is not True
            for key in [
                "complete",
                "all_expected_paths_present",
                "original_order_preserved",
                "every_clinical_main_bytes_unchanged",
                "every_payload_intermediate_rehashed",
                "all_new_pdf_ids_match_html",
                "all_dates_match_epoch",
                "source_license_links_retained_every_pdf",
                "license_readme_archive_audits_byte_identical",
                "all_fonts_preserved",
                "all_pdfs_within_budget",
            ]
        )
    ):
        raise ValueError("Full medical audit does not bind this complete proof and its holds")
    recomposition = json.loads((proof / "recomposition.json").read_text())
    if recomposition["original"]["canonical_generation_sha256"] != item.sha256:
        raise ValueError("Recomposition parent identity differs")
    for relative, pin in recomposition["source_files"].items():
        if digest(confined_file(proof_source, relative)) != pin:
            raise ValueError("Recorded proof producer source changed")
    old_rows = json.loads((parent / "articles.json").read_text())
    new_rows = json.loads((proof / "articles.json").read_text())
    old_files = {r["path"]: r for r in old["files"]}
    new_files = {r["path"]: r for r in new["files"]}
    if (
        len(new_files) != len(new["files"])
        or set(old_files) != set(new_files)
        or len(old_rows) != 158
        or len(new_rows) != 158
        or len({r["id"] for r in new_rows}) != 158
    ):
        raise ValueError("Exact original medical path/topic membership differs")
    checks = []
    for number, (before, after) in enumerate(zip(old_rows, new_rows, strict=True), 1):
        if {k: v for k, v in before.items() if k != "pages"} != {
            k: v for k, v in after.items() if k != "pages"
        }:
            raise ValueError("Original article identity, revision, or license metadata changed")
        name = f"{number:03d}_{before['id']}.pdf"
        old_pdf = payloads[name]
        new_pdf = confined_file(proof, "files/" + name)
        row = new_files[name]
        if new_pdf.stat().st_size != row["size_bytes"] or digest(new_pdf) != row["sha256"]:
            raise ValueError("New medical payload differs")
        main_sha = clinical_pair(
            confined_file(parent, "audit/" + name[:-4] + ".html"),
            old_pdf,
            confined_file(proof, "audit/" + name[:-4] + ".html"),
            new_pdf,
        )
        checks.append({"path": name, "id": before["id"], "clinical_main_sha256": main_sha})
    for name, row in new_files.items():
        path = confined_file(proof, "files/" + name)
        if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
            raise ValueError("New proof notice or payload changed")
        if not name.endswith(".pdf") and name != "README.TXT" and row != old_files[name]:
            raise ValueError("Required source/license notice must remain byte-identical")
    if report["new_recipe"] != new["pipeline_version"]:
        raise ValueError("Audited medical recipe differs")
    return item, old, new, report, recomposition, checks


def admit(
    *,
    root: Path,
    base: Path,
    base_provenance: Path,
    base_sha256: str,
    parent: Path,
    proof: Path,
    generation_sha256: str,
    raw_generation_sha256: str,
    audit: Path,
    audit_sha256: str,
    proof_source: Path,
    output: Path,
) -> dict:
    external = output.with_name(output.name + ".provenance.json")
    if output.exists() or output.is_symlink() or external.exists() or external.is_symlink():
        raise ValueError("Choose a fresh proof clone; no overwrite")
    ancestor = authenticated_receipt(base_provenance, base_sha256)
    check_manifest(base)
    if digest(base / "MANIFEST.SHA256") != ancestor["manifest_sha256"]:
        raise ValueError("Base tree and pinned ancestor differ")
    originals = {p.relative_to(base).as_posix(): p for p in validate_tree(base)}
    expected_base = {r["path"]: r for r in ancestor["files"]}
    if set(expected_base) != set(originals):
        raise ValueError("Ancestor inventory differs from actual base")
    for name, path in originals.items():
        row = expected_base[name]
        if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
            raise ValueError("Base differs from pinned ancestor")
    item, old, new, audit_data, recomposition, checks = medical_proof(
        root,
        parent,
        proof,
        generation_sha256,
        raw_generation_sha256,
        audit,
        audit_sha256,
        proof_source,
    )
    old_rows = {r["path"]: r for r in old["files"]}
    new_rows = {r["path"]: r for r in new["files"]}
    prefix = item.dest.rstrip("/") + "/"
    if {name[len(prefix) :] for name in originals if name.startswith(prefix)} != set(old_rows):
        raise ValueError("Base medical path set is not the complete historical pack")
    for name, row in old_rows.items():
        path = originals[prefix + name]
        if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
            raise ValueError("Base medical PDF or notice differs from historical catalog parent")
    moves = {name: "7_LAPTOP/Source notes/" + name for name in PROJECT_NOTES if name in originals}
    if any(target in originals for target in moves.values()):
        raise ValueError("Project-note relocation collides with an existing file")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".ck-medical-admission-", dir=output.parent
    ) as temporary:
        tree = Path(temporary) / "tree"
        tree.mkdir()
        replaced = []
        for name, path in originals.items():
            if name in {"MANIFEST.SHA256", "VERIFY.TXT", "README.TXT", INDEX, "BACKUP/" + INDEX}:
                continue
            if name.startswith(prefix):
                relative = name[len(prefix) :]
                row = new_rows[relative]
                source = confined_file(proof, "files/" + relative)
                copy_exact(source, tree / name, row["sha256"])
                if row != old_rows[relative]:
                    replaced.append(name)
            else:
                copy_exact(path, tree / moves.get(name, name), expected_base[name]["sha256"])
        readme = (base / "README.TXT").read_text()
        readme += (
            "\nFor shorter medical basics, open the two 00_ PDFs in 5_MEDICAL_REFERENCE/.\n"
            "Medical content and physical-phone checks still need human review.\n"
        )
        (tree / "README.TXT").write_text(readme)
        verification = (base / "VERIFY.TXT").read_text()
        verification = (
            "\n".join(
                line + "; medical framing proof " + audit_data["source_commit"]
                if line.startswith("Source:")
                else line
                for line in verification.splitlines()
            )
            + "\n"
        )
        verification += (
            "\nMedical framing PROOF: " + audit_data["source_commit"] + "\n"
            "New proof generation: " + generation_sha256 + "\n"
            "Historical parent catalog pin remains: " + item.sha256 + "\n"
            "Exact clinical main bodies preserved. Not a normal catalog placement or release.\n"
        )
        (tree / "VERIFY.TXT").write_text(verification)
        files = validate_tree(tree)
        maximum = load_config(root).build.pdf.max_file_bytes
        if any(p.suffix.lower() == ".pdf" and p.stat().st_size > maximum for p in files):
            raise ValueError("Proof clone exceeds a configured PDF byte limit")
        for path in (tree / "4_PHONE_PACK").rglob("*"):
            if path.is_file() and digest(path) != digest(tree / "BACKUP" / path.relative_to(tree)):
                raise ValueError("Phone-pack backup differs")
        for path in (tree / "1_START").rglob("*"):
            if path.is_file() and digest(path) != digest(tree / "BACKUP" / path.relative_to(tree)):
                raise ValueError("START backup differs")
        checksum = write_manifest(tree)
        check_manifest(tree)
        check_manifest(base)
        if digest(base / "MANIFEST.SHA256") != ancestor["manifest_sha256"]:
            raise ValueError("Source base changed during proof admission")
        result = {
            "status": "Incomplete local medical framing PROOF; no review or release approval",
            "variant": 1,
            "profile": "local-inspection",
            "epoch": new["source_date_epoch"],
            "normal_assembly_gates_changed": False,
            "catalog_pin_unchanged": item.sha256,
            "base": {"provenance_sha256": base_sha256, "provenance": ancestor},
            "medical_proof": {
                "canonical_generation_sha256": generation_sha256,
                "raw_generation_sha256": raw_generation_sha256,
                "generation": new,
                "audit_sha256": audit_sha256,
                "audit": audit_data,
                "recomposition": recomposition,
                "original_generation": old,
                "clinical_admission_checks": checks,
                "review_hold": item.review,
                "technical_complete": new["complete"],
                "normal_catalog_pin_matches_new_proof": False,
            },
            "relocations": moves,
            "absent_optional_project_notes": [n for n in PROJECT_NOTES if n not in originals],
            "replaced_files": replaced,
            "copy_index": "Pending final folder reorganization; no stale index retained",
            "manifest_sha256": checksum,
            "files": [
                {
                    "path": p.relative_to(tree).as_posix(),
                    "sha256": digest(p),
                    "size_bytes": p.stat().st_size,
                }
                for p in validate_tree(tree)
            ],
        }
        result["file_count"] = len(result["files"])
        result["total_bytes"] = sum(r["size_bytes"] for r in result["files"])
        for path in [*tree.rglob("*"), tree]:
            os.utime(
                path, (new["source_date_epoch"], new["source_date_epoch"]), follow_symlinks=False
            )
        if output.exists() or external.exists():
            raise ValueError("Output appeared; no overwrite")
        tree.rename(output)
        with external.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "root",
        "base",
        "base-provenance",
        "parent",
        "proof",
        "audit",
        "proof-source",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("base-sha256", "generation-sha256", "raw-generation-sha256", "audit-sha256"):
        parser.add_argument("--" + name, required=True)
    result = admit(**vars(parser.parse_args()))
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("status", "file_count", "total_bytes", "manifest_sha256", "relocations")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
