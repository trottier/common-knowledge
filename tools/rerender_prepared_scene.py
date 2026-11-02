"""Render an authenticated scene with explicit visible names under a fresh source recipe."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from ck.countyproof import producer_recipe, render
from ck.fetch import digest
from tools.assemble_inspection_preview import authenticated_receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "scene", "policy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--scene-sha256", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Fresh output required; do not overwrite an earlier recipe")
    data = authenticated_receipt(args.scene, args.scene_sha256)
    policy = json.loads(args.policy.read_text())
    if set(policy) != {"area_name", "overview_filename", "expected_zctas", "status"}:
        raise ValueError("Only visible names/status may change in this rerender")
    if policy["expected_zctas"] != data["zctas"]:
        raise ValueError("Visible name does not match authenticated ZIP scope")
    for font in data["fonts"]:
        if digest(Path(font["path"])) != font["sha256"]:
            raise ValueError("Prepared font changed")
    previous = data["producer"]
    source = producer_recipe(args.root, args.root / "pipelines/atlas/kent-proof.json")
    binding = {
        "input_scene_sha256": args.scene_sha256,
        "previous_producer": previous,
        "render_source": source,
        "visible_policy_sha256": digest(args.policy),
        "visible_policy": policy,
        "helper_sha256": digest(Path(__file__)),
    }
    h = hashlib.sha256(
        json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    data["policy"] = {**data["policy"], **policy}
    data["producer"] = {"version": "named-prepared-scene-v1-" + h, **binding}
    args.output.mkdir(parents=True)
    (args.output / "scene.json").write_text(json.dumps(data, indent=2) + "\n")
    started = time.monotonic()
    result = render(args.root, data, args.output / "proof")
    receipt = {
        "status": "Unreviewed partial county proof; geometry/roads unchanged",
        "scene_sha256": digest(args.output / "scene.json"),
        "input_scene_sha256": args.scene_sha256,
        "prototype_sha256": digest(args.output / "proof/prototype.json"),
        "prototype": result,
        "wall_seconds": time.monotonic() - started,
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "prototype_sha256": receipt["prototype_sha256"],
                "files": result["files"],
                "wall_seconds": receipt["wall_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
