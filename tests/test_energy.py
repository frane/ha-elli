"""Energy calculated from the charging power (EEBUS)."""

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.elli.sensor import EnergyIntegrator

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def test_power_holds_until_the_next_value():
    e = EnergyIntegrator()
    e.sample(11000, at(0))
    e.sample(11000, at(30))  # the minute tick, power unchanged
    assert e.wh == pytest.approx(5500)
    e.sample(0, at(60))
    assert e.wh == pytest.approx(11000)
    e.sample(0, at(120))
    assert e.wh == pytest.approx(11000)


def test_no_data_counts_nothing():
    e = EnergyIntegrator(wh=1000)
    e.sample(7000, at(0))
    e.sample(None, at(60))  # connection lost
    e.sample(7000, at(180))  # back: the gap is not counted
    e.sample(7000, at(240))
    assert e.wh == pytest.approx(1000 + 7000 + 7000)


def test_never_decreases():
    e = EnergyIntegrator()
    e.sample(-50, at(0))
    e.sample(0, at(60))
    e.sample(3000, at(60))
    e.sample(3000, at(30))  # clock went back
    assert e.wh == 0
