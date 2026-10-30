from __future__ import annotations

import pytest

from lab_analysis.granulometer.parsing import parse_condition, split_replicate


class TestSplitReplicate:
    @pytest.mark.parametrize("name, expected", [
        ("SF_1.5mL_30s_2",        ("SF_1.5mL_30s", "2")),
        ("SF_1.5mL_30s_10",       ("SF_1.5mL_30s", "10")),
        ("SF_1.5mL_30s_a",        ("SF_1.5mL_30s", "a")),
        ("SF_1.5mL_30s_b",        ("SF_1.5mL_30s", "b")),
        ("SF_1.5mL_30s",          ("SF_1.5mL_30s", "")),
        ("SF_1.5mL_30s rep 2",    ("SF_1.5mL_30s", "2")),
        ("Mice emul_1.5mL_30s_3", ("Mice emul_1.5mL_30s", "3")),
    ])
    def test_replicate_extraction(self, name, expected):
        assert split_replicate(name) == expected

    def test_three_digit_number_is_not_a_replicate(self):
        assert split_replicate("SF_100s") == ("SF_100s", "")

    def test_ml_volume_is_not_a_replicate(self):
        assert split_replicate("SF_1.5mL_30s") == ("SF_1.5mL_30s", "")


class TestParseCondition:
    @pytest.mark.parametrize("name, expected", [
        ("SF_1.5mL_30s",        ("SF", 1.5, 30.0)),
        ("Mice emul_1.5mL_30s", ("Mice emul", 1.5, 30.0)),
        ("SF_1.5mL",            ("SF", 1.5, None)),
        ("SF_30s",              ("SF", None, 30.0)),
        ("SF",                  ("SF", None, None)),
        ("SF 1.5mL 60s",        ("SF", 1.5, 60.0)),
        ("SF_0.5mL_60s",        ("SF", 0.5, 60.0)),
    ])
    def test_parse(self, name, expected):
        assert parse_condition(name) == expected