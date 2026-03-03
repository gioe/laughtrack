"""
Email entity - colocated model and handler.
"""

from .handler import EmailHandler
from .model import EmailNotification

__all__ = ["EmailNotification", "EmailHandler"]
