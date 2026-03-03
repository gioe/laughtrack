from typing import Any, Dict, Optional

from laughtrack.core.entities.club.model import Club



class DataDomeProtectionHandler:
    """
    Handler for DataDome bot protection, providing methods to generate
    bypass headers and handle DataDome responses.
    """

    def __init__(self, club: Optional[Club] = None, logger=None):
        """
        Initialize the DataDome protection handler.

        Args:
            club: Club instance for configuration access
            logger: Logger instance for logging (should have log_info, log_warning, log_error methods)
        """
        self.club = club
        self.logger = logger

    def get_datadome_cookie(self) -> Optional[str]:
        """
        Get DataDome cookie from club configuration.

        Returns:
            DataDome cookie value if available, None otherwise
        """
        # DataDome cookies are no longer stored in club configuration
        # They should be managed through session handling instead
        return None

    def get_bypass_headers(self, event_id: str, base_url: str = "https://www.tixr.com") -> Dict[str, str]:
        """
        Get headers that match a working browser session to bypass DataDome.

        Args:
            event_id: The event ID (not used in header generation, kept for compatibility)
            base_url: Base URL for constructing host header (defaults to Tixr)

        Returns:
            Headers dictionary that successfully bypass DataDome protection
        """
        host = self._extract_host_from_url(base_url)

        # Get datadome cookie from club config if available, otherwise use default
        datadome_cookie = self.get_datadome_cookie()
        if datadome_cookie:
            cookie_value = f"datadome={datadome_cookie}"
            self._log_info(f"Using datadome cookie for event {event_id}")
        else:
            # If no datadome cookie available, log and set cookie_value to None
            cookie_value = None
            self._log_info(f"No datadome cookie available for event {event_id}")

        # Use the exact headers that work in the browser
        headers = {
            "X-NewRelic-ID": "Ug8CWVVXGwcEUlFVDwM=",
            "sec-ch-ua-full-version-list": '"Google Chrome";v="137.0.7151.69", "Chromium";v="137.0.7151.69", "Not/A)Brand";v="24.0.0.0"',
            "sec-ch-ua-platform": '"macOS"',
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-model": '""',
            "sec-ch-device-memory": "8",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-arch": '"arm"',
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Host": host,
            "Referer": base_url,
        }

        # Only add Cookie header if we have a cookie value
        if cookie_value:
            headers["Cookie"] = cookie_value
        return headers

    def handle_datadome_response(self, event_id: str, response: Any) -> None:
        """
        Handle DataDome protection responses with proper logging and suggestions.

        Args:
            event_id: The event ID that was blocked
            response: The HTTP response from DataDome (should have .headers and .text attributes)
        """
        # Check if it's specifically DataDome
        is_datadome = self._is_datadome_response(response)

        if is_datadome:
            self._log_warning(f"DataDome bot protection detected for event {event_id}")
            self._log_info("DataDome protection prevents direct API access")
            self._log_info("Consider implementing browser automation (Selenium/Playwright)")

            # Log the DataDome challenge details if available
            if hasattr(response, "text") and "captcha" in response.text.lower():
                self._log_info(f"DataDome captcha challenge triggered for event {event_id}")

            # Suggest alternative approaches
            self._suggest_alternatives(event_id)
        else:
            response_text = getattr(response, "text", "")[:200] if hasattr(response, "text") else "No response text"
            self._log_warning(f"403 Forbidden for event {event_id} (not DataDome): {response_text}")

    def is_datadome_protected(self, response: Any) -> bool:
        """
        Check if a response indicates DataDome protection.

        Args:
            response: HTTP response to check

        Returns:
            True if DataDome protection is detected, False otherwise
        """
        return self._is_datadome_response(response)

    def _is_datadome_response(self, response: Any) -> bool:
        """
        Check if a response is from DataDome protection.

        Args:
            response: HTTP response to check

        Returns:
            True if DataDome protection is detected, False otherwise
        """
        if not response:
            return False

        # Check headers
        if hasattr(response, "headers") and "X-DataDome" in response.headers:
            return True

        # Check response text
        if hasattr(response, "text") and response.text:
            text_lower = response.text.lower()
            return "datadome" in text_lower or "captcha-delivery.com" in text_lower

        return False

    def _suggest_alternatives(self, event_id: str) -> None:
        """
        Log suggestions for handling DataDome protection.

        Args:
            event_id: The event ID that was blocked
        """
        self._log_info("Possible solutions for DataDome protection:")
        self._log_info("1. Implement Selenium/Playwright browser automation")
        self._log_info("2. Use proxy services like ScrapingBee or Bright Data")
        self._log_info("3. Add longer delays and rotate user agents")
        self._log_info("4. Consider alternative data sources")

        # For debugging purposes, log the event URL pattern
        self._log_info(f"Event ID: {event_id}")

    def _extract_host_from_url(self, url: str) -> str:
        """
        Extract host from URL.

        Args:
            url: Full URL

        Returns:
            Host portion of the URL
        """
        if url.startswith("https://"):
            return url[8:].split("/")[0]
        elif url.startswith("http://"):
            return url[7:].split("/")[0]
        else:
            return url.split("/")[0]

    def _log_info(self, message: str) -> None:
        """Log info message using available logger."""
        if self.logger and hasattr(self.logger, "log_info"):
            self.logger.log_info(message)
        elif self.logger and hasattr(self.logger, "info"):
            self.logger.info(message)

    def _log_warning(self, message: str) -> None:
        """Log warning message using available logger."""
        if self.logger and hasattr(self.logger, "log_warning"):
            self.logger.log_warning(message)
        elif self.logger and hasattr(self.logger, "warning"):
            self.logger.warning(message)

    def _log_error(self, message: str) -> None:
        """Log error message using available logger."""
        if self.logger and hasattr(self.logger, "log_error"):
            self.logger.log_error(message)
        elif self.logger and hasattr(self.logger, "error"):
            self.logger.error(message)
