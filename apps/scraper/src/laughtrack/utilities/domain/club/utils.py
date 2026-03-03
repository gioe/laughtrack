"""Club-specific utility functions for the Laughtrack domain."""

from typing import Dict, List, Optional

from laughtrack.foundation.models.types import JSONDict


class ClubUtils:
    """Domain-specific utilities for Club entities."""

    @staticmethod
    def standardize_club_name(name: str) -> str:
        """
        Standardize club name for consistency.

        Args:
            name: Raw club name

        Returns:
            Standardized club name
        """
        if not name:
            return ""

        # Remove extra whitespace
        import re

        name = re.sub(r"\s+", " ", name.strip())

        # Remove common prefixes
        name = re.sub(r"^(the\s+)", "", name, flags=re.IGNORECASE)

        # Remove common suffixes
        suffixes = ["comedy club", "comedy", "club", "theater", "theatre"]
        for suffix in suffixes:
            pattern = rf"\s+{re.escape(suffix)}$"
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)

        return name.title()

    @staticmethod
    def extract_location_info(club_data: JSONDict) -> Dict[str, str]:
        """
        Extract location information from club data.

        Args:
            club_data: Dictionary containing club information

        Returns:
            Dictionary with extracted location fields
        """
        location_info = {}

        # Common location fields to extract
        location_fields = ["city", "state", "zip_code", "address", "country"]

        for field in location_fields:
            value = club_data.get(field, "")
            if isinstance(value, str):
                location_info[field] = value.strip()
            else:
                location_info[field] = str(value) if value is not None else ""

        return location_info

    @staticmethod
    def generate_club_slug(name: str, city: str = "", state: str = "") -> str:
        """
        Generate URL-friendly slug for a club.

        Args:
            name: Club name
            city: City name (optional)
            state: State name (optional)

        Returns:
            URL-friendly slug
        """
        import re

        # Combine name with location if provided
        parts = [name]
        if city:
            parts.append(city)
        if state:
            parts.append(state)

        combined = " ".join(parts).lower()

        # Replace spaces and special characters with hyphens
        slug = re.sub(r"[^\w\s-]", "", combined)
        slug = re.sub(r"[\s_-]+", "-", slug)

        # Remove leading/trailing hyphens
        return slug.strip("-")

    @staticmethod
    def parse_venue_capacity(capacity_str: str) -> Optional[int]:
        """
        Parse venue capacity from string.

        Args:
            capacity_str: String containing capacity information

        Returns:
            Parsed capacity as integer or None if invalid
        """
        if not capacity_str:
            return None

        # Extract numbers from string
        import re

        numbers = re.findall(r"\d+", str(capacity_str))

        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                pass

        return None

    @staticmethod
    def validate_club_data(club_data: JSONDict) -> List[str]:
        """
        Validate club data and return list of issues.

        Args:
            club_data: Dictionary containing club information

        Returns:
            List of validation error messages
        """
        issues = []

        # Required fields
        required_fields = ["name"]
        for field in required_fields:
            if not club_data.get(field):
                issues.append(f"Missing required field: {field}")

        # Validate email format if present
        email = club_data.get("email")
        if email:
            import re

            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, email):
                issues.append("Invalid email format")

        # Validate phone format if present
        phone = club_data.get("phone")
        if phone:
            # Remove all non-digit characters
            digits = re.sub(r"\D", "", phone)
            if not (10 <= len(digits) <= 15):
                issues.append("Invalid phone number format")

        # Validate website URL if present
        website = club_data.get("website")
        if website:
            if not website.startswith(("http://", "https://")):
                issues.append("Website URL should start with http:// or https://")

        return issues

    @staticmethod
    def categorize_club_by_size(capacity: int) -> str:
        """
        Categorize club by venue size.

        Args:
            capacity: Venue capacity

        Returns:
            Size category string
        """
        if capacity <= 50:
            return "Intimate"
        elif capacity <= 150:
            return "Small"
        elif capacity <= 300:
            return "Medium"
        elif capacity <= 500:
            return "Large"
        else:
            return "Theater"

    @staticmethod
    def extract_social_media_handles(club_data: JSONDict) -> Dict[str, str]:
        """
        Extract social media handles from club data.

        Args:
            club_data: Dictionary containing club information

        Returns:
            Dictionary with social media handles
        """
        social_media = {}

        # Common social media fields
        social_fields = ["instagram", "twitter", "facebook", "tiktok", "youtube"]

        for field in social_fields:
            value = club_data.get(field, "")
            if value:
                # Clean up handle (remove @ symbol, URLs, etc.)
                handle = str(value).strip()
                if handle.startswith("@"):
                    handle = handle[1:]
                elif "/" in handle:
                    # Extract handle from URL
                    handle = handle.split("/")[-1]

                social_media[field] = handle

        return social_media

    @staticmethod
    def calculate_distance_score(club1_coords: tuple, club2_coords: tuple) -> float:
        """
        Calculate a simple distance score between two clubs.

        Args:
            club1_coords: (latitude, longitude) of first club
            club2_coords: (latitude, longitude) of second club

        Returns:
            Distance score (lower is closer)
        """
        import math

        lat1, lon1 = club1_coords
        lat2, lon2 = club2_coords

        # Simple Euclidean distance for rough comparison
        # For more accurate distance, would use Haversine formula
        distance = math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)

        return distance
