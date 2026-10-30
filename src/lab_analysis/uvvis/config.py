from __future__ import annotations

# --- Input / output ----------------------------------------------------------
INPUT_DIR = None
OUTPUT_NAME = "uvvis_results"
READ_TXT = True
READ_CSV = True
SHOW_INLINE = "comparison"

# --- Plot production ---------------------------------------------------------
MAKE_INDIVIDUAL = True
MAKE_REPLICATES = True
MAKE_COMPARISONS = True
MAKE_OVERVIEW = True

COMPARE_OVER = "sample"
COMPARE_SHOW_MEAN = True
COMPARE_SHOW_REPLICATES = True
SHOW_SD_BAND = True
SHOW_WAVELENGTH_MARKERS = True

# --- UV-Vis specific settings (Ritchie 2008 Ethanol) -------------------------
SOLVENT = "ethanol"
TARGET_WAVELENGTHS = [362, 470, 520, 632, 649, 664, 695, 750]
MAX_ABSORBANCE_WARNING = 1.0
TURBIDITY_THRESHOLD_A750 = 0.02          # A750 should ideally equal 0
CAROTENOID_MAX_RATIO_A520 = 0.10         # A520 < 10% of main red max

# --- Extraction parameters ---------------------------------------------------
DEFAULT_DILUTION_FACTOR = 1.0
DEFAULT_EXTRACT_VOLUME_ML = 3.0          # V d'éthanol de reprise (mL)
DEFAULT_DRY_MASS_MG = 10.0               # dry mass total (mg)

# --- Statistics & Quality ----------------------------------------------------
STATS_FIELDS = ("A_664", "A_649", "A_632", "A_750", "Chl_a", "Chl_b", "Total_Chl")
SHOW_STATS_BOX = True
SHOW_TITLE = False
LEGEND_OUTSIDE = True
STATS_IN_LEGEND = False

# --- Colours (Reusing your granulometer palettes) ----------------------------
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
GROUP_PALETTES: dict[str, str] = {}

# --- Appearance --------------------------------------------------------------
X_RANGE_MODE = "active"
X_LIMITS = None
FIGURE_SIZE = (9.0, 5.6)
PNG_DPI = 300
SAVE_PDF = False
SHOW_GRID = True
X_AXIS_LABEL = "Wavelength (nm)"
Y_AXIS_LABEL = "Absorbance (A)"
TITLE_PREFIX = "UV-Vis absorption spectrum"

# --- Name overrides ----------------------------------------------------------
CUSTOM_LEGEND_LABELS: dict[str, str] = {}
CUSTOM_TITLES: dict[str, str] = {}
NAME_ALIASES: dict[str, str] = {}