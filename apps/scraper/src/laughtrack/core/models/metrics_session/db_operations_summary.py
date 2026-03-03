from __future__ import annotations
from dataclasses import dataclass


@dataclass
class DBOperationsSummary:
    total: int
    inserts: int
    updates: int
    errors: int
    duplicates_dropped: int = 0
    validation_errors: int = 0
    db_errors: int = 0
