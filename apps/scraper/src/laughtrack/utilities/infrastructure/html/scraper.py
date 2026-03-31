import json
import re
from typing import Any, List, Optional, Union

from bs4 import BeautifulSoup as bs
from bs4.element import Tag

from laughtrack.foundation.models.types import JSONDict
from gioe_libs.string_utils import StringUtils
from laughtrack.foundation.utilities.url import URLUtils
from urllib.parse import urlsplit, urlunsplit


class HtmlScraper:
    """
    Static utility class for HTML scraping operations.

    Provides a collection of static methods for parsing HTML content and extracting
    various elements like links, text, and JSON-LD data. All methods are stateless
    and pass exceptions up to the caller for appropriate error handling.

    Main capabilities:
    - Link extraction with various filters (class, prefix, domain, text patterns)
    - Generic element finding with CSS selectors and attributes
    - JSON-LD data extraction from script tags
    - Text content extraction
    - Safe URL building and attribute extraction
    """

    @staticmethod
    def _parse_html(html: str) -> bs:
        """Create and return a BeautifulSoup instance."""
        return bs(html, "html.parser")

    @staticmethod
    def _safe_get_href(element: Any) -> Optional[str]:
        """Safely extract href attribute from a BeautifulSoup element."""
        if hasattr(element, "get"):
            href = element.get("href")
            return str(href) if href and isinstance(href, (str, int, float)) else None
        return None

    @staticmethod
    def _build_absolute_url(href: str, base_url: str) -> str:
        """Build absolute URL from href and base URL."""
        if href.startswith(("http://", "https://")):
            return href

        # If href is a query-only or fragment-only reference, replace the base's query/fragment
        if href.startswith("?"):
            parts = urlsplit(base_url)
            # Replace query with the provided one (without '?') and clear fragment
            return urlunsplit((parts.scheme, parts.netloc, parts.path, href[1:], ""))
        if href.startswith("#"):
            parts = urlsplit(base_url)
            # Keep existing query, replace fragment
            return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, href[1:]))

        # Normalize URL construction
        if base_url.endswith("/") and href.startswith("/"):
            href = href[1:]
        elif not base_url.endswith("/") and not href.startswith("/"):
            href = "/" + href

        return base_url.rstrip("/") + "/" + href.lstrip("/")

    @staticmethod
    def find_links_by_class(html: str, class_name: str, base_url: Optional[str] = None) -> List[str]:
        """
        Find all links with a specific class name.

        Args:
            html: HTML string to parse
            class_name: Class name to search for
            base_url: Optional base URL for constructing absolute URLs

        Returns:
            List[str]: List of href values from matching links

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)
        links = soup.find_all("a", class_=class_name, href=True)
        hrefs = [HtmlScraper._safe_get_href(link) for link in links]
        # Filter out None values
        valid_hrefs = [href for href in hrefs if href is not None]

        if base_url:
            return [HtmlScraper._build_absolute_url(href, base_url) for href in valid_hrefs]
        return valid_hrefs

    @staticmethod
    def find_element(html: str, tag: Optional[str] = None, **attrs) -> Optional[Any]:
        """
        Find a single element matching the criteria.

        Args:
            html: HTML string to parse
            tag: HTML tag to search for (optional)
            **attrs: Attributes to match (class_, id, etc.)

        Returns:
            Optional[Any]: Matching element or None if not found

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)
        return soup.find(tag, attrs=attrs)

    @staticmethod
    def find_elements(html: str, tag: Optional[str] = None, **attrs) -> List[Any]:
        """
        Find all elements matching the criteria.

        Args:
            html: HTML string to parse
            tag: HTML tag to search for (optional)
            **attrs: Attributes to match (class_, id, etc.)

        Returns:
            List[Any]: List of matching elements

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)
        return soup.find_all(tag, attrs=attrs)

    @staticmethod
    def find_links_by_prefix(html: str, prefix: str, base_url: Optional[str] = None) -> List[str]:
        """
        Find all links with a specific prefix.

        Args:
            html: HTML string to parse
            prefix: Prefix to search for
            base_url: Optional base URL for constructing absolute URLs

        Returns:
            List[str]: List of href values from matching links

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)
        links = soup.find_all("a", href=True)
        hrefs = []

        for link in links:
            href = HtmlScraper._safe_get_href(link)
            if href and href.startswith(prefix):
                hrefs.append(href)

        if base_url:
            return [HtmlScraper._build_absolute_url(href, base_url) for href in hrefs]
        return hrefs

    @staticmethod
    def find_script_elements(html: str, script_type: Optional[str] = None) -> List[Any]:
        """
        Find all script elements, optionally filtered by type.

        Args:
            html: HTML string to parse
            script_type: Optional script type to filter by (e.g., "application/ld+json")

        Returns:
            List[Any]: List of matching script elements

        Raises:
            Exception: If parsing fails
        """
        attrs = {"type": script_type} if script_type else {}
        return HtmlScraper.find_elements(html, "script", **attrs)

    @staticmethod
    def find_elements_by_selector(html: str, selector: str) -> List[Any]:
        """
        Find elements using CSS selectors.

        Args:
            html: HTML string to parse
            selector: CSS selector to match

        Returns:
            List[Any]: List of matching elements

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)
        return soup.select(selector)

    @staticmethod
    def get_text_content(html: str, selector: str) -> Optional[str]:
        """
        Get text content from an element matching a CSS selector.

        Args:
            html: HTML string to parse
            selector: CSS selector to match

        Returns:
            Optional[str]: Text content or None if not found

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else None

    @staticmethod
    def check_component_match(html: str, component_type: str, class_name: str, target_text: str) -> bool:
        """
        Check if the first BeautifulSoup component matching the criteria has the target text.

        Args:
            html: HTML string to parse
            component_type (str): The HTML element type (e.g., 'p', 'div', 'span')
            class_name (str): The CSS class name to match
            target_text (str): The text content to match

        Returns:
            bool: True if the first matching component has the target text, False otherwise

        Raises:
            Exception: If parsing fails
        """
        component = HtmlScraper.find_element(html, component_type, class_=class_name)
        return component is not None and component.text.strip() == target_text.strip()

    @staticmethod
    def find_child_component(component: Any, tag: str, class_name: str) -> Any:
        """
        Find a child element with a specific class name within a parent component.

        Args:
            component: Parent BeautifulSoup element
            tag: HTML tag to search for
            class_name: Class name to search for

        Returns:
            Any: Matching child element or None if not found

        Raises:
            Exception: If search fails
        """
        return component.find(tag, class_=class_name)

    @staticmethod
    def find_links_by_domain(html: str, domain: str) -> List[str]:
        """
        Find all links that share a domain with the provided one.

        Args:
            html: HTML string to parse
            domain: Domain to match against (e.g., 'example.com')

        Returns:
            List[str]: List of href values from matching links

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)
        links = soup.find_all("a", href=True)
        result = []

        for link in links:
            href = HtmlScraper._safe_get_href(link)
            if href:
                try:
                    if URLUtils.get_formatted_domain(href) == domain:
                        result.append(href)
                except Exception:
                    # Skip links with invalid URLs
                    continue

        return result

    @staticmethod
    def get_json_ld_script_contents(html_content: str) -> List[str]:
        """
        Extract raw JSON-LD script contents from HTML.

        Args:
            html_content: HTML content to parse

        Returns:
            List[str]: List of raw JSON-LD script contents (unprocessed)
        """
        script_contents = []
        json_ld_scripts = HtmlScraper.find_script_elements(html_content, "application/ld+json")

        for script in json_ld_scripts:
            try:
                content = script.get_text()
                if content:
                    script_contents.append(content)
            except Exception:
                # Silently continue on parsing errors
                continue

        return script_contents

    @staticmethod
    def find_all_links(html: str) -> List[Any]:
        """
        Find all <a> elements with href attributes.

        Args:
            html: HTML string to parse

        Returns:
            List[Any]: List of link elements

        Raises:
            Exception: If parsing fails
        """
        return HtmlScraper.find_elements(html, "a", href=True)

    @staticmethod
    def get_link_url_by_id(html: str, anchor_id: str, base_url: Optional[str] = None) -> Optional[str]:
        """
        Return the (optionally absolute) href for an anchor with a specific id.

        Args:
            html: HTML string to parse
            anchor_id: Exact id attribute of the <a> tag to find
            base_url: If provided, convert href to an absolute URL using this base

        Returns:
            The matching URL (absolute if base_url provided) or None if not found
        """
        soup = HtmlScraper._parse_html(html)
        a = soup.find("a", id=anchor_id, href=True)
        if not a:
            return None
        href = HtmlScraper._safe_get_href(a)
        if not href:
            return None
        return HtmlScraper._build_absolute_url(href, base_url) if base_url else href

    @staticmethod
    def extract_links_by_text_pattern(html: str, pattern: str, base_url: Optional[str] = None, **kwargs) -> List[str]:
        """
        Extract links whose href attribute contains a specific text pattern.

        Args:
            html: HTML string to parse
            pattern: Text pattern to search for in href attributes
            base_url: Optional base URL for constructing absolute URLs
            **kwargs: Additional arguments for compatibility (e.g., logger_context)

        Returns:
            List[str]: List of matching URLs

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)
        links = soup.find_all("a", href=True)
        hrefs = []

        for link in links:
            href = HtmlScraper._safe_get_href(link)
            if href and pattern in href:
                hrefs.append(href)

        if base_url:
            return [HtmlScraper._build_absolute_url(href, base_url) for href in hrefs]
        return hrefs

    @staticmethod
    def extract_anchor_hrefs_having_child(html: str, child_tag: str, child_class: str) -> List[str]:
        """
        Return hrefs for anchors that contain a child element matching tag/class.

        Example: find <a ...><h3 class="card-title my-1">...</h3></a> and return href.

        Args:
            html: HTML string to parse
            child_tag: Tag name of the child to be contained within the anchor
            child_class: Class name of the child element

        Returns:
            List of href strings
        """
        soup = HtmlScraper._parse_html(html)
        results: List[str] = []
        for a in soup.find_all("a", href=True):
            try:
                # BeautifulSoup typing for find(*) doesn't include class_; suppress type checker noise
                if not isinstance(a, Tag):
                    continue
                child = a.find(child_tag, class_=child_class)  # type: ignore[call-arg]
                if child:
                    href = HtmlScraper._safe_get_href(a)
                    if href:
                        results.append(href)
            except Exception:
                continue
        return results

    @staticmethod
    def extract_card_id_to_href_by_child(
        html: str,
        card_class: str,
        child_tag: str,
        child_class: str,
    ) -> dict:
        """
        Build a mapping of card id -> href for anchors that contain a specific child element.

        Designed for Tessera-style show cards where each card div has an id and contains
        an <a> that wraps an <h3 class="card-title my-1"> element.

        Args:
            html: HTML string to parse
            card_class: Class name of the card container (e.g., "tessera-show-card")
            child_tag: Tag name of the child contained within the anchor (e.g., "h3")
            child_class: Class of the child contained within the anchor

        Returns:
            Dict mapping card id (string) to href (string)
        """
        soup = HtmlScraper._parse_html(html)
        mapping: dict = {}

        # Find all card containers by CSS selector for class inclusion
        cards = soup.select(f"div.{card_class}")
        for card in cards:
            try:
                if not isinstance(card, Tag):
                    continue
                card_id = card.get("id")
                if not card_id:
                    continue

                # Find an anchor that contains the child_tag/class
                anchor = None
                for a in card.find_all("a", href=True):  # type: ignore[attr-defined]
                    if not isinstance(a, Tag):
                        continue
                    child = a.find(child_tag, class_=child_class)  # type: ignore[call-arg]
                    if child:
                        anchor = a
                        break

                if not anchor:
                    continue

                href = HtmlScraper._safe_get_href(anchor)
                if href:
                    mapping[str(card_id)] = href
            except Exception:
                continue

        return mapping

    @staticmethod
    def extract_card_id_to_child_text_by_class(
        html: str,
        card_class: str,
        child_tag: str,
        child_class: str,
    ) -> dict:
        """
        Build a mapping of card id -> text content of a descendant child element.

        Useful for Tessera cards where metadata like the room appears in a div such as
        <div class="tessera-venue fw-bold">Main Room</div> inside the card container.

        Args:
            html: HTML string to parse
            card_class: Class name of the card container (e.g., "tessera-show-card")
            child_tag: Tag name of the child element (e.g., "div")
            child_class: Class of the child element (e.g., "tessera-venue")

        Returns:
            Dict mapping card id (string) to the child's text content (string)
        """
        soup = HtmlScraper._parse_html(html)
        mapping: dict = {}

        # Find all card containers by CSS selector for class inclusion
        cards = soup.select(f"div.{card_class}")
        for card in cards:
            try:
                if not isinstance(card, Tag):
                    continue
                card_id = card.get("id")
                if not card_id:
                    continue

                # Find the child element by tag and class. Using class_ will match multi-class elements.
                child = card.find(child_tag, class_=child_class)  # type: ignore[call-arg]
                if not child:
                    # Try via CSS selector as a fallback to handle space-separated classes precisely
                    # Example: child_class "tessera-venue" should match <div class="tessera-venue fw-bold">
                    sel = f"{child_tag}.{child_class}"
                    child = card.select_one(sel)

                if not child:
                    continue

                text = child.get_text(strip=True) if hasattr(child, "get_text") else None
                if text:
                    mapping[str(card_id)] = text
            except Exception:
                continue

        return mapping

    @staticmethod
    def extract_links_by_regex_patterns(
        html: str, patterns: List[str], base_url: Optional[str] = None, **kwargs
    ) -> List[str]:
        """
        Extract links whose href attribute matches any of the provided regex patterns.

        Args:
            html: HTML string to parse
            patterns: List of regex patterns to match against href attributes
            base_url: Optional base URL for constructing absolute URLs
            **kwargs: Additional arguments for compatibility (e.g., logger_context)

        Returns:
            List[str]: List of unique matching URLs

        Raises:
            Exception: If parsing fails
        """
        import re

        soup = HtmlScraper._parse_html(html)
        links = soup.find_all("a", href=True)
        hrefs = set()  # Use set to avoid duplicates

        # Compile patterns for efficiency
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

        for link in links:
            href = HtmlScraper._safe_get_href(link)
            if href:
                # Check if href matches any of the patterns
                if any(pattern.match(href) for pattern in compiled_patterns):
                    if base_url:
                        hrefs.add(HtmlScraper._build_absolute_url(href, base_url))
                    else:
                        hrefs.add(href)

        return list(hrefs)

    @staticmethod
    def find_elements_with_patterns(html: str, tag: str, attrs: Optional[dict] = None) -> List[Any]:
        """
        Find elements matching a tag and optional attribute patterns.

        Supports regex pattern matching for attribute values.

        Args:
            html: HTML string to parse
            tag: HTML tag to search for
            attrs: Optional dictionary of attributes to match. Values can be regex patterns.

        Returns:
            List[Any]: List of matching elements

        Raises:
            Exception: If parsing fails
        """
        soup = HtmlScraper._parse_html(html)

        if not attrs:
            return soup.find_all(tag)

        # Handle regex patterns in attributes
        search_attrs = {}
        for key, value in attrs.items():
            if hasattr(value, "search"):  # Check if it's a regex pattern
                search_attrs[key] = value
            else:
                search_attrs[key] = value

        return soup.find_all(tag, attrs=search_attrs)

    @staticmethod
    def find_parent_containers_by_child_class(html: str, child_tag: str, child_class: str) -> List[Any]:
        """
        Find parent containers by locating child elements with a specific class.

        Args:
            html: HTML content to parse
            child_tag: HTML tag of the child element (e.g., "div", "span")
            child_class: CSS class of the child element to find

        Returns:
            List of parent container elements
        """
        soup = HtmlScraper._parse_html(html)
        child_elements = soup.find_all(child_tag, class_=child_class)

        parent_containers = []
        for element in child_elements:
            if element.parent:
                parent_containers.append(element.parent)

        return parent_containers

    @staticmethod
    def extract_nested_link_href(container: Any, wrapper_class: str, link_tag: str = "a") -> Optional[str]:
        """
        Extract href from a link nested within a container with a specific class.

        Args:
            container: Parent container element
            wrapper_class: CSS class of the wrapper element containing the link
            link_tag: HTML tag of the link element (default: "a")

        Returns:
            Link href or None if not found
        """
        if not hasattr(container, "find"):
            return None

        wrapper_div = container.find("div", class_=wrapper_class)
        if not wrapper_div:
            return None

        link_elem = wrapper_div.find(link_tag)
        if not link_elem:
            return None

        href_attr = link_elem.get("href")
        return str(href_attr) if href_attr and isinstance(href_attr, (str, int, float)) else None

    @staticmethod
    def extract_text_from_links_by_href_pattern(container: Any, href_pattern: str) -> List[str]:
        """
        Extract text content from links whose href contains a specific pattern.

        Args:
            container: Container element to search within
            href_pattern: Text pattern to match in href attributes

        Returns:
            List of text content from matching links (duplicates removed)
        """
        text_list = []

        if not hasattr(container, "find_all"):
            return text_list

        # Look for links with href containing the pattern
        matching_links = container.find_all("a", href=lambda href: bool(href and href_pattern in href))

        for link in matching_links:
            text = link.get_text(strip=True)
            if text and text not in text_list:  # Avoid duplicates
                text_list.append(text)

        return text_list

    @staticmethod
    def extract_links_by_attribute_within_container(
        html: str,
        container_tag: Optional[str] = None,
        container_class: Optional[str] = None,
        link_tag: str = "a",
        href_required: bool = True,
        attr_name: Optional[str] = None,
        attr_includes: Optional[List[str]] = None,
        base_url: Optional[str] = None,
    ) -> List[str]:
        """
        Extract link hrefs within optional container constraints where a link attribute contains target text.

        Args:
            html: HTML content to parse
            container_tag: Optional tag name of the container to scope the search (e.g., "div")
            container_class: Optional CSS class of the container to scope the search (e.g., "button")
            link_tag: Link element tag to search for (default: "a")
            href_required: Whether to require an href attribute on the link (default: True)
            attr_name: Optional attribute name on the link to filter by (e.g., "aria-label")
            attr_includes: Optional list of substrings; if provided, the attribute's value must include
                           at least one of these (case-insensitive)
            base_url: Optional base URL for constructing absolute URLs

        Returns:
            List of (optionally absolute) hrefs matching the criteria (deduplicated, order preserved)
        """
        soup = HtmlScraper._parse_html(html)

        # Determine search scope
        if container_tag:
            containers = soup.find_all(container_tag, class_=container_class) if container_class else soup.find_all(container_tag)
        else:
            containers = [soup]

        # Normalize include filters
        includes = [s.lower() for s in (attr_includes or [])]

        results: List[str] = []
        seen = set()

        for container in containers:
            if not hasattr(container, "find_all"):
                continue

            # Build attribute filter for the "find_all" call
            attrs_filter = {}
            if attr_name:
                # Require the attribute to be present if we're going to test its contents later
                attrs_filter[attr_name] = True

            # Note: BeautifulSoup's href=True filter only checks presence; we'll safely read it via helper
            # Pylance: container is a bs4 element at runtime; suppress dynamic attr warning
            link_candidates = container.find_all(  # type: ignore[attr-defined]
                link_tag, href=True if href_required else False, attrs=attrs_filter
            )

            for link in link_candidates:
                # Attribute content filter (if configured)
                if attr_name and includes:
                    attr_val_raw = None
                    if hasattr(link, "get"):
                        try:
                            attr_val_raw = link.get(attr_name)  # type: ignore[call-arg]
                        except Exception:
                            attr_val_raw = None

                    # Normalize to string for comparison
                    if isinstance(attr_val_raw, list):
                        joined = " ".join([str(x) for x in attr_val_raw])
                        attr_val = joined.strip().lower()
                    else:
                        attr_val = (str(attr_val_raw) if attr_val_raw is not None else "").strip().lower()

                    if not any(s in attr_val for s in includes):
                        continue

                href = HtmlScraper._safe_get_href(link)
                if not href:
                    continue

                url = HtmlScraper._build_absolute_url(href, base_url) if base_url else href
                if url not in seen:
                    seen.add(url)
                    results.append(url)

        return results

    @staticmethod
    def extract_price_offers_from_containers(
        html: str,
        container_selector: str,
        term_selector: str,
        price_selector: str,
        fee_selector: Optional[str] = None,
    ) -> List[dict]:
        """
        Extract offer-like data (name, price, optional fee breakdown) from repeated containers.

        Args:
            html: HTML content to parse
            container_selector: CSS selector for each offer container
            term_selector: CSS selector (relative to container) for the offer name element
            price_selector: CSS selector (relative to container) for the price element
            fee_selector: Optional CSS selector (relative to container) for the fee breakdown element

        Returns:
            List of dicts like {"name": str, "price": float, "feeBreakdown": str?, "basePrice": float?, "fees": float?}
        """
        soup = HtmlScraper._parse_html(html)
        containers = soup.select(container_selector)

        offers: List[dict] = []

        for c in containers:
            try:
                term_el = c.select_one(term_selector)
                price_el = c.select_one(price_selector)
                if not term_el or not price_el:
                    continue

                name_raw = term_el.get_text(strip=True)
                name = name_raw.split("|")[0].strip() if "|" in name_raw else name_raw

                price_text = price_el.get_text(strip=True)
                try:
                    price_val = float(price_text.replace("$", "").replace(",", ""))
                except Exception:
                    continue

                offer: dict = {"name": name, "price": price_val}

                if fee_selector:
                    fee_el = c.select_one(fee_selector)
                    if fee_el:
                        fee_text = fee_el.get_text(strip=True)
                        offer["feeBreakdown"] = fee_text
                        # Try to parse fee breakdown like "($15.00 + $4.04 fees)"
                        m = re.search(r"\(\$?([\d.,]+)\s*\+\s*\$?([\d.,]+)", fee_text)
                        if m:
                            try:
                                base_price = float(m.group(1).replace(",", ""))
                                fees = float(m.group(2).replace(",", ""))
                                offer.update({"basePrice": base_price, "fees": fees})
                            except Exception:
                                pass

                offers.append(offer)
            except Exception:
                # Skip malformed containers
                continue

        return offers
