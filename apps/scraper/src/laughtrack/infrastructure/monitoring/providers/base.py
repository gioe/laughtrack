"""Provider abstraction for monitoring service generalization."""

from __future__ import annotations

from typing import Any, Optional, Protocol

from laughtrack.infrastructure.monitoring.alert_system import BaseAlertSystem
from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig


class FailureMonitorProtocol(Protocol):
    """Minimal interface expected by MonitoringService from a failure monitor."""

    window_minutes: int

    def export_metrics(self) -> dict:
        ...

    def get_current_stats(self, force_refresh: bool = False) -> Any:
        ...

    def get_failure_rate(self, minutes: Optional[int] = None) -> float:
        ...

    def get_failure_pattern(self, minutes: int) -> dict:
        ...

    # Optional capability; providers can no-op/return False
    def is_cookie_issue_detected(self, minutes: int = 30) -> bool:
        ...


class MonitoringProvider(Protocol):
    """Provider responsible for constructing monitoring primitives for a domain."""

    def create_failure_monitor(self, config: MonitoringConfig) -> FailureMonitorProtocol:
        ...

    def create_alert_system(
        self,
        monitor: FailureMonitorProtocol,
        channels: list,
        config: MonitoringConfig,
    ) -> Optional[BaseAlertSystem]:
        ...
