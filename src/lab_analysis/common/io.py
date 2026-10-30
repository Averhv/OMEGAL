"""Shared I/O primitives: text decoding, filename safety, run-info sidecar."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    """Decode a text file, tolerating UTF-16 / UTF-8 / CP1252 / Latin-1."""
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def safe_filename(text: str, fallback: str = "plot") -> str:
    """Turn arbitrary text into a filesystem-safe stem (no path separators)."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(text).strip()).strip("._")
    return cleaned or fallback


def write_run_info(payload: dict, out_dir: Path) -> None:
    """Write `_run_info.json` (timestamp + payload) into `out_dir`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {"timestamp": datetime.now().isoformat(timespec="seconds"), **payload}
    (out_dir / "_run_info.json").write_text(
        json.dumps(data, indent=2, default=str), encoding="utf-8"
    )