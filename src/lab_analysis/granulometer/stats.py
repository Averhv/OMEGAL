"""Statistic text, palette helpers, mean/SD curves."""
from __future__ import annotations

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_hex

from . import config
from .models import Condition, Measurement

FIELD_SPECS = {
    "D10": ("D10_um", "µm"), "D50": ("D50_um", "µm"), "D90": ("D90_um", "µm"),
    "Span": ("span_calculated", ""), "SD": ("std_um", "µm"),
    "Variance": ("var_um2", "µm²"), "Mean": ("mean_um", "µm"),
    "Mode": ("mode_um", "µm"), "D32": ("d32_um", "µm"),
}


def fmt(value: float) -> str:
    return f"{value:.3f}" if abs(value) >= 0.001 else f"{value:.2e}"


def stat_values(members: list[Measurement], key: str) -> np.ndarray:
    return np.array(
        [m.stats.get(key) for m in members if m.stats.get(key) is not None],
        dtype=float,
    )


def stats_text(members: list[Measurement]) -> str:
    lines = []
    for name in config.STATS_FIELDS:
        key, unit = FIELD_SPECS[name]
        v = stat_values(members, key)
        if v.size == 0:
            continue
        if len(members) == 1:
            txt = fmt(v[0])
        else:
            txt = f"{fmt(v.mean())} ± {fmt(v.std(ddof=1)) if v.size > 1 else '–'}"
        lines.append(f"{name}: {txt}{(' ' + unit) if unit else ''}")
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


def common_curves(members: list[Measurement]):
    """Mean and SD of q / Passant across replicates on the first member's grid."""
    x = members[0].diameter
    qs, ps = [], []
    for m in members:
        if m.diameter.shape == x.shape and np.allclose(m.diameter, x):
            qs.append(m.q); ps.append(m.passant)
        else:
            lx, lm = np.log10(x), np.log10(m.diameter)
            qs.append(np.interp(lx, lm, m.q, left=0, right=0))
            ps.append(np.interp(lx, lm, m.passant, left=0, right=100))
    qs, ps = np.array(qs), np.array(ps)
    sd = (
        (lambda a: a.std(axis=0, ddof=1))
        if len(members) > 1
        else (lambda a: np.zeros(a.shape[1]))
    )
    return x, qs.mean(axis=0), ps.mean(axis=0), sd(qs), sd(ps)


def check_condition(c: Condition) -> list[str]:
    msgs = [f"{m.name}: {f}" for m in c.members for f in m.flags]
    d50 = stat_values(c.members, "D50_um")
    if d50.size > 1 and d50.mean() > 0:
        cv = 100 * d50.std(ddof=1) / d50.mean()
        if cv > config.WARN_CV_D50_PERCENT:
            msgs.append(
                f"{c.name}: D50 CV = {cv:.1f} % (> {config.WARN_CV_D50_PERCENT:.0f} %)"
            )
    return msgs