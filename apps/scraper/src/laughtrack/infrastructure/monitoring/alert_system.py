"""Alert system module (barrel).

This module re-exports generic alert types, channels, and base system.
Provider-specific systems (e.g., Tixr) live in separate modules.
"""

from .alerts import Alert, AlertSeverity
from .channels import AlertChannel, EmailAlertChannel, SlackAlertChannel, WebhookAlertChannel
from .base_system import BaseAlertSystem

__all__ = [
    "Alert",
    "AlertSeverity",
    "AlertChannel",
    "EmailAlertChannel",
    "SlackAlertChannel",
    "WebhookAlertChannel",
    "BaseAlertSystem",
]
