#!/usr/bin/env python3
"""
One-off migration: update St. Marks Comedy Club scraping_url to the Tixr group page.

stmarkscomedy.com/shows is a React SPA whose initial HTML contains no Tixr links.
The correct scraping target is https://www.tixr.com/groups/stmarkscomedyclub, which
has static event links that StMarksEventExtractor can parse.

Usage:
    cd apps/scraper && python scripts/utils/update_st_marks_scraping_url.py
"""

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger

NEW_URL = "https://www.tixr.com/groups/stmarkscomedyclub"
SCRAPER_KEY = "st_marks"

_UPDATE_SQL = """
    UPDATE clubs
    SET scraping_url = %s
    WHERE scraper = %s
    RETURNING id, name, scraping_url
"""


class _MigrationHandler(BaseDatabaseHandler[Club]):
    def get_entity_name(self) -> str:
        return "club"

    def get_entity_class(self) -> type[Club]:
        return Club


def main() -> None:
    handler = _MigrationHandler()
    results = handler.execute_with_cursor(_UPDATE_SQL, (NEW_URL, SCRAPER_KEY), return_results=True)
    if not results:
        Logger.warn("No rows updated — is the st_marks scraper row present in clubs?")
        return
    for row in results:
        Logger.info(f"Updated club id={row['id']} '{row['name']}' → scraping_url={row['scraping_url']}")
    Logger.info(f"Done. {len(results)} club(s) updated.")


if __name__ == "__main__":
    main()
