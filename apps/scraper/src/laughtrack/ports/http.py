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
class JSBrowser(Protocol):
    """Protocol for a JavaScript-capable browser that renders dynamic pages.

    Implemented by PlaywrightBrowser in foundation/infrastructure/http/.
    Used as the fallback when curl-cffi returns an empty body or a bot-block
    response.
    """

    async def fetch_html(self, url: str, proxy_url: Optional[str] = None) -> str:
        """Fetch fully-rendered HTML from *url*.

        Args:
            url: Page URL to navigate to.
            proxy_url: Optional proxy URL applied to the browser context
                       (e.g. "http://user:pass@host:port").

        Returns:
            The rendered HTML string after the DOM is ready.
        """
        ...


@runtime_checkable
class HttpConvenience(Protocol):
    """Protocol for convenient HTTP operations with error handling.

    Implemented today by HttpConvenienceMixin. Scrapers using BaseScraper
    inherit these methods.
    """

    async def fetch_json(self, url: str, /, **kwargs) -> Any:
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
