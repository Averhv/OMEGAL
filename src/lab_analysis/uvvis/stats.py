from __future__ import annotations

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_hex

from . import config
from .models import Condition, Spectrum

# Wavelengths exported to the CSV (nm): yours + the two used by Lopez 2025 (648, 664).
CSV_WAVELENGTHS = (470, 520, 632, 648, 649, 664, 665, 696, 750)
FLAG_WAVELENGTHS = (470, 632, 648, 649, 664, 665, 696)  # absorbances actually used by the equations


def _cfg(name: str, default):
    return getattr(config, name, default)


def abs_at(spec: Spectrum, wl: float) -> float:
    """Absorbance at wl (linear interpolation). NaN if wl is outside the measured range
    (np.interp alone would silently return the edge value)."""
    x = spec.wavelength
    if x.size == 0 or wl < x.min() - 0.5 or wl > x.max() + 0.5:
        return float("nan")
    return float(np.interp(wl, x, spec.absorbance))


def baseline(spec: Spectrum) -> float:
    """Offset subtracted from every wavelength (A750), 0 if the correction is switched off."""
    a750 = abs_at(spec, 750.0)
    return a750 if (_cfg("SUBTRACT_A750", True) and np.isfinite(a750)) else 0.0


def _scale_to_mass(spec: Spectrum):
    """Return (dilution F, stock volume mL, extract mass mg); mass is NaN when unknown."""
    df = float(spec.dilution_factor)
    v = float(getattr(spec, "extract_volume_ml", float("nan")))
    m = float(getattr(spec, "dry_mass_mg", float("nan")))
    if not (np.isfinite(m) and m > 0 and np.isfinite(v) and v > 0):
        return df, float("nan"), float("nan")
    return df, v, m


def calculate_pigments_and_metrics(spec: Spectrum) -> dict:
    """Chlorophylls a, b and carotenoids (Lopez 2025 / Lichtenthaler & Buschmann 2001, ethanol):
         ca = 13.36 A664 - 5.19 A648
         cb = 27.43 A648 - 8.12 A664
         cc = (1000 A470 - 2.13 ca - 97.64 cb) / 209          [ug/mL]
    A(wl) is first corrected by subtracting A750 (config.SUBTRACT_A750, default True)."""
    s = {}
    off = baseline(spec)
    for wl in CSV_WAVELENGTHS:
        raw = abs_at(spec, float(wl))
        s[f"A_{wl}"] = raw
        s[f"Ac_{wl}"] = raw - off
    s["A750_offset_used"] = off

    max_abs = float(spec.absorbance.max()) if spec.absorbance.size else 0.0
    s["max_absorbance"] = max_abs  # information only (includes the Soret band)

    a470, a648, a664 = s["Ac_470"], s["Ac_648"], s["Ac_664"]
    ca = 13.36 * a664 - 5.19 * a648
    cb = 27.43 * a648 - 8.12 * a664
    cc = (1000.0 * a470 - 2.13 * ca - 97.64 * cb) / 209.0
    # No clamping to 0: a negative value is information (low signal / interference).
    s["Chl_a_ug_mL"], s["Chl_b_ug_mL"] = ca, cb
    s["Total_Chl_ug_mL"] = ca + cb
    s["Carotenoids_ug_mL"] = cc

    df, v_stock, mass = _scale_to_mass(spec)
    for key in ("Chl_a", "Chl_b", "Total_Chl", "Carotenoids"):
        c = s[f"{key}_ug_mL"]
        s[f"{key}_stock_ug_mL"] = c * df                     # undiluted solution
        s[f"{key}_ug_mg"] = c * df * v_stock / mass          # per mg of dry extract (NaN if mass unknown)
    s["Chl_a"], s["Chl_b"], s["Total_Chl"] = s["Chl_a_ug_mg"], s["Chl_b_ug_mg"], s["Total_Chl_ug_mg"]

    # ---- flags
    flags = []
    thr = _cfg("MAX_ABSORBANCE_WARNING", 1.0)
    used = [abs_at(spec, float(w)) for w in FLAG_WAVELENGTHS]
    used = [u for u in used if np.isfinite(u)]
    if used and max(used) > thr:
        flags.append(f"Absorbance used by the equations ({max(used):.3f}) > {thr}: dilute and redo.")
    if len(used) < len(FLAG_WAVELENGTHS):
        flags.append("Some equation wavelengths are outside the measured range.")
    a750 = abs_at(spec, 750.0)
    if np.isfinite(a750) and abs(a750) > _cfg("TURBIDITY_THRESHOLD_A750", 0.02):
        action = "subtracted from all wavelengths" if off else "NOT subtracted"
        flags.append(f"A750 = {a750:.3f} (baseline offset or turbidity), {action}.")
    mask = (spec.wavelength >= 630) & (spec.wavelength <= 680)
    red_max = float(spec.absorbance[mask].max()) - off if np.any(mask) else a664
    if red_max > 0 and np.isfinite(s["Ac_520"]) and s["Ac_520"] / red_max > _cfg("CAROTENOID_MAX_RATIO_A520", 0.10):
        flags.append(f"A520/RedMax = {s['Ac_520'] / red_max * 100:.1f} % (>= {_cfg('CAROTENOID_MAX_RATIO_A520', 0.10) * 100:.0f} %).")
    if any(np.isfinite(s[k]) and s[k] < 0 for k in ("Chl_a_ug_mL", "Chl_b_ug_mL", "Carotenoids_ug_mL")):
        flags.append("Negative pigment value (low signal): do not use this spectrum.")
    spec.flags = flags
    s["flags"] = flags
    return s


def calculate_ritchie_pigments(spec: Spectrum) -> dict:
    """Ritchie (2008) ethanol equations, Table 1 (632/649/665/696) and Table 2 (632/649/665), ug/mL.
    A750 is subtracted as in calculate_pigments_and_metrics; no clamping."""
    s = {}
    off = baseline(spec)
    x11 = abs_at(spec, 632.0) - off
    x12 = abs_at(spec, 649.0) - off
    x13 = abs_at(spec, 665.0) - off
    x14 = abs_at(spec, 696.0) - off

    s["Chl_a_T1_ug_mL"] = 0.0604 * x11 - 4.5224 * x12 + 13.2969 * x13 - 1.7453 * x14
    s["Chl_b_T1_ug_mL"] = -4.1982 * x11 + 25.7205 * x12 - 7.4096 * x13 - 2.7418 * x14
    s["Chl_c_T1_ug_mL"] = 28.4593 * x11 - 9.9944 * x12 - 1.9344 * x13 - 1.8093 * x14
    s["Chl_d_T1_ug_mL"] = -0.2007 * x11 + 0.0848 * x12 - 0.1909 * x13 + 12.1302 * x14
    s["Total_Chl_T1_ug_mL"] = 24.1209 * x11 + 11.2884 * x12 + 3.7620 * x13 + 5.8338 * x14

    s["Chl_a_T2_ug_mL"] = -0.9394 * x11 - 4.2774 * x12 + 13.3914 * x13
    s["Chl_b_T2_ug_mL"] = -4.0937 * x11 + 25.6865 * x12 - 7.3430 * x13
    s["Chl_c_T2_ug_mL"] = 28.5073 * x11 - 9.9940 * x12 - 1.9749 * x13
    s["Total_Chl_T2_ug_mL"] = 23.4742 * x11 + 11.4096 * x12 + 4.0735 * x13

    df, v_stock, mass = _scale_to_mass(spec)
    factor = df * v_stock / mass  # NaN when mass/volume are unknown
    for k in ("Chl_a_T1", "Chl_b_T1", "Chl_c_T1", "Chl_d_T1", "Total_Chl_T1",
              "Chl_a_T2", "Chl_b_T2", "Chl_c_T2", "Total_Chl_T2"):
        s[f"{k}_ug_mg"] = s[f"{k}_ug_mL"] * factor
    return s

calculate_lichtenthaler_pigments = calculate_ritchie_pigments


def stat_values(members: list[Spectrum], key: str) -> np.ndarray:
    return np.array(
        [m.stats.get(key) for m in members if m.stats.get(key) is not None],
        dtype=float,
    )


def fmt(value: float) -> str:
    return f"{value:.3f}" if abs(value) >= 0.001 else f"{value:.2e}"


def stats_text(members: list[Spectrum]) -> str:
    lines = []
    for name in config.STATS_FIELDS:
        v = stat_values(members, name)
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        if len(members) == 1:
            txt = fmt(v[0])
        else:
            txt = f"{fmt(v.mean())} ± {fmt(v.std(ddof=1)) if v.size > 1 else '–'}"
        lines.append(f"{name}: {txt}")
    if len(members) > 1:
        lines.append(f"(mean ± SD, n = {len(members)})")
    return "\n".join(lines)


def palette_name(key, index: int) -> str:
    for candidate in (key, f"{key:g}" if isinstance(key, float) else None):
        if candidate in config.GROUP_PALETTES:
            return config.GROUP_PALETTES[candidate]
    if config.PALETTE_PRESET != "auto":
        return config.PALETTE_PRESET
    return config.PALETTE_CYCLE[index % len(config.PALETTE_CYCLE)]


def shades(name: str, n: int) -> list[str]:
    base = config.PALETTES[name]
    if n <= 1:
        return [base[1]]
    if n == 2:
        return [base[0], base[2]]
    if n == 3:
        return list(base)
    cmap = LinearSegmentedColormap.from_list(name, base)
    return [to_hex(cmap(x)) for x in np.linspace(0, 1, n)]


def common_curves(members: list[Spectrum]):
    x = members[0].wavelength
    abs_list = []
    for m in members:
        if m.wavelength.shape == x.shape and np.allclose(m.wavelength, x):
            abs_list.append(m.absorbance)
        else:
            abs_list.append(np.interp(x, m.wavelength, m.absorbance, left=0, right=0))
    arr = np.array(abs_list)
    sd = arr.std(axis=0, ddof=1) if len(members) > 1 else np.zeros(arr.shape[1])
    return x, arr.mean(axis=0), sd