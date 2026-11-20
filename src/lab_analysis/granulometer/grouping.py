"""Group replicate measurements into experimental conditions."""
from __future__ import annotations

import string

from .models import Condition, Measurement
from .parsing import parse_condition, split_replicate


def _rep_sort_key(rep: str) -> tuple[int, int, str]:
    """Tri naturel des réplicats (ex: 1, 2, 3 avant a, b, c)."""
    if rep.isdigit():
        return (0, int(rep), "")
    return (1, 0, rep)


def _temp_sort_key(temp: str | None) -> float:
    """Convertit la température en float pour un tri numérique (None -> -1.0)."""
    if not temp:
        return -1.0
    try:
        return float(temp.rstrip("cC° "))
    except ValueError:
        return 1e6


def organise(measurements: list[Measurement], sequential: set[str]) -> list[Condition]:
    """Regroupe les réplicats individuels en Conditions expérimentales."""
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

        seen_labels: set[str] = set()
        for idx, m in enumerate(members, start=1):
            m.sample, m.volume, m.time, m.temperature = sample, vol, tim, temp
            rep_tag = f"rep{m.replicate}" if m.replicate else f"rep{idx}"
            candidate_name = f"{base} ({rep_tag})" if len(members) > 1 else base
            if candidate_name in seen_labels:
                candidate_name = f"{base} ({rep_tag}#{idx})"
            seen_labels.add(candidate_name)
            m.name = candidate_name

        conditions.append(Condition(base, members, sample, vol, tim, temp))

    return sorted(
        conditions,
        key=lambda c: (
            c.sample.lower(),
            c.volume if c.volume is not None else 1e9,
            c.time if c.time is not None else 1e9,
            _temp_sort_key(c.temperature),
        ),
    )