"""Infrastructure implementation of the HTTP port protocol.

Wraps the shared HttpClient utilities in a Protocol-compliant adapter.
"""

from typing import Dict, Optional

from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.models.types import JSONDict
from laughtrack.ports.http import HttpClientProtocol


class HttpClientAdapter(HttpClientProtocol):
    async def fetch_html(
        self,
        session,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
    ) -> Optional[str]:
        return await HttpClient.fetch_html(session, url, headers=headers, logger_context=logger_context)

    async def fetch_json(
        self,
        session,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
    ) -> Optional[JSONDict]:
        return await HttpClient.fetch_json(session, url, headers=headers, logger_context=logger_context)


# Default instance for wiring
default_http_client: HttpClientProtocol = HttpClientAdapter()
