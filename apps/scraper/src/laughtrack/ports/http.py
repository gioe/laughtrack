"""HTTP ports and protocols.

Stable, dependency-free Protocols describing HTTP capabilities used by scrapers.
We keep re-exports of the current mixins for backward compatibility during the
transition period.
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable

from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.data.mixins.async_http_mixin import AsyncHttpMixin  # noqa: F401
from laughtrack.core.data.mixins.http_convenience_mixin import (  # noqa: F401
    HttpConvenienceMixin,
)


@runtime_checkable
class HttpConvenience(Protocol):
    """Protocol for convenient HTTP operations with error handling.

    Implemented today by HttpConvenienceMixin. Scrapers using BaseScraper
    inherit these methods.
    """

    async def fetch_json(self, url: str, /, **kwargs) -> Dict[str, Any]:
        ...

    async def fetch_html(self, url: str, /, **kwargs) -> str:
        ...

    async def post_json(self, url: str, data: JSONDict, /, **kwargs) -> JSONDict:
        ...

    async def post_form(self, url: str, data: str, /, **kwargs) -> str:
        ...


@runtime_checkable
class HttpClientProtocol(Protocol):
    """Protocol for a simple stateless HTTP client facade.

    Note: Current implementation (`foundation.infrastructure.http.client.HttpClient`)
    exposes these as @staticmethods; this protocol treats them as instance methods to
    allow future evolution to an injectable client. Adapters can provide a thin
    instance wrapper if needed later without changing call sites.
    """

    async def fetch_html(
        self,
        session: Any,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
    ) -> Optional[str]:
        ...

    async def fetch_json(
        self,
        session: Any,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
    ) -> Optional[JSONDict]:
        ...
