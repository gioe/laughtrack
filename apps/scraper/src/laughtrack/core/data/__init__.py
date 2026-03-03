"""
Core database infrastructure components.

This module contains the foundational database handling classes:
- BaseDatabaseHandler: Unified database operations with entity abstractions
- TransactionManager: Transaction and retry logic
"""

from .base_handler import BaseDatabaseHandler
from laughtrack.adapters.db import (
    create_connection,
    create_connection_with_transaction,
    get_connection,
    get_transaction,
)

__all__ = [
    "BaseDatabaseHandler",
    "create_connection",
    "create_connection_with_transaction",
    "get_connection",
    "get_transaction",
]
