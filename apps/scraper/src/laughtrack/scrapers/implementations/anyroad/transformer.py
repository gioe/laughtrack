"""AnyRoad event -> Show transformer.

AnyRoad experiences are normalized into ``JsonLdEvent`` by the extractor. The
only customization over the default ``DataTransformer`` is mapping the
experience's free-text ``locationInfo`` (carried as ``Place.name``) onto
``Show.room``.

Why room: AnyRoad's plugin *summary* feed reports a placeholder slot time
(every occurrence at the same nominal time), so the show identity key
``(club_id, date, room)`` would collapse distinct experiences that share a
date. Using the sub-venue string as the room keeps experiences at *different*
spaces distinct (and powers the club page's "Show Rooms" grouping with a real
location rather than a synthetic token). Experiences at the *same* sub-venue on
the same date still collapse — an inherent limit of a feed with no real times,
surfaced by the dedup WARNING and documented in ``apps/scraper/SCRAPERS.md``.
"""

from typing import Optional

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class AnyRoadTransformer(DataTransformer[JsonLdEvent]):
    def transform_to_show(self, raw_data: ShowConvertible) -> Optional[Show]:
        show = super().transform_to_show(raw_data)
        if show is None:
            return None
        location = getattr(raw_data, "location", None)
        room = getattr(location, "name", "") if location else ""
        if room:
            show.room = room.strip()
        return show
