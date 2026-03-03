"""Email notifications from metrics snapshots."""

from __future__ import annotations
from typing import Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.core.models.metrics import ScrapingMetricsSnapshot


class MetricsReporter:
    def send_session_email(self, snapshot: Optional[ScrapingMetricsSnapshot]) -> bool:
        if not snapshot:
            Logger.warn("No metrics session found for email reporting")
            return False
        try:
            payload = snapshot.to_json_dict()
            from laughtrack.infrastructure.email.service import EmailService
            sent = EmailService.send_scraping_session_summary(payload)
            if sent:
                Logger.info("Metrics email report sent successfully")
            else:
                Logger.error("Failed to send metrics email report")
            return sent
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Error sending metrics email: {e}")
            return False

__all__ = ["MetricsReporter"]
