"""Orchestrator: wire parsing -> organise -> plot -> report."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from . import config
from .grouping import organise
from .models import Condition, Measurement
from .parsing import parse_txt, parse_xlsx
from .plotting import (
    plot_comparison, plot_individual, plot_overview, plot_replicates,
)
from .reports import write_csvs
from .stats import check_condition, palette_name, shades
from ..common.io import write_run_info
from ..common.plotting import apply_style


def _default_input_dir() -> Path:
    return Path.cwd()


def _collect_paths(in_dir: Path) -> list[Path]:
    paths: list[Path] = []
    if config.READ_TXT:
        paths += sorted(in_dir.glob("*.txt"), key=lambda p: p.name.lower())
    if config.READ_XLSX:
        paths += sorted(
            (p for p in in_dir.glob("*.xlsx") if not p.name.startswith("~$")),
            key=lambda p: p.name.lower(),
        )
    return [p for p in paths
            if not p.name.lower().startswith(("requirements", "readme"))]


def _family_for(cond: Condition, samples: list[str], fallback: int) -> str:
    for key in (cond.name, cond.sample):
        if key in config.GROUP_PALETTES:
            return config.GROUP_PALETTES[key]
    return palette_name(
        cond.sample,
        samples.index(cond.sample) if cond.sample in samples else fallback,
    )


def run(
    input_dir: Optional[Union[Path, str]] = None,
    output_dir: Optional[Union[Path, str]] = None,
) -> tuple[list[Measurement], list[Condition]]:
    """Exécute l'ensemble du pipeline d'analyse granulométrique."""
    apply_style()

    in_dir = Path(input_dir).expanduser().resolve() if input_dir else _default_input_dir()
    out_dir = (Path(output_dir).expanduser().resolve() if output_dir
               else in_dir / config.OUTPUT_NAME)
    print(f"Reading from: {in_dir}")
    print(f"Writing to:   {out_dir}")

    measurements: list[Measurement] = []
    sequential: set[str] = set()
    for path in _collect_paths(in_dir):
        try:
            found = parse_xlsx(path) if path.suffix.lower() == ".xlsx" else [parse_txt(path)]
        except Exception as exc:
            print(f"[SKIP] {path.name}: {exc}")
            continue
        if path.suffix.lower() == ".xlsx":
            sequential.update(m.source for m in found)
        measurements += found
        print(f"[OK] {path.name}: {len(found)} measurement(s)")

    if not measurements:
        print(f"No usable files in {in_dir}.")
        return [], []

    conditions = organise(measurements, sequential)
    samples = sorted({c.sample for c in conditions})

    # --- Graphiques Individuels et Réplicats ---
    for i, cond in enumerate(conditions):
        family = _family_for(cond, samples, i)
        if config.MAKE_INDIVIDUAL:
            colours = shades(family, max(len(cond.members), 1))
            for j, m in enumerate(cond.members):
                plot_individual(m, colours[j], out_dir / "individual")
        if config.MAKE_REPLICATES and len(cond.members) > 1:
            plot_replicates(cond, family, out_dir / "replicates")

    # --- Comparaisons Multi-Conditions ---
    if config.MAKE_COMPARISONS:
        temp_sort = lambda c: (
            -1.0 if not c.temperature else float(c.temperature.rstrip("cC° "))
        )
        if config.COMPARE_OVER == "time":
            key_of = lambda c: (c.sample, c.volume, c.temperature)
            sort_of = lambda c: c.time if c.time is not None else 1e9
            base_folder = out_dir / "comparisons" / "by_time"
        elif config.COMPARE_OVER == "volume":
            key_of = lambda c: (c.sample, c.time, c.temperature)
            sort_of = lambda c: c.volume if c.volume is not None else 1e9
            base_folder = out_dir / "comparisons" / "by_volume"
        elif config.COMPARE_OVER == "temperature":
            key_of = lambda c: (c.sample, c.volume, c.time)
            sort_of = temp_sort
            base_folder = out_dir / "comparisons" / "by_temperature"
        else:  # sample
            key_of = lambda c: (c.volume, c.time, c.temperature)
            sort_of = lambda c: c.sample.lower()
            base_folder = out_dir / "comparisons" / "by_sample"

        series: dict[tuple, list[Condition]] = {}
        for cond in conditions:
            series.setdefault(key_of(cond), []).append(cond)

        for index, key in enumerate(
            sorted(series, key=lambda k: tuple(v if isinstance(v, (int, float)) else 0 for v in k))
        ):
            conds = sorted(series[key], key=sort_of)
            if len(conds) < 2:
                continue
            if config.COMPARE_OVER == "temperature" and len({c.temperature for c in conds}) < 2:
                continue
            plot_comparison(
                key, conds, _family_for(conds[0], samples, index),
                base_folder, config.COMPARE_OVER,
            )

    # --- Vue d'ensemble ---
    if config.MAKE_OVERVIEW:
        plot_overview(conditions, lambda c, i: _family_for(c, samples, i),
                      out_dir / "overview")

    # --- Rapports CSV & Run Info ---
    write_csvs(measurements, conditions, out_dir / "summary")
    write_run_info({
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "n_measurements": len(measurements),
        "n_conditions": len(conditions),
        "plot_kinds": list(config.PLOT_KINDS),
        "compare_over": config.COMPARE_OVER,
        "stats_fields": list(config.STATS_FIELDS),
        "x_range_mode": config.X_RANGE_MODE,
        "q_cutoff": config.Q_CUTOFF,
    }, out_dir)

    print("\nChecks:")
    warnings = [msg for c in conditions for msg in check_condition(c)]
    print("\n".join(f"  [WARN] {m}" for m in warnings) or "  none")
    print(f"\nResults folder: {out_dir}")
    return measurements, conditions