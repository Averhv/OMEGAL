"""Placeholder — implement once the UV-Vis workflow is specified."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


def run(
    input_dir: Optional[Union[Path, str]] = None,
    output_dir: Optional[Union[Path, str]] = None,
):
    """Not yet implemented. Mirror `lab_analysis.granulometer.runner.run`."""
    raise NotImplementedError(
        "UV-Vis pipeline not yet implemented. "
        "Shared helpers are ready in lab_analysis.common."
    )