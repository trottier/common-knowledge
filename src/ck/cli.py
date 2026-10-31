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
    catalog = commands.add_parser("catalog", help="Generate third-party attributions")
    catalog.add_argument("--output", type=Path, default=Path("THIRD_PARTY.md"))
    fetch = commands.add_parser("fetch", help="Fetch pinned items into the verified cache")
    fetch.add_argument("items", nargs="+")
    fetch.add_argument("--cache", type=Path, default=Path("cache"))
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
    directory.add_argument("--epoch", type=int)
    android_map = commands.add_parser("android-map", help="Build a roads-and-places OsmAnd map")
    android_map.add_argument("--state", required=True)
    android_map.add_argument("--osm-id", required=True)
    android_map.add_argument("--cache", type=Path, default=Path("cache"))
    android_map.add_argument("--output", type=Path, required=True)
    android_map.add_argument("--epoch", type=int)
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
    atlas = commands.add_parser("atlas", help="Prepare and compose a checked county road atlas")
    atlas_commands = atlas.add_subparsers(dest="atlas_action", required=True)
    atlas_prepare = atlas_commands.add_parser(
        "prepare", help="Prepare viewports and extraction region"
    )
    atlas_prepare.add_argument("--state", required=True)
    atlas_prepare.add_argument("--state-fips", required=True)
    atlas_prepare.add_argument("--directory", type=Path, required=True)
    atlas_prepare.add_argument("--directory-id", default="national_directory")
    atlas_prepare.add_argument("--output", type=Path, required=True)
    atlas_prepare.add_argument("--cache", type=Path, default=Path("cache"))
    atlas_prepare.add_argument("--generated", type=Path, default=Path("build/generated"))
    atlas_prepare.add_argument("--basemap-id")
    atlas_prepare.add_argument("--places-id")
    atlas_prepare.add_argument("--epoch", type=int)
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
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            parser.print_help()
            return 0
        from ck.config import findability, load_config

        config = load_config(args.root)
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
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "atlas":
            from ck.atlas import Settings, atlas_budget, compose_atlas, prepare_atlas
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
