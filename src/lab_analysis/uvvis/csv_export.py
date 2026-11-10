"""CSV outputs for the UV-Vis pipeline.

Three files are written in `out_dir`:
  uvvis_absorbances.csv  key absorbances (raw and A750-corrected) + metadata
  uvvis_pigments.csv     chlorophyll a, b, total and carotenoids (Lopez 2025), per mL and per mg
  uvvis_ritchie.csv      Ritchie (2008) Tables 1 and 2 (ethanol), for comparison
Options (config.py, all optional): CSV_SEP (default ";"), CSV_DECIMAL (default ".", use "," for French Excel),
SUBTRACT_A750 (default True).
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from . import config
from .models import Spectrum
from .parsing import get_meta
from .stats import CSV_WAVELENGTHS, calculate_pigments_and_metrics, calculate_ritchie_pigments

META_COLS = ["file", "batch", "condition", "tube", "dilution_F", "carbon_ratio_r", "is_reference", "time"]


def _meta_row(spec: Spectrum) -> list:
    m = get_meta(spec)
    return [spec.source, m["batch"], m["group"], spec.replicate, spec.dilution_factor,
            "" if m["carbon_ratio"] is None else m["carbon_ratio"], int(m["is_reference"]), m["time"]]


def _fmt(v, dec: str) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return ""
    if isinstance(v, float):
        s = f"{v:.6g}"
        return s.replace(".", dec) if dec != "." else s
    return str(v)


def _write(path: Path, header: list[str], rows: list[list]) -> Path:
    sep = getattr(config, "CSV_SEP", ";")
    dec = getattr(config, "CSV_DECIMAL", ".")
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel reads µ correctly; QUOTE_MINIMAL quotes any field containing the separator.
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=sep, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow([_fmt(v, dec) for v in r])
    return path


def _sort_key(spec: Spectrum):
    m = get_meta(spec)
    return (m["batch"], m["group"], m["carbon_ratio"] if m["carbon_ratio"] is not None else -1.0,
            str(spec.replicate), spec.dilution_factor)


def export_csvs(spectra: list[Spectrum], out_dir: Path) -> dict[str, Path]:
    out_dir = Path(out_dir)
    spectra = sorted(spectra, key=_sort_key)

    # 1) absorbances
    h1 = META_COLS + [f"A_{w}" for w in CSV_WAVELENGTHS] + [f"Ac_{w}" for w in CSV_WAVELENGTHS] \
        + ["A750_offset_used", "max_absorbance", "flags"]
    r1, r2, r3 = [], [], []
    for sp in spectra:
        st = calculate_pigments_and_metrics(sp)
        rt = calculate_ritchie_pigments(sp)
        sp.stats = {**getattr(sp, "stats", {}), **st}
        meta = _meta_row(sp)
        r1.append(meta + [st[f"A_{w}"] for w in CSV_WAVELENGTHS] + [st[f"Ac_{w}"] for w in CSV_WAVELENGTHS]
                  + [st["A750_offset_used"], st["max_absorbance"], " | ".join(st["flags"])])
        r2.append(meta + [st["Chl_a_ug_mL"], st["Chl_b_ug_mL"], st["Total_Chl_ug_mL"], st["Carotenoids_ug_mL"],
                          st["Chl_a_stock_ug_mL"], st["Chl_b_stock_ug_mL"], st["Total_Chl_stock_ug_mL"],
                          st["Carotenoids_stock_ug_mL"],
                          st["Chl_a_ug_mg"], st["Chl_b_ug_mg"], st["Total_Chl_ug_mg"], st["Carotenoids_ug_mg"],
                          " | ".join(st["flags"])])
        r3.append(meta + [rt[k] for k in (
            "Chl_a_T1_ug_mL", "Chl_b_T1_ug_mL", "Chl_c_T1_ug_mL", "Chl_d_T1_ug_mL", "Total_Chl_T1_ug_mL",
            "Chl_a_T2_ug_mL", "Chl_b_T2_ug_mL", "Chl_c_T2_ug_mL", "Total_Chl_T2_ug_mL")])

    h2 = META_COLS + ["Chl_a_ug_mL", "Chl_b_ug_mL", "Chl_total_ug_mL", "Carotenoids_ug_mL",
                      "Chl_a_stock_ug_mL", "Chl_b_stock_ug_mL", "Chl_total_stock_ug_mL", "Carotenoids_stock_ug_mL",
                      "Chl_a_ug_per_mg", "Chl_b_ug_per_mg", "Chl_total_ug_per_mg", "Carotenoids_ug_per_mg", "flags"]
    h3 = META_COLS + ["T1_Chl_a", "T1_Chl_b", "T1_Chl_c", "T1_Chl_d", "T1_Chl_total",
                      "T2_Chl_a", "T2_Chl_b", "T2_Chl_c", "T2_Chl_total"]
    return {
        "absorbances": _write(out_dir / "uvvis_absorbances.csv", h1, r1),
        "pigments": _write(out_dir / "uvvis_pigments.csv", h2, r2),
        "ritchie": _write(out_dir / "uvvis_ritchie.csv", h3, r3),
    }