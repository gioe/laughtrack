"""
Unit tests for PopularityScorer.calculate_comedian_popularity.

Covers:
- Social-only scoring (no recency, no performance data)
- Recency and historical sold-out blend additively into performance_score
- Cold-start (recency_score = 0) collapses to historical-only via the blend weight
- Touring-only case still ranks via the recency contribution
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
    """recency_score blends with sold_out history inside performance_score."""

    def test_no_data_returns_zero(self):
        """Comedian with no social and no recency/performance data scores 0."""
        score = PopularityScorer.calculate_comedian_popularity()
        assert score == 0.0

    def test_recency_score_combined_with_social(self):
        """Recency + social produce additive weighted score (no sold_out history)."""
        # instagram=10M → social_score=1.0
        # performance = RECENCY_BLEND_WEIGHT*0.5 + HISTORICAL_BLEND_WEIGHT*0.0 = 0.6*0.5 = 0.3
        # popularity = 1.0*0.4 + 0.3*0.6 = 0.58
        score = PopularityScorer.calculate_comedian_popularity(
            instagram_followers=10_000_000,
            recency_score=0.5,
        )
        expected_perf = (
            PopularityScorer.RECENCY_BLEND_WEIGHT * 0.5
            + PopularityScorer.HISTORICAL_BLEND_WEIGHT * 0.0
        )
        assert score == round(1.0 * 0.4 + expected_perf * 0.6, 4)

    def test_recency_score_above_1_is_clamped(self):
        """recency_score > 1.0 is clamped to 1.0 before blending; popularity stays in [0, 1]."""
        score = PopularityScorer.calculate_comedian_popularity(recency_score=2.0)
        # clamped recency=1.0, no sold_out → performance = 0.6*1.0 + 0.4*0.0 = 0.6
        # popularity = 0.0*0.4 + 0.6*0.6 = 0.36
        expected_perf = PopularityScorer.RECENCY_BLEND_WEIGHT * 1.0
        assert score == round(0.0 * 0.4 + expected_perf * 0.6, 4)
        assert score <= 1.0

    def test_partial_social_with_recency(self):
        """Partial social data + recency (no sold_out) produces expected weighted result."""
        # tiktok=50M → tiktok_score=1.0, weight=0.3; social normalized to 1.0
        # performance = 0.6*0.3 + 0.4*0.0 = 0.18
        # popularity = 1.0*0.4 + 0.18*0.6 = 0.508
        score = PopularityScorer.calculate_comedian_popularity(
            tiktok_followers=50_000_000,
            recency_score=0.3,
        )
        expected_perf = PopularityScorer.RECENCY_BLEND_WEIGHT * 0.3
        assert score == round(1.0 * 0.4 + expected_perf * 0.6, 4)


def test_performance_score_blends_recency_and_sold_out():
    """
    When both recency and historical sold-out data exist, both contribute to
    performance_score. The blended score must exceed what either signal alone
    would produce — the headliner-with-upcoming-show case the branch used to
    mask.
    """
    # recency=0.5 + 100/100 sold_out (perf=min(1.0+0.2,1.0)=1.0)
    # blended performance = 0.6*0.5 + 0.4*1.0 = 0.7
    # popularity (no social) = 0.0*0.4 + 0.7*0.6 = 0.42
    blended = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=100, total_shows=100, recency_score=0.5
    )
    recency_only = PopularityScorer.calculate_comedian_popularity(recency_score=0.5)
    sold_out_only = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=100, total_shows=100, recency_score=0.0
    )

    expected_perf = (
        PopularityScorer.RECENCY_BLEND_WEIGHT * 0.5
        + PopularityScorer.HISTORICAL_BLEND_WEIGHT * 1.0
    )
    assert blended == round(0.0 * 0.4 + expected_perf * 0.6, 4)
    assert blended > recency_only
    assert blended > sold_out_only


def test_performance_score_cold_start_historical_fallback():
    """
    Cold start: recency_score=0 collapses performance to HISTORICAL_BLEND_WEIGHT *
    historical_component. The historical component itself (sellout_rate +
    experience_bonus, capped at 1.0) is unchanged in shape.
    """
    # 10/10 sold_out → historical_component = min(1.0 + 0.1, 1.0) = 1.0
    # blended performance = 0.6*0.0 + 0.4*1.0 = 0.4
    # popularity (no social) = 0.0*0.4 + 0.4*0.6 = 0.24
    score = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=10, total_shows=10, recency_score=0.0
    )
    expected_perf = PopularityScorer.HISTORICAL_BLEND_WEIGHT * 1.0
    assert score == round(0.0 * 0.4 + expected_perf * 0.6, 4)

    # default (omitted recency_score) matches explicit 0.0 — shape parity check
    default_recency = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=10, total_shows=10
    )
    assert default_recency == score


def test_performance_score_touring_only_recency_contribution():
    """
    Touring-only: zero sold_out history but high recency. The comedian still
    ranks via the recency contribution — the blend does not penalize them for
    lacking history.
    """
    # recency=0.8, sold_out=0, total=0 → historical_component=0.0
    # blended performance = 0.6*0.8 + 0.4*0.0 = 0.48
    # popularity (no social) = 0.0*0.4 + 0.48*0.6 = 0.288
    score = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=0, total_shows=0, recency_score=0.8
    )
    expected_perf = PopularityScorer.RECENCY_BLEND_WEIGHT * 0.8
    assert score == round(0.0 * 0.4 + expected_perf * 0.6, 4)
    assert score > 0.0


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

    def test_query_normalizes_by_20(self):
        """Normalization constant: 5 upcoming shows (4 pts each) = max score."""
        sql = self.ComedianQueries.GET_COMEDIAN_RECENCY_SCORES
        assert "20.0" in sql or "/ 20" in sql
