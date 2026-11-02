"""Render one actual partial-county leaf from a pinned scene and measured split trigger."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from shapely.geometry import shape

from ck.countyparts import plan_county_parts
from ck.countyproof import producer_recipe, render
from ck.fetch import digest
from ck.preparedparts import part_scene
from tools.assemble_inspection_preview import authenticated_receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "prepared", "label-result", "limits", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("prepared-sha256", "label-result-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument(
        "--part-id", help="Omit to choose the smallest actual named-context ZIP leaf"
    )
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Fresh attempt output required")
    data = authenticated_receipt(args.prepared, args.prepared_sha256)
    label = authenticated_receipt(args.label_result, args.label_result_sha256)
    if label["prepared_sha256"] != args.prepared_sha256 or label.get("cap_failure") is not True:
        raise ValueError("A confirmed page-limit failure is required before splitting")
    limits = json.loads(args.limits.read_text())
    for font in data["fonts"]:
        if digest(Path(font["path"])) != font["sha256"]:
            raise ValueError("Prepared font changed")
    county = shape(data["county"])

    def evaluate(geometry, codes):
        if geometry.equals(county):
            return {
                "kind": "measured",
                "page_limit_exceeded": True,
                "evidence": "Actual named-label failure in pinned result "
                + args.label_result_sha256,
            }
        return {"kind": "unknown", "pages": None, "bytes": None}

    started = time.monotonic()
    plan = plan_county_parts(data, evaluate, limits)
    candidates = []
    for part in plan["parts"]:
        if args.part_id and part["id"] != args.part_id:
            continue
        if not args.part_id and not part["zctas"]:
            continue
        scene = part_scene(data, part, limits["coverage_tolerance_m2"])
        named = sum(bool(row["name"]) for row in scene["roads"])
        if not args.part_id and named == 0:
            continue
        candidates.append((named, part["id"], part, scene))
    if not candidates:
        raise ValueError("No selected part")
    named, identifier, part, scene = min(candidates, key=lambda row: (row[0], row[1]))
    files = {
        **producer_recipe(args.root, args.root / "pipelines/atlas/kent-proof.json")["source_files"],
        "src/ck/countyparts.py": digest(args.root / "src/ck/countyparts.py"),
        "src/ck/preparedparts.py": digest(args.root / "src/ck/preparedparts.py"),
        "tools/render_prepared_part.py": digest(Path(__file__)),
        "pipelines/atlas/kent-parts.json": digest(args.limits),
    }
    binding = {
        "prepared_sha256": args.prepared_sha256,
        "preparation_producer": data["producer"],
        "render_source_files": files,
        "measured_label_result_sha256": args.label_result_sha256,
        "limits": limits,
        "part": part,
    }
    encoded = json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()
    scene["producer"] = {
        "version": "prepared-county-part-v1-" + hashlib.sha256(encoded).hexdigest(),
        **binding,
    }
    args.output.mkdir(parents=True)
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    (args.output / "scene.json").write_text(json.dumps(scene, indent=2) + "\n")
    receipt = {
        "status": "Partial county engineering proof; remaining areas are not built",
        "part_id": identifier,
        "zctas": part["zctas"],
        "context_named_ways": named,
        "parent_frame_audit": scene["parent_frame_audit"],
        "producer": scene["producer"],
        "plan_sha256": digest(args.output / "plan.json"),
        "scene_sha256": digest(args.output / "scene.json"),
    }
    try:
        result = render(args.root, scene, args.output / "proof")
        receipt.update(
            complete_leaf=True,
            prototype=result,
            prototype_sha256=digest(args.output / "proof/prototype.json"),
        )
    except ValueError as error:
        receipt.update(complete_leaf=False, actual_failure=str(error))
    receipt["wall_seconds"] = time.monotonic() - started
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: receipt.get(key)
                for key in (
                    "complete_leaf",
                    "part_id",
                    "zctas",
                    "context_named_ways",
                    "wall_seconds",
                    "actual_failure",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
