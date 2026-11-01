"""Stage verified variant builds and compare independent image builds."""

import json
import re
import shutil
import tempfile
from pathlib import Path

from ck.assemble import assemble, core_size
from ck.catalog import load_catalog
from ck.config import load_config
from ck.core import build_core
from ck.fetch import digest
from ck.image import build_image
from ck.planner import plan_variants
from ck.render import epoch_for
from ck.review import require_release_ready


def check_profile(root: Path, profile: str, variants: list[int] | None = None) -> list[dict]:
    from ck.preparation import selected_variants

    config = load_config(root)
    numbers = selected_variants(config, variants)
    if profile == "full":
        require_release_ready(root)
    plans = [
        plan
        for plan in plan_variants(config, load_catalog(root, config), profile, 0)
        if plan.variant in numbers
    ]
    blockers = sorted({problem for plan in plans for problem in plan.blockers})
    if blockers:
        raise ValueError(f"{profile} profile is not ready:\n" + "\n".join(blockers))
    return [plan.as_dict() for plan in plans]


def build_profile(
    root: Path,
    output: Path,
    cache: Path,
    generated: Path,
    profile: str,
    variants: list[int],
    epoch: int | None = None,
    reproduce: bool = False,
    keep_raw: bool = False,
    commit: str | None = None,
) -> dict:
    config = load_config(root)
    if (
        not variants
        or len(set(variants)) != len(variants)
        or not set(variants) <= config.variants.variants.keys()
    ):
        raise ValueError("Choose distinct configured variants")
    check_profile(root, profile)
    timestamp = epoch_for(config, epoch)
    if profile == "full" and (
        config.build.source_date_epoch != timestamp
        or not commit
        or not re.fullmatch(r"[0-9a-f]{40}", commit)
    ):
        raise ValueError("Full builds need the confirmed epoch and exact source commit")
    if output.exists():
        raise ValueError("Build output must be new")
    output.mkdir(parents=True)
    core = output / "core"
    build_core(root, config, core, timestamp, profile=profile)
    plans = plan_variants(config, load_catalog(root, config), profile, core_size(core))
    if any(not plan.fits for plan in plans):
        raise ValueError("Rendered core makes a variant overflow or exposes an unresolved input")
    repeat_core = output / "repeat-core"
    if reproduce:
        build_core(root, config, repeat_core, timestamp, profile=profile)
    images = []
    for number in sorted(variants):
        with tempfile.TemporaryDirectory(dir=output, prefix=".ck-variant-") as temporary:
            tree = Path(temporary) / "tree"
            assemble(root, config, core, tree, number, profile, cache, generated, timestamp)
            result = build_image(tree, output / "images", config, number, profile, timestamp)
            sizes = {
                "image_size_bytes": Path(result["image"]).stat().st_size,
                "compressed_size_bytes": Path(result["compressed"]).stat().st_size,
            }
            if not keep_raw:
                Path(result["image"]).unlink()
            if reproduce:
                shutil.rmtree(tree)
                assemble(
                    root, config, repeat_core, tree, number, profile, cache, generated, timestamp
                )
                repeated = build_image(
                    tree, Path(temporary) / "repeat", config, number, profile, timestamp
                )
                if any(
                    result[key] != repeated[key]
                    for key in ("sha256", "compressed_sha256", "manifest_sha256")
                ):
                    raise ValueError(f"Variant {number} is not reproducible")
            images.append(
                {
                    "variant": number,
                    **sizes,
                    **{
                        key: Path(value).name
                        if key in {"image", "compressed", "manifest"}
                        else value
                        for key, value in result.items()
                    },
                }
            )
    summary = {
        "version": config.build.version,
        "profile": profile,
        "source_date_epoch": timestamp,
        "commit": commit,
        "reproduced": reproduce,
        "raw_images_retained": keep_raw,
        "core_manifest_sha256": digest(core / "core-manifest.json"),
        "variants": sorted(variants),
        "images": images,
    }
    (output / "build-manifest.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n"
    )
    return summary
