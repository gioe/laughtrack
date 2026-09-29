"""Real-library regressions: deliberately do not mock timezone databases."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
import pytz

from laughtrack.foundation.utilities.datetime import DateTimeUtils
from scripts.verify_timezone_data import CASES, verify_timezone_data


def test_production_timezone_guard_accepts_actual_installed_data():
    assert verify_timezone_data()["cases"] == 28


@pytest.mark.parametrize("instant,zone_name,offset", CASES)
def test_actual_pytz_and_zoneinfo_preserve_instant_and_apply_canadian_rules(instant, zone_name, offset):
    stored = datetime.fromisoformat(instant)
    for zone in (pytz.timezone(zone_name), ZoneInfo(zone_name)):
        local = stored.astimezone(zone)
        assert local.utcoffset().total_seconds() == offset * 3600
        assert local.astimezone(timezone.utc) == stored


@pytest.mark.parametrize("zone_name,utc_hour", [("America/Edmonton", 2), ("America/Vancouver", 3)])
def test_winter_wall_clock_conversion_uses_current_rules(zone_name, utc_hour):
    actual = DateTimeUtils.venue_wall_clock_to_utc(datetime(2026, 12, 1, 20), zone_name)
    assert actual == datetime(2026, 12, 2, utc_hour, tzinfo=timezone.utc)


@pytest.mark.parametrize("source", ["2027-03-13T19:00:00-07:00", "2027-03-12T19:00:00-07:00"])
def test_explicit_alberta_source_offsets_preserve_the_source_instant(source):
    # Source offset conflicts require a separate evidence-based correction; never
    # reinterpret an already-aware source timestamp as newly advertised wall time.
    parsed = DateTimeUtils.parse_datetime_with_timezone(source, "America/Edmonton")
    expected = datetime.fromisoformat(source).astimezone(timezone.utc)
    assert parsed.astimezone(timezone.utc) == expected
    assert DateTimeUtils.venue_wall_clock_to_utc(parsed, "America/Edmonton") == expected
    assert parsed.astimezone(pytz.timezone("America/Edmonton")).hour == 20
