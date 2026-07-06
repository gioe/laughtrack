"""
Greenwich Village Comedy Club specific Tessera client.

This client provides Greenwich Village Comedy Club specific configuration
for interacting with its Tessera-based ticketing system.
"""

from typing import Optional

from ..client import TesseraClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool


class GreenwichVillageTesseraClient(TesseraClient):
    """
    Greenwich Village Comedy Club specific Tessera client.

    This subclass provides the Greenwich Village Comedy Club API endpoints,
    headers, and URL formats.
    """

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """
        Initialize the Greenwich Village Comedy Club Tessera client.

        Args:
            club: Club entity for this venue.
            proxy_pool: Optional ProxyPool for rotating proxy support.
        """
        super().__init__(
            club=club,
            base_domain="greenwichvillagecomedyclub.com",
            api_base_url="https://tickets.greenwichvillagecomedyclub.com/api/v1/products",
            origin_url="https://www.greenwichvillagecomedyclub.com",
            proxy_pool=proxy_pool,
        )
