"""Shared matplotlib configuration and figure persistence."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def apply_style() -> None:
    """Apply project-wide rcParams. Idempotent — call once per run."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def save_figure(fig, out_stem: Path, dpi: int = 300, save_pdf: bool = False) -> None:
    """Save `fig` as PNG (always) and PDF (optional) at `out_stem`.

    Uses `str(out_stem) + ".png"` (not `with_suffix`) because measurement names
    can legitimately contain dots (e.g. `SF_1.5mL_30s_2`), and `Path.with_suffix`
    would truncate everything after the last dot — corrupting the filename.
    """
    out_stem = Path(out_stem)
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(Path(str(out_stem) + ".png"), dpi=dpi,
                bbox_inches="tight", facecolor="white")
    if save_pdf:
        fig.savefig(Path(str(out_stem) + ".pdf"),
                    bbox_inches="tight", facecolor="white")