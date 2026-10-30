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
    coverage = commands.add_parser("coverage", help="Show findability of modules and shelves")
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
    core.add_argument("--languages", nargs="+", default=["en"])
    core.add_argument("--profile", choices=["dev", "sample", "full"], default="dev")
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
                f"Configuration valid: 8 variants, 12 modules, 15 language editions; "
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
                **{m: 2 for m in config.variants.modules},
                **{s: 1 for s in config.variants.shelves},
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
