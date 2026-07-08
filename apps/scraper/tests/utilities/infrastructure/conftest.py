"""
Shared test fixtures for utilities/infrastructure tests.

Pre-stubs gioe_libs (optional private dep not in requirements.txt) and
bypasses laughtrack.utilities.infrastructure.__init__ so pipeline modules
can be imported without triggering the gioe_libs dependency chain.
"""

from pathlib import Path
from gioe_stubs import register_stubs

# tests/utilities/infrastructure/ → parents[3] = apps/scraper/
register_stubs(Path(__file__).parents[3] / "src")
