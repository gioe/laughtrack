from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from laughtrack.foundation.models.types import JSONDict


class AlertSeverity(Enum):
    """Severity levels for alerts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert."""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    timestamp: datetime
    source: str
    metadata: JSONDict
    resolved: bool = False
    resolved_at: Optional[datetime] = None
