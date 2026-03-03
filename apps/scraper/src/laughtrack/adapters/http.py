"""HTTP adapter facade.

Provides a stable, typed HTTP client that satisfies the port protocol.
Also re-exports the underlying concrete implementation for legacy imports.
"""

from typing import Dict, Optional

from laughtrack.foundation.infrastructure.http.client import HttpClient  # noqa: F401
from laughtrack.foundation.models.types import JSONDict
from laughtrack.ports.http import HttpClientProtocol


class _HttpClientAdapter(HttpClientProtocol):
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


# Export a default HTTP client instance that matches the port protocol
http_client: HttpClientProtocol = _HttpClientAdapter()

