"""Real cross-language club admission contracts on embedded PostgreSQL."""
from pathlib import Path
import subprocess


def test_durable_club_intake_contract():
    web = Path(__file__).resolve().parents[3] / "web"
    result = subprocess.run(["npm", "test", "--", "lib/admin/curation/clubIntake.test.ts"],
                            cwd=web, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
