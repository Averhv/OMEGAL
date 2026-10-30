from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE_TXT = """\
Diamčtre médian\t 1.41977Microns
Diamčtre moyen\t 1.50675Microns
D10\t 0.90369Microns
D90\t 2.22720Microns

Diamčtre(Micro_m)\tq(%)\tPassant(%)
0.011\t0.000\t0.000
0.100\t0.000\t0.000
0.172\t0.106\t0.106
0.877\t3.211\t8.579
1.005\t6.509\t15.088
1.318\t15.041\t41.557
1.729\t14.568\t71.568
2.269\t7.858\t91.069
3.409\t1.136\t99.093
5.122\t0.119\t100.000
"""


def test_parse_txt_roundtrip(tmp_path: Path):
    from lab_analysis.granulometer.parsing import parse_txt
    p = tmp_path / "SF_1.5mL_30s_2.txt"
    p.write_text(SAMPLE_TXT, encoding="utf-8")
    m = parse_txt(p)
    assert m.name == "SF_1.5mL_30s_2"
    assert len(m.diameter) > 0
    assert m.stats["D10_um"] == pytest.approx(0.90369)
    assert m.stats["D50_um"] == pytest.approx(1.41977)
    assert m.stats["D90_um"] == pytest.approx(2.22720)