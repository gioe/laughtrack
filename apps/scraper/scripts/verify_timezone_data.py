"""Verify the actual production timezone libraries without touching stored shows."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytz
import tzdata

# Historical winter remains standard time; autumn 2026 no longer falls back.
CASES = (
    ("2026-01-15T20:00:00+00:00", "America/Edmonton", -7),
    ("2026-01-15T20:00:00+00:00", "America/Vancouver", -8),
    ("2026-10-31T20:00:00+00:00", "America/Edmonton", -6),
    ("2026-10-31T20:00:00+00:00", "America/Vancouver", -7),
    ("2026-11-01T07:59:00+00:00", "America/Edmonton", -6),
    ("2026-11-01T08:00:00+00:00", "America/Edmonton", -6),
    ("2026-11-01T08:59:00+00:00", "America/Vancouver", -7),
    ("2026-11-01T09:00:00+00:00", "America/Vancouver", -7),
    ("2026-12-01T20:00:00+00:00", "America/Edmonton", -6),
    ("2026-12-01T20:00:00+00:00", "America/Vancouver", -7),
    ("2027-03-01T20:00:00+00:00", "America/Edmonton", -6),
    ("2027-03-01T20:00:00+00:00", "America/Vancouver", -7),
    ("2026-12-01T20:00:00+00:00", "America/Denver", -7),
    ("2026-12-01T20:00:00+00:00", "America/Los_Angeles", -8),
)


def verify_timezone_data():
    for instant, timezone, expected in CASES:
        utc = datetime.fromisoformat(instant)
        for library, zone in (("pytz", pytz.timezone(timezone)), ("zoneinfo", ZoneInfo(timezone))):
            actual = utc.astimezone(zone).utcoffset().total_seconds() / 3600
            if actual != expected:
                raise RuntimeError(
                    f"Stale {library} timezone data: {timezone} at {instant}: "
                    f"expected UTC{expected:+}, got UTC{actual:+}; "
                    f"pytz={pytz.__version__}, tzdata={tzdata.__version__}. "
                    "Install the locked dependencies and use PYTHONTZPATH='' for the pinned tzdata wheel."
                )
    return {"pytz": pytz.__version__, "tzdata": tzdata.__version__, "cases": len(CASES) * 2}


if __name__ == "__main__":
    print(json.dumps(verify_timezone_data()))
