"""
Shared fixtures for tests/utilities/.

Pre-stubs gioe_libs and bypasses laughtrack.utilities.infrastructure.__init__
so utility modules can be imported without the optional gioe_libs dependency.
"""

from pathlib import Path

from gioe_stubs import register_stubs

# tests/utilities/ -> parents[2] = apps/scraper/
register_stubs(Path(__file__).parents[2] / "src")
