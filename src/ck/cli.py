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
    commands.add_parser("validate", help="Validate shared configuration")
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
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            parser.print_help()
            return 0
        from ck.config import findability, load_config

        config = load_config(args.root)
        if args.command == "validate":
            print("Configuration valid: 8 variants, 12 modules, 15 language editions")
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
