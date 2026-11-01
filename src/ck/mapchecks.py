"""Check every regional object before publishing a mixed national map collection."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from ck.catalog import Item, safe_path
from ck.fetch import digest
from ck.generated import generation_manifest
from ck.mapsplit import collect_mixed_maps, split_version


def checked_collection_version(root: Path) -> str:
    recipe = hashlib.sha256(split_version(root).encode())
    recipe.update((root / "src/ck/mapchecks.py").read_bytes())
    return "android-set-checked-v1-" + recipe.hexdigest()


def verify_region_subset(source: Path, region: Path, temporary: Path) -> dict:
    """Compare a region with original objects selected only by its object IDs."""
    reference = temporary / "original-region.osm.pbf"
    if reference.exists() or reference.is_symlink():
        raise ValueError("Subset reference output must be new")
    try:
        references = subprocess.run(
            ["osmium", "check-refs", "--check-relations", str(region)],
            capture_output=True,
            text=True,
        )
        if references.returncode:
            raise ValueError(
                f"Regional source has missing object references: {region.name}; "
                + references.stderr
            )
        selected = subprocess.run(
            [
                "osmium",
                "getid",
                str(source),
                "--id-osm-file",
                str(region),
                "--output",
                str(reference),
            ],
            capture_output=True,
            text=True,
        )
        if selected.returncode:
            raise ValueError(
                f"Regional source IDs are not an original-source subset: {region.name}; "
                + selected.stderr
            )
        compared = subprocess.run(
            ["osmium", "diff", "--quiet", str(reference), str(region)],
            capture_output=True,
            text=True,
        )
        if compared.returncode:
            raise ValueError(
                f"Regional source objects differ from the original: {region.name}; "
                + compared.stderr
            )
        return {
            "region_sha256": digest(region),
            "reference_sha256": digest(reference),
            "all_objects_and_attributes_equal": True,
        }
    finally:
        reference.unlink(missing_ok=True)


def collect_checked_maps(
    root: Path, items: dict[str, Item], cache: Path, outputs: list[Path], output: Path, epoch: int
) -> dict:
    """Add exact subset checks without changing frozen per-state producer recipes."""
    if output.exists():
        raise ValueError("Checked Android collection output must be new")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ck-checked-maps-") as temporary:
        stage = Path(temporary)
        candidate = stage / "collection"
        collect_mixed_maps(root, items, cache, outputs, candidate, epoch)
        # The lower collector has already bound every original payload, part
        # path, and audit to the catalog, and checked the complete jurisdiction set.
        proofs = {}
        for folder in outputs:
            metadata = json.loads((folder / "generation.json").read_text())
            if not metadata["pipeline_version"].startswith("android-split-v1-"):
                continue
            plan = json.loads((folder / "parts.json").read_text())
            state = plan["state"]
            source = candidate / "files/data" / f"{state}_roads_places.osm.pbf"
            regions = []
            for part in plan["parts"]:
                relative = str(safe_path(part["source_path"]))
                regions.append(
                    {
                        "source_path": relative,
                        **verify_region_subset(source, folder / relative, stage),
                    }
                )
            proofs[state] = {"source_sha256": digest(source), "regions": regions}
        proof_path = candidate / "regional-subsets.json"
        proof_path.write_text(json.dumps(proofs, sort_keys=True, indent=2) + "\n")
        baseline = candidate / "generation.json"
        metadata = json.loads(baseline.read_text())
        baseline.rename(candidate / "collection-generation.json")
        versions = subprocess.run(
            ["osmium", "--version"], check=True, capture_output=True, text=True
        )
        result = generation_manifest(
            candidate,
            checked_collection_version(root),
            metadata["inputs"],
            complete=True,
            epoch=epoch,
            intermediates=[
                *[entry["path"] for entry in metadata["intermediates"]],
                "collection-generation.json",
                "regional-subsets.json",
            ],
            tool_versions=versions.stdout + versions.stderr,
        )
        candidate.rename(output)
    return {**result, "jurisdictions": len(outputs), "split_jurisdictions": len(proofs)}
