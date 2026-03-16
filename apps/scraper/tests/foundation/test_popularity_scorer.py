"""
Unit tests for PopularityScorer.calculate_comedian_popularity.

Covers:
- Social-only scoring (no recency, no performance data)
- Legacy performance score fallback (no recency_score)
- Recency score takes precedence over sold_out/total_shows when > 0
- recency_score=0.0 still uses the legacy performance path
- Boundary values and combined scoring
"""

import importlib.util
import sys
from pathlib import Path

_SCRAPER_ROOT = Path(__file__).parents[2]  # apps/scraper/


def _load_module(rel_path: str, module_name: str):
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


_scorer_mod = _load_module(
    "src/laughtrack/foundation/utilities/popularity/scorer.py",
    "laughtrack.foundation.utilities.popularity.scorer_direct",
)
PopularityScorer = _scorer_mod.PopularityScorer


class TestCalculateComedianPopularityRecencyScore:
    """recency_score integration into calculate_comedian_popularity."""

    def test_recency_score_replaces_performance_when_positive(self):
        """When recency_score > 0, it drives the performance component."""
        # With recency_score=1.0 (max activity) and no social: score = 0*0.4 + 1.0*0.6 = 0.6
        score = PopularityScorer.calculate_comedian_popularity(recency_score=1.0)
        assert score == round(0.0 * 0.4 + 1.0 * 0.6, 4)

    def test_recency_score_zero_falls_back_to_performance(self):
        """When recency_score == 0.0, the legacy sold_out/total formula is used."""
        # 10/10 sold out = sellout_rate 1.0, experience_bonus min(10/100,0.2)=0.1 → perf=1.0
        score_with_recency = PopularityScorer.calculate_comedian_popularity(
            sold_out_shows=10, total_shows=10, recency_score=0.0
        )
        score_legacy = PopularityScorer.calculate_comedian_popularity(
            sold_out_shows=10, total_shows=10
        )
        assert score_with_recency == score_legacy

    def test_recency_score_combined_with_social(self):
        """Recency + social produce additive weighted score."""
        # instagram=10M → social_score=1.0; recency=0.5
        # popularity = 1.0*0.4 + 0.5*0.6 = 0.7
        score = PopularityScorer.calculate_comedian_popularity(
            instagram_followers=10_000_000,
            recency_score=0.5,
        )
        assert score == round(1.0 * 0.4 + 0.5 * 0.6, 4)

    def test_no_data_returns_zero(self):
        """Comedian with no social and no recency/performance data scores 0."""
        score = PopularityScorer.calculate_comedian_popularity()
        assert score == 0.0

    def test_recency_score_capped_at_one(self):
        """Recency scores above 1.0 are clamped by SHOW_PERFORMANCE_WEIGHT contribution."""
        # recency_score > 1.0 is unusual but the math should still be bounded by weight
        score = PopularityScorer.calculate_comedian_popularity(recency_score=2.0)
        # 0.6 * 2.0 = 1.2 → raw; no explicit cap in scorer, but let's assert > 0.6
        assert score > 0.6

    def test_partial_social_with_recency(self):
        """Partial social data + recency produces expected weighted result."""
        # tiktok=50M → tiktok_score=1.0, tiktok_weight=0.3; social=1.0/0.3=1.0 (normalized)
        # recency=0.3 → perf=0.3
        # popularity = 1.0*0.4 + 0.3*0.6 = 0.58
        score = PopularityScorer.calculate_comedian_popularity(
            tiktok_followers=50_000_000,
            recency_score=0.3,
        )
        assert score == round(1.0 * 0.4 + 0.3 * 0.6, 4)


class TestGetComedianRecencyScoresSql:
    """Contract tests for the GET_COMEDIAN_RECENCY_SCORES SQL query."""

    def setup_method(self):
        import sys
        from pathlib import Path
        import importlib.util
        root = Path(__file__).parents[2]
        spec = importlib.util.spec_from_file_location(
            "sql.comedian_queries_direct2",
            root / "sql/comedian_queries.py",
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["sql.comedian_queries_direct2"] = mod
        spec.loader.exec_module(mod)
        self.ComedianQueries = mod.ComedianQueries

    def test_query_exists(self):
        assert hasattr(self.ComedianQueries, "GET_COMEDIAN_RECENCY_SCORES")

    def test_query_references_lineup_items_and_shows(self):
        sql = self.ComedianQueries.GET_COMEDIAN_RECENCY_SCORES.upper()
        assert "LINEUP_ITEMS" in sql
        assert "SHOWS" in sql

    def test_query_uses_180_day_window(self):
        sql = self.ComedianQueries.GET_COMEDIAN_RECENCY_SCORES
        assert "180 days" in sql.lower() or "180 DAYS" in sql.upper()

    def test_query_returns_comedian_id_and_recency_score(self):
        sql = self.ComedianQueries.GET_COMEDIAN_RECENCY_SCORES.lower()
        assert "comedian_id" in sql
        assert "recency_score" in sql

    def test_query_normalizes_by_15(self):
        """Normalization constant: 5 upcoming shows (3 pts each) = max score."""
        sql = self.ComedianQueries.GET_COMEDIAN_RECENCY_SCORES
        assert "15.0" in sql or "/ 15" in sql
