"""Zip code distance utilities using pgeocode and haversine formula."""
import math
from typing import Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger


class ZipCodeDistance:
    """Converts US zip codes to lat/lon and computes haversine distance in miles."""

    def __init__(self):
        self._cache: dict = {}
        self._nomi = None  # lazy-init pgeocode.Nominatim("us")

    def _get_nomi(self):
        if self._nomi is None:
            import pgeocode
            self._nomi = pgeocode.Nominatim("us")
        return self._nomi

    def get_coords(self, zip_code: str) -> Optional[tuple]:
        """Return (lat, lon) for a US zip code, or None if unknown."""
        zip_code = zip_code.strip()[:5]  # normalize to 5-digit
        if zip_code in self._cache:
            return self._cache[zip_code]
        try:
            result = self._get_nomi().query_postal_code(zip_code)
            if result is None or (hasattr(result, 'latitude') and math.isnan(result.latitude)):
                self._cache[zip_code] = None
                return None
            coords = (float(result.latitude), float(result.longitude))
            self._cache[zip_code] = coords
            return coords
        except Exception as e:
            Logger.warn(f"ZipCodeDistance: failed to look up zip {zip_code!r}: {e}")
            self._cache[zip_code] = None
            return None

    def distance_miles(self, zip1: str, zip2: str) -> Optional[float]:
        """Return great-circle distance in miles between two zip codes, or None if either is unknown."""
        c1 = self.get_coords(zip1)
        c2 = self.get_coords(zip2)
        if c1 is None or c2 is None:
            return None
        return _haversine_miles(c1[0], c1[1], c2[0], c2[1])


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
