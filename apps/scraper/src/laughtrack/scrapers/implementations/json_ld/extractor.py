"""JSON-LD data extraction utilities."""

from typing import Any, Iterable, List, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.core.entities.event.event import JsonLdEvent


class EventExtractor:
    """Utility class for extracting JSON-LD event dictionaries from HTML content."""

    @staticmethod
    def extract_events(
        html_content: str,
        *,
        same_as_override: str | None = None,
        base_url: str | None = None,
        skip_parent_events_with_subevents: bool = False,
    ) -> List[JsonLdEvent]:
        """
        Extract JSON-LD data from HTML content.

        Args:
            html_content: HTML content to parse
            same_as_override: Canonical detail-page URL supplied as the event url
                for blocks that omit one.
            base_url: The URL the HTML was fetched from. When provided, relative
                event/offer ``url`` values (e.g. mynorthtickets emits
                ``"/events/..."``) are resolved against it before validation, so
                events on sites that emit root-relative URLs are not dropped for
                "must be a valid URL format" (TASK-3513).

        Returns:
            List of Event dictionaries found in the HTML (all objects or events only)
        """
        microdata_events = EventExtractor._extract_microdata_events(
            html_content,
            url_fallback=same_as_override,
        )

        # Use the HtmlScraper utility method to extract JSON-LD data
        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)

        if not script_contents:
            return EventExtractor._events_from_dicts(
                microdata_events,
                same_as_override=same_as_override,
                source_label="microdata",
                base_url=base_url,
            )

        json_objects = JSONUtils.parse_json_ld_contents(script_contents)
        if not json_objects:
            return EventExtractor._events_from_dicts(
                microdata_events,
                same_as_override=same_as_override,
                source_label="microdata",
                base_url=base_url,
            )

        # For non-event-only extraction, return all JSON-LD objects that look like events
        json_ld_events = EventExtractor._extract_events_from_data(
            json_objects,
            same_as_override=same_as_override,
            base_url=base_url,
            skip_parent_events_with_subevents=skip_parent_events_with_subevents,
        )
        if not microdata_events:
            return json_ld_events

        microdata_parsed = EventExtractor._events_from_dicts(
            microdata_events,
            same_as_override=same_as_override,
            source_label="microdata",
            base_url=base_url,
        )
        return EventExtractor._dedupe_events(json_ld_events + microdata_parsed)

    @staticmethod
    def extract_min_offer_price(html_content: str) -> float | None:
        """Lowest per-tier offer price across the page's JSON-LD Event blocks.

        Reads offers from the raw event dicts rather than through the
        JsonLdEvent factory: ticket-page JSON-LD frequently omits the model's
        required url/name/startDate fields (SimpleTix's array-of-showtimes
        block has no url; ThunderTix detail pages omit startDate), and a price
        must survive that. Tolerates both offer shapes (single dict and list
        of per-tier Offers) and both price keys via the Offer parser's
        lowPrice/highPrice fallback for offers that omit ``price``
        (AggregateOffer ranges, including mislabelled ones). Returns the lowest positive
        price; 0.0 only when every parseable offer is an explicit zero
        (proven-free, e.g. RSVP-only open mics); None when no parseable offers
        exist. A zero tier alongside paid tiers is treated as a
        comp/placeholder, not the show's price.
        """
        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)
        if not script_contents:
            return None
        json_objects = JSONUtils.parse_json_ld_contents(script_contents)

        prices = []
        for item in json_objects or []:
            for event in EventExtractor._extract_events_recursively(item):
                try:
                    offers = JsonLdEvent._parse_offers(event)
                except Exception:
                    continue
                for offer in offers:
                    try:
                        prices.append(float(offer.price))
                    except (TypeError, ValueError):
                        continue

        positive = [p for p in prices if p > 0]
        if positive:
            return min(positive)
        if prices:
            return 0.0
        return None

    @staticmethod
    def extract_event_field_values(html_content: str, field_path: str) -> Set[str]:
        """Extract string values from a JSON-LD field on Event objects.

        ``field_path`` supports dotted lookup for nested dictionaries. If the
        resolved value is a list, string members are returned.
        """
        return EventExtractor.extract_typed_field_values(
            html_content,
            object_type="Event",
            field_path=field_path,
        )

    @staticmethod
    def extract_typed_field_values(
        html_content: str,
        *,
        object_type: str,
        field_path: str,
    ) -> Set[str]:
        """Extract string values from JSON-LD objects of ``object_type``.

        ``field_path`` supports dotted dictionary lookup and ``[]`` list
        traversal segments, such as ``mainEntity.itemListElement[].url``.
        The special ``object_type="Event"`` path preserves the existing
        recursive Event/ComedyEvent matching semantics.
        """
        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)
        if not script_contents:
            return set()

        json_objects = JSONUtils.parse_json_ld_contents(script_contents)
        if not json_objects:
            return set()

        values: Set[str] = set()
        for item in json_objects:
            for obj in EventExtractor._extract_objects_by_type(item, object_type):
                for value in EventExtractor._field_values(obj, field_path):
                    values.add(value)
        return values

    @staticmethod
    def _field_values(obj: dict[str, Any], field_path: str) -> List[str]:
        values: Iterable[Any] = [obj]
        for raw_part in field_path.split("."):
            traverse_list = raw_part.endswith("[]")
            part = raw_part[:-2] if traverse_list else raw_part
            next_values: list[Any] = []

            for value in values:
                if isinstance(value, list) and not traverse_list:
                    candidates = value
                else:
                    candidates = [value]

                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    resolved = candidate.get(part)
                    if traverse_list:
                        if isinstance(resolved, list):
                            next_values.extend(resolved)
                    else:
                        next_values.append(resolved)

            values = next_values

        strings: list[str] = []
        for value in values:
            if isinstance(value, str) and value:
                strings.append(value)
            elif isinstance(value, list):
                strings.extend(item for item in value if isinstance(item, str) and item)
        return strings

    @staticmethod
    def _extract_objects_by_type(obj: Any, object_type: str) -> list[dict[str, Any]]:
        if object_type.lower() == "event":
            return EventExtractor._extract_events_recursively(obj)
        return EventExtractor._extract_objects_by_exact_type_recursively(obj, object_type)

    @staticmethod
    def _extract_objects_by_exact_type_recursively(obj: Any, object_type: str) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        if isinstance(obj, list):
            for item in obj:
                matches.extend(EventExtractor._extract_objects_by_exact_type_recursively(item, object_type))
        elif isinstance(obj, dict):
            if EventExtractor._json_ld_type_matches(obj.get("@type"), object_type):
                matches.append(obj)
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    matches.extend(EventExtractor._extract_objects_by_exact_type_recursively(value, object_type))
        return matches

    @staticmethod
    def _json_ld_type_matches(raw_type: Any, expected_type: str) -> bool:
        expected = expected_type.lower()
        if isinstance(raw_type, list):
            return any(isinstance(item, str) and item.lower() == expected for item in raw_type)
        return isinstance(raw_type, str) and raw_type.lower() == expected

    @staticmethod
    def _extract_events_recursively(
        obj,
        processed_keys=None,
        *,
        skip_parent_events_with_subevents: bool = False,
    ):
        """
        Recursively extract event dicts from a JSON-LD object or structure.

        Args:
            obj: The object to search for events (dict, list, or other)
            processed_keys: Set of keys already processed to avoid infinite recursion

        Returns:
            List of event dictionaries found in the object
        """
        if processed_keys is None:
            processed_keys = set()

        events = []
        if isinstance(obj, list):
            for item in obj:
                events.extend(
                    EventExtractor._extract_events_recursively(
                        item,
                        processed_keys,
                        skip_parent_events_with_subevents=skip_parent_events_with_subevents,
                    )
                )
        elif isinstance(obj, dict):
            # If this dict looks like an event, add it (case-insensitive)
            event_type = obj.get("@type", "")
            if isinstance(event_type, list):
                event_type = " ".join(event_type)
            event_type_lower = event_type.lower()

            # Only match actual event types, not event-containing words
            is_event = event_type_lower in ("event", "comedyevent") or (
                "event" in event_type_lower and event_type_lower not in ("eventseries", "eventlisting", "eventschedule")
            )
            has_subevents = any(key in obj for key in ("subEvent", "subEvents"))
            if is_event and not (skip_parent_events_with_subevents and has_subevents):
                events.append(obj)

            # Special handling for Events key to avoid double-processing
            if "Events" in obj:
                events.extend(
                    EventExtractor._extract_events_recursively(
                        obj["Events"],
                        processed_keys,
                        skip_parent_events_with_subevents=skip_parent_events_with_subevents,
                    )
                )
                processed_keys.add("Events")

            # Check other values, but skip already processed keys
            for key, value in obj.items():
                if key not in processed_keys and isinstance(value, (dict, list)):
                    events.extend(
                        EventExtractor._extract_events_recursively(
                            value,
                            processed_keys,
                            skip_parent_events_with_subevents=skip_parent_events_with_subevents,
                        )
                    )

        return events

    @staticmethod
    def _extract_events_from_data(
        json_ld_data: List[JSONDict],
        *,
        same_as_override: str | None = None,
        base_url: str | None = None,
        skip_parent_events_with_subevents: bool = False,
    ) -> List[JsonLdEvent]:
        """
        Extract events from already-parsed JSON-LD data using recursive logic.

        Args:
            json_ld_data: List of already-parsed JSON-LD objects
            base_url: see :meth:`extract_events`.

        Returns:
            List of Event dictionaries found in the data
        """
        all_events = []
        for item in json_ld_data:
            all_events.extend(
                EventExtractor._extract_events_recursively(
                    item,
                    skip_parent_events_with_subevents=skip_parent_events_with_subevents,
                )
            )

        return EventExtractor._events_from_dicts(
            all_events,
            same_as_override=same_as_override,
            source_label="JSON-LD",
            base_url=base_url,
        )

    @staticmethod
    def _resolve_relative_event_urls(event: dict[str, Any], base_url: str) -> dict[str, Any]:
        """Return a copy of ``event`` with root-relative ``url``/offer urls made absolute.

        Some venues' JSON-LD emits root-relative event URLs (e.g. mynorthtickets
        renders ``"url": "/events/<slug>"``). Those reach Show validation as
        ``show_page_url`` / ticket ``purchase_url`` and are rejected for "must be
        a valid URL format", silently dropping otherwise-valid upcoming shows
        (TASK-3513, Traverse City Comedy Club 1058). Resolve them against the
        page they were fetched from. Absolute URLs (with a netloc) are left
        untouched, so this is a no-op for the common case. The event dict is
        copied before mutation so the caller's dict and the dedup key are intact.
        """
        def _abs(value: Any) -> Any:
            if isinstance(value, str) and value and not urlparse(value).netloc:
                return urljoin(base_url, value)
            return value

        patched = dict(event)
        if "url" in patched:
            patched["url"] = _abs(patched["url"])
        offers = patched.get("offers")
        if isinstance(offers, dict) and "url" in offers:
            patched["offers"] = {**offers, "url": _abs(offers.get("url"))}
        elif isinstance(offers, list):
            patched["offers"] = [
                {**o, "url": _abs(o.get("url"))} if isinstance(o, dict) and "url" in o else o
                for o in offers
            ]
        return patched

    @staticmethod
    def _events_from_dicts(
        raw_events: list[dict[str, Any]],
        *,
        same_as_override: str | None = None,
        source_label: str,
        base_url: str | None = None,
    ) -> List[JsonLdEvent]:
        # Deduplicate events by their string representation
        seen = set()
        unique_events = []
        for event in raw_events:
            event_str = str(sorted(event.items()))
            if event_str in seen:
                continue

            seen.add(event_str)
            # Build using the model factory to tolerate extra keys like '@context'
            try:
                # Resolve root-relative event/offer URLs against the fetched page
                # before validation so they don't fail Show's URL-format check
                # (TASK-3513). No-op when base_url is absent or the URL is already
                # absolute.
                if base_url:
                    event = EventExtractor._resolve_relative_event_urls(event, base_url)
                # When the canonical detail-page URL is known
                # (set_same_as_to_detail_url), supply it as the event url for
                # blocks that omit one. Some detail-page Event JSON-LD — e.g.
                # city/government arts calendars like pompanobeacharts.org —
                # carries name/startDate/location but no `url`, and
                # JsonLdEvent.from_json_ld requires url, so the event would be
                # dropped even though the scraper fetched its canonical page.
                # Copy before mutating so the caller's dict (and the dedup key
                # already computed above) is untouched; never overrides a real url.
                if same_as_override and not event.get("url"):
                    event = {**event, "url": same_as_override}
                parsed_event = JsonLdEvent.from_json_ld(event)
                if same_as_override:
                    parsed_event.same_as = same_as_override
                unique_events.append(parsed_event)
            except Exception as exc:
                # A JSON-LD Event block that fails validation (e.g. JsonLdEvent
                # requires url and raises ValueError when it's missing) is
                # dropped here. Without a signal, a vendor silently dropping a
                # required field looks identical to a page with no JSON-LD at
                # all (TASK-2838). Log enough to diagnose from nightly logs:
                # the event's @type/name and the failing exception.
                Logger.debug(
                    f"Skipping unparseable {source_label} event "
                    f"(@type={event.get('@type')!r}, name={event.get('name')!r}): "
                    f"{type(exc).__name__}: {exc}"
                )
                continue

        return unique_events

    @staticmethod
    def _dedupe_events(events: list[JsonLdEvent]) -> list[JsonLdEvent]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[JsonLdEvent] = []
        for event in events:
            key = (
                event.name or "",
                event.start_date.isoformat() if event.start_date else "",
                event.same_as or event.url or "",
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(event)
        return unique

    @staticmethod
    def _extract_microdata_events(
        html_content: str,
        *,
        url_fallback: str | None = None,
    ) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html_content or "", "html.parser")
        events: list[dict[str, Any]] = []
        for scope in soup.find_all(attrs={"itemscope": True}):
            if not isinstance(scope, Tag):
                continue
            if not EventExtractor._itemtype_matches(scope, "Event"):
                continue

            raw = EventExtractor._microdata_event(scope, url_fallback=url_fallback)
            if raw:
                events.append(raw)
        return events

    @staticmethod
    def _microdata_event(scope: Tag, *, url_fallback: str | None = None) -> dict[str, Any] | None:
        name = EventExtractor._microdata_value(scope, "name")
        start = EventExtractor._microdata_value(scope, "startDate")
        url = EventExtractor._microdata_value(scope, "url")
        description = EventExtractor._microdata_value(scope, "description") or ""
        location = EventExtractor._microdata_location(scope)
        offers = EventExtractor._microdata_offers(scope)

        if not url and offers:
            url = offers[0].get("url")
        if not url:
            url = url_fallback

        if not name or not start or not url:
            return None

        return {
            "@type": "Event",
            "name": name,
            "startDate": start,
            "url": url,
            "description": description,
            "location": location,
            "offers": offers,
        }

    @staticmethod
    def _microdata_location(scope: Tag) -> dict[str, Any]:
        location_scope = EventExtractor._microdata_scope(scope, "location")
        if location_scope is None:
            return {"@type": "Place", "name": EventExtractor._microdata_value(scope, "location") or ""}

        address_scope = EventExtractor._microdata_scope(location_scope, "address")
        address: dict[str, str] | str
        if address_scope is not None:
            address = {
                "@type": "PostalAddress",
                "streetAddress": EventExtractor._microdata_value(address_scope, "streetAddress") or "",
                "addressLocality": EventExtractor._microdata_value(address_scope, "addressLocality") or "",
                "addressRegion": EventExtractor._microdata_value(address_scope, "addressRegion") or "",
                "postalCode": EventExtractor._microdata_value(address_scope, "postalCode") or "",
                "addressCountry": EventExtractor._microdata_value(address_scope, "addressCountry") or "",
            }
        else:
            address = EventExtractor._microdata_value(location_scope, "address") or ""

        return {
            "@type": "Place",
            "name": EventExtractor._microdata_value(location_scope, "name") or "",
            "address": address,
        }

    @staticmethod
    def _microdata_offers(scope: Tag) -> list[dict[str, str]]:
        offers: list[dict[str, str]] = []
        for offer_scope in EventExtractor._microdata_scopes(scope, "offers"):
            offer = {
                "@type": "Offer",
                "url": EventExtractor._microdata_value(offer_scope, "url") or "",
                "price": EventExtractor._microdata_value(offer_scope, "price") or "",
                "priceCurrency": EventExtractor._microdata_value(offer_scope, "priceCurrency") or "",
                "availability": EventExtractor._microdata_value(offer_scope, "availability") or "",
            }
            if any(offer.values()):
                offers.append(offer)
        return offers

    @staticmethod
    def _microdata_scope(scope: Tag, prop: str) -> Tag | None:
        scopes = EventExtractor._microdata_scopes(scope, prop)
        return scopes[0] if scopes else None

    @staticmethod
    def _microdata_scopes(scope: Tag, prop: str) -> list[Tag]:
        return [
            element
            for element in EventExtractor._scoped_prop_elements(scope, prop)
            if element.has_attr("itemscope")
        ]

    @staticmethod
    def _microdata_value(scope: Tag, prop: str) -> str | None:
        element = next(iter(EventExtractor._scoped_prop_elements(scope, prop)), None)
        if not element:
            return None
        for attr in ("content", "href", "src", "datetime"):
            value = element.get(attr)
            if isinstance(value, str) and value.strip():
                return value.strip()
        text = element.get_text(" ", strip=True)
        return text or None

    @staticmethod
    def _scoped_prop_elements(scope: Tag, prop: str) -> list[Tag]:
        elements: list[Tag] = []
        for element in scope.find_all(attrs={"itemprop": True}):
            if not isinstance(element, Tag):
                continue
            props = element.get("itemprop")
            prop_values = props if isinstance(props, list) else str(props).split()
            if prop not in prop_values:
                continue
            if not EventExtractor._belongs_to_scope(element, scope):
                continue
            elements.append(element)
        return elements

    @staticmethod
    def _belongs_to_scope(element: Tag, scope: Tag) -> bool:
        parent = element.parent
        while isinstance(parent, Tag) and parent is not scope:
            if parent.has_attr("itemscope"):
                return False
            parent = parent.parent
        return True

    @staticmethod
    def _itemtype_matches(scope: Tag, expected_type: str) -> bool:
        raw = scope.get("itemtype")
        values = raw if isinstance(raw, list) else str(raw or "").split()
        expected = expected_type.lower()
        for value in values:
            normalized = value.rstrip("/").rsplit("/", 1)[-1].lower()
            if normalized == expected or normalized == f"comedy{expected}":
                return True
        return False
