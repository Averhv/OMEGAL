"""CSV summaries specific to granulometer output."""
from __future__ import annotations

import csv
from pathlib import Path

from .models import Condition, Measurement
from .stats import stat_values

_COLS = [
    "D10_um", "D50_um", "D90_um", "span_calculated", "std_um", "var_um2",
    "mean_um", "mode_um", "geomean_um", "d32_um",
]


def write_csvs(measurements: list[Measurement], conditions: list[Condition],
               out: Path) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    with (out / "measurement_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "name", "condition", "sample", "replicate", "volume_mL", "time_s",
            "temperature_C", "source", "basis", "span_instrument", "circulation",
            "agitation", "flags",
        ] + _COLS)
        for m in measurements:
            w.writerow([
                m.name, m.group, m.sample, m.replicate, m.volume, m.time,
                m.temperature, m.source, m.stats.get("basis"),
                m.stats.get("span_instrument"), m.stats.get("circulation"),
                m.stats.get("agitation"), "; ".join(m.flags),
            ] + [m.stats.get(c) for c in _COLS])

    with (out / "condition_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        header = ["condition", "sample", "volume_mL", "time_s", "temperature_C", "n"]
        for c in _COLS:
            header += [f"{c}_mean", f"{c}_sd"]
        w.writerow(header + ["D50_cv_percent"])
        for cond in conditions:
            row = [
                cond.name, cond.sample, cond.volume, cond.time,
                cond.temperature, len(cond.members),
            ]
            for c in _COLS:
                v = stat_values(cond.members, c)
                row += [
                    v.mean() if v.size else None,
                    v.std(ddof=1) if v.size > 1 else None,
                ]
            d50 = stat_values(cond.members, "D50_um")
            row.append(
                100 * d50.std(ddof=1) / d50.mean()
                if d50.size > 1 and d50.mean() else None
            )
            w.writerow(row)