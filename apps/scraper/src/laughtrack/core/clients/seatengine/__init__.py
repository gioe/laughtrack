"""SeatEngine client package."""

# Keep imports minimal to avoid circulars; the scraper lives under scrapers/implementations
from .client import SeatEngineClient

__all__ = ["SeatEngineClient"]
