"""Cross-language admission contract on embedded PostgreSQL (no production DB).

The actual migration, admin service and direct SQL writers are exercised in the
web PGlite suite. Running it here keeps the scraper acceptance command tied to
the same authoritative boundary, without a second Python policy implementation.
"""
from pathlib import Path
import subprocess


def test_durable_comedian_intake_contract():
    web = Path(__file__).resolve().parents[3] / "web"
    result = subprocess.run(
        ["npm", "test", "--", "lib/admin/curation/comedianIntake.test.ts"],
        cwd=web, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
