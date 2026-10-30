"""Readers for granulometer exports + sample-name parsing."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional

import numpy as np

from . import config
from .models import Measurement
from ..common.io import read_text

# --- Regexes -----------------------------------------------------------------
NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[Ee][-+]?\d+)?")
STRICT_NUMBER_RE = re.compile(r"^[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[Ee][-+]?\d+)?$")

# Replicate suffix: last token is a..z OR 1..99, optionally preceded by "rep".
REPLICATE_SUFFIX_RE = re.compile(
    r"[\s_-]+(?:rep(?:licate)?[\s_-]*)?([a-z]|\d{1,2})\s*$",
    re.IGNORECASE | re.ASCII,
)

VOLUME_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*ml(?![a-zA-Z])", re.IGNORECASE)
TIME_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:s|sec|secs|seconds?)(?![a-zA-Z])", re.IGNORECASE)

LABEL_MAP = [
    ("variance geo", None), ("variance", "var_um2"), ("ecart", "std_um"),
    ("diametre median", "D50_um"), ("diametre moyen", "mean_um"), ("diametre mode", "mode_um"),
    ("moyenne geo", "geomean_um"), ("d10", "D10_um"), ("d90", "D90_um"),
    ("surface specifique", "ssa_cm2_cm3"), ("span", "span_instrument"),
    ("base de distribution", "basis"), ("vitesse circulation", "circulation"),
    ("vitesse agitation", "agitation"), ("ultra-sons", "ultrasound"),
    ("nom echantillon", "sample_name"), ("nom de fichier resultats", "result_name"),
]
TEXT_KEYS = {"span_instrument", "basis", "circulation", "agitation", "ultrasound",
             "sample_name", "result_name"}


# --- Primitive helpers -------------------------------------------------------
def normalise_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\ufffd", "e").replace("č", "e").replace("Č", "E")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower()


def to_float(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        raise ValueError("empty")
    token = str(value).strip()
    token = token.strip('"\' ')      
    if not STRICT_NUMBER_RE.match(token):
        raise ValueError(token)
    return float(token.replace(",", "."))


def first_number(text: str) -> Optional[float]:
    m = NUMBER_RE.search(text or "")
    return float(m.group(0).replace(",", ".")) if m else None


# --- Metadata block ----------------------------------------------------------
def split_label_value(line: str) -> tuple[str, str]:
    s = line.strip().strip('"\'')            # ← NEW: strip surrounding quotes
    parts = re.split(r"\t+|\s{2,}|\s*:\s*", s, maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    m = NUMBER_RE.search(s)
    if m and m.start() > 0:
        return s[:m.start()].strip(), s[m.start():]
    return s, ""


def parse_metadata(lines: list[str]) -> dict:
    stats: dict = {}
    for line in lines:
        if not line.strip():
            continue
        label, value = split_label_value(line)
        lab = normalise_text(label).strip()
        for prefix, key in LABEL_MAP:
            if lab.startswith(prefix):
                if key is None or key in stats:
                    break
                stats[key] = value.strip() if key in TEXT_KEYS else first_number(value)
                break
    d10, d50, d90 = stats.get("D10_um"), stats.get("D50_um"), stats.get("D90_um")
    stats["span_calculated"] = (
        (d90 - d10) / d50 if None not in (d10, d50, d90) and d50 else None
    )
    ssa = stats.get("ssa_cm2_cm3")
    stats["d32_um"] = 6.0 / ssa * 1e4 if ssa else None
    return stats


# --- Name parsing ------------------------------------------------------------
def split_replicate(name: str) -> tuple[str, str]:
    """`SF_1.5mL_30s_2` -> (`SF_1.5mL_30s`, `2`); `..._a` -> (..., `a`)."""
    m = REPLICATE_SUFFIX_RE.search(name)
    if m:
        return name[:m.start()].rstrip(" _-"), m.group(1).lower()
    return name, ""


def parse_condition(group: str) -> tuple[str, Optional[float], Optional[float]]:
    """Return (sample, volume_mL, time_s) from a condition group name."""
    vol = VOLUME_RE.search(group)
    tim = TIME_RE.search(group)
    cut = min(
        (m.start() for m in (vol, tim) if m is not None), default=len(group)
    ) if (vol or tim) else len(group)
    sample = group[:cut].strip(" _-") or "unknown"
    v = float(vol.group(1).replace(",", ".")) if vol else None
    t = float(tim.group(1).replace(",", ".")) if tim else None
    return sample, v, t


# --- Builders ----------------------------------------------------------------
def build_measurement(name, source, d, q, p, stats) -> Measurement:
    d, q, p = (np.asarray(x, dtype=float) for x in (d, q, p))
    ok = np.isfinite(d) & (d > 0) & np.isfinite(q) & np.isfinite(p)
    if ok.sum() < 3:
        raise ValueError(f"only {int(ok.sum())} valid data rows")
    order = np.argsort(d[ok])
    name = config.NAME_ALIASES.get(name, name)
    flags = []
    for key, text in (("circulation", "circulation"), ("agitation", "stirring")):
        if str(stats.get(key, "")).lower().startswith("inact"):
            flags.append(f"{text} inactive")
    return Measurement(name, source, d[ok][order], q[ok][order], p[ok][order], stats, flags=flags)


# --- File readers ------------------------------------------------------------
def parse_txt(path: Path) -> Measurement:
    lines = read_text(path).splitlines()
    start = None
    for i, line in enumerate(lines):
        n = normalise_text(line)
        if "diam" in n and "q(%)" in n and "passant(%)" in n:
            start = i + 1
            break
    if start is None:
        raise ValueError("table header (diameter, q(%), Passant(%)) not found")
    d, q, p = [], [], []
    for line in lines[start:]:
        tokens = [t for t in re.split(r"[\t ;]+", line.strip()) if t]
        try:
            values = [to_float(t) for t in tokens[:3]]
        except ValueError:
            values = None
        if values and len(values) == 3:
            d.append(values[0]); q.append(values[1]); p.append(values[2])
        elif d:
            break
    return build_measurement(
        path.stem, str(path), d, q, p, parse_metadata(lines[:start - 1])
    )


def parse_xlsx(path: Path) -> list[Measurement]:
    try:
        import openpyxl
    except ImportError:
        print(f"[SKIP] {path.name}: install openpyxl (pip install openpyxl)")
        return []
    out: list[Measurement] = []
    wb = openpyxl.load_workbook(path, data_only=True)
    for ws in wb.worksheets:
        headers = [
            (c.row, c.column) for row in ws.iter_rows() for c in row
            if isinstance(c.value, str)
            and normalise_text(c.value).startswith("diametre(micro")
        ]
        for r0, c0 in sorted(headers, key=lambda t: (t[0], t[1])):
            d, q, p = [], [], []
            r = r0 + 1
            while True:
                try:
                    vals = [to_float(ws.cell(r, c0 + i).value) for i in range(3)]
                except ValueError:
                    break
                d.append(vals[0]); q.append(vals[1]); p.append(vals[2]); r += 1
            prev = max([h[0] for h in headers if h[1] == c0 and h[0] < r0], default=0)
            meta = []
            for rr in range(prev + 1, r0):
                label = ws.cell(rr, c0).value
                value = ws.cell(rr, c0 + 1).value
                if isinstance(label, str):
                    meta.append(f"{label}\t{'' if value is None else value}")
            stats = parse_metadata(meta)
            name = str(stats.get("sample_name") or f"{ws.title} col{c0}")
            out.append(build_measurement(
                name, f"{path.name}!{ws.title}!R{r0}C{c0}", d, q, p, stats
            ))
    return out