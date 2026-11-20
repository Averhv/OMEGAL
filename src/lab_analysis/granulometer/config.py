"""User configuration — the only file you should edit between runs.

Importing modules read these constants at call time, so you can also override
programmatically:

    from lab_analysis.granulometer import config, run
    config.PLOT_KINDS = ("combined", "q")
    measurements, conditions = run(input_dir="/path/to/data")
"""
from __future__ import annotations

# --- Input / output ----------------------------------------------------------
INPUT_DIR = None
OUTPUT_NAME = "particle_size_results"
READ_TXT = True
READ_XLSX = True
SHOW_INLINE = "comparison"

# --- Plot production ---------------------------------------------------------
# "combined"  : q (%) + cumulative in one two-panel figure (recommended)
# "q"         : differential only
# "passant"   : cumulative only
# "both"      : twin axes q (left) + cumulative (right)
PLOT_KINDS = ("q",)

MAKE_INDIVIDUAL = True
MAKE_REPLICATES = True
MAKE_COMPARISONS = True
MAKE_OVERVIEW = True

COMPARE_OVER = "time"       # "time" | "volume" | "sample"
COMPARE_SHOW_MEAN = True
COMPARE_SHOW_REPLICATES = True
SHOW_SD_BAND = True

# --- Optional statistics box -------------------------------------------------
STATS_FIELDS = ("D10", "D50", "D90", "Span", "SD", "Variance")
SHOW_STATS_BOX = True
SHOW_TITLE = False  
LEGEND_OUTSIDE = True   
STATS_IN_LEGEND = False
LEGEND_COMPARE_SHORT = False
WARN_CV_D50_PERCENT = 10.0

# --- Colours -----------------------------------------------------------------
PALETTES = {
    "ocean":  ["#A9CBE8", "#4F91C5", "#174A7E"],
    "teal":   ["#A8DAD4", "#48A99D", "#146B65"],
    "amber":  ["#F8D49A", "#E99A35", "#98520B"],
    "violet": ["#D0C5E8", "#9278C7", "#51357D"],
    "rose":   ["#F2BFC6", "#D96B7B", "#922B42"],
    "green":  ["#C5DDA8", "#83B45C", "#3F702E"],
}
PALETTE_CYCLE = ["ocean", "teal", "amber", "violet", "rose", "green"]
PALETTE_PRESET = "auto"
GROUP_PALETTES: dict[str, str] = {}   # {"SF": "teal"} pins a sample's colour

# --- Appearance --------------------------------------------------------------
X_RANGE_MODE = "active"
X_LIMITS = None             # manual (min, max) in µm, e.g. (0.1, 100)
Q_CUTOFF = 0.001
X_MARGIN = 1.15
FIGURE_SIZE = (9.0, 5.6)
FIGURE_SIZE_COMBINED = (12.0, 5.0)
PNG_DPI = 300
SAVE_PDF = False
SHOW_GRID = True
X_AXIS_LABEL = "Droplet diameter (µm)"
Q_AXIS_LABEL = "Differential distribution, q (%)"
PASSANT_AXIS_LABEL = "Cumulative distribution, Passant (%)"
TITLE_PREFIX = "Particle-size distribution"

# --- Name overrides ----------------------------------------------------------
CUSTOM_LEGEND_LABELS: dict[str, str] = {}
CUSTOM_TITLES: dict[str, str] = {}
NAME_ALIASES: dict[str, str] = {}