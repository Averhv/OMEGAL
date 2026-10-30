from __future__ import annotations

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_hex

from . import config
from .models import Condition, Spectrum


def calculate_pigments_and_metrics(spec: Spectrum) -> dict:
    s = {}
    for wl in config.TARGET_WAVELENGTHS:
        s[f"A_{wl}"] = spec.get_absorbance_at(float(wl))

    a_750 = s.get("A_750", spec.get_absorbance_at(750.0))
    a_520 = s.get("A_520", spec.get_absorbance_at(520.0))
    a_649 = s.get("A_649", spec.get_absorbance_at(649.0))
    a_664 = s.get("A_664", spec.get_absorbance_at(664.0))

    red_region_mask = (spec.wavelength >= 630) & (spec.wavelength <= 680)
    red_max = float(spec.absorbance[red_region_mask].max()) if np.any(red_region_mask) else a_664

    max_abs = float(spec.absorbance.max()) if spec.absorbance.size > 0 else 0.0
    s["max_absorbance"] = max_abs

    flags = []
    if max_abs > config.MAX_ABSORBANCE_WARNING:
        flags.append(f"Max absorbance ({max_abs:.3f}) > {config.MAX_ABSORBANCE_WARNING}: Over 1.0, dilute and redo.")

    if abs(a_750) > config.TURBIDITY_THRESHOLD_A750:
        flags.append(f"A750 ({a_750:.3f}) > {config.TURBIDITY_THRESHOLD_A750}: Turbidity check failed (should be ~0).")

    if red_max > 0 and (a_520 / red_max) > config.CAROTENOID_MAX_RATIO_A520:
        flags.append(f"A520/RedMax ratio ({(a_520/red_max)*100:.1f}%) >= 10%.")

    spec.flags = flags
    s["flags"] = flags

    try:
        # Ritchie 2008 Ethanol Equations
        s["Chl_a_ug_mL"] = float(max(0.0, 13.36 * a_664 - 5.19 * a_649))
        s["Chl_b_ug_mL"] = float(max(0.0, 27.43 * a_649 - 8.12 * a_664))
        s["Total_Chl_ug_mL"] = s["Chl_a_ug_mL"] + s["Chl_b_ug_mL"]

        df = spec.dilution_factor
        v_etoh = spec.extract_volume_ml
        mass = spec.dry_mass_mg if spec.dry_mass_mg > 0 else 1.0

        # Chl (µg/mg d'extrait) = C (µg/mL) * facteur de dilution * V d'éthanol de reprise (mL) / dry mass total (mg)
        s["Chl_a_ug_mg"] = (s["Chl_a_ug_mL"] * df * v_etoh) / mass
        s["Chl_b_ug_mg"] = (s["Chl_b_ug_mL"] * df * v_etoh) / mass
        s["Total_Chl_ug_mg"] = (s["Total_Chl_ug_mL"] * df * v_etoh) / mass

        s["Chl_a"] = s["Chl_a_ug_mg"]
        s["Chl_b"] = s["Chl_b_ug_mg"]
        s["Total_Chl"] = s["Total_Chl_ug_mg"]

    except Exception:
        s["Chl_a_ug_mL"] = 0.0
        s["Chl_b_ug_mL"] = 0.0
        s["Total_Chl_ug_mL"] = 0.0
        s["Chl_a_ug_mg"] = 0.0
        s["Chl_b_ug_mg"] = 0.0
        s["Total_Chl_ug_mg"] = 0.0
        s["Chl_a"] = 0.0
        s["Chl_b"] = 0.0
        s["Total_Chl"] = 0.0

    return s


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