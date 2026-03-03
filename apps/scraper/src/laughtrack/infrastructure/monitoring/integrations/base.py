"""Base interfaces for provider-specific client monitoring integrations."""

from __future__ import annotations

import abc
from typing import Any, Optional

from laughtrack.infrastructure.monitoring.factory import MonitoringFactory


class BaseClientMonitoringIntegration(abc.ABC):
    """
    Base class for client monitoring integration per provider.

    Subclasses should hide provider-specific types behind runtime imports
    to avoid import-time coupling and potential circular imports.
    """

    provider_key: str = "base"

    def __init__(self):
        # Lazy-create the monitoring service once per integration instance
        self._monitoring_service = None

    @property
    def monitoring_service(self):
        if self._monitoring_service is None:
            self._monitoring_service = MonitoringFactory.create_monitoring_components()
        return self._monitoring_service

    @abc.abstractmethod
    def get_failure_monitor(self, club: Optional[Any] = None) -> Optional[Any]:
        """Return a provider-specific failure monitor instance or None."""

    @abc.abstractmethod
    def create_monitored_client(self, club: Any, **kwargs) -> Any:
        """Return a provider-specific client wired with monitoring if available."""

    def is_monitoring_available(self) -> bool:
        try:
            return self.get_failure_monitor() is not None
        except Exception:
            return False

    def get_monitoring_status(self) -> dict:
        try:
            monitor = self.get_failure_monitor()
            if not monitor:
                return {"available": False, "reason": "Monitor not available"}
            stats = monitor.get_current_stats()
            # Access common attributes; provider-specific fields can extend this in subclasses
            return {
                "available": True,
                "total_requests": getattr(stats, "total_requests", None),
                "total_failures": getattr(stats, "total_failures", None),
                "current_failure_rate": getattr(stats, "failure_rate", None),
                "monitoring_window_minutes": getattr(monitor, "window_minutes", None),
            }
        except Exception as e:
            return {"available": False, "reason": f"Error: {e}"}
