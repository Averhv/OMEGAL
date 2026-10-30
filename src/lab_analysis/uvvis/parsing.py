from __future__ import annotations

import re
from pathlib import Path
import numpy as np

from .models import Spectrum
from ..common.io import read_text


def split_replicate(name: str) -> tuple[str, str]:
    stem = Path(name).stem
    match = re.search(r"[-_](?:rep)?([0-9]+|[a-zA-Z])$", stem)
    if match:
        rep = match.group(1)
        base = stem[:match.start()]
        return base.strip("-_"), rep
    return stem, ""


def parse_spectrum_file(path: Path) -> Spectrum:
    path = Path(path)
    text = read_text(path)
    lines = text.splitlines()

    wavelengths = []
    absorbances = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cleaned = line.replace('"', '').replace("'", "")
        for sep in (';', ',', '\t'):
            parts = [p.strip() for p in cleaned.split(sep) if p.strip()]
            if len(parts) >= 2:
                try:
                    wl = float(parts[0].replace(',', '.'))
                    abs_val = float(parts[1].replace(',', '.'))
                    wavelengths.append(wl)
                    absorbances.append(abs_val)
                    break
                except ValueError:
                    continue

    if not wavelengths:
        raise ValueError(f"Could not parse valid wavelength/absorbance data from {path.name}")

    wl_arr = np.array(wavelengths, dtype=float)
    abs_arr = np.array(absorbances, dtype=float)

    sort_idx = np.argsort(wl_arr)
    wl_arr = wl_arr[sort_idx]
    abs_arr = abs_arr[sort_idx]

    base, rep = split_replicate(path.name)
    spec = Spectrum(
        name=path.stem,
        source=path.name,
        wavelength=wl_arr,
        absorbance=abs_arr,
        group=base,
        replicate=rep,
        sample=base,
    )
    return spec