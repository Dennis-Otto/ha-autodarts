"""The frozen clock of the tests, which starts at the same quiet moment in every run."""

from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util

from .conftest import QUIET_MOMENT


async def test_the_frozen_clock_starts_at_noon_in_the_middle_of_a_week(hass, freezer):
    now = dt_util.now()
    assert now == dt_util.parse_datetime(QUIET_MOMENT)
    assert (now.strftime("%A"), now.hour, now.minute) == ("Wednesday", 12, 0)
    # The weekly report is due at the midnight before Monday: a tick of hours, as the
    # tests make, reaches neither the next day nor the end of the week.
    assert (now + timedelta(hours=11)).date() == now.date()
    assert (now + timedelta(days=4, hours=11)).strftime("%A") == "Sunday"


async def test_the_frozen_clock_follows_on_from_its_quiet_moment(hass, freezer):
    freezer.tick(timedelta(hours=1))
    assert dt_util.now() == dt_util.parse_datetime(QUIET_MOMENT) + timedelta(hours=1)


@pytest.mark.freeze_time("2026-10-18T23:30:00-07:00")
async def test_a_test_names_a_moment_of_its_own_with_the_marker(hass, freezer):
    assert dt_util.now() == dt_util.parse_datetime("2026-10-18T23:30:00-07:00")
