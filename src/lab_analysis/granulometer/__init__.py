"""Laser-diffraction granulometer particle-size analysis.

Quick start
-----------
    from lab_analysis.granulometer import run, config

    config.INPUT_DIR = "/path/to/my/data"
    measurements, conditions = run()

Or from a terminal after `pip install -e .`:

    granulometer-analysis /path/to/my/data --output-dir outputs/run1
"""
from __future__ import annotations

from .models import Condition, Measurement
from .runner import run

__all__ = ["run", "Measurement", "Condition"]