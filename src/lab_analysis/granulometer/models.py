from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import numpy as np

from . import config


@dataclass
class Measurement:
    """One instrument export: diameter/q/Passant arrays + parsed metadata."""
    name: str
    source: str
    diameter: "np.ndarray"
    q: "np.ndarray"
    passant: "np.ndarray"
    stats: dict
    group: str = ""
    replicate: str = ""
    sample: str = ""
    volume: Optional[float] = None
    time: Optional[float] = None
    flags: list = field(default_factory=list)

    @property
    def label(self) -> str:
        return config.CUSTOM_LEGEND_LABELS.get(self.name, self.name)


@dataclass
class Condition:
    """A set of replicate measurements sharing sample/volume/time."""
    name: str
    members: list
    sample: str
    volume: Optional[float]
    time: Optional[float]