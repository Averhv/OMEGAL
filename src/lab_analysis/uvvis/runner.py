from __future__ import annotations

import string
from pathlib import Path
from typing import Optional, Union

from . import config
from .models import Condition, Spectrum
from .parsing import parse_spectrum_file, split_replicate
from .stats import calculate_pigments_and_metrics, palette_name, shades, stat_values
from .plotting import plot_comparison, plot_individual, plot_overview, plot_replicates
from .reports import write_csvs
from ..common.io import write_run_info
from ..common.plotting import apply_style


def _default_input_dir() -> Path:
    return Path.cwd()


def _collect_paths(in_dir: Path) -> list[Path]:
    paths = []
    if config.READ_TXT:
        paths += sorted(in_dir.glob("*.txt"), key=lambda p: p.name.lower())
    if config.READ_CSV:
        paths += sorted(in_dir.glob("*.csv"), key=lambda p: p.name.lower())
    return [p for p in paths if not p.name.lower().startswith(("requirements", "readme"))]


def organise(spectra: list[Spectrum]) -> list[Condition]:
    groups: dict[str, list[Spectrum]] = {}
    for spec in spectra:
        sample, rep, dil = split_replicate(spec.source)
        spec.group = sample
        spec.replicate = rep
        spec.sample = sample
        spec.dilution_factor = dil
        groups.setdefault(sample, []).append(spec)

    conditions: list[Condition] = []
    for sample_name, members in groups.items():
        used = {m.replicate for m in members if m.replicate}
        free = iter(c for c in string.ascii_lowercase if c not in used)
        for m in members:
            if not m.replicate:
                candidate = next(free, None)
                if candidate is None:
                    idx = sum(1 for x in members if m.replicate.startswith("rep"))
                    candidate = f"rep{idx + 1}"
                m.replicate = candidate
        members.sort(key=lambda m: m.replicate)

        for m in members:
            if len(members) > 1:
                # Include dilution factor F in the display name for clarity
                m.name = f"{sample_name} (Tube {m.replicate}, F={m.dilution_factor:g})"
            else:
                m.name = f"{sample_name} (F={m.dilution_factor:g})"

        conditions.append(Condition(
            name=sample_name,
            members=members,
            sample=sample_name,
            dilution_factor=members[0].dilution_factor if members else config.DEFAULT_DILUTION_FACTOR,
            extract_volume_ml=config.DEFAULT_EXTRACT_VOLUME_ML,
            dry_mass_mg=config.DEFAULT_DRY_MASS_MG,
        ))

    return sorted(conditions, key=lambda c: c.sample.lower())


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
) -> tuple[list[Spectrum], list[Condition]]:
    apply_style()

    in_dir = Path(input_dir).expanduser().resolve() if input_dir else _default_input_dir()
    out_dir = (Path(output_dir).expanduser().resolve() if output_dir
               else in_dir / config.OUTPUT_NAME)
    print(f"Reading UV-Vis from: {in_dir}")
    print(f"Writing to:          {out_dir}")

    spectra: list[Spectrum] = []
    for path in _collect_paths(in_dir):
        try:
            spec = parse_spectrum_file(path)
            spec.stats = calculate_pigments_and_metrics(spec)
            spectra.append(spec)
            print(f"[OK] {path.name}")
        except Exception as exc:
            print(f"[SKIP] {path.name}: {exc}")

    if not spectra:
        print(f"No usable UV-Vis files found in {in_dir}.")
        return [], []

    conditions = organise(spectra)
    samples = sorted({c.sample for c in conditions})

    for i, cond in enumerate(conditions):
        family = _family_for(cond, samples, i)
        colors = shades(family, max(len(cond.members), 1))
        
        if config.MAKE_INDIVIDUAL:
            for j, m in enumerate(cond.members):
                plot_individual(m, colors[j], out_dir / "individual")
                
        if config.MAKE_REPLICATES and len(cond.members) > 1:
            plot_replicates(cond, family, out_dir / "replicates")

    # Combined comparison for all samples grouped together
    if config.MAKE_COMPARISONS and conditions:
        comp_dir = out_dir / "comparison"
        comp_dir.mkdir(parents=True, exist_ok=True)
        for i, cond in enumerate(conditions):
            family = _family_for(cond, samples, i)
            plot_comparison((cond.name,), [cond], family, comp_dir)

    if config.MAKE_OVERVIEW:
        plot_overview(conditions, lambda c, i: _family_for(c, samples, i), out_dir / "overview")

    write_csvs(spectra, conditions, out_dir / "summary")
    write_run_info({
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "n_spectra": len(spectra),
        "n_conditions": len(conditions),
    }, out_dir)

    print("\nUV-Vis Quality Checks & Warnings:")
    all_warnings = [f"{s.name}: {w}" for s in spectra for w in s.flags]
    print("\n".join(f"  [WARN] {w}" for w in all_warnings) or "  none (all measurements passed)")
    print(f"\nResults folder: {out_dir}")
    return spectra, conditions