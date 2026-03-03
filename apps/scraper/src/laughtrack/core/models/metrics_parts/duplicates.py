from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DuplicateShow:
    name: str = ""
    show_page_url: Optional[str] = None


@dataclass
class DuplicateShowDetail:
    club_id: Optional[int] = None
    club_name: Optional[str] = None
    date: str = ""
    room: Optional[str] = None
    kept: DuplicateShow = field(default_factory=DuplicateShow)
    dropped: List[DuplicateShow] = field(default_factory=list)
