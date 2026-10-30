"""CLI: `granulometer-analysis [input_dir] [--output-dir DIR]` or `python -m lab_analysis.granulometer`."""
from __future__ import annotations

import argparse
import sys

from . import config
from .runner import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="granulometer-analysis",
        description="Laser-diffraction granulometer particle-size analysis.",
    )
    parser.add_argument("input_dir", nargs="?", default=None,
                        help="Folder with .txt/.xlsx exports (default: cwd).")
    parser.add_argument("--output-dir", default=None,
                        help="Where to write results. "
                             f"Default: <input_dir>/{config.OUTPUT_NAME}.")
    parser.add_argument("--plot-kinds", nargs="+",
                        choices=["combined", "q", "passant", "both"], default=None,
                        help="Figure kinds to produce (default: combined).")
    parser.add_argument("--compare-over", choices=["time", "volume", "sample"],
                        default=None, help="Dimension varied in comparison plots.")
    parser.add_argument("--no-individual", action="store_true")
    parser.add_argument("--no-replicates", action="store_true")
    parser.add_argument("--no-comparisons", action="store_true")
    parser.add_argument("--no-overview", action="store_true")
    args = parser.parse_args(argv)

    if args.plot_kinds:
        config.PLOT_KINDS = tuple(args.plot_kinds)
    if args.compare_over:
        config.COMPARE_OVER = args.compare_over
    if args.no_individual:
        config.MAKE_INDIVIDUAL = False
    if args.no_replicates:
        config.MAKE_REPLICATES = False
    if args.no_comparisons:
        config.MAKE_COMPARISONS = False
    if args.no_overview:
        config.MAKE_OVERVIEW = False

    try:
        run(input_dir=args.input_dir, output_dir=args.output_dir)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())