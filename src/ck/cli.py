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
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            parser.print_help()
            return 0
        from ck.config import findability, load_config

        config = load_config(args.root)
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

            files = build_core(args.root, config, args.output, args.epoch, args.languages)
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
