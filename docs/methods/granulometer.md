# Granulometer Method — Architecture & Processing Pipeline

This document details the implementation of the **Granulometer (Laser-Diffraction)** module within the `lab-analysis` package. It covers the data format, parsing logic, grouping algorithms, statistical computations, and the specific rendering architecture for publication-ready figures.

## 1. Input Data & Naming Convention

The pipeline relies strictly on the filename to extract experimental dimensions. The parser targets `.txt` and `.xlsx` exports from the instrument.

### 1.1 Canonical Filename Format
```text
<sample>_<volume>mL_<time>s[_<replicate>].txt
```

### 1.2 Parsing Rules (parsing.py)

- **Sample:** Everything before the first NmL or Ns token. (Note: Extra dimensions like amplitude or temperature MUST be placed here: SF_10A_1.5mL_30s_1).
- **Volume:** Matches NmL (case-insensitive). Uses a negative lookahead (?![a-zA-Z]) to avoid matching mLX.
- **Time:** Matches Ns, Nsec, Nseconds.
- **Replicate:** The last token matching _a–_z or _1–_99. If missing, replicates are auto-assigned alphabetically (a, b, c).
- **Quotes:** The parser uses .strip('"\' ') on all incoming numeric and label data to handle CSV files falsely exported with wrapping quotes.

### 1.3 Metadata Extraction

The parser reads the instrument metadata block for statistics:
- D10_um, D50_um, D90_um
- std_um (Ecart-type), var_um2 (Variance)
- mean_um, mode_um, geomean_um
- d32_um (calculated via specific surface area)
- span_calculated = (D90 - D10) / D50

## 2. Grouping & Condition Assembly (grouping.py)

- Measurements are grouped by their base name (filename minus replicate).
- **Natural Sort:** Replicates are sorted numerically if they are digits (e.g., _1, _2, _10 rather than _1, _10, _2).
- **Condition Dataclass:** Each group becomes a Condition containing a list of Measurement members, the sample name, volume, and time.
- **Sequential XLSX:** For .xlsx files where replicates are separated by columns rather than filenames, the runner assigns replicates sequentially based on order.

## 3. Figure Rendering Architecture (plotting.py)

The plotting engine is designed to produce publication-ready figures with a strict layout to prevent overlaps.

### 3.1 The Layout Engine (CRITICAL)

Do NOT use bbox_to_anchor on the main data axes to place legends or text boxes, and do NOT use tight_layout(rect=...) to reserve space. In twin-axis plots, the right y-axis draws its ticks and labels at x > 1.0, causing overlaps.

Instead, the layout uses a dedicated side panel via GridSpec:
- The figure is split into 2 columns: [Main Plot Axes] | [Side Panel Axes].
- **Side Panel Width:** Calculated dynamically based on the longest legend label and the longest stats box line (side_w = max(0.75 + 0.065 * n_leg, 0.45 + 0.065 * n_box, 1.4) inches).
- **Main Axes Width:** Fixed at MAIN_W_IN = 8.2 inches to ensure consistency across all figures.
- The side panel axis is turned off (side.axis("off")).

### 3.2 Legend & Stats Box Placement

- The legend is placed at the top-left of the side panel.
- The stats box is placed directly beneath the legend.
- **Dynamic Stacking:** The code calls fig.canvas.draw() to measure the exact bounding box of the legend (legend.get_window_extent()). The stats box is then anchored using ScaledTranslation just below the legend's bottom edge (y_top = bbox.y0 - 0.025).

### 3.3 Curve Rendering (render)

The function handles three plot modes: "q", "passant", and "both" (or "combined").
- **Twin Axis (both/combined):** 
  - Left axis: q (%) (Solid lines).
  - Right axis: Passant (%) (Dashed lines).
  - Legend includes the curves plus two custom grey handles labeled q (%) and Passant (%).
- **X-Axis (Log Scale):** 
  - Major ticks: 1, 2, 5.
  - Minor ticks: 1.5, 3, 4, 6, 7, 8, 9. (The 1.5 is manually injected to fill the large gap between 1 and 2 on log scales).
- **No Title:** SHOW_TITLE defaults to False to keep the figure clean.
- **SD Bands:** Shaded regions represent mean ± SD across replicates.

## 4. Output Directory Structure

The runner.py orchestrates the creation of the following output tree:

outputs/YYYY_MM_DD_[batch]/
├── _run_info.json # Config snapshot & timestamp
├── summary/
│ ├── measurement_summary.csv # Per-measurement stats
│ └── condition_summary.csv # Per-condition mean ± SD, D50 CV%
├── individual/
│ └── [condition]/ # One folder per condition
│ └── [measurement]_combined.png
├── replicates/
│ └── [condition]_combined.png # a/b/c overlaid with SD band
├── comparisons/
│ ├── by_time/ # 30s vs 60s at fixed sample+volume
│ ├── by_volume/ # 1.5mL vs 3mL at fixed sample+time
│ └── by_sample/ # Sample A vs B at fixed volume+time
└── overview/
└── all_conditions.png # Small multiples (q only)

## 5. Common Pitfalls & Maintenance Notes

- **Dots in Filenames:** Never use Path.with_suffix() to append .png or .pdf. Filenames like SF_1.5mL_30s_1 contain dots that will truncate the file. Always use str(out_stem) + ".png".
- **CSV Quotes:** If the instrument starts exporting CSVs wrapped in quotes, the parser handles it via .strip('"\' ').
- **Extra Dimensions:** If you introduce a new variable (e.g., Temperature), it must go in the sample slot (SF_25C_1.5mL_30s_1), otherwise the comparison engine will group different temperatures together.
- **Warnings:** The terminal will print [WARN] if D50_CV_PERCENT > 10% or if the instrument pump/stirrer was marked as "Inactif" in the metadata.