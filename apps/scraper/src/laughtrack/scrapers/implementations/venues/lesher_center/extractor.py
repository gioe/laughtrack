"""Extract Lesher Center comedy events from Spektrix Link JSON."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from laughtrack.core.entities.event.lesher_center import LesherCenterEvent


class LesherCenterExtractor:
    """Parsers for the Lesher Center Spektrix Link event catalog."""

    COMEDY_GENRE = "comedy and improv"

    @classmethod
    def extract_events(cls, payload: object) -> List[LesherCenterEvent]:
        if not isinstance(payload, list):
            return []

        events: List[LesherCenterEvent] = []
        for item in payload:
            if not isinstance(item, dict) or not cls._is_comedy(item):
                continue

            title = cls._clean(item.get("name"))
            event_id = cls._clean(item.get("id"))
            if not title or not event_id:
                continue

            for date_time in cls._parse_instance_dates(item.get("availableInstanceDates")):
                events.append(
                    LesherCenterEvent(
                        title=title,
                        date_time=date_time,
                        event_id=event_id,
                        web_event_id=cls._clean(item.get("webEventId")),
                        genre=cls._clean(item.get("attribute_Genre")),
                        presenter=cls._clean(item.get("attribute_Presenter")),
                        description=cls._clean(item.get("description")),
                        sold_out=bool(item.get("isSoldOut")),
                    )
                )

        return events

    @classmethod
    def _is_comedy(cls, item: dict) -> bool:
        genre = cls._clean(item.get("attribute_Genre")).lower()
        return genre == cls.COMEDY_GENRE

    @staticmethod
    def _parse_instance_dates(value: object) -> Iterable[datetime]:
        if not isinstance(value, list):
            return []

        parsed = []
        for raw_date in value:
            try:
                parsed.append(datetime.fromisoformat(str(raw_date)))
            except ValueError:
                continue
        return parsed

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").replace("\xa0", " ").split())
