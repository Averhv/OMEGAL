# lab-analysis

Internal lab data-processing toolkit — one installable package, one config per
method, one command per instrument.

| Method | Command | Status |
|---|---|---|
| Granulometer (laser diffraction) | `granulometer-analysis` | ✅ working |
| UV-Vis spectroscopy | `uvvis-analysis` | 🚧 placeholder |

---

## Contents

- [lab-analysis](#lab-analysis)
  - [Contents](#contents)
  - [Install](#install)
  - [Quick start](#quick-start)
  - [CLI reference](#cli-reference)
  - [Configuration](#configuration)
    - [Most-used](#most-used)
    - [Appearance](#appearance)
    - [Programmatic override](#programmatic-override)
  - [Naming convention](#naming-convention)
    - [Additional experimental dimensions (amplitude, temperature, pH, batch, …)](#additional-experimental-dimensions-amplitude-temperature-ph-batch-)
    - [What does *not* work](#what-does-not-work)
  - [Input files](#input-files)
    - [Instrument metadata](#instrument-metadata)
  - [Output layout](#output-layout)
  - [Troubleshooting](#troubleshooting)
  - [Development](#development)
    - [Tests](#tests)
    - [Adding a new method](#adding-a-new-method)
    - [Layout](#layout)
    - [Never commit](#never-commit)
  - [Known limitations](#known-limitations)

---

## Install

```bash
cd ~/Documents/Internship_Anthony_Data_Processing
python -m venv .venv
source .venv/Scripts/activate         # Windows (Git Bash)
# source .venv/bin/activate            # macOS / Linux
pip install -e ".[test]"
```

The `-e` (editable) flag is **required** if you plan to edit files under
`src/lab_analysis/*/config.py` — changes take effect on the next run without
reinstalling. A non-editable `pip install .` would freeze the config.

**Every new terminal session:**
```bash
source .venv/Scripts/activate
```
You'll see `(.venv)` at the start of the prompt — that's the confirmation.

If `granulometer-analysis` is `command not found` even inside the venv, use
`python -m lab_analysis.granulometer` (identical behavior, same arguments) — the
module form works regardless of `PATH`.

---

## Quick start

```bash
cd ~/Documents/Internship_Anthony_Data_Processing
source .venv/Scripts/activate
granulometer-analysis data/raw/2026_10_26_SF_test/ \
    --output-dir outputs/2026_10_26_SF_test
```

Output is written to `outputs/2026_10_26_SF_test/`. Open the folder — the two
most useful figures are:

- `replicates/SF_1.5mL_30s_combined.png` — your a/b/c replicates overlaid
- `overview/all_conditions.png` — small-multiples of every condition

**Python:**

```python
from lab_analysis.granulometer import run, config

config.PLOT_KINDS = ("combined",)
config.SHOW_TITLE = False
config.GROUP_PALETTES = {"SF": "teal", "TG": "amber"}

measurements, conditions = run(
    input_dir="data/raw/2026_10_26_SF_test",
    output_dir="outputs/2026_10_26_SF_test",
)
```

---

## CLI reference

```
usage: granulometer-analysis [-h]
                             [--output-dir OUTPUT_DIR]
                             [--plot-kinds {combined,q,passant,both} ...]
                             [--compare-over {time,volume,sample}]
                             [--no-individual] [--no-replicates]
                             [--no-comparisons] [--no-overview]
                             [input_dir]
```

| Flag | Default | Effect |
|---|---|---|
| `input_dir` | cwd | Folder with `.txt` / `.xlsx` exports (top level only — not recursive) |
| `--output-dir` | `<input_dir>/particle_size_results` | Where results go (relative to cwd or absolute) |
| `--plot-kinds` | `combined` | One or more of `combined`, `q`, `passant`, `both` |
| `--compare-over` | `time` | Which dimension varies in comparison overlays |
| `--no-individual` | off | Skip per-measurement figures |
| `--no-replicates` | off | Skip a/b/c overlays |
| `--no-comparisons` | off | Skip by-time / by-volume / by-sample overlays |
| `--no-overview` | off | Skip `all_conditions.png` |

**Examples:**

```bash
# Standard run
granulometer-analysis data/raw/2026_10_26_SF_test/ --output-dir outputs/2026_10_26_SF_test

# Also produce volume comparisons (1.5 vs 3 mL at fixed time)
granulometer-analysis data/raw/2026_10_26_SF_test/ \
    --output-dir outputs/2026_10_26_SF_test_volume \
    --compare-over volume

# Skip comparisons — fastest run, individual + replicates only
granulometer-analysis data/raw/2026_10_26_SF_test/ \
    --output-dir outputs/2026_10_26_SF_test_quick \
    --no-comparisons --no-overview

# Publication extras: q only, single-panel
granulometer-analysis data/raw/2026_10_26_SF_test/ \
    --output-dir outputs/2026_10_26_SF_test_pub \
    --plot-kinds q
```

Every run also writes `_run_info.json` (config snapshot + timestamp) so you can
regenerate the exact same output later.

---

## Configuration

All tunable knobs live in `src/lab_analysis/granulometer/config.py`. With the
editable install, editing the file takes effect on the next run — no reinstall.

### Most-used

| Setting | Default | What it controls |
|---|---|---|
| `PLOT_KINDS` | `("combined",)` | Figure kinds: `combined` (q + cumulative on twin axes), `q`, `passant`, `both` |
| `COMPARE_OVER` | `"time"` | `"time"` / `"volume"` / `"sample"` |
| `MAKE_INDIVIDUAL` / `MAKE_REPLICATES` / `MAKE_COMPARISONS` / `MAKE_OVERVIEW` | `True` | Which figure families to produce |
| `SHOW_TITLE` | `False` | Big title above each figure |
| `SHOW_STATS_BOX` | `True` | D10/D50/D90 box on figures |
| `STATS_FIELDS` | `("D10","D50","D90","Span","SD","Variance")` | Fields shown in the box |
| `LEGEND_OUTSIDE` | `True` | Place legend to the right of the plot |
| `SHOW_SD_BAND` | `True` | Shaded mean ± SD band on replicate/compare overlays |
| `GROUP_PALETTES` | `{}` | Pin a colour family per sample: `{"SF": "teal"}` |
| `CUSTOM_LEGEND_LABELS` | `{}` | Rename conditions in legends: `{"SF_1.5mL_30s": "SF 30 s"}` |
| `CUSTOM_TITLES` | `{}` | Rename plot titles |
| `WARN_CV_D50_PERCENT` | `10.0` | Warn when replicate D50 CV exceeds this |

### Appearance

`FIGURE_SIZE`, `FIGURE_SIZE_COMBINED`, `PNG_DPI` (300), `SAVE_PDF` (False),
`SHOW_GRID`, `X_RANGE_MODE` (`"active"` / `"full"`), `X_LIMITS` (`None` or a
`(lo, hi)` tuple in µm), `Q_CUTOFF`, `X_MARGIN`.

### Programmatic override

```python
from lab_analysis.granulometer import config, run

config.SHOW_TITLE = True
config.STATS_FIELDS = ("D10", "D50", "D90")
config.GROUP_PALETTES = {"SF": "teal", "TG": "amber"}

run(input_dir="data/raw/2026_10_26_SF_test", output_dir="outputs/run1")
```

---

## Naming convention

The parser extracts **four dimensions** from each filename:

| Dimension | Pattern | Example → extracted |
|---|---|---|
| **replicate** | last `_a`–`_z` or `_1`–`_99` | `SF_1.5mL_30s_2` → `2` |
| **sample** | everything before the first `NmL` or `Ns` | `SF_1.5mL_30s` → `SF` |
| **volume** | `NmL` (case-insensitive) | `SF_1.5mL_30s` → `1.5` |
| **time** | `Ns`, `Nsec`, `Nseconds` | `SF_1.5mL_30s` → `30` |

**Canonical form:**
```
<sample>_<volume>mL_<time>s[_<rep>].txt
```

Examples that work:

| Filename | Parsed as |
|---|---|
| `SF_1.5mL_30s_1.txt` | sample=`SF`, volume=`1.5`, time=`30`, rep=`1` |
| `SF_1.5mL_30s_a.txt` | sample=`SF`, volume=`1.5`, time=`30`, rep=`a` |
| `SF_3mL_60s_2.txt` | sample=`SF`, volume=`3`, time=`60`, rep=`2` |
| `SF_1.5mL_30s.txt` | sample=`SF`, volume=`1.5`, time=`30`, rep=auto-assigned |

### Additional experimental dimensions (amplitude, temperature, pH, batch, …)

**The parser does NOT recognize these as separate dimensions.** If you write
`SF_1.5mL_30s_10A_1.txt`, the amplitude `10A` is kept *inside the condition
name* but **invisible to the comparison engine** — `--compare-over time` would
treat `10A` and `20A` as the same physical sample and merge them into one plot.

**Correct pattern — put the extra dimension in the sample slot, BEFORE the
volume:**

```
SF_10A_1.5mL_30s_1.txt     ✅  sample="SF_10A", volume=1.5, time=30, rep=1
SF_20A_1.5mL_30s_1.txt     ✅  sample="SF_20A", volume=1.5, time=30, rep=1
```

Now `--compare-over sample` overlays 10A vs 20A at fixed volume and time —
which is what you actually want. Sample names read `SF_10A` / `SF_20A` in
plots; rename them via `CUSTOM_LEGEND_LABELS` if you want something prettier.

**Same approach for any extra dimension:** temperature → `SF_25C_1.5mL_30s_1`;
batch → `SF_b2_1.5mL_30s_1`; pH → `SF_pH7_1.5mL_30s_1`.

### What does *not* work

| Filename | Why |
|---|---|
| `SF_1.5_30s_1.txt` | no `mL` unit → volume not recognized, whole prefix becomes sample |
| `SF_1-5mL_30s_1.txt` | use a dot (`.`) for decimals, not a comma |
| `SF_1.5mL_30sec_1.txt` | `sec` is accepted; but `seconds` and `s` are safest |
| `SF_1.5mL_30s_100.txt` | 3-digit numbers are not treated as replicates (avoids confusing with a volume) |
| `sf_1.5ml_30s_1.txt` | lowercase is fine, but be consistent across a batch |

---

## Input files

| Extension | Status | Notes |
|---|---|---|
| `.txt` | ✅ | Instrument export; must contain metadata block + table with header `Diamètre(Micro_m)`, `q(%)`, `Passant(%)` |
| `.xlsx` | ✅ | Same layout, one sheet per measurement (columns a/b/c within each sheet) |
| `.xls` | ❌ | Old Excel format — openpyxl cannot read; convert to `.xlsx` |
| `.csv` | ❌ | Not read (yet). Convert to tab-delimited `.txt` or ask to add a native reader |

**One format per input folder.** Mixing `.txt` and `.xlsx` from retried exports
will silently produce duplicate measurements.

### Instrument metadata

The parser reads the metadata block at the top of each export — this is what
populates the stats box and CSV columns:

- `Diamètre médian` / `D50` → `D50_um`
- `D10`, `D90` → `D10_um`, `D90_um`
- `Écart-type` → `std_um`
- `Variance` → `var_um2`
- `Diamètre moyen`, `Diamètre Mode`, `Moyenne géo. diamètre` → `mean_um`, `mode_um`, `geomean_um`
- `Surface spécifique` → `ssa_cm2_cm3` (and derived `d32_um`)
- `Ultra-sons`, `Vitesse circulation`, `Vitesse agitation` → flags (warns in the terminal if inactive)

---

## Output layout

```
outputs/2026_10_26_SF_test/
├── _run_info.json                    config snapshot + timestamp
├── summary/
│   ├── measurement_summary.csv       one row per measurement (n=12)
│   └── condition_summary.csv         one row per condition, with mean ± SD (n=4)
├── individual/
│   └── SF_1.5mL_30s/                 one subfolder per condition
│       ├── SF_1.5mL_30s_1_combined.png
│       ├── SF_1.5mL_30s_2_combined.png
│       └── SF_1.5mL_30s_3_combined.png
├── replicates/
│   └── SF_1.5mL_30s_combined.png     a/b/c overlaid, mean ± SD band
├── comparisons/
│   ├── by_time/                      30 s vs 60 s at fixed sample + volume
│   │   ├── SF_1.5mL_combined.png
│   │   └── SF_3mL_combined.png
│   ├── by_volume/                    1.5 mL vs 3 mL at fixed sample + time
│   └── by_sample/                    sample A vs B at fixed volume + time
└── overview/
    └── all_conditions.png            small-multiples of every condition
```

Comparison folders only contain figures where **≥2 conditions share the fixed
dimensions**. A run with a single sample and a single time produces no
comparisons — that's expected.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `command not found: granulometer-analysis` | venv not activated, or CLI not on PATH | `source .venv/Scripts/activate`, or use `python -m lab_analysis.granulometer` |
| `No usable files in …` | No `.txt` / `.xlsx` at the top of `input_dir` | Point at the folder **containing** the exports; subfolders are not scanned |
| `[SKIP] file: table header … not found` | File isn't a granulometer export | Check the format; convert to `.txt` if it's `.csv` |
| `[SKIP] file: only 0 valid data rows` | File parsed but table is empty / malformed | Open the file, verify the data block exists |
| `[WARN] <condition>: circulation inactive` | Instrument pump was off during measurement | Re-measure with pump on, or exclude this condition from comparisons |
| `[WARN] <condition>: D50 CV = 12.4 %` | Replicate D50 varies >10 % between a/b/c | Check for bubbles/artefacts; re-run the outliers |
| `findfont: Failed to find font weight semibold` | Cosmetic — matplotlib fallback to bold | Ignore |
| CSV has `sample = "SF_1.5mL"` and empty `volume` | Old parser bug (fixed 2026-10) | Update `parsing.py`; verify `python -c "from lab_analysis.granulometer.parsing import parse_condition; print(parse_condition('SF_1.5mL_30s'))"` → `('SF', 1.5, 30.0)` |
| Comparison plot shows two curves with **the same time** | Amplitude/temperature/etc. encoded *after* time (see [naming](#naming-convention)) | Move the extra dimension into the sample slot: `SF_10A_1.5mL_30s_1` |

---

## Development

### Tests

```bash
pip install -e ".[test]"
pytest
```

Expected: **13 items**, all passing. The suite covers:

- `split_replicate` on `_1`, `_2`, `_10`, `_a`, `rep 2`, `_100s`, `_1.5mL` (must NOT match)
- `parse_condition` on 7 filename variants including decimal volumes
- `organise` grouping, natural sort (`_10` after `_2`), sample separation (`SF` vs `TG`)
- `parse_txt` on a real instrument export fixture (D10/D50/D90 recovered)
- `safe_filename`, `write_run_info`, `read_text` UTF-8 BOM handling

### Adding a new method

Each method is an isolated sub-package that reuses `common/`:

```
src/lab_analysis/
├── common/          shared: io, plotting, reports
├── granulometer/    working method (template)
├── uvvis/           placeholder
└── <new_method>/
```

To add a method:

1. Copy `uvvis/` as a template — same file layout as `granulometer/`
2. Implement `config.py` (method-specific knobs), `models.py`, `parsing.py`, `plotting.py`, `runner.py` (`run(input_dir, output_dir) -> (measurements, conditions)`), `__main__.py` (argparse, same CLI shape)
3. Register the CLI script in `pyproject.toml`:
   ```toml
   [project.scripts]
   new-method-analysis = "lab_analysis.new_method.__main__:main"
   ```
4. Add tests under `tests/new_method/`
5. `pip install -e ".[test]"` and run

Reuse from `common/`:
```python
from ..common.io       import read_text, safe_filename, write_run_info
from ..common.plotting import apply_style, save_figure
from ..common.reports  import write_csv
```

### Layout

```
src/lab_analysis/    ← the installable package
tests/               ← mirrors src/lab_analysis/
data/raw/<date>_<batch>/   ← instrument exports (gitignored)
outputs/<date>_<batch>/    ← generated results (gitignored)
docs/                ← free-form notes per method
```

### Never commit

`data/**`, `outputs/**` — the `.gitignore` already excludes them. Raw exports
are the only irreplaceable asset; back them up separately (OneDrive, lab NAS,
external drive).

---

## Known limitations

- **`.csv` files are not read** — convert to `.txt` or `.xlsx`. Native CSV
  support is a ~25-line patch; a sample CSV is enough to add it.
- **Extra dimensions** (amplitude, temperature, pH, batch) are **not** parsed as
  structured fields — see [naming convention](#naming-convention) for the
  workaround.
- **`--recursive`** is not implemented — each run targets one flat folder. Loop
  over date folders in Python:
  ```python
  from pathlib import Path
  from lab_analysis.granulometer import run
  for d in sorted(Path("data/raw").iterdir()):
      if d.is_dir() and not d.name.startswith("."):
          run(input_dir=d, output_dir=Path("outputs") / d.name)
  ```
- **`uvvis-analysis` is a stub** — raises `NotImplementedError` until the
  pipeline is specified.