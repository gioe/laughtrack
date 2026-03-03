"""
Infrastructure utilities for operational concerns.

These utilities handle infrastructure, operational, and cross-cutting concerns
like error handling, HTTP clients, logging, task queues, and data processing.
"""

from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.infrastructure.database.template import BatchTemplateGenerator
from .email.utils import EmailUtils  # Importing EmailUtils for email-related operations
from .error_handling import ErrorHandler, RetryConfig
from .paginator.url_discovery import create_discovery_manager
from laughtrack.foundation.utilities.path.utils import PathUtils, ProjectPaths
from .rate_limiter import RateLimiter
from laughtrack.foundation.infrastructure.task_queue.models import Task, TaskQueue, TaskStatus
from .transformer.base import DataTransformer

__all__ = [
    "DataTransformer",
    "ErrorHandler",
    "HttpClient",
    "TaskQueue",
    "Task",
    "TaskStatus",
    "RetryConfig",
    "DatabaseOperationResult",
    "PathUtils",
    "ProjectPaths",
    "BatchTemplateGenerator",
    "EmailUtils",
    "RateLimiter",
    "create_discovery_manager",
]
