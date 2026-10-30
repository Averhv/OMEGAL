from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def fake_measurement_factory():
    """Build a synthetic Measurement for tests without file I/O."""
    from lab_analysis.granulometer.models import Measurement

    def build(name: str, *, source: str = "synthetic", d50: float = 1.5):
        d = np.logspace(-2, 2, 100)
        q = np.exp(-((d - d50) ** 2) / 0.5) * 10
        p = np.clip(100 * (1 - np.exp(-d / d50)), 0, 100)
        return Measurement(
            name=name, source=source, diameter=d, q=q, passant=p,
            stats={
                "D10_um": d50 * 0.5, "D50_um": d50, "D90_um": d50 * 1.5,
                "span_calculated": 2.0 / 3.0, "std_um": 0.1,
            },
        )

    return build