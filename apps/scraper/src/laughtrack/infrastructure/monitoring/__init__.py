"""
Streamlined Monitoring System

This package provides comprehensive monitoring and alerting for API failures,
with a focus on simplicity and configuration-driven setup.

Key Components:
- MonitoringService: Centralized monitoring with self-configuration
- TixrFailureMonitor: Tracks and classifies API failures
- Alert System: Multi-channel alerting (email, Slack, webhooks)
- MonitoringConfig: Configuration management with environment variable support
- MonitoringFactory: Simplified factory for creating configured components

Quick Start:
```python
from laughtrack.infrastructure.monitoring import (
    MonitoringConfig,
    MonitoringService,
    get_monitoring_service
)

# Simple setup with defaults
monitoring_service = MonitoringService()

# Setup with configuration
config = MonitoringConfig.from_env()
monitoring_service = MonitoringService(config=config)

# Or use global service
monitoring_service = get_monitoring_service()

# Integrate with TixrClient
tixr_client = TixrClient(
    club=club,
    failure_monitor=monitoring_service.get_failure_monitor()
)
```

Configuration-Driven Setup:
The monitoring system is now configuration-driven. Set environment variables
or create a MonitoringConfig object to configure alert channels:

```bash
# Email alerts
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=alerts@example.com
SMTP_PASSWORD=your_password
EMAIL_FROM=alerts@example.com
ALERT_RECIPIENTS=admin@example.com,ops@example.com

# Slack alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Webhook alerts
MONITORING_WEBHOOK_URL=https://your-webhook.com/alerts
```
"""

from ..config.monitoring_config import MonitoringConfig
from .alert_system import (
    Alert,
    AlertChannel,
    AlertSeverity,
    EmailAlertChannel,
    SlackAlertChannel,
    WebhookAlertChannel,
)
from .client_integration import (
    ClientMonitoringIntegration,
    create_monitored_tixr_client,
    get_tixr_failure_monitor,
    is_monitoring_available,
)
from .factory import MonitoringFactory

__all__ = [
    # Core monitoring - simplified interface (access via factory to avoid cycles)
    # Configuration
    "MonitoringConfig",
    "MonitoringFactory",
    # Failure monitoring
    "AlertSeverity",
    "Alert",
    "AlertChannel",
    "EmailAlertChannel",
    "SlackAlertChannel",
    "WebhookAlertChannel",
    # Client integration utilities
    "ClientMonitoringIntegration",
    "create_monitored_tixr_client",
    "get_tixr_failure_monitor",
    "is_monitoring_available",
]
