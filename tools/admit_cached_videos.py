"""Admit two authenticated cached video packets to a fresh local inspection clone."""

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

from ck.assemble import check_manifest, copy_exact, write_manifest
from ck.catalog import Topics, load_catalog, safe_path
from ck.config import load_config, read_yaml
from ck.drive_safety import validate_tree
from ck.fetch import digest
from ck.generated import cached_input, verified_generated_files
from ck.video import (
    Clip,
    VideoSettings,
    check_faststart,
    language_codes,
    probe,
    validate_video,
    video_rights_allowed,
)
from tools.assemble_inspection_preview import authenticated_receipt, confined_file
from tools.attach_copy_index import INDEX_PATH

SELECTED = {"cdc_handwashing_asl": "handwashing_asl", "fema_be_prepared": "be_prepared"}


def packets(root, cache, outputs, epoch):
    """Authenticate current rights/pins and actual tracks without relabeling old recipes."""
    if set(outputs) != set(SELECTED):
        raise ValueError("Select exactly the two audited video packets")
    config = load_config(root)
    if config.variants.offline_ai_enabled:
        raise ValueError("This milestone excludes offline AI")
    items = load_catalog(root, config)
    settings = VideoSettings.model_validate(read_yaml(root / "pipelines/video/settings.yaml"))
    clips = read_yaml(root / "pipelines/video/clips.yaml")
    closure, pending = {}, list(SELECTED)
    while pending:
        key = pending.pop()
        if key in closure:
            continue
        item = items[key]
        hard = [p for p in item.blockers() if not p.startswith(key + ".review:")]
        if hard or re.search(
            r"unknown|unconfirmed|unclear|unresolved|missing permission|written permission|"
            r"license compatibility|per-file license inventory",
            item.review or "",
            re.I,
        ):
            raise ValueError(f"Unresolved source rights or pins: {key}")
        closure[key] = {"catalog": item.model_dump(mode="json")}
        if item.family != "generated":
            closure[key].update(cache_sha256=digest(cached_input(item, cache)), redistributed=False)
        pending.extend(item.inputs)
        if item.source_id:
            pending.append(item.source_id)
    codes = language_codes(cached_input(items[settings.language_codes_id], cache), config)
    bindings, components = {}, []
    for key, clip_name in SELECTED.items():
        item, output = items[key], outputs[key]
        placement = item.placement
        if item.family != "generated" or not (
            placement == "universal"
            or isinstance(placement, Topics)
            and set(placement.topics) & set(config.variants.variants[1].topics)
        ):
            raise ValueError("Not a selected Variant 1 video")
        validate_tree(output)
        metadata, files = verified_generated_files(item, output, items)
        if metadata.get("source_date_epoch") != epoch or not metadata.get("tool_versions"):
            raise ValueError("Historical epoch or environment differs")
        clip = Clip.model_validate(clips[clip_name])
        expected = {clip.filename, clip.filename.removesuffix(".mp4") + "_SOURCE.TXT"}
        if set(files) != expected or set(files) != {
            p.relative_to(output / "files").as_posix() for p in validate_tree(output / "files")
        }:
            raise ValueError("Packet must retain exactly the MP4 and its source notice")
        if not video_rights_allowed(items[clip.source_id]):
            raise ValueError("Video lacks supported per-item rights proof")
        for row in metadata.get("intermediates", []):
            path = confined_file(output, row["path"])
            if path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
                raise ValueError("Historical video audit differs")
        report = probe(files[clip.filename])
        validate_video(report, clip, settings, codes, [lang.code for lang in config.languages])
        check_faststart(files[clip.filename])
        destinations = []
        for name, source in files.items():
            destination = (safe_path(item.dest) / safe_path(name)).as_posix()
            if destination in bindings:
                raise ValueError("Video destination collision")
            bindings[destination] = source
            destinations.append(destination)
        components.append(
            {
                "id": key,
                "catalog": item.model_dump(mode="json"),
                "original_generation_path": str(output / "generation.json"),
                "original_generation_file_sha256": digest(output / "generation.json"),
                "historical_generation": metadata,
                "destinations": destinations,
                "actual_probe": report,
            }
        )
    return config, bindings, {"components": components, "source_closure": closure}


def admit(
    *,
    root,
    cache,
    outputs,
    base,
    base_manifest_sha256,
    base_provenance,
    base_provenance_sha256,
    output,
    epoch,
):
    external = output.with_name(output.name + ".provenance.json")
    for path in (output, external):
        if path.exists() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("Choose fresh output and provenance; no overwrite or symlinks")
    for source in (root, cache, base, *outputs.values()):
        if output.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(
            output.resolve()
        ):
            raise ValueError("Output overlaps an input")
    if digest(confined_file(base, "MANIFEST.SHA256")) != base_manifest_sha256:
        raise ValueError("Base manifest differs")
    check_manifest(base)
    ancestor = authenticated_receipt(base_provenance, base_provenance_sha256)
    if ancestor.get("manifest_sha256") != base_manifest_sha256:
        raise ValueError("Ancestor does not bind the base manifest")
    config, bindings, proof = packets(root, cache, outputs, epoch)
    originals = {p.relative_to(base).as_posix(): p for p in validate_tree(base)}
    if set(bindings) & set(originals):
        raise ValueError("Video collides with an existing file")
    for name, source in originals.items():
        if name.startswith(("1_START/", "4_PHONE_PACK/")) and digest(
            confined_file(base, "BACKUP/" + name)
        ) != digest(source):
            raise ValueError("Base backup differs")
    removed = {INDEX_PATH, "BACKUP/" + INDEX_PATH}
    if not removed <= set(originals):
        raise ValueError("Expected old copy index and backup")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ck-videos-", dir=output.parent) as temporary:
        tree = Path(temporary) / "tree"
        tree.mkdir()
        for name, source in originals.items():
            if name not in removed | {"MANIFEST.SHA256"}:
                copy_exact(source, tree / name, digest(source))
        for name, source in bindings.items():
            copy_exact(source, tree / name, digest(source))
        readme = tree / "README.TXT"
        previous = readme.read_text()
        old = "Still missing: Android and laptop reader apps, mesh apps, videos,\n"
        if previous.count(old) != 1:
            raise ValueError("Unrecognized omission text; inspect rather than guess")
        readme.write_text(
            previous.replace(
                old, "Still missing: Android and laptop reader apps, mesh apps, more videos,\n"
            )
            + "\nVideos: handwashing in 2_VIDEOS/; Be Prepared in\n"
            "6_VIDEOS_AND_IN_DEPTH/topics/convening/. English audio only.\n"
            "Be Prepared includes publisher English subtitles.\n"
            "Video safety, currency, caption, and physical-phone reviews remain pending.\n"
        )
        with (tree / "VERIFY.TXT").open("a") as stream:
            stream.write(
                "\nTwo cached videos added for local draft inspection.\n"
                "Original generation recipes and epochs retained in external provenance.\n"
                "This is not normal sample assembly or a release.\n"
            )
        files = validate_tree(tree)
        if any(
            p.suffix.lower() == ".pdf" and p.stat().st_size > config.build.pdf.max_file_bytes
            for p in files
        ):
            raise ValueError("PDF exceeds configured byte budget")
        if any(p.relative_to(tree).parts[0] in {"9_OFFLINE_AI", "9_LOCAL_LLM"} for p in files):
            raise ValueError("No offline AI in this milestone")
        manifest = write_manifest(tree)
        check_manifest(tree)
        check_manifest(base)
        if digest(base / "MANIFEST.SHA256") != base_manifest_sha256:
            raise ValueError("Base changed during admission")
        result = {
            "status": "Incomplete local draft inspection; no release approval",
            "variant": 1,
            "profile": "local-inspection",
            "epoch": epoch,
            "normal_assembly_gates_changed": False,
            "admission_tool_sha256": digest(Path(__file__)),
            "base": {
                "manifest_sha256": base_manifest_sha256,
                "provenance_path": str(base_provenance),
                "provenance_sha256": base_provenance_sha256,
            },
            "cached_videos": proof,
            "removed_stale_indexes": sorted(removed),
            "modified_navigation": ["README.TXT", "VERIFY.TXT"],
            "copy_index": "Pending regeneration from this actual tree",
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
            raise ValueError("Output appeared during admission")
        tree.rename(output)
        with external.open("x") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "cache", "base", "base-provenance", "output", *SELECTED):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    for name in ("base-manifest-sha256", "base-provenance-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--epoch", type=int, required=True)
    args = vars(parser.parse_args())
    args["outputs"] = {key: args.pop(key) for key in SELECTED}
    result = admit(**args)
    print(
        json.dumps(
            {"manifest_sha256": result["manifest_sha256"], "files": len(result["files"])}, indent=2
        )
    )


if __name__ == "__main__":
    main()
