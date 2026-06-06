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
import re
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
        """Recency + social produce additive weighted score (no sold_out history).

        Passes has_image=True so the confidence gate doesn't cap the performance
        contribution — this case is about verifying the recency/social additive
        shape, not the gate. (Without a gate signal, total_shows=0 would trip the
        low-confidence cap; the gate behavior is exercised in TestConfidenceGate.)
        """
        # instagram=10M → social_score=1.0
        # performance = RECENCY_BLEND_WEIGHT*0.5 + HISTORICAL_BLEND_WEIGHT*0.0 = 0.6*0.5 = 0.3
        # popularity = 1.0*0.4 + 0.3*0.6 = 0.58
        score = PopularityScorer.calculate_comedian_popularity(
            instagram_followers=10_000_000,
            recency_score=0.5,
            has_image=True,
        )
        expected_perf = (
            PopularityScorer.RECENCY_BLEND_WEIGHT * 0.5
            + PopularityScorer.HISTORICAL_BLEND_WEIGHT * 0.0
        )
        assert score == round(1.0 * 0.4 + expected_perf * 0.6, 4)

    def test_recency_score_above_1_is_clamped(self):
        """recency_score > 1.0 is clamped to 1.0 before blending; popularity stays in [0, 1]."""
        score = PopularityScorer.calculate_comedian_popularity(
            recency_score=2.0, has_image=True
        )
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
            has_image=True,
        )
        expected_perf = PopularityScorer.RECENCY_BLEND_WEIGHT * 0.3
        assert score == round(1.0 * 0.4 + expected_perf * 0.6, 4)


def test_performance_score_blends_recency_and_sold_out():
    """
    When both recency and historical sold-out data exist, both contribute to
    performance_score — the headliner-with-upcoming-show case the original
    branch used to mask. We pick a regime where recency > historical so the
    blend genuinely sits between the two single-signal paths (the cold-start
    fallback at recency=0 returns historical-only, so to beat sold_out_only
    the recency contribution must exceed the historical one).
    """
    # recency=0.9 + 2/10 sold_out → historical = 0.2 + min(10/100, 0.2) = 0.3
    # blended performance = 0.6*0.9 + 0.4*0.3 = 0.66
    # popularity (no social) = 0.0*0.4 + 0.66*0.6 = 0.396
    blended = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=2, total_shows=10, recency_score=0.9
    )
    recency_only = PopularityScorer.calculate_comedian_popularity(recency_score=0.9)
    sold_out_only = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=2, total_shows=10, recency_score=0.0
    )

    expected_perf = (
        PopularityScorer.RECENCY_BLEND_WEIGHT * 0.9
        + PopularityScorer.HISTORICAL_BLEND_WEIGHT * 0.3
    )
    assert blended == round(0.0 * 0.4 + expected_perf * 0.6, 4)
    assert blended > recency_only  # historical contributes — bug-fix proof
    assert blended > sold_out_only  # recency contributes too


def test_performance_score_cold_start_historical_fallback():
    """
    Cold start: when recency_score=0 (no shows in the recency window),
    performance falls back to historical-only. A dormant headliner is neither
    rewarded nor penalized for the missing recency signal — they keep the
    score they would have had under the pre-blend formula.
    """
    # 10/10 sold_out → historical_component = min(1.0 + 0.1, 1.0) = 1.0
    # cold-start performance = 1.0 (historical only; no blend penalty)
    # popularity (no social) = 0.0*0.4 + 1.0*0.6 = 0.6
    score = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=10, total_shows=10, recency_score=0.0
    )
    assert score == round(0.0 * 0.4 + 1.0 * 0.6, 4)

    # default (omitted recency_score) matches explicit 0.0 — shape parity check
    default_recency = PopularityScorer.calculate_comedian_popularity(
        sold_out_shows=10, total_shows=10
    )
    assert default_recency == score


def test_blend_weights_sum_to_one():
    """
    RECENCY_BLEND_WEIGHT + HISTORICAL_BLEND_WEIGHT must equal 1.0 — the blend
    path's [0, 1] contract relies on it. Pinning the invariant here prevents a
    future tuner from editing one constant without the other and silently
    pushing performance_score out of bounds.
    """
    assert (
        PopularityScorer.RECENCY_BLEND_WEIGHT
        + PopularityScorer.HISTORICAL_BLEND_WEIGHT
        == 1.0
    )


class TestConfidenceGate:
    """Performance saturation is gated behind confidence signals so a 1-of-1
    sold-out attribution on lineup-extraction noise cannot land on the 0.6
    popularity cliff."""

    def test_low_confidence_caps_the_0_6_popularity_cliff(self):
        """The exact bug: no social data + 1-of-1 sold_out used to produce
        popularity=0.6 (Rising Star). With the gate, performance is capped at
        LOW_CONFIDENCE_PERFORMANCE_CAP and popularity falls below the cliff."""
        score = PopularityScorer.calculate_comedian_popularity(
            sold_out_shows=1, total_shows=1
        )
        # historical = 1/1 + min(1/100, 0.2) = 1.0, capped at LOW_CONFIDENCE_PERFORMANCE_CAP (0.5)
        # popularity = 0.0*0.4 + 0.5*0.6 = 0.3
        expected = round(
            0.0 * PopularityScorer.SOCIAL_MEDIA_WEIGHT
            + PopularityScorer.LOW_CONFIDENCE_PERFORMANCE_CAP * PopularityScorer.SHOW_PERFORMANCE_WEIGHT,
            4,
        )
        assert score == expected
        assert score < 0.6  # off the cliff

    def test_total_shows_threshold_passes_gate(self):
        """total_shows >= MIN_CONFIDENT_TOTAL_SHOWS satisfies the gate by
        itself — a real track record needs no other corroboration."""
        # MIN_CONFIDENT_TOTAL_SHOWS=3, sold_out=3/3 → historical=1.0
        # popularity = 0.0*0.4 + 1.0*0.6 = 0.6 (gate passes, no cap)
        score = PopularityScorer.calculate_comedian_popularity(
            sold_out_shows=PopularityScorer.MIN_CONFIDENT_TOTAL_SHOWS,
            total_shows=PopularityScorer.MIN_CONFIDENT_TOTAL_SHOWS,
        )
        assert score == round(0.0 * 0.4 + 1.0 * 0.6, 4)

    def test_total_shows_one_below_threshold_is_capped(self):
        """Boundary: MIN_CONFIDENT_TOTAL_SHOWS - 1 is still low-confidence."""
        below = PopularityScorer.MIN_CONFIDENT_TOTAL_SHOWS - 1
        score = PopularityScorer.calculate_comedian_popularity(
            sold_out_shows=below, total_shows=below
        )
        expected = round(
            PopularityScorer.LOW_CONFIDENCE_PERFORMANCE_CAP
            * PopularityScorer.SHOW_PERFORMANCE_WEIGHT,
            4,
        )
        assert score == expected

    def test_has_image_signal_passes_gate(self):
        """A sourced image (Wikidata/TMDb hit) is itself a confidence signal —
        a real comedian whose only show data is 1-of-1 sold_out still saturates."""
        score = PopularityScorer.calculate_comedian_popularity(
            sold_out_shows=1, total_shows=1, has_image=True
        )
        # gate passes via has_image → historical=1.0 → popularity=0.6
        assert score == round(0.0 * 0.4 + 1.0 * 0.6, 4)

    def test_verified_podcast_appearance_signal_passes_gate(self):
        """A verified podcast appearance (accepted comedian_podcasts or
        episode_appearances row) also passes the gate by itself."""
        score = PopularityScorer.calculate_comedian_popularity(
            sold_out_shows=1, total_shows=1, has_podcast_appearance=True
        )
        assert score == round(0.0 * 0.4 + 1.0 * 0.6, 4)

    def test_low_confidence_with_recency_is_also_capped(self):
        """The cap applies to the blended performance score too, so a
        low-confidence comedian with high recency activity still cannot
        saturate above the cap."""
        # recency=1.0 → blended perf = 0.6*1.0 + 0.4*0.0 = 0.6, capped at 0.5
        # popularity = 0.0*0.4 + 0.5*0.6 = 0.3
        score = PopularityScorer.calculate_comedian_popularity(
            sold_out_shows=0, total_shows=0, recency_score=1.0
        )
        expected = round(
            PopularityScorer.LOW_CONFIDENCE_PERFORMANCE_CAP
            * PopularityScorer.SHOW_PERFORMANCE_WEIGHT,
            4,
        )
        assert score == expected

    def test_low_confidence_below_cap_unaffected(self):
        """When the unblended performance score is already below the cap, the
        gate does not change the outcome — capping is a ceiling, not a floor."""
        # recency=0.5, no historical → blended perf = 0.6*0.5 + 0.0 = 0.3, below 0.5 cap
        # popularity = 0.0*0.4 + 0.3*0.6 = 0.18
        score = PopularityScorer.calculate_comedian_popularity(recency_score=0.5)
        expected = round(
            0.0 * 0.4
            + (PopularityScorer.RECENCY_BLEND_WEIGHT * 0.5) * 0.6,
            4,
        )
        assert score == expected

    def test_confidence_gate_constants_in_sensible_ranges(self):
        """Pin the gate constants against accidental retuning: the cap must be
        in (0, 1) and the threshold must be a positive integer."""
        assert 0.0 < PopularityScorer.LOW_CONFIDENCE_PERFORMANCE_CAP < 1.0
        assert isinstance(PopularityScorer.MIN_CONFIDENT_TOTAL_SHOWS, int)
        assert PopularityScorer.MIN_CONFIDENT_TOTAL_SHOWS >= 1


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


class TestCalculateShowPopularity:
    """calculate_show_popularity blends lineup/venue/sales/click demand and clamps to [0, 1]."""

    def test_zero_inputs_returns_zero(self):
        assert PopularityScorer.calculate_show_popularity() == 0.0

    def test_blends_three_signals_weighted(self):
        # lineup=0.8 -> 0.36, venue=0.5 -> 0.1, sales=1.0 -> 0.25, clicks=0.5 -> 0.05 => 0.76
        score = PopularityScorer.calculate_show_popularity(
            lineup_popularity=0.8,
            venue_popularity=0.5,
            ticket_sales_rate=1.0,
            click_demand_rate=0.5,
        )
        expected = (
            0.8 * PopularityScorer.SHOW_LINEUP_WEIGHT
            + 0.5 * PopularityScorer.SHOW_VENUE_WEIGHT
            + 1.0 * PopularityScorer.SHOW_SALES_WEIGHT
            + 0.5 * PopularityScorer.SHOW_CLICK_DEMAND_WEIGHT
        )
        assert score == round(expected, 4)

    def test_all_max_inputs_returns_one(self):
        score = PopularityScorer.calculate_show_popularity(
            lineup_popularity=1.0,
            venue_popularity=1.0,
            ticket_sales_rate=1.0,
            click_demand_rate=1.0,
        )
        assert score == 1.0

    def test_out_of_range_inputs_are_clamped_to_one(self):
        """Defensive clamp pins the [0, 1] docstring contract — guards against
        legacy unclamped lineup popularity (prod max=3.76 before TASK-2697)
        and any future buggy upstream signal."""
        score = PopularityScorer.calculate_show_popularity(
            lineup_popularity=3.76,
            venue_popularity=1.0,
            ticket_sales_rate=1.0,
            click_demand_rate=1.0,
        )
        assert score == 1.0

    def test_negative_inputs_are_clamped_to_zero(self):
        score = PopularityScorer.calculate_show_popularity(
            lineup_popularity=-0.5,
            venue_popularity=-1.0,
            ticket_sales_rate=-0.2,
            click_demand_rate=-0.4,
        )
        assert score == 0.0


def test_show_blend_weights_sum_to_one():
    """SHOW_*_WEIGHTs must sum to 1.0 — the [0, 1] contract relies on it.
    Pinning the invariant here keeps a future tuner from editing one constant
    without the others and silently pushing show popularity out of bounds."""
    assert (
        PopularityScorer.SHOW_LINEUP_WEIGHT
        + PopularityScorer.SHOW_VENUE_WEIGHT
        + PopularityScorer.SHOW_SALES_WEIGHT
        + PopularityScorer.SHOW_CLICK_DEMAND_WEIGHT
        == 1.0
    )


class TestBatchUpdateComedianShowCountsSql:
    """Contract tests for comedian sold-out denominator filtering."""

    def setup_method(self):
        self.ComedianQueries = _load_module(
            "sql/comedian_queries.py", "sql.comedian_queries_direct"
        ).ComedianQueries

    def test_query_uses_reports_sold_out_flag_for_denominator(self):
        sql = self.ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS
        assert "reports_sold_out" in sql
        assert "last_scraped_by" in sql
        assert "scraping_sources" in sql

    def test_query_counts_confirmed_sellouts_even_from_unreliable_sources(self):
        sql = self.ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS.lower()
        assert "ta.all_sold_out" in sql
        assert re.search(
            r"count\(distinct\s+li\.show_id\)\s+filter\s*\([^)]*ta\.all_sold_out",
            sql,
            re.DOTALL,
        )
        assert re.search(
            r"count\(distinct\s+li\.show_id\)\s+filter\s*\([^)]*reports_sold_out",
            sql,
            re.DOTALL,
        )


class TestBatchGetShowPopularitySql:
    """Contract tests for the BATCH_GET_LINEUP_POPULARITY SQL query — pins the
    signals (lineup popularity, clubs.popularity, ticket sold_out, click demand, time-decay)
    and the [0, 1] clamp so a future SQL refactor cannot silently revert to
    the unclamped lineup-only formula that produced prod max=3.76 (TASK-2697)."""

    def setup_method(self):
        self.ShowQueries = _load_module(
            "sql/show_queries.py", "sql.show_queries_direct"
        ).ShowQueries

    def test_query_exists(self):
        assert hasattr(self.ShowQueries, "BATCH_GET_LINEUP_POPULARITY")

    def test_query_reads_clubs_popularity(self):
        sql = self.ShowQueries.BATCH_GET_LINEUP_POPULARITY
        assert "cl.popularity" in sql or "clubs.popularity" in sql

    def test_query_reads_ticket_sold_out(self):
        sql = self.ShowQueries.BATCH_GET_LINEUP_POPULARITY.lower()
        assert "tickets" in sql
        assert "sold_out" in sql
        assert "bool_or" in sql

    def test_click_demand_helper_exists(self):
        assert hasattr(self.ShowQueries, "BATCH_GET_SHOW_CLICK_DEMAND")
        sql = self.ShowQueries.BATCH_GET_SHOW_CLICK_DEMAND.lower()
        assert "ticket_purchase_click_events" in sql
        assert "click_count" in sql
        assert "30 days" in sql

    def test_query_reads_ticket_purchase_click_events(self):
        sql = self.ShowQueries.BATCH_GET_LINEUP_POPULARITY.lower()
        assert "ticket_purchase_click_events" in sql
        assert "click_demand_rate" in sql
        assert "30 days" in sql
        assert "/ 5.0" in sql

    def test_query_applies_time_decay(self):
        sql = self.ShowQueries.BATCH_GET_LINEUP_POPULARITY
        # piecewise decay on s.date — at least one cut point present
        assert "CURRENT_DATE" in sql
        assert "INTERVAL" in sql

    def test_query_clamps_to_one(self):
        """LEAST(...) must use 1.0 as its upper bound — the docstring contract.
        Substring 'LEAST(' + '1.0' is too loose: '1.0' also appears in the
        time-decay CASE WHEN, so a refactor to LEAST(x, 2.0) would slip through.
        Anchor on the full `LEAST(..., 1.0)` shape (with the comma + optional
        whitespace) so an upper-bound regression cannot pass."""
        sql = self.ShowQueries.BATCH_GET_LINEUP_POPULARITY
        assert re.search(r"LEAST\(.*?,\s*1\.0\s*\)", sql, re.DOTALL) is not None


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

    def test_query_reads_click_demand_through_lineup_shows(self):
        sql = self.ComedianQueries.GET_COMEDIAN_RECENCY_SCORES.lower()
        assert "lineup_items" in sql
        assert "ticket_purchase_click_events" in sql
        assert "click_demand_rate" in sql
        assert "30 days" in sql


class TestBatchGetClubPopularitySql:
    """Contract tests for the BATCH_GET_CLUB_POPULARITY SQL query."""

    def setup_method(self):
        self.ClubQueries = _load_module(
            "sql/club_queries.py", "sql.club_queries_direct"
        ).ClubQueries

    def test_query_exists(self):
        assert hasattr(self.ClubQueries, "BATCH_GET_CLUB_POPULARITY")

    def test_click_demand_helper_exists(self):
        assert hasattr(self.ClubQueries, "BATCH_GET_CLUB_CLICK_DEMAND")
        sql = self.ClubQueries.BATCH_GET_CLUB_CLICK_DEMAND.lower()
        assert "ticket_purchase_click_events" in sql
        assert "click_count" in sql
        assert "30 days" in sql

    def test_query_reads_ticket_purchase_click_events(self):
        sql = self.ClubQueries.BATCH_GET_CLUB_POPULARITY.lower()
        assert "ticket_purchase_click_events" in sql
        assert "click_demand_rate" in sql
        assert "30 days" in sql
        assert "/ 20.0" in sql
