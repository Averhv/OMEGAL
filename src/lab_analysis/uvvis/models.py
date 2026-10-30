from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from . import config


@dataclass
class Spectrum:
    """One UV-Vis spectral measurement: wavelength and absorbance arrays + metadata."""
    name: str
    source: str
    wavelength: np.ndarray
    absorbance: np.ndarray
    stats: dict = field(default_factory=dict)
    group: str = ""
    replicate: str = ""
    sample: str = ""
    dilution_factor: float = config.DEFAULT_DILUTION_FACTOR
    extract_volume_ml: float = config.DEFAULT_EXTRACT_VOLUME_ML
    dry_mass_mg: float = config.DEFAULT_DRY_MASS_MG
    flags: list = field(default_factory=list)

    @property
    def label(self) -> str:
        return config.CUSTOM_LEGEND_LABELS.get(self.name, self.name)

    def get_absorbance_at(self, wl: float) -> float:
        """Linear interpolation of absorbance at a given wavelength (nm)."""
        if self.wavelength.size == 0:
            return 0.0
        return float(np.interp(wl, self.wavelength, self.absorbance, left=np.nan, right=np.nan))


@dataclass
class Condition:
    """A set of replicate spectral measurements sharing sample/condition."""
    name: str
    members: list[Spectrum]
    sample: str
    dilution_factor: float
    extract_volume_ml: float
    dry_mass_mg: float