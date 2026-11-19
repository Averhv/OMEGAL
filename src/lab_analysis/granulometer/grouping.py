"""Group replicate measurements into conditions."""
from __future__ import annotations

import string

from .models import Condition, Measurement
from .parsing import parse_condition, split_replicate


def _rep_sort_key(rep: str):
    """Sort replicates naturally: 1, 2, 3, 10 before a, b, c."""
    if rep.isdigit():
        return (0, int(rep), "")
    return (1, 0, rep)


def _temp_value(temp: str | None) -> float:
    if not temp:
        return -1.0
    try:
        return float(temp.rstrip("cC° "))
    except ValueError:
        return 1e6


def organise(measurements: list[Measurement], sequential: set[str]) -> list[Condition]:
    """Group replicates (by base name) into Conditions."""
    groups: dict[str, list[Measurement]] = {}
    for m in measurements:
        base, letter, basis = split_replicate(m.name, fallback_basis=m.stats.get("basis"))
        if basis:
            m.stats["basis"] = basis
        m.group = base
        m.replicate = "" if m.source in sequential else letter
        groups.setdefault(base, []).append(m)

    conditions: list[Condition] = []
    for base, members in groups.items():
        used = {m.replicate for m in members if m.replicate}
        free = iter(c for c in string.ascii_lowercase if c not in used)
        for m in members:
            if not m.replicate:
                candidate = next(free, None)
                if candidate is None:
                    idx = sum(1 for x in members if x.replicate.startswith("rep"))
                    candidate = f"rep{idx + 1}"
                m.replicate = candidate
        members.sort(key=lambda m: _rep_sort_key(m.replicate))

        sample, vol, tim, temp = parse_condition(base)
        for m in members:
            m.sample, m.volume, m.time, m.temperature = sample, vol, tim, temp
            if len(members) > 1:
                m.name = f"{base} {m.replicate}"

        conditions.append(Condition(base, members, sample, vol, tim, temp))

    return sorted(
        conditions,
        key=lambda c: (
            c.sample.lower(),
            c.volume if c.volume is not None else 1e9,
            c.time if c.time is not None else 1e9,
            _temp_value(c.temperature),
        ),
    )