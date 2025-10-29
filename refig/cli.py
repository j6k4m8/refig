"""Command line interface for the refig package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ._core import load_metadata


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="refig", description="Inspect refig-managed figures.")
    subparsers = parser.add_subparsers(dest="command")

    meta_parser = subparsers.add_parser("meta", help="Display metadata embedded in a figure.")
    meta_parser.add_argument("figure", type=Path, help="Path to the figure file.")

    args = parser.parse_args(argv)

    if args.command == "meta":
        metadata = load_metadata(args.figure)
        json.dump(metadata, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
