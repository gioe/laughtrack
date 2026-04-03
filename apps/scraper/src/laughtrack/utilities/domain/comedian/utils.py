"""Comedian-specific utility functions for the Laughtrack domain."""

import hashlib
import re
from typing import Any, Dict, List, Optional, Set

from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.popularity.scorer import PopularityScorer
from gioe_libs.string_utils import StringUtils


# Leading noise prefix: "Comedian Name" / "Comedy Magician Name" → "Name"
_PREFIX_NOISE_RE = re.compile(r'^(?:Comedian|Comedy\s+Magician)\s+', re.IGNORECASE)

# Trailing noise suffix anchored on a known noise keyword.
# Strips everything from the match point onward.
#
# Patterns (case-insensitive):
#   • " - Special Event..."  – dash then "special event" or "special show"
#   • " - Live" / " - LIVE"  – dash then "live" as a standalone word
#   • " Live in <word>"       – city suffix common in Naples venue listings
#   • ' From "..." '         – From followed by a quoted show name
#   • ' From SNL/FOX/...'    – From followed by an all-caps abbreviation
_SUFFIX_NOISE_RE = re.compile(
    r'(?:'
    r'\s+[-–]\s+special[\s_]event|'          # " - Special Event"
    r'\s+[-–]\s+special\s+show|'             # " - Special Show"
    r'\s+[-–]\s+live\b|'                     # " - Live" / " - LIVE"
    r'\s+live\s+in\s+\w|'                    # " Live in Naples"
    r'\s+from\s+[\"\'\u201c\u2018]|'         # ' From "Show"' or " From 'Show'"
    r'\s+from\s+[A-Z]{2,}'                   # " From SNL" / " From FOX"
    r')',
    re.IGNORECASE,
)


class ComedianUtils:
    """Domain-specific utilities for Comedian entities."""

    @staticmethod
    def get_unique_names(comedians: List[Comedian]) -> Set[str]:
        """
        Get unique comedian names from a list.

        Args:
            comedians: List of comedians

        Returns:
            Set of unique comedian names
        """
        return {comedian.name for comedian in comedians if comedian.name}

    @staticmethod
    def filter_by_popularity_threshold(comedians: List[Comedian], min_popularity: float) -> List[Comedian]:
        """
        Filter comedians by minimum popularity score.

        Args:
            comedians: List of comedians to filter
            min_popularity: Minimum popularity score (0-1)

        Returns:
            List of comedians meeting popularity threshold
        """
        return [comedian for comedian in comedians if comedian.popularity and comedian.popularity >= min_popularity]

    @staticmethod
    def group_by_popularity_tier(comedians: List[Comedian]) -> Dict[str, List[Comedian]]:
        """
        Group comedians by popularity tier.

        Args:
            comedians: List of comedians to group

        Returns:
            Dictionary mapping popularity tiers to lists of comedians
        """

        grouped = {}
        for comedian in comedians:
            popularity = comedian.popularity or 0.0
            tier = PopularityScorer.get_popularity_tier(popularity)

            if tier not in grouped:
                grouped[tier] = []
            grouped[tier].append(comedian)

        return grouped

    @staticmethod
    def find_by_name_partial(comedians: List[Comedian], search_name: str) -> List[Comedian]:
        """
        Find comedians by partial name match (case-insensitive).

        Args:
            comedians: List of comedians to search
            search_name: Partial name to search for

        Returns:
            List of comedians with matching names
        """
        search_lower = search_name.lower()
        return [comedian for comedian in comedians if comedian.name and search_lower in comedian.name.lower()]

    @staticmethod
    def get_most_popular(comedians: List[Comedian], limit: int = 10) -> List[Comedian]:
        """
        Get the most popular comedians from a list.

        Args:
            comedians: List of comedians
            limit: Maximum number of comedians to return

        Returns:
            List of top comedians sorted by popularity (descending)
        """
        sorted_comedians = sorted(comedians, key=lambda c: c.popularity or 0.0, reverse=True)
        return sorted_comedians[:limit]

    @staticmethod
    def calculate_average_popularity(comedians: List[Comedian]) -> float:
        """
        Calculate average popularity across comedians.

        Args:
            comedians: List of comedians

        Returns:
            Average popularity score
        """
        if not comedians:
            return 0.0

        total_popularity = sum(comedian.popularity or 0.0 for comedian in comedians)
        return total_popularity / len(comedians)

    @staticmethod
    def get_comedians_with_social_media(comedians: List[Comedian]) -> List[Comedian]:
        """
        Filter comedians who have social media information.

        Args:
            comedians: List of comedians to filter

        Returns:
            List of comedians with social media data
        """
        return [
            comedian
            for comedian in comedians
            if (comedian.instagram_followers and comedian.instagram_followers > 0)
            or (comedian.tiktok_followers and comedian.tiktok_followers > 0)
            or (comedian.youtube_followers and comedian.youtube_followers > 0)
        ]

    @staticmethod
    def get_social_media_stats(comedian: Comedian) -> Dict[str, int]:
        """
        Get social media statistics for a comedian.

        Args:
            comedian: Comedian to analyze

        Returns:
            Dictionary with social media follower counts
        """
        return {
            "instagram": comedian.instagram_followers or 0,
            "tiktok": comedian.tiktok_followers or 0,
            "youtube": comedian.youtube_followers or 0,
            "total": (comedian.instagram_followers or 0)
            + (comedian.tiktok_followers or 0)
            + (comedian.youtube_followers or 0),
        }

    @staticmethod
    def sort_by_name(comedians: List[Comedian], reverse: bool = False) -> List[Comedian]:
        """
        Sort comedians alphabetically by name.

        Args:
            comedians: List of comedians to sort
            reverse: Whether to sort in reverse order

        Returns:
            Sorted list of comedians
        """
        return sorted(comedians, key=lambda c: c.name or "", reverse=reverse)

    @staticmethod
    def has_valid_uuid(comedian: Comedian) -> bool:
        """
        Check if comedian has a valid UUID.

        Args:
            comedian: Comedian to check

        Returns:
            True if comedian has a non-None UUID
        """
        return comedian.uuid is not None and comedian.uuid != ""

    @staticmethod
    def deduplicate_comedians(comedians: List[Any]) -> List[Any]:
        """
        Deduplicate comedians based on name or UUID.

        Args:
            comedians: List of comedian objects

        Returns:
            List of deduplicated comedians
        """
        if not comedians:
            return []

        unique_comedians = {}

        for comedian in comedians:
            # Use UUID if available, otherwise use name
            key = getattr(comedian, "uuid", None) or getattr(comedian, "name", str(comedian))

            if key not in unique_comedians:
                unique_comedians[key] = comedian

        deduplicated = list(unique_comedians.values())

        if len(deduplicated) < len(comedians):
            removed_count = len(comedians) - len(deduplicated)
            Logger.info(f"Deduplicated {removed_count} duplicate comedians (kept {len(deduplicated)})")

        return deduplicated

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalizes a raw performer name to a canonical comedian name.

        Transformations applied in order:
          1. Strip leading/trailing whitespace.
          2. Strip leading role prefix ("Comedian ", "Comedy Magician ").
          3. Strip post-colon subtitle ("Adam Carolla: All New Material" → "Adam Carolla").
          4. Strip trailing noise suffix anchored on a keyword:
               - " - Special Event..." / " - Special Show..."
               - " - Live" / " - LIVE"
               - " Live in <city>" (Naples venue listing pattern)
               - ' From "Show"' / " From SNL" (quoted or all-caps show reference)
          5. Remove content in parentheses.
          6. Title-case if the result is entirely upper- or lower-case.
        """
        try:
            canonical = name.strip()

            # 2. Strip leading role prefix
            canonical = _PREFIX_NOISE_RE.sub("", canonical).strip()

            # 3. Strip post-colon subtitle
            canonical = canonical.split(":")[0].strip()

            # 4. Strip trailing noise suffix
            m = _SUFFIX_NOISE_RE.search(canonical)
            if m:
                canonical = canonical[: m.start()].strip()

            # 5. Remove parenthetical content
            outside_parenthesis = StringUtils.remove_parentheses_content(canonical)

            # 6. Title-case normalisation
            return (
                outside_parenthesis.title()
                if outside_parenthesis.isupper() or outside_parenthesis.islower()
                else outside_parenthesis
            )
        except Exception as e:
            Logger.error(f"Error normalizing name: {e}")
            return ""

    @staticmethod
    def generate_uuid(name: str) -> str:
        """Generates a UUID by hashing the cleaned, lowercased name string."""
        cleaned_name = StringUtils.remove_non_alphanumeric(name)
        lower_case_name = cleaned_name.lower()
        return hashlib.md5(lower_case_name.encode()).hexdigest()
