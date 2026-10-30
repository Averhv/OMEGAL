from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from .models import Condition, Spectrum
from .stats import stat_values


def write_csvs(spectra: list[Spectrum], conditions: list[Condition], out: Path) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    with (out / "spectrum_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        header = [
            "name", "sample", "replicate", "source", "dilution_factor",
            "extract_volume_ml", "dry_mass_mg", "max_absorbance",
            "A_664", "A_649", "A_632", "A_520", "A_750",
            "Chl_a_ug_mL", "Chl_b_ug_mL", "Total_Chl_ug_mL",
            "Chl_a_ug_mg", "Chl_b_ug_mg", "Total_Chl_ug_mg", "flags"
        ]
        w.writerow(header)
        for s in spectra:
            w.writerow([
                s.name, s.group, s.replicate, s.source, s.dilution_factor,
                s.extract_volume_ml, s.dry_mass_mg, s.stats.get("max_absorbance"),
                s.stats.get("A_664"), s.stats.get("A_649"), s.stats.get("A_632"),
                s.stats.get("A_520"), s.stats.get("A_750"),
                s.stats.get("Chl_a_ug_mL"), s.stats.get("Chl_b_ug_mL"), s.stats.get("Total_Chl_ug_mL"),
                s.stats.get("Chl_a_ug_mg"), s.stats.get("Chl_b_ug_mg"), s.stats.get("Total_Chl_ug_mg"),
                "; ".join(s.flags),
            ])

    with (out / "condition_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        metrics = ["max_absorbance", "A_664", "A_649", "A_632", "A_520", "A_750",
                   "Chl_a_ug_mL", "Chl_b_ug_mL", "Total_Chl_ug_mL",
                   "Chl_a_ug_mg", "Chl_b_ug_mg", "Total_Chl_ug_mg"]
        header = ["condition", "sample", "n"]
        for m in metrics:
            header += [f"{m}_mean", f"{m}_sd"]
        w.writerow(header)
        for cond in conditions:
            row = [cond.name, cond.sample, len(cond.members)]
            for m in metrics:
                v = stat_values(cond.members, m)
                row += [
                    v.mean() if v.size else None,
                    v.std(ddof=1) if v.size > 1 else None,
                ]
            w.writerow(row)