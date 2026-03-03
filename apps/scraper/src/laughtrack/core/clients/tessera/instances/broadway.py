"""
Broadway Comedy Club specific Tessera client.

This client provides Broadway Comedy Club specific configurations
for interacting with their Tessera-based ticketing system.
"""

from ..client import TesseraClient
from laughtrack.core.entities.club.model import Club

class BroadwayTesseraClient(TesseraClient):
    """
    Broadway Comedy Club specific Tessera client.

    This subclass provides Broadway Comedy Club specific configurations
    including proper API endpoints, headers, and URL formats.
    """

    def __init__(self, club: Club):
        """
        Initialize the Broadway Comedy Club Tessera client.

        Args:
            None beyond club
        """
        super().__init__(
            club=club,
            base_domain="broadwaycomedyclub.com",
            api_base_url="https://tickets.broadwaycomedyclub.com/api/v1/products",
            origin_url="https://www.broadwaycomedyclub.com",
        )
