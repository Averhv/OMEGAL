from __future__ import annotations

from lab_analysis.granulometer.grouping import organise


def test_numeric_replicates_grouped(fake_measurement_factory):
    ms = [fake_measurement_factory(f"SF_1.5mL_30s_{i}") for i in (1, 2, 3)]
    conds = organise(ms, sequential=set())
    assert len(conds) == 1
    c = conds[0]
    assert len(c.members) == 3
    assert c.sample == "SF"
    assert c.volume == 1.5
    assert c.time == 30.0
    assert sorted(m.replicate for m in c.members) == ["1", "2", "3"]


def test_letter_replicates_grouped(fake_measurement_factory):
    ms = [fake_measurement_factory(f"SF_1.5mL_30s_{l}") for l in "abc"]
    conds = organise(ms, sequential=set())
    assert len(conds) == 1
    assert sorted(m.replicate for m in conds[0].members) == ["a", "b", "c"]


def test_samples_are_not_mixed(fake_measurement_factory):
    ms = [
        fake_measurement_factory("SF_1.5mL_30s_1"),
        fake_measurement_factory("TG_1.5mL_30s_1"),
        fake_measurement_factory("SF_1.5mL_60s_1"),
    ]
    conds = organise(ms, sequential=set())
    assert {c.sample for c in conds} == {"SF", "TG"}
    sf = [c for c in conds if c.sample == "SF"]
    assert len(sf) == 2
    assert sorted(c.time for c in sf) == [30.0, 60.0]


def test_numeric_replicates_sorted_naturally(fake_measurement_factory):
    ms = [fake_measurement_factory(f"SF_1.5mL_30s_{i}") for i in (1, 2, 10, 11)]
    conds = organise(ms, sequential=set())
    assert [m.replicate for m in conds[0].members] == ["1", "2", "10", "11"]