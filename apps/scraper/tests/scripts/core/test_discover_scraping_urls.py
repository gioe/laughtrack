from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from laughtrack.core.clients.google.custom_search import SearchResult  # noqa: E402
from scripts.core import discover_comedian_tour_sources as mod  # noqa: E402


def test_registered_comedian_site_is_scraping_candidate_without_json_ld_event_markup():
    comedian = mod.TourDiscoveryCandidate(uuid="comic-ben", name="Ben Bankas", total_shows=10)
    result = SearchResult(
        title="Ben Bankas: International Stand-Up Comedian",
        link="https://benbankas.com/",
        snippet="Upcoming Shows with tickets and tour dates",
        display_link="https://benbankas.com/",
    )

    candidate = mod._candidate_from_result(
        comedian=comedian,
        result=result,
        query="Ben Bankas tour dates",
        rank=1,
    )

    assert candidate is not None
    assert candidate.source_type == "registered_comedian_website"
    assert candidate.confidence == "high"
    assert candidate.is_scraping_url_candidate is True
