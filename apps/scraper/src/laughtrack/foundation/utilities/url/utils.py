"""Pure URL manipulation utilities with no domain dependencies."""

from typing import Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse


class URLUtils:
    """Pure URL manipulation and parsing utilities."""

    @staticmethod
    def get_formatted_domain(url: str) -> str:
        """
        Extract and format the domain from a URL.

        Args:
            url (str): The URL to extract the domain from

        Returns:
            str: The formatted domain (e.g., 'govs.govs.com' from 'https://govs.govs.com')

        Examples:
            >>> URLUtils.get_formatted_domain('https://govs.govs.com')
            'govs.govs.com'
            >>> URLUtils.get_formatted_domain('http://www.example.com/path')
            'example.com'
        """
        parsed = urlparse(url)
        domain = parsed.netloc

        # Remove 'www.' if present for cleaner domain name
        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    @staticmethod
    def get_domain_with_subdomain(url: str) -> str:
        """
        Extract the full domain including subdomain from a URL.

        Args:
            url (str): The URL to extract the domain from

        Returns:
            str: The full domain including subdomain
        """
        parsed = urlparse(url)
        return parsed.netloc

    @staticmethod
    def extract_query_param(url: str, param_name: str) -> Optional[str]:
        """
        Extract a specific query parameter from a URL.

        Args:
            url (str): The URL to parse
            param_name (str): The name of the parameter to extract

        Returns:
            Optional[str]: The parameter value or None if not found
        """
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        if param_name in query_params:
            return query_params[param_name][0]
        return None

    @staticmethod
    def extract_all_query_params(url: str) -> Dict[str, List[str]]:
        """
        Extract all query parameters from a URL.

        Args:
            url (str): The URL to parse

        Returns:
            Dict[str, List[str]]: Dictionary of parameter names to lists of values
        """
        parsed = urlparse(url)
        return parse_qs(parsed.query)

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Check if a URL is valid.

        Args:
            url (str): The URL to validate

        Returns:
            bool: True if the URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            if result.scheme not in {"http", "https"}:
                return False
            host = result.netloc
            # Require a dot in the host to reduce false positives like 'not-a-url'
            if not host or "." not in host:
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def normalize_url(url: str, remove_trailing_slash: bool = True) -> str:
        """
        Normalize a URL by ensuring it has a scheme and optionally removing trailing slashes.

        Args:
            url (str): The URL to normalize
            remove_trailing_slash (bool): Whether to remove trailing slash

        Returns:
            str: The normalized URL
        """
        if not url:
            return url

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Remove trailing slash if requested
        if remove_trailing_slash:
            url = url.rstrip("/")

        return url

    @staticmethod
    def extract_id_from_url(url: str, patterns: List[str]) -> Optional[str]:
        """
        Extract ID from URL using various patterns.

        Args:
            url (str): The URL to extract ID from
            patterns (List[str]): List of path patterns to look for (e.g., ['/events/', '/api/event/'])

        Returns:
            Optional[str]: The extracted ID or None if not found
        """
        if not url:
            return None

        parsed = urlparse(url)
        path = parsed.path

        for pattern in patterns:
            if pattern in path:
                # Get the part after the pattern
                after_pattern = path.split(pattern)[-1]

                # Handle cases where ID might be at end with hyphens (event-name-123)
                if "-" in after_pattern:
                    parts = after_pattern.split("-")
                    # Check if last part is numeric
                    if parts[-1].isdigit():
                        return parts[-1]

                # Handle direct numeric IDs
                # Remove any trailing slash and path segments
                id_candidate = after_pattern.split("/")[0]
                if id_candidate.isdigit():
                    return id_candidate

        return None

    @staticmethod
    def get_base_domain_with_protocol(url: str) -> str:
        """
        Extract the base domain with protocol from a URL.

        Args:
            url (str): The URL to extract the base domain from

        Returns:
            str: The base domain with protocol (e.g., 'https://www.example.com')
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def build_url(base: str, path: str = "", params: Optional[Dict[str, str]] = None) -> str:
        """
        Build a URL from components.

        Args:
            base (str): Base URL
            path (str): Path to append
            params (Dict[str, str]): Query parameters to add

        Returns:
            str: Constructed URL
        """
        # Join base and path
        if path:
            url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
        else:
            url = base

        # Add query parameters
        if params:
            param_pairs = [f"{quote(str(k))}={quote(str(v))}" for k, v in params.items()]
            query_string = "&".join(param_pairs)
            url = f"{url}?{query_string}"

        return url

    @staticmethod
    def encode_url_component(text: str) -> str:
        """
        URL encode a text component.

        Args:
            text (str): Text to encode

        Returns:
            str: URL encoded text
        """
        return quote(str(text))

    @staticmethod
    def decode_url_component(text: str) -> str:
        """
        URL decode a text component.

        Args:
            text (str): Text to decode

        Returns:
            str: URL decoded text
        """
        return unquote(text)

    @staticmethod
    def get_file_extension_from_url(url: str) -> Optional[str]:
        """
        Extract file extension from URL path.

        Args:
            url (str): URL to extract extension from

        Returns:
            Optional[str]: File extension (without dot) or None
        """
        parsed = urlparse(url)
        path = parsed.path

        if "." in path:
            return path.split(".")[-1].lower()

        return None

    @staticmethod
    def extract_event_id_from_url(url: str) -> Optional[str]:
        """
        Extract the event ID from the URL by looking for numeric IDs at the end of URL paths.

        Examples:
        - https://improv.com/hollywood/event/lab+work%21/14371333/ -> 14371333
        - https://improvtx.com/sanantonio/event/revolver+comedy+with+raul+sanchez/14415053/ -> 14415053

        Args:
            url: URL to extract event ID from

        Returns:
            Event ID string or None if not found
        """
        import re

        # Look for numeric ID at the end of the URL path
        match = re.search(r"/(\d+)/?$", url)
        return match.group(1) if match else None

    @staticmethod
    def is_same_domain(url1: str, url2: str) -> bool:
        """
        Check if two URLs are from the same domain.

        Args:
            url1 (str): First URL
            url2 (str): Second URL

        Returns:
            bool: True if same domain, False otherwise
        """
        try:
            domain1 = URLUtils.get_formatted_domain(url1)
            domain2 = URLUtils.get_formatted_domain(url2)
            return domain1 == domain2
        except:
            return False
