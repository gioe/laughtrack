"""The Setup SF event extraction from Google Sheets CSV."""

import csv
import io
from datetime import date
from typing import List

from laughtrack.core.entities.event.setup_sf import SetupSFEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class SetupSFExtractor:
    """Converts raw Google Sheets CSV text into SetupSFEvent objects."""

    @staticmethod
    def extract_events(csv_text: str, today: date | None = None) -> List[SetupSFEvent]:
        """Extract SetupSFEvent objects from the published Google Sheets CSV.

        Args:
            csv_text: Raw CSV text from the Google Sheets publish URL.
            today: Filter cutoff — rows with date < today are skipped.
                   Defaults to date.today().

        Returns:
            List of SetupSFEvent objects for upcoming shows.
        """
        if today is None:
            today = date.today()

        # Strip UTF-8 BOM if present — Google Sheets can export BOM-prefixed CSV,
        # which would corrupt the first column header (e.g. '\ufeffdate' ≠ 'date').
        csv_text = csv_text.lstrip('\ufeff')

        events: List[SetupSFEvent] = []
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            for row in reader:
                try:
                    event = SetupSFExtractor._parse_row(row, today)
                    if event is not None:
                        events.append(event)
                except Exception as e:
                    Logger.warn(f"SetupSFExtractor: skipping row due to error: {e}")
        except Exception as e:
            Logger.error(f"SetupSFExtractor: failed to parse CSV: {e}")
        return events

    @staticmethod
    def _parse_row(row: dict, today: date) -> SetupSFEvent | None:
        """Parse a single CSV row into a SetupSFEvent, or None to skip."""
        raw_date = (row.get("date") or "").strip()
        raw_time = (row.get("time") or "").strip()
        title = (row.get("title") or "").strip()
        venue = (row.get("venue") or "").strip()
        ticket_url = (row.get("ticket_url") or "").strip()

        if not raw_date or not raw_time or not title or not venue or not ticket_url:
            return None

        try:
            event_date = date.fromisoformat(raw_date)
        except ValueError:
            return None

        if event_date < today:
            return None

        sold_out_raw = (row.get("sold_out") or "").strip().lower()
        sold_out = sold_out_raw in ("true", "1", "yes", "sold out")

        return SetupSFEvent(
            date=raw_date,
            time=raw_time,
            title=title,
            venue=venue,
            ticket_url=ticket_url,
            sold_out=sold_out,
        )
