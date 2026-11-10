from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .models import Spectrum
from ..common.io import read_text

# ---------------------------------------------------------------------------
# File-name convention (tokens separated by "_", order does not matter after the batch):
#   Sat_s2_F2_113154                  -> batch Sat, tube 2, dilution 2, time 11:31:54
#   Sat_depig_s1_r12.5_EtOH_ref       -> batch Sat, depigmentation test, tube 1,
#                                        carbon/pigment ratio r = 12.5 mg/mg, solvent EtOH, reference
#   Sat_1_F2_112638 / Sat_a_F4_...    -> legacy names (bare tube number or letter) still work
# F is 1 when it is not in the name.
# ---------------------------------------------------------------------------
_TIME_RE = re.compile(r"^\d{6}$")
_DIL_RE = re.compile(r"^F(?P<v>\d+(?:\.\d+)?)$", re.IGNORECASE)
_RATIO_RE = re.compile(r"^r(?P<v>\d+(?:\.\d+)?)$", re.IGNORECASE)
_TUBE_RE = re.compile(r"^(?:s|rep|tube)?(?P<v>\d{1,3})$", re.IGNORECASE)
_LETTER_RE = re.compile(r"^[a-zA-Z]$")
_SOLVENTS = {"etoh", "meoh", "acetone", "h2o", "water"}


def parse_filename(name: str) -> dict:
    """Return the metadata encoded in a spectrum file name (never raises)."""
    stem = Path(name).stem  # only strips the last suffix, so "r12.5" is safe
    tokens = [t for t in re.split(r"[_\-]+", stem) if t]
    meta = {
        "batch": tokens[0] if tokens else stem,
        "tube": "",
        "dilution": 1.0,
        "carbon_ratio": None,
        "is_reference": False,
        "depig": False,
        "time": "",
        "solvent": "",
        "extras": [],
    }
    letter_tube = ""
    for tok in tokens[1:]:
        low = tok.lower()
        if low == "depig":
            meta["depig"] = True
        elif low == "ref":
            meta["is_reference"] = True
        elif _TIME_RE.match(tok):
            meta["time"] = tok
        elif _DIL_RE.match(tok):
            meta["dilution"] = float(_DIL_RE.match(tok).group("v"))
        elif _RATIO_RE.match(tok):
            meta["carbon_ratio"] = float(_RATIO_RE.match(tok).group("v"))
        elif _TUBE_RE.match(tok) and not meta["tube"]:
            meta["tube"] = _TUBE_RE.match(tok).group("v")
        elif low in _SOLVENTS:
            meta["solvent"] = tok
        elif _LETTER_RE.match(tok) and not letter_tube:
            letter_tube = tok
        else:
            meta["extras"].append(tok)
    if not meta["tube"]:
        meta["tube"] = letter_tube

    # Condition label: everything that defines the experiment except tube, dilution and time.
    parts = [meta["batch"]]
    if meta["depig"]:
        parts.append("depig")
    if meta["carbon_ratio"] is not None:
        parts.append(f"r{meta['carbon_ratio']:g}")
    if meta["is_reference"]:
        parts.append("ref")
    meta["group"] = "_".join(parts)
    return meta


def get_meta(spec: Spectrum) -> dict:
    """Metadata of a Spectrum, always derived from its file name (no change to models.py needed)."""
    return parse_filename(spec.source)


def split_replicate(name: str) -> tuple[str, str, float]:
    """Kept for backward compatibility: (condition label, tube, dilution factor)."""
    m = parse_filename(name)
    return m["group"], m["tube"], m["dilution"]


def _parse_numeric_line(line: str):
    cleaned = line.replace('"', "").replace("'", "")
    for sep in (";", ",", "\t", None):  # None = any whitespace
        raw = cleaned.split(sep) if sep else cleaned.split()
        parts = [p.strip() for p in raw if p.strip()]
        if len(parts) >= 2:
            try:
                return float(parts[0].replace(",", ".")), float(parts[1].replace(",", "."))
            except ValueError:
                continue
    return None


def parse_spectrum_file(path: Path) -> Spectrum:
    path = Path(path)
    lines = read_text(path).splitlines()

    wavelengths, absorbances = [], []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pair = _parse_numeric_line(line)
        if pair is not None:  # header lines and units are silently skipped
            wavelengths.append(pair[0])
            absorbances.append(pair[1])

    if not wavelengths:
        raise ValueError(f"Could not parse valid wavelength/absorbance data from {path.name}")

    wl_arr = np.array(wavelengths, dtype=float)
    abs_arr = np.array(absorbances, dtype=float)
    order = np.argsort(wl_arr)
    wl_arr, abs_arr = wl_arr[order], abs_arr[order]

    meta = parse_filename(path.name)
    return Spectrum(
        name=path.stem,
        source=path.name,
        wavelength=wl_arr,
        absorbance=abs_arr,
        group=meta["group"],
        replicate=meta["tube"],
        sample=meta["group"],
        dilution_factor=meta["dilution"],
    )