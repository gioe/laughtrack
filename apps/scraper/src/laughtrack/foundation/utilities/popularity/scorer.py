"""
Popularity scoring utilities for comedians and shows.

This module provides consistent popularity calculation algorithms specific to
the comedy show domain.
"""

from typing import Optional


class PopularityScorer:
    """Domain-specific utility class for calculating popularity scores for comedians and shows."""

    # Social media follower weights
    INSTAGRAM_WEIGHT = 0.4
    TIKTOK_WEIGHT = 0.3
    YOUTUBE_WEIGHT = 0.3

    # Performance metric weights
    SHOW_PERFORMANCE_WEIGHT = 0.6
    SOCIAL_MEDIA_WEIGHT = 0.4

    # Follower count thresholds for normalization
    MAX_INSTAGRAM_FOLLOWERS = 10_000_000  # 10M followers = max score
    MAX_TIKTOK_FOLLOWERS = 50_000_000  # 50M followers = max score
    MAX_YOUTUBE_FOLLOWERS = 5_000_000  # 5M followers = max score

    @classmethod
    def calculate_comedian_popularity(
        cls,
        instagram_followers: Optional[int] = None,
        tiktok_followers: Optional[int] = None,
        youtube_followers: Optional[int] = None,
        sold_out_shows: int = 0,
        total_shows: int = 0,
    ) -> float:
        """
        Calculate comedian popularity based on social media followers and performance metrics.

        Args:
            instagram_followers: Number of Instagram followers
            tiktok_followers: Number of TikTok followers
            youtube_followers: Number of YouTube subscribers
            sold_out_shows: Number of sold out shows
            total_shows: Total number of shows performed

        Returns:
            float: Popularity score between 0 and 1
        """
        # Calculate social media score (0-1)
        social_score = cls._calculate_social_media_score(instagram_followers, tiktok_followers, youtube_followers)

        # Calculate performance score (0-1)
        performance_score = cls._calculate_performance_score(sold_out_shows, total_shows)

        # Weighted combination
        popularity = social_score * cls.SOCIAL_MEDIA_WEIGHT + performance_score * cls.SHOW_PERFORMANCE_WEIGHT

        return round(popularity, 4)

    @classmethod
    def _calculate_social_media_score(
        cls, instagram_followers: Optional[int], tiktok_followers: Optional[int], youtube_followers: Optional[int]
    ) -> float:
        """Calculate normalized social media score."""
        total_score = 0.0
        total_weight = 0.0

        if instagram_followers is not None and instagram_followers > 0:
            instagram_score = min(instagram_followers / cls.MAX_INSTAGRAM_FOLLOWERS, 1.0)
            total_score += instagram_score * cls.INSTAGRAM_WEIGHT
            total_weight += cls.INSTAGRAM_WEIGHT

        if tiktok_followers is not None and tiktok_followers > 0:
            tiktok_score = min(tiktok_followers / cls.MAX_TIKTOK_FOLLOWERS, 1.0)
            total_score += tiktok_score * cls.TIKTOK_WEIGHT
            total_weight += cls.TIKTOK_WEIGHT

        if youtube_followers is not None and youtube_followers > 0:
            youtube_score = min(youtube_followers / cls.MAX_YOUTUBE_FOLLOWERS, 1.0)
            total_score += youtube_score * cls.YOUTUBE_WEIGHT
            total_weight += cls.YOUTUBE_WEIGHT

        # Normalize by actual weights used (handles missing social media data)
        if total_weight > 0:
            return total_score / total_weight
        return 0.0

    @classmethod
    def _calculate_performance_score(cls, sold_out_shows: int, total_shows: int) -> float:
        """Calculate performance score based on show history."""
        if total_shows == 0:
            return 0.0

        # Base sellout rate (0-1)
        sellout_rate = sold_out_shows / total_shows

        # Bonus for having more shows (experience factor)
        experience_bonus = min(total_shows / 100, 0.2)  # Up to 20% bonus for 100+ shows

        # Combined performance score
        performance_score = min(sellout_rate + experience_bonus, 1.0)

        return performance_score

    @classmethod
    def get_popularity_tier(cls, popularity_score: float) -> str:
        """
        Get a human-readable popularity tier for a given score.

        Args:
            popularity_score: Popularity score between 0 and 1

        Returns:
            str: Popularity tier description
        """
        if popularity_score >= 0.9:
            return "A-List"
        elif popularity_score >= 0.7:
            return "Headliner"
        elif popularity_score >= 0.5:
            return "Rising Star"
        elif popularity_score >= 0.3:
            return "Established"
        elif popularity_score >= 0.1:
            return "Emerging"
        else:
            return "New Talent"

    @classmethod
    def calculate_show_popularity(
        cls, lineup_popularity: float = 0.0, venue_popularity: float = 0.0, ticket_sales_rate: float = 0.0
    ) -> float:
        """
        Calculate show popularity based on lineup, venue, and ticket sales.

        Args:
            lineup_popularity: Average popularity of comedians in lineup (0-1)
            venue_popularity: Popularity of the venue (0-1)
            ticket_sales_rate: Percentage of tickets sold (0-1)

        Returns:
            float: Show popularity score between 0 and 1
        """
        # Weights for different factors
        LINEUP_WEIGHT = 0.5
        VENUE_WEIGHT = 0.2
        SALES_WEIGHT = 0.3

        popularity = (
            lineup_popularity * LINEUP_WEIGHT + venue_popularity * VENUE_WEIGHT + ticket_sales_rate * SALES_WEIGHT
        )

        return round(popularity, 4)
