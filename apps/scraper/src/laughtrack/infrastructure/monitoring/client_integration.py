"""
Client integration utilities for monitoring.

This module centralizes how API clients wire up monitoring. It delegates
provider-specific details to integration subclasses to avoid hard-coding
types like TixrFailureMonitor in generic paths.
"""

import logging
from typing import Optional, Any

from laughtrack.infrastructure.monitoring.integrations.tixr import TixrClientMonitoringIntegration


class ClientMonitoringIntegration:
    """Utilities for integrating monitoring with API clients per provider."""

    _logger = logging.getLogger(__name__)
    _tixr: Optional[TixrClientMonitoringIntegration] = None

    @classmethod
    def _tixr_integration(cls) -> TixrClientMonitoringIntegration:
        if cls._tixr is None:
            cls._tixr = TixrClientMonitoringIntegration()
        return cls._tixr

    # Tixr-specific API
    @classmethod
    def get_tixr_failure_monitor(cls, club: Optional[Any] = None):
        return cls._tixr_integration().get_failure_monitor(club)

    @classmethod
    def create_monitored_tixr_client(cls, club: Any, **kwargs):
        try:
            return cls._tixr_integration().create_monitored_client(club, **kwargs)
        except Exception as e:
            cls._logger.warning(f"Failed to create TixrClient with monitoring: {e}")
            from laughtrack.core.clients.tixr.client import TixrClient

            return TixrClient(club, **kwargs)

    @classmethod
    def is_monitoring_available(cls) -> bool:
        return cls._tixr_integration().is_monitoring_available()

    @classmethod
    def get_monitoring_status(cls) -> dict:
        return cls._tixr_integration().get_monitoring_status()


# Convenience functions for backward compatibility and ease of use
def create_monitored_tixr_client(club: Any, **kwargs):
    """Convenience function to create a TixrClient with monitoring."""
    return ClientMonitoringIntegration.create_monitored_tixr_client(club, **kwargs)


def get_tixr_failure_monitor(club: Optional[Any] = None):
    """Convenience function to get a TixrFailureMonitor."""
    return ClientMonitoringIntegration.get_tixr_failure_monitor(club)


def is_monitoring_available() -> bool:
    """Convenience function to check if monitoring is available."""
    return ClientMonitoringIntegration.is_monitoring_available()
