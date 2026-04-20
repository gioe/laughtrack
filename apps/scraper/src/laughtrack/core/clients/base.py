"""Base API client class providing common functionality for all API clients."""

from abc import ABC
from typing import Any, Dict, List, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.client import HttpClient, _bot_block_reason
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool

# POST requests in this module do NOT get the Playwright fallback that the
# GET-side fetch_html/fetch_json enjoy. Replaying a POST body from a
# browser context requires a pre-warmed cookie jar (a prior GET that cleared
# any challenge) and a page.request.post() call that inherits that context —
# the audit in TASK-1648 flagged this as MEDIUM severity because POSTs are
# rarely the scrape entry point (they follow an authenticated GET that has
# already satisfied the WAF). Until a concrete case justifies the extra
# machinery, the POST helpers surface bot-block signatures and non-200 /
# empty-body failures via Logger.error so they are visible in triage rather
# than swallowed as WARNINGs.


class BaseApiClient(ABC):
    """Base class for all API clients with common functionality."""

    def __init__(self, club: Club, rate_limiter=None, proxy_pool: Optional[ProxyPool] = None):
        """Initialize the base API client.

        Args:
            club: The Club instance this client will work with
            rate_limiter: Optional rate limiter for HTTP requests
            proxy_pool: Optional ProxyPool for rotating proxy support.
                When provided, each request is routed through the next
                available proxy in the pool.  When ``None`` (default) or
                when the pool has no active proxies, requests are sent
                directly as before.
        """
        self.club = club
        self.rate_limiter = rate_limiter
        self.proxy_pool = proxy_pool
        self.http_client = HttpClient()

        # Initialize headers - subclasses can override this
        self.headers = self._initialize_headers()

    async def _apply_rate_limit(self, target: str) -> None:
        """Apply rate limiting if a limiter is configured.

        Supports multiple limiter styles:
        - Our project RateLimiter: has await_if_needed(target)
        - Token-based limiters: have an awaitable acquire() method
        - Async context managers are not required (to avoid protocol errors)
        """
        limiter = getattr(self, "rate_limiter", None)
        if not limiter:
            return

        # Prefer our RateLimiter protocol
        import inspect

        await_if_needed = getattr(limiter, "await_if_needed", None)
        if callable(await_if_needed):
            try:
                try:
                    Logger.debug(
                        "Applying rate limit (await_if_needed)",
                        context={"club_name": getattr(self.club, "name", "-"), "target": target},
                    )
                except Exception:
                    pass
                if inspect.iscoroutinefunction(await_if_needed):
                    await await_if_needed(target)
                else:
                    result = await_if_needed(target)
                    if inspect.isawaitable(result):
                        await result
                return
            except Exception:
                # Fall through to other strategies
                pass

        # Fallback: acquire() coroutine
        acquire = getattr(limiter, "acquire", None)
        if callable(acquire):
            try:
                try:
                    Logger.debug(
                        "Applying rate limit (acquire)",
                        context={"club_name": getattr(self.club, "name", "-"), "target": target},
                    )
                except Exception:
                    pass
                if inspect.iscoroutinefunction(acquire):
                    await acquire()
                else:
                    result = acquire()
                    if inspect.isawaitable(result):
                        await result
                return
            except Exception:
                return

    def _get_impersonation_target(self, url: str) -> str:
        """Return the curl-cffi impersonation target for *url*.

        Asks the rate limiter for the active BrowserProfile of the request's
        domain so the TLS fingerprint always matches the HTTP headers.  Falls
        back to ``"chrome124"`` when no rate limiter or no active profile is
        available.
        """
        limiter = getattr(self, "rate_limiter", None)
        if limiter is None:
            return "chrome124"
        get_profile = getattr(limiter, "get_domain_profile", None)
        if not callable(get_profile):
            return "chrome124"
        try:
            if "://" in url:
                domain = url.split("://", 1)[1].split("/")[0].lower()
            else:
                domain = url.split("/")[0].lower()
            profile = get_profile(domain)
            if profile is not None:
                return profile.impersonation_target
        except Exception:
            pass
        return "chrome124"

    def _get_proxy_url(self) -> Optional[str]:
        """Return the next proxy URL from the pool, or ``None`` if no pool."""
        if self.proxy_pool is None:
            return None
        return self.proxy_pool.get_proxy()

    def _initialize_headers(self) -> Dict[str, str]:
        """Initialize default headers. Subclasses should override for custom auth."""
        return BaseHeaders.get_headers("json")

    # No extra systems: use direct DEBUG logging inline in request methods

    def log_info(self, message: str) -> None:
        """Log an info message."""
        Logger.info(f"[{self.club.name}] {message}")

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        Logger.warning(f"[{self.club.name}] {message}")

    def log_error(self, message: str) -> None:
        """Log an error message."""
        Logger.error(f"[{self.club.name}] {message}")

    async def cleanup(self):
        """Optional async cleanup hook for clients with persistent resources."""
        return None

    async def fetch_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        logger_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[JSONDict]:
        """
        Fetch JSON data from a URL with session management and error handling.

        Args:
            url: URL to fetch from
            headers: Optional headers to include (defaults to self.headers)
            timeout: Request timeout in seconds
            logger_context: Context for logging

        Returns:
            JSON data as dictionary, or None if fetch failed
        """
        request_headers = headers or self.headers
        context = logger_context or {}
        proxy_url = self._get_proxy_url()
        try:
            async with AsyncSession(impersonate=self._get_impersonation_target(url), timeout=timeout) as session:
                # DEBUG pre-request details
                try:
                    ctx: JSONDict = {"club_name": getattr(self.club, "name", "-")}
                    if isinstance(context, dict):
                        ctx.update(context)
                    Logger.debug(
                        f"HTTP GET {url} (pre) headers={list(request_headers.keys())} timeout={timeout}",
                        context=ctx,
                    )
                except Exception:
                    pass
                await self._apply_rate_limit(url)
                data = await self.http_client.fetch_json(
                    session=session, url=url, headers=request_headers,
                    logger_context=context, proxy_url=proxy_url,
                )
                # DEBUG summary of response
                try:
                    ctx: JSONDict = {"club_name": getattr(self.club, "name", "-")}
                    if isinstance(context, dict):
                        ctx.update(context)
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        msg = data.get("message")
                        msg_part = f", message={msg!r}" if isinstance(msg, (str, int, float, bool)) else ""
                        summary = f"json dict keys={keys}{msg_part}"
                    elif isinstance(data, list):
                        summary = f"json list len={len(data)}"
                    elif isinstance(data, str):
                        preview = (data[:300] + "…") if len(data) > 300 else data
                        summary = f"text len={len(data)} preview={preview!r}"
                    else:
                        summary = f"type={type(data).__name__}"
                    Logger.debug(f"HTTP GET {url} → {summary}", context=ctx)
                except Exception:
                    pass
                if proxy_url and self.proxy_pool is not None:
                    if data is None:
                        self.proxy_pool.report_failure(proxy_url)
                    else:
                        self.proxy_pool.report_success(proxy_url)
                return data
        except Exception as e:
            if proxy_url and self.proxy_pool is not None:
                self.proxy_pool.report_failure(proxy_url)
            self.log_error(f"Failed to fetch JSON from {url}: {e}")
            return None

    async def fetch_json_list(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        logger_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[Any]]:
        """
        Fetch a root-level JSON array from a URL.

        Use this instead of fetch_json() when the API is known to return a JSON
        array at the root level (e.g. Ninkashi). Returns None on network failure
        or when the response is not a list.

        Args:
            url: URL to fetch from
            headers: Optional headers to include (defaults to self.headers)
            timeout: Request timeout in seconds
            logger_context: Context for logging

        Returns:
            JSON array, or None if fetch failed or response was not a list
        """
        data = await self.fetch_json(url, headers=headers, timeout=timeout, logger_context=logger_context)
        if data is None:
            return None
        if not isinstance(data, list):
            self.log_warning(f"fetch_json_list: expected list from {url}, got {type(data).__name__}")
            return None
        return data

    async def fetch_html(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        logger_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Fetch HTML content from a URL with session management and error handling.

        Args:
            url: URL to fetch from
            headers: Optional headers to include (defaults to self.headers)
            timeout: Request timeout in seconds
            logger_context: Context for logging

        Returns:
            HTML content as string, or None if fetch failed
        """
        request_headers = headers or self.headers
        context = logger_context or {}
        proxy_url = self._get_proxy_url()

        try:
            async with AsyncSession(impersonate=self._get_impersonation_target(url), timeout=timeout) as session:
                # DEBUG pre-request details
                try:
                    ctx: JSONDict = {"club_name": getattr(self.club, "name", "-")}
                    if isinstance(context, dict):
                        ctx.update(context)
                    Logger.debug(
                        f"HTTP GET {url} (pre) headers={list(request_headers.keys())} timeout={timeout}",
                        context=ctx,
                    )
                except Exception:
                    pass
                await self._apply_rate_limit(url)
                text = await self.http_client.fetch_html(
                    session=session, url=url, headers=request_headers,
                    logger_context=context, proxy_url=proxy_url,
                )
                # DEBUG summary of response
                try:
                    ctx: JSONDict = {"club_name": getattr(self.club, "name", "-")}
                    if isinstance(context, dict):
                        ctx.update(context)
                    if isinstance(text, str):
                        preview = (text[:300] + "…") if len(text) > 300 else text
                        summary = f"text len={len(text)} preview={preview!r}"
                    else:
                        summary = f"type={type(text).__name__}"
                    Logger.debug(f"HTTP GET {url} → {summary}", context=ctx)
                except Exception:
                    pass
                if proxy_url and self.proxy_pool is not None:
                    if text is None:
                        self.proxy_pool.report_failure(proxy_url)
                    else:
                        self.proxy_pool.report_success(proxy_url)
                return text
        except Exception as e:
            if proxy_url and self.proxy_pool is not None:
                self.proxy_pool.report_failure(proxy_url)
            self.log_error(f"Failed to fetch HTML from {url}: {e}")
            return None

    async def post_json(
        self,
        url: str,
        payload: Any,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        logger_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[JSONDict]:
        """
        POST JSON data to a URL and parse the JSON response.

        Args:
            url: URL to post to
            payload: JSON-serializable payload (dict/list/etc.)
            headers: Optional headers to include (defaults to self.headers)
            timeout: Request timeout in seconds
            logger_context: Context for logging

        Returns:
            Parsed JSON response as dict, or None on failure
        """
        request_headers = headers or self.headers
        # Ensure content type for JSON
        if not any(k.lower() == "content-type" for k in request_headers.keys()):
            request_headers["Content-Type"] = "application/json"

        context = logger_context or {}
        proxy_url = self._get_proxy_url()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        try:
            async with AsyncSession(impersonate=self._get_impersonation_target(url), timeout=timeout) as session:
                # DEBUG pre-request details
                try:
                    ctx: JSONDict = {"club_name": getattr(self.club, "name", "-")}
                    if isinstance(context, dict):
                        ctx.update(context)
                    Logger.debug(
                        f"HTTP POST {url} (pre json) headers={list(request_headers.keys())} timeout={timeout}",
                        context=ctx,
                    )
                except Exception:
                    pass
                await self._apply_rate_limit(url)
                response = await session.post(url, json=payload, headers=request_headers, proxies=proxies)
                resp_text = response.text if isinstance(response.text, str) else ""
                if response.status_code != 200:
                    bot_signature = _bot_block_reason(resp_text) if resp_text else None
                    if bot_signature is not None:
                        Logger.error(
                            f"Bot-block signature {bot_signature!r} in HTTP {response.status_code} "
                            f"POST response from {url}. Playwright fallback is not implemented for "
                            f"POST — see module docstring in core/clients/base.py."
                        )
                    else:
                        Logger.error(f"HTTP {response.status_code} when POSTing {url}")
                    if proxy_url and self.proxy_pool is not None:
                        self.proxy_pool.report_failure(proxy_url)
                    return None
                if not resp_text or not resp_text.strip():
                    Logger.error(f"HTTP 200 with empty body when POSTing {url}")
                    if proxy_url and self.proxy_pool is not None:
                        self.proxy_pool.report_failure(proxy_url)
                    return None
                # Some WAFs return 200 + an HTML challenge interstitial; detect that here
                # so the caller isn't handed a cart/auth response that is actually a block page.
                bot_signature = _bot_block_reason(resp_text)
                if bot_signature is not None:
                    Logger.error(
                        f"Bot-block signature {bot_signature!r} in HTTP 200 POST response body "
                        f"from {url}. Playwright fallback is not implemented for POST — see module "
                        f"docstring in core/clients/base.py."
                    )
                    if proxy_url and self.proxy_pool is not None:
                        self.proxy_pool.report_failure(proxy_url)
                    return None
                obj = response.json()
                # DEBUG summary of response
                try:
                    ctx: JSONDict = {"club_name": getattr(self.club, "name", "-")}
                    if isinstance(context, dict):
                        ctx.update(context)
                    if isinstance(obj, dict):
                        keys = list(obj.keys())
                        msg = obj.get("message")
                        msg_part = f", message={msg!r}" if isinstance(msg, (str, int, float, bool)) else ""
                        summary = f"json dict keys={keys}{msg_part}"
                    elif isinstance(obj, list):
                        summary = f"json list len={len(obj)}"
                    elif isinstance(obj, str):
                        preview = (obj[:300] + "…") if len(obj) > 300 else obj
                        summary = f"text len={len(obj)} preview={preview!r}"
                    else:
                        summary = f"type={type(obj).__name__}"
                    Logger.debug(f"HTTP POST {url} → {summary}", context=ctx)
                except Exception:
                    pass
                if not isinstance(obj, dict):
                    Logger.warning(f"Unexpected JSON type from {url}; expected dict, got {type(obj).__name__}")
                    return None
                if proxy_url and self.proxy_pool is not None:
                    self.proxy_pool.report_success(proxy_url)
                return obj
        except Exception as e:
            if proxy_url and self.proxy_pool is not None:
                self.proxy_pool.report_failure(proxy_url)
            self.log_error(f"Failed to POST JSON to {url}: {e}")
            return None

    async def post_form(
        self,
        url: str,
        payload: Any,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        logger_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        POST form-encoded data to a URL and return text response.

        Args:
            url: URL to post to
            payload: Form data (dict or string)
            headers: Optional headers to include (defaults to self.headers)
            timeout: Request timeout in seconds
            logger_context: Context for logging

        Returns:
            Response text, or None on failure
        """
        request_headers = headers or self.headers
        # Ensure content type for form if not explicitly set
        headers_lower = {k.lower(): v for k, v in request_headers.items()}
        if "content-type" not in headers_lower:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

        context = logger_context or {}
        proxy_url = self._get_proxy_url()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        try:
            async with AsyncSession(impersonate=self._get_impersonation_target(url), timeout=timeout) as session:
                # DEBUG pre-request details
                try:
                    ctx: JSONDict = {"club_name": getattr(self.club, "name", "-")}
                    if isinstance(context, dict):
                        ctx.update(context)
                    Logger.debug(
                        f"HTTP POST {url} (pre form) headers={list(request_headers.keys())} timeout={timeout}",
                        context=ctx,
                    )
                except Exception:
                    pass
                await self._apply_rate_limit(url)
                response = await session.post(url, data=payload, headers=request_headers, proxies=proxies)
                resp_text = response.text if isinstance(response.text, str) else ""
                if response.status_code != 200:
                    bot_signature = _bot_block_reason(resp_text) if resp_text else None
                    if bot_signature is not None:
                        Logger.error(
                            f"Bot-block signature {bot_signature!r} in HTTP {response.status_code} "
                            f"POST (form) response from {url}. Playwright fallback is not implemented "
                            f"for POST — see module docstring in core/clients/base.py."
                        )
                    else:
                        Logger.error(f"HTTP {response.status_code} when POSTing form to {url}")
                    if proxy_url and self.proxy_pool is not None:
                        self.proxy_pool.report_failure(proxy_url)
                    return None
                if not resp_text or not resp_text.strip():
                    Logger.error(f"HTTP 200 with empty body when POSTing form to {url}")
                    if proxy_url and self.proxy_pool is not None:
                        self.proxy_pool.report_failure(proxy_url)
                    return None
                # Some WAFs return 200 + an HTML challenge interstitial in response to a POST;
                # surface that as an error so the caller doesn't treat the block page as real data.
                bot_signature = _bot_block_reason(resp_text)
                if bot_signature is not None:
                    Logger.error(
                        f"Bot-block signature {bot_signature!r} in HTTP 200 POST (form) response "
                        f"body from {url}. Playwright fallback is not implemented for POST — see "
                        f"module docstring in core/clients/base.py."
                    )
                    if proxy_url and self.proxy_pool is not None:
                        self.proxy_pool.report_failure(proxy_url)
                    return None
                text = resp_text
                # DEBUG summary of response
                try:
                    ctx: JSONDict = {"club_name": getattr(self.club, "name", "-")}
                    if isinstance(context, dict):
                        ctx.update(context)
                    if isinstance(text, str):
                        preview = (text[:300] + "…") if len(text) > 300 else text
                        summary = f"text len={len(text)} preview={preview!r}"
                    else:
                        summary = f"type={type(text).__name__}"
                    Logger.debug(f"HTTP POST {url} → {summary}", context=ctx)
                except Exception:
                    pass
                if proxy_url and self.proxy_pool is not None:
                    self.proxy_pool.report_success(proxy_url)
                return text
        except Exception as e:
            if proxy_url and self.proxy_pool is not None:
                self.proxy_pool.report_failure(proxy_url)
            self.log_error(f"Failed to POST form to {url}: {e}")
            return None
