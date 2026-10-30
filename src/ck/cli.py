"""Command-line entry point; build commands arrive in later work-order steps."""

import argparse
from collections.abc import Sequence
from importlib.metadata import version


def main(argv: Sequence[str] | None = None) -> int:
    """Show CLI help or the installed package version."""
    parser = argparse.ArgumentParser(
        prog="ck",
        description="Build tools for the Common Knowledge offline emergency USB drive.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('common-knowledge')}"
    )
    parser.parse_args(argv)
    parser.print_help()
    return 0
