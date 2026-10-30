"""CLI stub: `uvvis-analysis [input_dir] [--output-dir DIR]`."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="uvvis-analysis",
        description="UV-Vis analysis (not yet implemented).",
    )
    parser.add_argument("input_dir", nargs="?", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.parse_args(argv)
    print(
        "[uvvis] not yet implemented. Run `granulometer-analysis` for the "
        "working pipeline.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())