"""
JSON-LD data transformation utilities.

This module provides utilities for transforming Event objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.event import JsonLdEvent
from copy import deepcopy
from html import unescape
from laughtrack.foundation.utilities.datetime import DateTimeUtils


class JsonLdTransformer(DataTransformer[JsonLdEvent]):
    def transform_to_show(self, raw_data):
        metadata = self.club.source_metadata or {}
        aliases = metadata.get("performer_aliases")
        prefixes = metadata.get("performer_prefixes")
        if aliases is not None or prefixes is not None:
            if aliases is not None and not isinstance(aliases, dict):
                raise ValueError("performer_aliases must be an object")
            if prefixes is not None and (not isinstance(prefixes, list) or
                    any(not isinstance(p, str) or not p.strip() for p in prefixes)):
                raise ValueError("performer_prefixes must be a list of nonempty strings")
            raw_data = deepcopy(raw_data)
            raw_data.name = unescape(raw_data.name)
            performers = []
            seen = set()
            for performer in raw_data.performers or []:
                name = " ".join(unescape(performer.name).split())
                for prefix in prefixes or []:
                    if name.startswith(prefix):
                        name = name[len(prefix):].strip()
                name = (aliases or {}).get(name, name)
                if name is None:
                    continue
                if not isinstance(name, str):
                    raise ValueError("performer alias targets must be strings or null")
                if name and name.casefold() not in seen:
                    performer.name = name
                    performers.append(performer)
                    seen.add(name.casefold())
            raw_data.performers = performers
        show = super().transform_to_show(raw_data)
        if show is not None and metadata.get("localize_naive_dates") is True and show.date.tzinfo is None:
            show.date = DateTimeUtils.venue_wall_clock_to_utc(show.date, self.club.timezone)
        if show is not None and metadata.get("infer_lineup_from_title") is False:
            show.infer_lineup_from_title = False
        return show
