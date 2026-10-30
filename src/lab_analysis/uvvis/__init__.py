"""UV-Vis spectroscopy analysis — placeholder.

Mirrors `lab_analysis.granulometer`:

    config.py    — user-tunable knobs (wavelength range, baselines, etc.)
    models.py    — Spectrum, Sample (dataclasses)
    parsing.py   — instrument export readers
    plotting.py  — spectrum overlays, calibration curves
    runner.py    — orchestrator (same `run(input_dir, output_dir)` signature)
    __main__.py  — CLI

Shared helpers:

    from ..common.io       import read_text, safe_filename, write_run_info
    from ..common.plotting import apply_style, save_figure
    from ..common.reports  import write_csv
"""