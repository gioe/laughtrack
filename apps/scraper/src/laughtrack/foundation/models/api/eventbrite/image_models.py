"""
Image-related Eventbrite API models.

This module contains dataclass definitions for image handling
in Eventbrite API responses.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EventbriteImageCropMask:
    """Image crop mask information."""

    top_left: Dict[str, int]  # {"x": int, "y": int}
    width: int
    height: int

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteImageCropMask":
        """Create EventbriteImageCropMask from JSON dict."""
        return cls(
            top_left=data.get("top_left", {"x": 0, "y": 0}), width=data.get("width", 0), height=data.get("height", 0)
        )


@dataclass
class EventbriteImage:
    """Image information with cropping and metadata."""

    id: str
    url: str
    crop_mask: Optional[EventbriteImageCropMask] = None
    original: Optional[Dict[str, Any]] = None  # {"url": str, "width": int, "height": int}
    aspect_ratio: Optional[str] = None
    edge_color: Optional[str] = None
    edge_color_set: Optional[bool] = None

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "EventbriteImage":
        """Create EventbriteImage from JSON dict."""
        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            crop_mask=(
                EventbriteImageCropMask.from_json_dict(data.get("crop_mask", {})) if data.get("crop_mask") else None
            ),
            original=data.get("original"),
            aspect_ratio=data.get("aspect_ratio"),
            edge_color=data.get("edge_color"),
            edge_color_set=data.get("edge_color_set"),
        )
