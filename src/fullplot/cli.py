from __future__ import annotations

import argparse
from pathlib import Path

from fullplot.fullplot import open as open_hdf5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fullplot",
        description="Inspect HDF5 files with FullPlot.",
    )
    parser.add_argument(
        "filename",
        nargs="?",
        type=Path,
        help="HDF5 file to inspect.",
    )
    parser.add_argument(
        "--root",
        default="/",
        help="HDF5 root/group to inspect. Default: /",
    )
    parser.add_argument(
        "--tree",
        action="store_true",
        help="Print the HDF5 tree. This is the default action.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List numeric datasets under the selected root.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum tree depth to print when using --tree.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.filename is None:
        parser.print_help()
        return 0

    data = open_hdf5(args.filename, root=args.root)

    if args.list:
        data.list(print_output=True)
    else:
        data.tree(max_depth=args.max_depth, print_output=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
