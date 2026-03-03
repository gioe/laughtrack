"""
Data models for Wix access token API responses.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WixAppData:
    """Represents individual app data from Wix access token response."""

    int_id: Optional[int] = None
    instance: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WixAppData":
        """Create WixAppData from dictionary."""
        return cls(int_id=data.get("intId"), instance=data.get("instance"), raw_data=data)


@dataclass
class WixAccessTokenResponse:
    """Represents the complete Wix access token API response."""

    apps: Dict[str, WixAppData]
    raw_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WixAccessTokenResponse":
        """Create WixAccessTokenResponse from dictionary."""
        apps_data = data.get("apps", {})
        apps = {}

        for key, app_data in apps_data.items():
            if isinstance(app_data, dict):
                apps[key] = WixAppData.from_dict(app_data)

        return cls(apps=apps, raw_data=data)

    def find_app_by_int_id(self, int_id: int) -> Optional[WixAppData]:
        """Find app data by intId."""
        for app_data in self.apps.values():
            if app_data.int_id == int_id:
                return app_data
        return None

    def get_access_token_for_app(self, int_id: int) -> Optional[str]:
        """Get access token (instance) for a specific app ID."""
        app = self.find_app_by_int_id(int_id)
        return app.instance if app else None
