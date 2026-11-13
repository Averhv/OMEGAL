from __future__ import annotations

import warnings
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import AutoMinorLocator
from matplotlib.transforms import ScaledTranslation

from . import config
from .models import Condition, Spectrum
from .parsing import get_meta
from .stats import (calculate_pigments_and_metrics, fmt, palette_name, shades, stats_text,
                    turbidity_corrected_absorbance)
from ..common.io import safe_filename
from ..common.plotting import save_figure

# Guide lines: the wavelengths of the equations of Lopez 2025 (carotenoids 470, Chl b 648, Chl a 664).
GUIDE_WAVELENGTHS = (470, 648, 664)
TURB_SUFFIX = "_turbidity_corrected"


@dataclass
class Curve:
    x: np.ndarray
    y: np.ndarray
    label: str
    color: str
    lw: float = 2.1
    alpha: float = 1.0
    y_sd: Optional[np.ndarray] = None
    legend: bool = True
    y_corr: Optional[np.ndarray] = None   # spectrum with the linear turbidity baseline removed
    label_corr: Optional[str] = None      # legend text for the corrected figure (no pigment values)


def x_limits(curves: list[Curve]) -> tuple[float, float]:
    if config.X_LIMITS:
        return config.X_LIMITS
    lo = min(c.x.min() for c in curves)
    hi = max(c.x.max() for c in curves)
    return lo, hi


def style_axes(ax, fontsize: float = 11, tick_size: float = 10) -> None:
    """Clean look: no grid, no top/right frame, outward major and minor ticks."""
    ax.grid(False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(1.0)
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.tick_params(which="major", direction="out", length=5, width=1.0, labelsize=tick_size)
    ax.tick_params(which="minor", direction="out", length=2.5, width=0.7)
    ax.set_axisbelow(True)


def draw_guides(ax) -> None:
    """Thin dotted guide lines at the wavelengths used by the pigment equations, labelled."""
    if not config.SHOW_WAVELENGTH_MARKERS:
        return
    for wl in GUIDE_WAVELENGTHS:
        ax.axvline(x=wl, color="0.65", linestyle=":", lw=1.0, zorder=1)
        ax.text(wl - 1.5, 0.985, f"{wl} nm", transform=ax.get_xaxis_transform(), rotation=90,
                ha="right", va="top", fontsize=7.5, color="0.45")


def _draw(curves: list[Curve], out_stem: Path, box_text: str, corrected: bool) -> None:
    margins = 1.2
    labels = [(c.label_corr or c.label) if corrected else c.label for c in curves]
    n_leg = max((len(t) for t in labels if t), default=0)
    n_box = max((len(t) for t in box_text.splitlines()), default=0)
    side_w = max(0.75 + 0.065 * n_leg, 0.45 + 0.065 * n_box, 1.4)

    fig = plt.figure(figsize=(8.2 + side_w + margins, 5.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[8.2, side_w])
    ax = fig.add_subplot(gs[0])
    side = fig.add_subplot(gs[1])
    side.axis("off")

    ys = [c.y_corr if corrected else c.y for c in curves]
    for c, y in zip(curves, ys):
        ax.plot(c.x, y, color=c.color, lw=c.lw, alpha=c.alpha, zorder=3)
        if c.y_sd is not None and config.SHOW_SD_BAND:
            ax.fill_between(c.x, y - c.y_sd, y + c.y_sd,
                            color=c.color, alpha=0.16, lw=0, zorder=2)

    ax.set_xlim(*x_limits(curves))
    if corrected:  # the corrected spectrum can dip below zero: keep it visible
        ax.set_ylim(min(-0.05, 1.05 * min(float(np.nanmin(y)) for y in ys)), None)
    else:
        ax.set_ylim(-0.05, None)  # automatic upper limit, as before
    ax.set_xlabel(config.X_AXIS_LABEL, fontsize=11)
    ax.set_ylabel(config.Y_AXIS_LABEL + (" – turbidity removed" if corrected else ""), fontsize=11)
    style_axes(ax)
    draw_guides(ax)

    handles = [Line2D([], [], color=c.color, lw=c.lw, label=t)
               for c, t in zip(curves, labels) if c.legend and t]
    legend = None
    if handles:
        legend = side.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, 1),
                             bbox_transform=side.transAxes, borderaxespad=0,
                             frameon=True, framealpha=0.94, fontsize=8.5)

    if box_text and config.SHOW_STATS_BOX:
        y_top = 1.0
        if legend is not None:
            fig.canvas.draw()
            bbox = legend.get_window_extent().transformed(side.transAxes.inverted())
            y_top = bbox.y0 - 0.025
        shift = ScaledTranslation(0.055, 0, fig.dpi_scale_trans)
        box_style = {"boxstyle": "round,pad=0.45", "facecolor": "white", "edgecolor": "#B8C1CC", "alpha": 0.92}
        side.text(0, y_top, box_text, transform=side.transAxes + shift, ha="left", va="top", fontsize=8.5, bbox=box_style)

    fig.tight_layout()
    Path(out_stem).parent.mkdir(parents=True, exist_ok=True)
    save_figure(fig, out_stem, config.PNG_DPI, config.SAVE_PDF)
    plt.close(fig)


def render(curves: list[Curve], title: str, out_stem: Path, box_text: str = "", box_text_corr: str = "") -> None:
    """Writes the figure, then the same figure with the linear turbidity baseline removed
    (<name>_turbidity_corrected.png) unless config.TURBIDITY_PLOTS is False.
    `title` is kept for the callers, but no title is drawn."""
    out_stem = Path(out_stem)
    _draw(curves, out_stem, box_text, corrected=False)
    if getattr(config, "TURBIDITY_PLOTS", True):
        if all(c.y_corr is not None for c in curves):
            _draw(curves, out_stem.with_name(out_stem.name + TURB_SUFFIX), box_text_corr, corrected=True)
        else:
            warnings.warn(f"{out_stem.name}: A520 or A750 outside the measured range, no turbidity-corrected plot.")


def legend_label(spec: Spectrum, with_stats: bool = True, turbidity: str | None = None) -> str:
    """'Tube 1 (F=2)', 'Tube 1 (r=12.5, ref)', 'Tube 2 (r=5, F=2)'...  The Chl a value in the legend follows
    the same turbidity model as the figure (turbidity='linear' for the corrected figure)."""
    meta = get_meta(spec)
    parts = []
    if meta["carbon_ratio"] is not None:
        parts.append(f"r={meta['carbon_ratio']:g}")
    if spec.dilution_factor != 1 or meta["carbon_ratio"] is None:
        parts.append(f"F={spec.dilution_factor:g}")
    if meta["is_reference"]:
        parts.append("ref")
    base = f"Tube {spec.replicate} ({', '.join(parts)})"
    if with_stats and config.STATS_IN_LEGEND:
        st = spec.stats if turbidity is None else calculate_pigments_and_metrics(spec, turbidity)
        chl_a = st.get("Chl_a_ug_mL")
        if chl_a is not None and np.isfinite(chl_a):
            base += f" (Chl a: {fmt(chl_a)} µg/mL)"
    return base


def _curve(spec: Spectrum, colour: str, **kw) -> Curve:
    return Curve(spec.wavelength, spec.absorbance, legend_label(spec), colour,
                 y_corr=turbidity_corrected_absorbance(spec),
                 label_corr=legend_label(spec, turbidity="linear"), **kw)


def _box_corr(members: list[Spectrum]) -> str:
    """Stats box of the corrected figure: pigments recomputed on the linearly corrected spectra."""
    txt = stats_text(members, turbidity="linear")
    return ("Linear turbidity correction\n" + txt) if txt else ""


def plot_individual(spec: Spectrum, shade: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    title = config.CUSTOM_TITLES.get(spec.name, spec.name)
    render([_curve(spec, shade)], title, out_dir / f"{safe_filename(spec.source)}_spectrum",
           stats_text([spec]), _box_corr([spec]))


def plot_replicates(cond: Condition, family: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    colours = shades(family, len(cond.members))
    curves = [_curve(m, colours[i]) for i, m in enumerate(cond.members)]
    render(curves, cond.name, out_dir / f"{safe_filename(cond.name)}_replicates",
           stats_text(cond.members), _box_corr(cond.members))


def _tube_sort_key(spec: Spectrum):
    m = get_meta(spec)
    r = m["carbon_ratio"] if m["carbon_ratio"] is not None else -1.0
    return (r, spec.dilution_factor, m["is_reference"], m["time"])


# Spectra seen by plot_comparison, per output folder: {out_dir: {(batch, tube): {file: Spectrum}}}.
# plot_comparison is called once per condition; each call re-writes the tube figures with everything seen
# so far, so the last call leaves the complete comparison on disk (same file names, overwritten).
_SEEN: dict[str, dict[tuple, dict[str, Spectrum]]] = defaultdict(lambda: defaultdict(dict))
_FAMILY: dict[tuple, str] = {}


def _register(out_dir: Path, spec: Spectrum, family: str | None) -> None:
    m = get_meta(spec)
    folder = str(Path(out_dir).resolve())
    _SEEN[folder][(m["batch"], m["tube"])][spec.source] = spec
    if family:
        _FAMILY.setdefault((folder, m["batch"], m["tube"]), family)


def _write_tube_comparisons(out_dir: Path) -> list[Path]:
    """One figure per (batch, tube) with every condition measured on that tube superimposed
    (r, ref, F...), light to dark with increasing r then F. Two files: raw and turbidity-corrected."""
    out_dir = Path(out_dir)
    folder = str(out_dir.resolve())
    written = []
    for idx, ((batch, tube), by_file) in enumerate(sorted(_SEEN[folder].items())):
        members = sorted(by_file.values(), key=_tube_sort_key)
        if len(members) < 2:
            continue  # nothing to compare yet
        for s in members:
            if not s.stats:
                s.stats = calculate_pigments_and_metrics(s)
        family = _FAMILY.get((folder, batch, tube)) or palette_name(batch, idx)
        colours = shades(family, len(members))
        curves = [_curve(s, colours[i], lw=1.9) for i, s in enumerate(members)]
        stem = out_dir / f"{safe_filename(batch)}_tube{safe_filename(tube)}_comparison"
        render(curves, f"{batch} tube {tube}", stem, "", "")  # a mean across different conditions would be meaningless
        written.append(stem)
    return written


def plot_comparison(key: tuple, conds: list[Condition], family: str, out_dir: Path) -> None:
    """Comparison of every condition measured on the same tube (one figure per tube, plus its
    turbidity-corrected version). Keeps the old signature, so the runner does not change."""
    for cond in conds:
        for m in cond.members:
            _register(out_dir, m, family)
    _write_tube_comparisons(out_dir)


def plot_tube_comparisons(spectra: list[Spectrum], out_dir: Path, family: str | None = None) -> list[Path]:
    """Same as plot_comparison but from a plain list of spectra (can be called once at the end of a folder)."""
    for s in spectra:
        _register(out_dir, s, family)
    return _write_tube_comparisons(out_dir)


def _overview(conditions: list[Condition], family_for, out_stem: Path, corrected: bool) -> None:
    n = len(conditions)
    cols = min(4, n)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.0 * rows), sharex=True, sharey=True, squeeze=False)
    axes = axes.ravel()
    for i, cond in enumerate(conditions):
        ax = axes[i]
        colours = shades(family_for(cond, i), max(len(cond.members), 1))
        for j, m in enumerate(cond.members):
            y = turbidity_corrected_absorbance(m) if corrected else m.absorbance
            if y is None:
                continue
            ax.plot(m.wavelength, y, color=colours[j], lw=1.2, label=legend_label(m, with_stats=False))
        ax.text(0.97, 0.95, cond.name, transform=ax.transAxes, ha="right", va="top", fontsize=8.5)
        style_axes(ax, tick_size=8)
        if i % cols == 0:
            ax.set_ylabel(config.Y_AXIS_LABEL + (" – turbidity removed" if corrected else ""), fontsize=8.5)
        if i >= (rows - 1) * cols:
            ax.set_xlabel(config.X_AXIS_LABEL, fontsize=8.5)
    for j in range(n, len(axes)):
        axes[j].axis("off")
    fig.tight_layout()
    Path(out_stem).parent.mkdir(parents=True, exist_ok=True)
    save_figure(fig, out_stem, config.PNG_DPI, False)
    plt.close(fig)


def plot_overview(conditions: list[Condition], family_for, out_dir: Path) -> None:
    if not conditions:
        return
    _overview(conditions, family_for, out_dir / "all_conditions", corrected=False)
    if getattr(config, "TURBIDITY_PLOTS", True):
        _overview(conditions, family_for, out_dir / f"all_conditions{TURB_SUFFIX}", corrected=True)