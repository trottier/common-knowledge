"""Command-line entry point; build commands arrive in later work-order steps."""

import argparse
import json
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    """Show CLI help or the installed package version."""
    parser = argparse.ArgumentParser(
        prog="ck",
        description="Build tools for the Common Knowledge offline emergency USB drive.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('common-knowledge')}"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    commands = parser.add_subparsers(dest="command")
    validate = commands.add_parser("validate", help="Validate configuration and catalog")
    validate.add_argument("--release", action="store_true")
    review = commands.add_parser("review-report", help="Inventory every remaining release gate")
    review.add_argument("--output", type=Path, required=True)
    language_audit = commands.add_parser(
        "languages-audit", help="Audit edition order against pinned ACS LEP estimates"
    )
    language_audit.add_argument("--cache", type=Path, default=Path("cache"))
    language_audit.add_argument("--output", type=Path, required=True)
    catalog = commands.add_parser("catalog", help="Generate third-party attributions")
    catalog.add_argument("--output", type=Path, default=Path("THIRD_PARTY.md"))
    fetch = commands.add_parser("fetch", help="Fetch pinned items into the verified cache")
    fetch.add_argument("items", nargs="+")
    fetch.add_argument("--cache", type=Path, default=Path("cache"))
    for operation in ("source-pack", "source-restore"):
        bundle = commands.add_parser(
            operation, help="Preserve or restore exact catalog source bytes"
        )
        bundle.add_argument("items", nargs="+")
        bundle.add_argument("--cache", type=Path, default=Path("cache"))
        if operation == "source-pack":
            bundle.add_argument("--output", type=Path, required=True)
            bundle.add_argument("--epoch", type=int)
        else:
            bundle.add_argument("--bundle", type=Path, required=True)
            bundle.add_argument("--sha256", required=True)
    coverage = commands.add_parser("coverage", help="Show findability of topics and collections")
    coverage.add_argument("--homes", type=int, default=5)
    coverage.add_argument("--carriers", type=int)
    coverage.add_argument("--json", action="store_true")
    render = commands.add_parser("render", help="Render a source document to an offline PDF")
    render.add_argument("--input", type=Path, required=True)
    render.add_argument("--language", default="en")
    render.add_argument("--format", choices=["phone", "print"], default="phone")
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--epoch", type=int)
    core = commands.add_parser("core", help="Build START, card, tags and variant guide")
    core.add_argument("--output", type=Path, default=Path("build/core"))
    core.add_argument("--epoch", type=int)
    core.add_argument("--languages", nargs="+", help="Edition codes; defaults to all fifteen")
    core.add_argument("--profile", choices=["dev", "sample", "full"], default="dev")
    directory = commands.add_parser("directory", help="Build a checked public-places directory")
    directory.add_argument("--state", required=True)
    directory.add_argument("--state-fips", required=True)
    directory.add_argument("--osm-id", default="geofabrik_ri")
    directory.add_argument("--cache", type=Path, default=Path("cache"))
    directory.add_argument("--output", type=Path, required=True)
    directory.add_argument("--atlas-index", type=Path)
    directory.add_argument("--atlas-id")
    directory.add_argument("--points", type=Path)
    directory.add_argument("--points-id")
    directory.add_argument(
        "--seed", action="store_true", help="Build atlas points before PDF page references exist"
    )
    directory.add_argument("--epoch", type=int)
    for name in ("directory-all", "directory-collect"):
        batch = commands.add_parser(name, help="Build or collect bounded national directory PDFs")
        batch.add_argument("--points", type=Path, required=True)
        batch.add_argument("--points-id", default="directory_points")
        batch.add_argument("--atlas", type=Path, required=True)
        batch.add_argument("--atlas-id", default="national_atlas")
        batch.add_argument("--output", type=Path, required=True)
        batch.add_argument("--epoch", type=int)
        if name == "directory-all":
            batch.add_argument("--states", nargs="+")
            batch.add_argument("--jobs", type=int)
        else:
            batch.add_argument("--outputs", type=Path, nargs="+", required=True)
    national = commands.add_parser(
        "national-points", help="Prepare all national directory points once"
    )
    national.add_argument("--cache", type=Path, default=Path("cache"))
    national.add_argument("--output", type=Path, required=True)
    national.add_argument("--epoch", type=int)
    laptop_tiles = commands.add_parser(
        "laptop-tiles", help="Regenerate the laptop collection's narrow offline vector basemap"
    )
    laptop_tiles.add_argument("--generated", type=Path, default=Path("build/generated"))
    laptop_tiles.add_argument("--output", type=Path, required=True)
    laptop_tiles.add_argument("--epoch", type=int)
    laptop_viewer = commands.add_parser(
        "laptop-viewer", help="Package the offline browser map and unchanged SDK files"
    )
    laptop_viewer.add_argument("--generated", type=Path, default=Path("build/generated"))
    laptop_viewer.add_argument("--cache", type=Path, default=Path("cache"))
    laptop_viewer.add_argument("--output", type=Path, required=True)
    laptop_viewer.add_argument("--epoch", type=int)
    android_map = commands.add_parser("android-map", help="Build a roads-and-places OsmAnd map")
    android_map.add_argument("--state", required=True)
    android_map.add_argument("--osm-id", required=True)
    android_map.add_argument("--cache", type=Path, default=Path("cache"))
    android_map.add_argument("--output", type=Path, required=True)
    android_map.add_argument("--epoch", type=int)
    android_map.add_argument("--prepared", type=Path)
    android_map.add_argument("--prepared-id")
    android_source = commands.add_parser(
        "android-source", help="Filter a verified national OSM parent once for state map builds"
    )
    android_source.add_argument("--osm-id", required=True)
    android_source.add_argument("--cache", type=Path, default=Path("cache"))
    android_source.add_argument("--output", type=Path, required=True)
    android_source.add_argument("--epoch", type=int)
    android_extract = commands.add_parser(
        "android-extract", help="Clip a checked road source to confirmed Census jurisdictions"
    )
    android_extract.add_argument("--prepared", type=Path, required=True)
    android_extract.add_argument("--prepared-id", required=True)
    android_extract.add_argument("--states", nargs="+", required=True)
    android_extract.add_argument("--cache", type=Path, default=Path("cache"))
    android_extract.add_argument("--output", type=Path, required=True)
    android_extract.add_argument("--epoch", type=int)
    android_collect = commands.add_parser(
        "android-collect", help="Collect all checked state maps with their ODbL source databases"
    )
    android_collect.add_argument("--outputs", type=Path, nargs="+", required=True)
    android_collect.add_argument("--cache", type=Path, default=Path("cache"))
    android_collect.add_argument("--output", type=Path, required=True)
    android_collect.add_argument("--epoch", type=int)
    android_howto = commands.add_parser(
        "android-howto", help="Render English/Spanish map instructions"
    )
    android_howto.add_argument("--output", type=Path, required=True)
    android_howto.add_argument("--epoch", type=int)
    medpdf = commands.add_parser("medpdf", help="Regenerate attributed medical phone PDFs")
    medpdf.add_argument("--output", type=Path, required=True)
    medpdf.add_argument("--cache", type=Path, default=Path("cache"))
    medpdf.add_argument("--epoch", type=int)
    medpdf.add_argument("--limit", type=int, help="Incomplete development subset only")
    medpdf.add_argument("--jobs", type=int, default=1)
    medpdf.add_argument("--generated", type=Path)
    wikem = commands.add_parser("wikem", help="Build a checked offline WikEM API snapshot")
    wikem.add_argument("--cache", type=Path, default=Path("cache"))
    wikem.add_argument("--output", type=Path, required=True)
    wikem.add_argument("--epoch", type=int)
    offline_zim = commands.add_parser("offline-zim", help="Regenerate an audited offline ZIM")
    offline_zim.add_argument("--item", required=True)
    offline_zim.add_argument("--cache", type=Path, default=Path("cache"))
    offline_zim.add_argument("--output", type=Path, required=True)
    offline_zim.add_argument("--epoch", type=int)
    local_llm = commands.add_parser("local-llm", help="Build offline local LLM launch materials")
    local_llm.add_argument("--profile", choices=["sample", "full"], required=True)
    local_llm.add_argument("--cache", type=Path, default=Path("cache"))
    local_llm.add_argument("--output", type=Path, required=True)
    local_llm.add_argument("--epoch", type=int)
    video = commands.add_parser(
        "video", help="Normalize a pinned imported video and subtitle tracks"
    )
    video.add_argument("--clip", required=True)
    video.add_argument("--cache", type=Path, default=Path("cache"))
    video.add_argument("--output", type=Path, required=True)
    video.add_argument("--epoch", type=int)
    phrasebooks = commands.add_parser("phrasebooks", help="Render all fifteen pinned phrasebooks")
    phrasebooks.add_argument("--cache", type=Path, default=Path("cache"))
    phrasebooks.add_argument("--output", type=Path, required=True)
    phrasebooks.add_argument("--epoch", type=int)
    atlas = commands.add_parser("atlas", help="Prepare and compose a checked county road atlas")
    atlas_commands = atlas.add_subparsers(dest="atlas_action", required=True)
    atlas_prepare = atlas_commands.add_parser(
        "prepare", help="Prepare viewports and extraction region"
    )
    atlas_prepare.add_argument("--state", required=True)
    atlas_prepare.add_argument("--state-fips", required=True)
    atlas_prepare.add_argument("--directory", type=Path, required=True)
    atlas_prepare.add_argument("--directory-id", default="directory_points")
    atlas_prepare.add_argument("--output", type=Path, required=True)
    atlas_prepare.add_argument("--cache", type=Path, default=Path("cache"))
    atlas_prepare.add_argument("--generated", type=Path, default=Path("build/generated"))
    atlas_prepare.add_argument("--basemap-id")
    atlas_prepare.add_argument("--places-id")
    atlas_prepare.add_argument("--epoch", type=int)
    atlas_all = atlas_commands.add_parser(
        "prepare-all", help="Prepare all Census jurisdictions from one national point seed"
    )
    atlas_all.add_argument("--directory", type=Path, required=True)
    atlas_all.add_argument("--directory-id", default="directory_points")
    atlas_all.add_argument("--output", type=Path, required=True)
    atlas_all.add_argument("--cache", type=Path, default=Path("cache"))
    atlas_all.add_argument("--generated", type=Path, default=Path("build/generated"))
    atlas_all.add_argument("--basemap-id")
    atlas_all.add_argument("--states", nargs="+")
    atlas_all.add_argument("--epoch", type=int)
    atlas_collect = atlas_commands.add_parser(
        "collect",
        help="Verify all county bookmarks and point references, then collect the national set",
    )
    atlas_collect.add_argument("--directory", type=Path, required=True)
    atlas_collect.add_argument("--directory-id", default="directory_points")
    atlas_collect.add_argument("--basemap-id", default="protomaps_us")
    atlas_collect.add_argument("--outputs", type=Path, nargs="+", required=True)
    atlas_collect.add_argument("--output", type=Path, required=True)
    atlas_collect.add_argument("--epoch", type=int)
    atlas_compose = atlas_commands.add_parser("compose", help="Compose verified rasters into a PDF")
    atlas_compose.add_argument("--jobs", type=Path, required=True)
    atlas_compose.add_argument("--output", type=Path, required=True)
    atlas_measure = atlas_commands.add_parser("budget", help="Check the total atlas byte budget")
    atlas_measure.add_argument("--outputs", type=Path, nargs="+", required=True)
    atlas_measure.add_argument("--states", nargs="+", required=True)
    plan = commands.add_parser("plan", help="Account for every variant's capacity")
    plan.add_argument("--profile", choices=["dev", "sample", "full"], default="dev")
    plan.add_argument("--core", type=Path, default=Path("build/core"))
    plan.add_argument(
        "--capacity-bytes", type=int, help="Explicit planning assumption; never used for images"
    )
    plan.add_argument("--json", action="store_true")
    for name in ("assemble", "image"):
        action = commands.add_parser(name, help=f"{name.capitalize()} one variant")
        action.add_argument("--variant", type=int, required=True, choices=range(1, 9))
        action.add_argument("--profile", choices=["dev", "sample", "full"], default="dev")
        action.add_argument("--core", type=Path, default=Path("build/core"))
        action.add_argument("--output", type=Path, required=True)
        action.add_argument("--cache", type=Path, default=Path("cache"))
        action.add_argument("--generated", type=Path, default=Path("build/generated"))
        action.add_argument("--epoch", type=int)
        action.add_argument("--fetch", action="store_true")
    verify = commands.add_parser(
        "verify-image", help="Verify every file against the image manifest"
    )
    verify.add_argument("image", type=Path)
    verify.add_argument("--epoch", type=int)
    site = commands.add_parser("site", help="Build the static verification site")
    site.add_argument("--output", type=Path, required=True)
    site.add_argument("--manifest", type=Path, action="append", default=[])
    site.add_argument("--full-manifest", type=Path, action="append", default=[])
    site.add_argument("--manifest-dir", type=Path, action="append", default=[])
    site.add_argument("--full-manifest-dir", type=Path, action="append", default=[])
    site.add_argument("--repository", required=True)
    lock = commands.add_parser("catalog-lock", help="Write the pinned catalog lock")
    lock.add_argument("--output", type=Path, required=True)
    lock.add_argument("--epoch", type=int)
    release = commands.add_parser("release-assets", help="Prepare gated GitHub release assets")
    release.add_argument("--core", type=Path, required=True)
    release.add_argument("--images", type=Path, required=True)
    release.add_argument("--cache", type=Path, default=Path("cache"))
    release.add_argument("--output", type=Path, required=True)
    release.add_argument("--commit", required=True)
    release.add_argument("--epoch", type=int)
    sources = commands.add_parser("release-sources", help="Fetch gated GPL corresponding sources")
    sources.add_argument("--cache", type=Path, default=Path("cache"))
    sourcecheck = commands.add_parser("verify-input", help="Cross-check a publisher BLAKE3 pin")
    sourcecheck.add_argument("--item", required=True)
    sourcecheck.add_argument("--file", type=Path, required=True)
    sourcecheck.add_argument("--report", type=Path)
    preflight = commands.add_parser("check-profile", help="Fail on every unresolved profile input")
    preflight.add_argument("--profile", choices=["dev", "sample", "full"], required=True)
    build = commands.add_parser("build-profile", help="Build staged, verified variant images")
    build.add_argument("--profile", choices=["dev", "sample", "full"], required=True)
    build.add_argument("--variants", type=int, nargs="+", choices=range(1, 9))
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--cache", type=Path, default=Path("cache"))
    build.add_argument("--generated", type=Path, default=Path("build/generated"))
    build.add_argument("--epoch", type=int)
    build.add_argument("--commit")
    build.add_argument("--reproduce", action="store_true")
    build.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            parser.print_help()
            return 0
        from ck.config import findability, load_config

        config = load_config(args.root)
        if args.command in {"source-pack", "source-restore"}:
            from ck.catalog import load_catalog
            from ck.render import epoch_for
            from ck.sourcebundle import pack_sources, restore_sources

            items = load_catalog(args.root, config)
            result = (
                pack_sources(
                    items, args.items, args.cache, args.output, epoch_for(config, args.epoch)
                )
                if args.command == "source-pack"
                else restore_sources(items, args.items, args.bundle, args.cache, args.sha256)
            )
            print(json.dumps(result, indent=2))
            return 0
        if args.command in {"directory-all", "directory-collect"}:
            from ck.catalog import load_catalog
            from ck.nationaldirectory import build_all, collect, prepare
            from ck.render import epoch_for

            context = prepare(
                args.root,
                config,
                load_catalog(args.root, config),
                args.points,
                args.atlas,
                epoch_for(config, args.epoch),
                args.points_id,
                args.atlas_id,
            )
            result = (
                build_all(context, args.output, args.states, args.jobs)
                if args.command == "directory-all"
                else collect(context, args.outputs, args.output)
            )
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "laptop-viewer":
            from ck.catalog import load_catalog
            from ck.laptopviewer import build_viewer
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_viewer(
                        args.root,
                        load_catalog(args.root, config),
                        args.cache,
                        args.generated,
                        args.output,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "laptop-tiles":
            from ck.catalog import load_catalog
            from ck.laptopmap import build_laptop_tiles
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_laptop_tiles(
                        args.root,
                        load_catalog(args.root, config),
                        args.generated,
                        args.output,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "national-points":
            from ck.catalog import load_catalog
            from ck.national import build_national_points
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_national_points(
                        args.root,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "languages-audit":
            from ck.language_audit import audit_languages

            result = audit_languages(args.root, args.cache, args.output)
            print(
                json.dumps({"order_matches": result["order_matches"], "output": str(args.output)})
            )
            return 0
        if args.command == "review-report":
            from ck.review import write_release_review

            write_release_review(args.root, args.output)
            print(args.output)
            return 0
        if args.command in {"check-profile", "build-profile"}:
            from ck.build import build_profile, check_profile

            if args.command == "check-profile":
                print(json.dumps(check_profile(args.root, args.profile), indent=2))
            else:
                print(
                    json.dumps(
                        build_profile(
                            args.root,
                            args.output,
                            args.cache,
                            args.generated,
                            args.profile,
                            args.variants or sorted(config.variants.variants),
                            args.epoch,
                            args.reproduce,
                            args.keep_raw,
                            args.commit,
                        ),
                        indent=2,
                    )
                )
            return 0
        if args.command == "release-sources":
            from ck.publication import release_sources

            release_sources(args.root, args.cache)
            return 0
        if args.command in {"site", "catalog-lock", "release-assets"}:
            from ck.publication import build_site, prepare_release, write_catalog_lock
            from ck.render import epoch_for

            if args.command == "site":
                manifests = args.manifest + [
                    p for folder in args.manifest_dir for p in folder.glob("*.json")
                ]
                full_manifests = args.full_manifest + [
                    p for folder in args.full_manifest_dir for p in folder.glob("*.json")
                ]
                build_site(args.root, manifests, args.output, args.repository, full_manifests)
            elif args.command == "catalog-lock":
                args.output.parent.mkdir(parents=True, exist_ok=True)
                write_catalog_lock(args.root, args.output, epoch_for(config, args.epoch))
            else:
                prepare_release(
                    args.root,
                    args.core,
                    args.images,
                    args.cache,
                    args.output,
                    epoch_for(config, args.epoch),
                    args.commit,
                )
            print(args.output)
            return 0
        if args.command == "verify-input":
            from ck.catalog import load_catalog
            from ck.sourcecheck import verify_publisher_input

            result = verify_publisher_input(load_catalog(args.root, config)[args.item], args.file)
            document = json.dumps(result, sort_keys=True, indent=2) + "\n"
            if args.report:
                if args.report.exists():
                    raise ValueError("Verification report output exists")
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(document)
            print(document, end="")
            return 0
        if args.command == "local-llm":
            from ck.catalog import load_catalog
            from ck.llm import build_bundle
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_bundle(
                        args.root,
                        config,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        args.profile,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "offline-zim":
            from ck.catalog import load_catalog
            from ck.render import epoch_for
            from ck.zimclean import build_offline_zim

            item = load_catalog(args.root, config)[args.item]
            print(
                json.dumps(
                    build_offline_zim(
                        args.root, item, args.cache, args.output, epoch_for(config, args.epoch)
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "phrasebooks":
            from ck.catalog import load_catalog
            from ck.phrasebooks import build_phrasebooks
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_phrasebooks(
                        args.root,
                        config,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "video":
            from ck.catalog import load_catalog
            from ck.render import epoch_for
            from ck.video import build_video

            config = load_config(args.root)
            print(
                json.dumps(
                    build_video(
                        args.root,
                        config,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        args.clip,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "medpdf":
            from ck.catalog import load_catalog
            from ck.render import epoch_for
            from ck.zim2pdf import build_medpdf

            print(
                json.dumps(
                    build_medpdf(
                        args.root,
                        config,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        epoch_for(config, args.epoch),
                        args.limit,
                        args.jobs,
                        args.generated,
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "android-howto":
            from ck.androidhowto import build_howto
            from ck.catalog import load_catalog
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_howto(
                        args.root,
                        config,
                        load_catalog(args.root, config),
                        args.output,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "android-source":
            from ck.catalog import load_catalog
            from ck.mapextract import build_road_source
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_road_source(
                        args.root,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        args.osm_id,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "android-extract":
            from ck.catalog import load_catalog
            from ck.mapextract import build_state_extracts
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_state_extracts(
                        args.root,
                        load_catalog(args.root, config),
                        args.cache,
                        args.prepared,
                        args.prepared_id,
                        args.output,
                        epoch_for(config, args.epoch),
                        [state.upper() for state in args.states],
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "wikem":
            from ck.catalog import load_catalog
            from ck.render import epoch_for
            from ck.wikem import build_archive

            print(
                json.dumps(
                    build_archive(
                        args.root,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "android-collect":
            from ck.catalog import load_catalog
            from ck.mapextract import collect_android_maps
            from ck.render import epoch_for

            print(
                json.dumps(
                    collect_android_maps(
                        args.root,
                        load_catalog(args.root, config),
                        args.cache,
                        args.outputs,
                        args.output,
                        epoch_for(config, args.epoch),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "android-map":
            from ck.androidmaps import build_android_map
            from ck.catalog import load_catalog
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_android_map(
                        args.root,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        args.state,
                        args.osm_id,
                        epoch_for(config, args.epoch),
                        args.prepared,
                        args.prepared_id,
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "atlas":
            from ck.atlas import (
                Settings,
                atlas_budget,
                collect_atlases,
                compose_atlas,
                prepare_atlas,
                prepare_atlases,
            )
            from ck.catalog import load_catalog
            from ck.config import read_yaml
            from ck.render import epoch_for

            if args.atlas_action == "prepare":
                print(
                    prepare_atlas(
                        args.root,
                        config,
                        load_catalog(args.root, config),
                        args.cache,
                        args.directory,
                        args.output,
                        args.state.upper(),
                        args.state_fips,
                        epoch_for(config, args.epoch),
                        basemap_id=args.basemap_id,
                        generated=args.generated,
                        places_id=args.places_id,
                        directory_id=args.directory_id,
                    )
                )
            elif args.atlas_action == "prepare-all":
                print(
                    json.dumps(
                        prepare_atlases(
                            args.root,
                            config,
                            load_catalog(args.root, config),
                            args.cache,
                            args.directory,
                            args.output,
                            epoch_for(config, args.epoch),
                            directory_id=args.directory_id,
                            basemap_id=args.basemap_id,
                            generated=args.generated,
                            states=[state.upper() for state in args.states]
                            if args.states
                            else None,
                        ),
                        indent=2,
                    )
                )
            elif args.atlas_action == "collect":
                print(
                    json.dumps(
                        collect_atlases(
                            args.root,
                            load_catalog(args.root, config),
                            args.directory,
                            args.outputs,
                            args.output,
                            epoch_for(config, args.epoch),
                            directory_id=args.directory_id,
                            basemap_id=args.basemap_id,
                        ),
                        indent=2,
                    )
                )
            elif args.atlas_action == "compose":
                print(
                    json.dumps(compose_atlas(args.root, config, args.jobs, args.output), indent=2)
                )
            else:
                settings = Settings.model_validate(
                    read_yaml(args.root / "pipelines/atlas/settings.yaml")
                )
                print(
                    json.dumps(
                        atlas_budget(args.outputs, args.states, settings.max_total_bytes), indent=2
                    )
                )
            return 0
        if args.command == "directory":
            from ck.catalog import load_catalog
            from ck.directory import build_directory
            from ck.render import epoch_for

            print(
                json.dumps(
                    build_directory(
                        args.root,
                        config,
                        load_catalog(args.root, config),
                        args.cache,
                        args.output,
                        args.state,
                        args.state_fips,
                        epoch_for(config, args.epoch),
                        args.osm_id,
                        args.atlas_index,
                        args.atlas_id,
                        args.seed,
                        args.points,
                        args.points_id,
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "plan":
            from ck.assemble import core_size
            from ck.catalog import load_catalog
            from ck.core import verify_core
            from ck.planner import plan_variants

            metadata = json.loads((args.core / "core-manifest.json").read_text())
            verify_core(args.root, args.core, metadata["epoch"], args.profile)
            plans = plan_variants(
                config,
                load_catalog(args.root, config),
                args.profile,
                core_size(args.core),
                args.capacity_bytes,
            )
            if args.json:
                print(json.dumps([plan.as_dict() for plan in plans], indent=2))
            else:
                print("VARIANT  KNOWN BYTES      USABLE BYTES     STATUS")
                for plan in plans:
                    print(
                        f"{plan.variant:>7}  {plan.known_total_bytes:>15,}  "
                        f"{plan.usable_bytes:>15,}  {'FITS' if plan.fits else 'BLOCKED'}"
                    )
                    for issue in plan.blockers:
                        print(f"  {issue}")
                    if plan.map_path:
                        print(f"  Android maps: {plan.map_path}. {plan.map_reason}")
                    if plan.llm_variants is not None:
                        print(f"  Local LLM variants: {plan.llm_variants}. {plan.llm_reason}")
                    if not plan.fits:
                        for item in plan.largest:
                            print(f"  Large item: {item['id']} — {item['size_bytes']:,} bytes")
            return 0 if all(plan.fits for plan in plans) else 1
        if args.command in {"assemble", "image"}:
            import tempfile

            from ck.assemble import assemble
            from ck.render import epoch_for

            epoch = epoch_for(config, args.epoch)
            if args.command == "assemble":
                print(
                    assemble(
                        args.root,
                        config,
                        args.core,
                        args.output,
                        args.variant,
                        args.profile,
                        args.cache,
                        args.generated,
                        epoch,
                        args.fetch,
                    )
                )
            else:
                from ck.image import build_image

                args.output.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(dir=args.output, prefix=".ck-tree-") as temporary:
                    tree = assemble(
                        args.root,
                        config,
                        args.core,
                        Path(temporary) / "tree",
                        args.variant,
                        args.profile,
                        args.cache,
                        args.generated,
                        epoch,
                        args.fetch,
                    )
                    print(
                        json.dumps(
                            build_image(
                                tree, args.output, config, args.variant, args.profile, epoch
                            ),
                            indent=2,
                        )
                    )
            return 0
        if args.command == "verify-image":
            from ck.image import verify_image
            from ck.render import epoch_for

            verify_image(args.image, epoch_for(config, args.epoch))
            print("Image manifest matches every payload file")
            return 0
        if args.command == "validate":
            from ck.catalog import load_catalog

            items = load_catalog(args.root, config)
            if args.release:
                from ck.review import require_release_ready

                require_release_ready(args.root)
            print(
                f"Configuration valid: 8 variants, 12 topics, 15 language editions; "
                f"{len(items)} catalog entries (release readiness checked separately)"
            )
        elif args.command in {"catalog", "fetch"}:
            from ck.catalog import attributions, load_catalog

            items = load_catalog(args.root, config)
            if args.command == "catalog":
                attributions(items, args.output)
                print(args.output)
            else:
                from ck.fetch import fetch

                unknown = set(args.items) - items.keys()
                if unknown:
                    raise ValueError(f"Unknown catalog ids: {sorted(unknown)}")
                for identifier in args.items:
                    print(fetch(items[identifier], args.cache))
        elif args.command == "core":
            from ck.core import build_core

            files = build_core(
                args.root, config, args.output, args.epoch, args.languages, args.profile
            )
            print(f"Built {len(files)} core PDFs in {args.output}")
        elif args.command == "render":
            from ck.render import render_pdf

            language = next((x for x in config.languages if x.code == args.language), None)
            if language is None:
                raise ValueError(f"Unknown language: {args.language}")
            print(
                render_pdf(
                    args.root,
                    config,
                    args.root / args.input,
                    language,
                    args.format,
                    args.output,
                    args.epoch,
                )
            )
        elif args.command == "coverage":
            rows = []
            groups = {
                "universal": 8,
                **{m: 2 for m in config.variants.topics},
                **{s: 1 for s in config.variants.collections},
            }
            if args.carriers is not None:
                groups = {"item": args.carriers}
            for item, k in groups.items():
                rows.append(
                    {
                        "item": item,
                        "k": k,
                        "n": args.homes,
                        "probability": findability(k, args.homes),
                    }
                )
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                print("ITEM                     k   HOMES   FINDABILITY")
                for row in rows:
                    print(
                        f"{row['item']:<24} {row['k']}   {row['n']:>5}   {row['probability']:.2%}"
                    )
    except (ValueError, OSError) as error:
        parser.exit(1, f"ck: {error}\n")
    return 0
