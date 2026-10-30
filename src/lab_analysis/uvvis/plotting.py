from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.transforms import ScaledTranslation
from matplotlib.lines import Line2D

from . import config
from .models import Condition, Spectrum
from .stats import common_curves, fmt, shades, stat_values, stats_text
from ..common.io import safe_filename
from ..common.plotting import save_figure


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


def x_limits(curves: list[Curve]) -> tuple[float, float]:
    if config.X_LIMITS:
        return config.X_LIMITS
    if config.X_RANGE_MODE.lower() == "full":
        return min(c.x.min() for c in curves), max(c.x.max() for c in curves)
    lo = min(c.x.min() for c in curves)
    hi = max(c.x.max() for c in curves)
    return lo, hi


def render(curves: list[Curve], title: str, out_stem: Path, box_text: str = "") -> None:
    margins = 1.2
    n_leg = max((len(c.label) for c in curves if c.label), default=0)
    n_box = max((len(t) for t in box_text.splitlines()), default=0)
    side_w = max(0.75 + 0.065 * n_leg, 0.45 + 0.065 * n_box, 1.4)

    fig = plt.figure(figsize=(8.2 + side_w + margins, 5.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[8.2, side_w])
    ax = fig.add_subplot(gs[0])
    side = fig.add_subplot(gs[1])
    side.axis("off")

    for c in curves:
        ax.plot(c.x, c.y, color=c.color, lw=c.lw, alpha=c.alpha, zorder=3)
        if c.y_sd is not None and config.SHOW_SD_BAND:
            ax.fill_between(
                c.x, np.clip(c.y - c.y_sd, 0, None), c.y + c.y_sd,
                color=c.color, alpha=0.16, lw=0, zorder=2,
            )

    if config.SHOW_WAVELENGTH_MARKERS:
        for wl in [470, 520, 649, 664]:
            ax.axvline(x=wl, color="0.7", linestyle=":", lw=1.0, alpha=0.7, zorder=1)

    xlims = x_limits(curves)
    ax.set_xlim(*xlims)
    ax.set_ylim(-0.05, None)
    ax.set_xlabel(config.X_AXIS_LABEL, fontsize=11)
    ax.set_ylabel(config.Y_AXIS_LABEL, fontsize=11)
    if config.SHOW_GRID:
        ax.grid(True, linestyle="--", linewidth=0.65, alpha=0.42)
    ax.set_axisbelow(True)

    handles = [Line2D([], [], color=c.color, lw=c.lw, label=c.label) for c in curves if c.legend and c.label]
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
    save_figure(fig, out_stem, config.PNG_DPI, config.SAVE_PDF)
    plt.close(fig)


def legend_label(spec: Spectrum) -> str:
    label = config.CUSTOM_LEGEND_LABELS.get(spec.name, spec.name)
    if config.STATS_IN_LEGEND and spec.stats.get("Chl_a_ug_mL"):
        label += f" (Chl a: {fmt(spec.stats['Chl_a_ug_mL'])} µg/mL)"
    return label


def plot_individual(spec: Spectrum, shade: str, out_dir: Path) -> None:
    folder = out_dir / safe_filename(spec.group or spec.name)
    curve = [Curve(spec.wavelength, spec.absorbance, legend_label(spec), shade)]
    title = config.CUSTOM_TITLES.get(spec.name, spec.name)
    render(curve, title, folder / f"{safe_filename(spec.name)}_spectrum", stats_text([spec]))


def plot_replicates(cond: Condition, family: str, out_dir: Path) -> None:
    colours = shades(family, len(cond.members))
    curves = [
        Curve(m.wavelength, m.absorbance, legend_label(m), colours[i])
        for i, m in enumerate(cond.members)
    ]
    render(curves, cond.name, out_dir / f"{safe_filename(cond.name)}_replicates", stats_text(cond.members))


def plot_comparison(key: tuple, conds: list[Condition], family: str, out_dir: Path) -> None:
    colours = shades(family, max(len(conds), 1))
    curves: list[Curve] = []
    for cond, colour in zip(conds, colours):
        x, mean_abs, sd_abs = common_curves(cond.members)
        multi = len(cond.members) > 1
        label = config.CUSTOM_LEGEND_LABELS.get(cond.name) or cond.name
        show_mean = config.COMPARE_SHOW_MEAN or not multi or not config.COMPARE_SHOW_REPLICATES

        if multi and config.COMPARE_SHOW_REPLICATES:
            for j, m in enumerate(cond.members):
                curves.append(Curve(
                    m.wavelength, m.absorbance,
                    label if (not show_mean and j == 0) else "",
                    colour,
                    lw=0.9 if show_mean else 1.8,
                    alpha=0.4 if show_mean else 0.9,
                    legend=(not show_mean and j == 0),
                ))
        if show_mean:
            curves.append(Curve(
                x, mean_abs, label, colour, lw=2.6,
                y_sd=sd_abs if multi else None,
            ))

    key_text = "_".join(str(v) for v in key if v is not None)
    title = config.CUSTOM_TITLES.get(key_text, f"{config.TITLE_PREFIX} — {key_text}")
    render(curves, title, out_dir / f"{safe_filename(key_text)}_comparison")


def plot_overview(conditions: list[Condition], family_for, out_dir: Path) -> None:
    n = len(conditions)
    if n == 0:
        return
    cols = min(4, n)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.0 * rows),
                             sharex=True, sharey=True, squeeze=False)
    axes = axes.ravel()
    for i, cond in enumerate(conditions):
        ax = axes[i]
        family = family_for(cond, i)
        colours = shades(family, max(len(cond.members), 1))
        for j, m in enumerate(cond.members):
            ax.plot(m.wavelength, m.absorbance, color=colours[j], lw=1.2)
        ax.set_title(cond.name, fontsize=8.5)
        if i % cols == 0:
            ax.set_ylabel(config.Y_AXIS_LABEL, fontsize=8.5)
        if i >= (rows - 1) * cols:
            ax.set_xlabel(config.X_AXIS_LABEL, fontsize=8.5)
        if config.SHOW_GRID:
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.35)
    for j in range(n, len(axes)):
        axes[j].axis("off")
    fig.suptitle(f"{config.TITLE_PREFIX} — overview", y=1.02, fontsize=12, weight="semibold")
    fig.tight_layout()
    save_figure(fig, out_dir / "all_conditions", config.PNG_DPI, False)
    plt.close(fig)