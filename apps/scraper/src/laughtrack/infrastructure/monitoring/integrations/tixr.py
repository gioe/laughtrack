"""Tixr-specific client monitoring integration."""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseClientMonitoringIntegration


class TixrClientMonitoringIntegration(BaseClientMonitoringIntegration):
    provider_key = "tixr"

    def get_failure_monitor(self, club: Optional[Any] = None) -> Optional[Any]:
        try:
            return self.monitoring_service.get_failure_monitor()
        except Exception:
            return None

    def create_monitored_client(self, club: Any, **kwargs) -> Any:
        # Import client lazily to avoid import-time cycles
        from laughtrack.core.clients.tixr.client import TixrClient
        # Current TixrClient does not accept a monitor in its constructor.
        # Monitoring is provided separately via the failure monitor accessor.
        return TixrClient(club, **kwargs)
