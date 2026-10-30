from __future__ import annotations

import argparse
import sys

from . import config
from .runner import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="uvvis-analysis",
        description="UV-Vis spectroscopy and chlorophyll pigment analysis.",
    )
    parser.add_argument("input_dir", nargs="?", default=None,
                        help="Folder with .txt/.csv spectral exports (default: cwd).")
    parser.add_argument("--output-dir", default=None,
                        help="Where to write results. Default: <input_dir>/uvvis_results.")
    parser.add_argument("--solvent", choices=["ethanol", "acetone", "methanol"], default="ethanol")
    args = parser.parse_args(argv)

    if args.solvent:
        config.SOLVENT = args.solvent

    try:
        run(input_dir=args.input_dir, output_dir=args.output_dir)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())