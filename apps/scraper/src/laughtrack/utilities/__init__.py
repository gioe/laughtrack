"""Laughtrack utilities package.

Keep this package lightweight at import time. Do not re-export subpackages here
to avoid circular imports (Python imports package __init__ before submodules).

Import directly from concrete modules instead, e.g.:
- from laughtrack.utilities.infrastructure.error_handling import ErrorHandler
- from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
"""

__all__: list[str] = []
