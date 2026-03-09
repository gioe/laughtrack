"""
Broadway Comedy Club specific Tessera client.

This client provides Broadway Comedy Club specific configurations
for interacting with their Tessera-based ticketing system.
"""

from typing import Optional

from ..client import TesseraClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool

class BroadwayTesseraClient(TesseraClient):
    """
    Broadway Comedy Club specific Tessera client.

    This subclass provides Broadway Comedy Club specific configurations
    including proper API endpoints, headers, and URL formats.
    """

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """
        Initialize the Broadway Comedy Club Tessera client.

        Args:
            club: Club entity for this venue.
            proxy_pool: Optional ProxyPool for rotating proxy support.
        """
        super().__init__(
            club=club,
            base_domain="broadwaycomedyclub.com",
            api_base_url="https://tickets.broadwaycomedyclub.com/api/v1/products",
            origin_url="https://www.broadwaycomedyclub.com",
            proxy_pool=proxy_pool,
        )
