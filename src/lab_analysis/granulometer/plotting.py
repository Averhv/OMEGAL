"""Rendering: individual, replicates, comparison, overview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.transforms import ScaledTranslation
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

from . import config
from .models import Condition, Measurement
from .stats import common_curves, fmt, shades, stat_values, stats_text
from ..common.io import safe_filename
from ..common.plotting import save_figure


@dataclass
class Curve:
    x: np.ndarray
    q: np.ndarray
    p: np.ndarray
    label: str
    color: str
    lw: float = 2.1
    alpha: float = 1.0
    q_sd: Optional[np.ndarray] = None
    p_sd: Optional[np.ndarray] = None
    legend: bool = True


# --- Utils -------------------------------------------------------------------
def in_notebook() -> bool:
    try:
        from IPython import get_ipython
        return get_ipython() is not None
    except Exception:
        return False


def x_limits(curves: list[Curve], kind: str) -> tuple[float, float]:
    if config.X_LIMITS:
        return config.X_LIMITS
    if config.X_RANGE_MODE.lower() == "full":
        return min(c.x.min() for c in curves), max(c.x.max() for c in curves)
    active = []
    for c in curves:
        qmax = float(c.q.max()) if c.q.size else 0.0
        mq = c.q > qmax * config.Q_CUTOFF if qmax > 0 else np.zeros_like(c.q, dtype=bool)
        mp = (c.p > 0.1) & (c.p < 99.9)
        mask = mq if kind == "q" else mp if kind == "passant" else (mq | mp)
        active.extend(c.x[mask].tolist())
    if not active:
        active = [v for c in curves for v in c.x]
    lo, hi = min(active), max(active)
    if lo == hi:
        lo, hi = lo / 1.5, hi * 1.5
    return lo / config.X_MARGIN, hi * config.X_MARGIN


def _format_log_x(ax, limits) -> None:
    ax.set_xscale("log")
    ax.set_xlim(*limits)
    ax.set_xlabel(config.X_AXIS_LABEL)
    ax.xaxis.set_major_locator(LogLocator(base=10.0, subs=(1.0, 2.0, 5.0)))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    # Add 1.5 to minor subs so the 1-2 gap (largest on log scale) gets a tick.
    ax.xaxis.set_minor_locator(LogLocator(
        base=10.0, subs=(1.5, 3.0, 4.0, 6.0, 7.0, 8.0, 9.0)
    ))
    ax.xaxis.set_minor_formatter(NullFormatter())
    if config.SHOW_GRID:
        ax.grid(True, which="major", linestyle="--", linewidth=0.65, alpha=0.42)
        ax.grid(True, which="minor", axis="x", linestyle=":", linewidth=0.45, alpha=0.25)
    ax.set_axisbelow(True)


def _draw_curves(ax_q, ax_p, curves, kind) -> None:
    """Draw curves on the given axes. Pass None for an axis to skip it."""
    for c in curves:
        if kind in ("q", "both", "combined") and ax_q is not None:
            ax_q.plot(c.x, c.q, color=c.color, lw=c.lw, alpha=c.alpha, zorder=3)
            if c.q_sd is not None and config.SHOW_SD_BAND:
                ax_q.fill_between(
                    c.x, np.clip(c.q - c.q_sd, 0, None), c.q + c.q_sd,
                    color=c.color, alpha=0.16, lw=0, zorder=2,
                )
        if kind in ("passant", "both", "combined") and ax_p is not None:
            ax_p.plot(c.x, c.p, color=c.color, lw=c.lw * 0.9, alpha=c.alpha,
                      ls="-" if kind == "passant" else "--", zorder=3)
            if c.p_sd is not None and config.SHOW_SD_BAND:
                ax_p.fill_between(
                    c.x, np.clip(c.p - c.p_sd, 0, 100), np.clip(c.p + c.p_sd, 0, 100),
                    color=c.color, alpha=0.14, lw=0, zorder=2,
                )


# --- Layout -------------------------------------------------------------------
MAIN_W_IN = 8.2   # width reserved for the plot itself (constant for every figure)
FIG_H_IN = 5.6


def _handles(curves, kind) -> list:
    handles = [
        Line2D([], [], color=c.color, lw=c.lw, label=c.label)
        for c in curves if c.legend
    ]
    if kind in ("both", "combined"):
        handles += [
            Line2D([], [], color="0.35", lw=1.8, label="q (%)"),
            Line2D([], [], color="0.35", lw=1.8, ls="--", label="Passant (%)"),
        ]
    return handles


def _new_figure(handles, box_text: str, twin: bool):
    """Return (fig, ax, side). `side` is a dedicated blank axes for legend + stats."""
    margins = 2.0 if twin else 1.2          # y-labels / tick labels (right one only if twin)
    if not (config.LEGEND_OUTSIDE and (handles or box_text)):
        fig, ax = plt.subplots(figsize=(MAIN_W_IN + margins, FIG_H_IN))
        return fig, ax, None
    n_leg = max((len(h.get_label()) for h in handles), default=0)
    n_box = max((len(t) for t in box_text.splitlines()), default=0)
    side_w = max(0.75 + 0.065 * n_leg, 0.45 + 0.065 * n_box, 1.4)   # inches
    fig = plt.figure(figsize=(MAIN_W_IN + side_w + margins, FIG_H_IN))
    gs = fig.add_gridspec(1, 2, width_ratios=[MAIN_W_IN, side_w])
    ax = fig.add_subplot(gs[0])
    side = fig.add_subplot(gs[1])
    side.axis("off")
    return fig, ax, side


def _annotate(fig, ax, side, handles, box_text: str, kind: str) -> None:
    show_box = bool(box_text) and config.SHOW_STATS_BOX
    box_style = {"boxstyle": "round,pad=0.45", "facecolor": "white",
                 "edgecolor": "#B8C1CC", "alpha": 0.92}
    if side is not None:
        legend = None
        if handles:
            legend = side.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, 1),
                                 bbox_transform=side.transAxes, borderaxespad=0,
                                 frameon=True, framealpha=0.94, fontsize=8.5)
        if show_box:
            y_top = 1.0
            if legend is not None:
                fig.canvas.draw()  # needed to measure the legend height
                bbox = legend.get_window_extent().transformed(side.transAxes.inverted())
                y_top = bbox.y0 - 0.025
            shift = ScaledTranslation(0.055, 0, fig.dpi_scale_trans)  # align with legend frame
            side.text(0, y_top, box_text, transform=side.transAxes + shift, ha="left",
                      va="top", fontsize=8.5, bbox=box_style)
        return
    if handles:
        ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=0.94, fontsize=8.5)
    if show_box:
        x, y, va = (0.97, 0.97, "top") if kind == "q" else (0.97, 0.04, "bottom")
        ax.text(x, y, box_text, transform=ax.transAxes, ha="right", va=va,
                fontsize=8.5, bbox=box_style)


def render(curves: list[Curve], kind: str, title: str, out_stem: Path,
           box_text: str = "", show: bool = False) -> None:
    twin = kind in ("combined", "both")
    kind = "both" if twin else kind
    handles = _handles(curves, kind)
    fig, ax, side = _new_figure(handles, box_text if config.SHOW_STATS_BOX else "", twin)

    if twin:
        ax2 = ax.twinx()
        _draw_curves(ax, ax2, curves, "both")
    elif kind == "passant":
        _draw_curves(None, ax, curves, "passant")
    else:
        _draw_curves(ax, None, curves, "q")

    _format_log_x(ax, x_limits(curves, kind))
    if kind == "passant":
        ax.set_ylabel(config.PASSANT_AXIS_LABEL, fontsize=11)
        ax.set_ylim(0, 100)
    else:
        ax.set_ylabel(config.Q_AXIS_LABEL, fontsize=11)
        ax.set_ylim(0, None)
    if twin:
        ax2.set_ylabel(config.PASSANT_AXIS_LABEL, fontsize=11, labelpad=10)
        ax2.set_ylim(0, 100)
        ax2.spines["right"].set_visible(True)
    if config.SHOW_TITLE:
        ax.set_title(title, pad=12, weight="semibold")

    fig.tight_layout()
    _annotate(fig, ax, side, handles, box_text, kind)
    save_figure(fig, out_stem, config.PNG_DPI, config.SAVE_PDF)
    if show and in_notebook():
        plt.show()
    plt.close(fig)


# --- Plot kinds --------------------------------------------------------------
def legend_label(m: Measurement) -> str:
    label = m.label
    if config.STATS_IN_LEGEND:
        parts = []
        if m.stats.get("D50_um"):
            parts.append(f"D50 {fmt(m.stats['D50_um'])} µm")
        if m.stats.get("span_calculated") is not None:
            parts.append(f"span {m.stats['span_calculated']:.2f}")
        if parts:
            label += f" ({', '.join(parts)})"
    return label


_DESCR = {"q": "q(%)", "passant": "cumulative", "both": "q + cumulative",
          "combined": "q + cumulative"}


def plot_individual(m: Measurement, shade: str, out_dir: Path) -> None:
    folder = out_dir / safe_filename(m.group or m.name)
    curve = [Curve(m.diameter, m.q, m.passant, legend_label(m), shade)]
    for kind in config.PLOT_KINDS:
        base = config.CUSTOM_TITLES.get(m.name, m.name)
        render(
            curve, kind,
            f"{config.TITLE_PREFIX} — {base} — {_DESCR[kind]}",
            folder / f"{safe_filename(m.name)}_{kind}",
            stats_text([m]),
            show=config.SHOW_INLINE == "all",
        )


def plot_replicates(c: Condition, family: str, out_dir: Path) -> None:
    """Trace les réplicats d'une condition donnée."""
    colours = shades(family, len(c.members))
    curves = []
    for i, m in enumerate(c.members):
        lbl = legend_label(m)
        if m.temperature and m.temperature not in lbl:
            lbl = f"{lbl} [{m.temperature}]"
        curves.append(Curve(m.diameter, m.q, m.passant, lbl, colours[i]))

    kinds = getattr(config, "REPLICATES_PLOT_KINDS", ("q",))
    for kind in kinds:
        render(
            curves, kind,
            f"{config.CUSTOM_TITLES.get(c.name, c.name)} — {_DESCR[kind]}",
            out_dir / f"{safe_filename(c.name)}_{kind}",
            stats_text(c.members),
            show=config.SHOW_INLINE == "all",
        )


def plot_comparison(key: tuple, conds: list[Condition], family: str,
                    out_dir: Path, compare_over: str) -> None:
    colours = shades(family, max(len(conds), 1))
    curves: list[Curve] = []
    for cond, colour in zip(conds, colours):
        x, q, p, qs, ps = common_curves(cond.members)
        multi = len(cond.members) > 1
        label = config.CUSTOM_LEGEND_LABELS.get(cond.name) or cond.name
        if config.LEGEND_COMPARE_SHORT and not config.CUSTOM_LEGEND_LABELS.get(cond.name):
            if compare_over == "time" and cond.time is not None:
                label = f"{cond.time:g} s"
            elif compare_over == "volume" and cond.volume is not None:
                label = f"{cond.volume:g} mL"
            elif compare_over == "sample":
                label = cond.sample
        d50 = stat_values(cond.members, "D50_um")
        if config.STATS_IN_LEGEND and d50.size:
            label += f" (D50 {fmt(d50.mean())} µm)"

        show_mean = (
            config.COMPARE_SHOW_MEAN or not multi or not config.COMPARE_SHOW_REPLICATES
        )
        if multi and config.COMPARE_SHOW_REPLICATES:
            for j, m in enumerate(cond.members):
                curves.append(Curve(
                    m.diameter, m.q, m.passant,
                    label if (not show_mean and j == 0) else "",
                    colour,
                    lw=0.9 if show_mean else 1.8,
                    alpha=0.4 if show_mean else 0.9,
                    legend=(not show_mean and j == 0),
                ))
        if show_mean:
            curves.append(Curve(
                x, q, p, label, colour, lw=2.6,
                q_sd=qs if multi else None,
                p_sd=ps if multi else None,
            ))

    what = {
        "time": "sonication time",
        "volume": "volume",
        "sample": "sample",
        "temperature": "heat treatment",
    }[compare_over]
    key_text = "_".join(str(v) for v in key if v is not None)
    title = config.CUSTOM_TITLES.get(
        key_text, f"{config.TITLE_PREFIX} — {key_text} — effect of {what}"
    )
    for kind in config.PLOT_KINDS:
        render(
            curves, kind,
            f"{title} — {_DESCR[kind]}",
            out_dir / f"{safe_filename(key_text)}_{kind}",
            show=config.SHOW_INLINE in ("all", "comparison"),
        )


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
            ax.plot(m.diameter, m.q, color=colours[j], lw=1.2)
        ax.set_title(cond.name, fontsize=8.5)
        ax.set_xscale("log")
        if i % cols == 0:
            ax.set_ylabel(config.Q_AXIS_LABEL, fontsize=8.5)
        if i >= (rows - 1) * cols:
            ax.set_xlabel(config.X_AXIS_LABEL, fontsize=8.5)
        if config.SHOW_GRID:
            ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.35)
    for j in range(n, len(axes)):
        axes[j].axis("off")
    fig.suptitle(f"{config.TITLE_PREFIX} — overview", y=1.02,
                 fontsize=12, weight="semibold")
    fig.tight_layout()
    save_figure(fig, out_dir / "all_conditions", config.PNG_DPI, False)
    plt.close(fig)