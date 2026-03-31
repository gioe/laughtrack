"""
Shared test fixtures for venue smoke tests.

Pre-stubs gioe_libs (optional private dep not in requirements.txt) and
bypasses laughtrack.utilities.infrastructure.__init__ so that venue scrapers
can be imported without triggering the gioe_libs dependency chain.
"""

from pathlib import Path
from gioe_stubs import register_stubs

# tests/scrapers/implementations/venues/ → parents[4] = apps/scraper/
register_stubs(Path(__file__).parents[4] / "src")
