"""Utilities package exports.

Dashboard generation now lives in `laughtrack.core.dashboard`. We re-export it
here temporarily for backward compatibility.
"""
from laughtrack.core.dashboard import generate_html_dashboard  # type: ignore

__all__ = ["generate_html_dashboard"]
