"""Shared report helpers.

`write_csv` is generic (header + rows) and reserved for UV-Vis and future
methods. Granulometer uses its own `write_csvs` in `granulometer.reports`
because it writes two domain-specific CSVs (wide layout, mean/SD columns).
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Sequence


def write_csv(path: Path, header: Sequence[str],
              rows: Iterable[Sequence]) -> None:
    """Write a UTF-8-BOM CSV (Excel opens it cleanly with accents)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(row)