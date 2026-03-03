"""
Path utilities for managing project paths and file operations.

This module provides centralized path management for the Laughtrack scraper project,
including template paths, metrics directories, and output path resolution.
"""

import json
from pathlib import Path
from typing import List, Optional

from laughtrack.foundation.models.types import JSONDict


class PathUtils:
    """Centralized path management utility for the Laughtrack project."""

    @staticmethod
    def get_project_root() -> Path:
        """Get the project root directory.

        Ascend from this file until we find a directory containing a
        project root marker (pyproject.toml) or a .git folder. Falls back
        to the src/ folder's parent if markers are not found.
        """
        current = Path(__file__).resolve()
        for parent in [current.parent] + list(current.parents):
            # Stop once we hit filesystem root
            if parent == parent.parent:
                break
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return parent
        # Fallback: ../../../../.. from this file to project root
        # utils.py -> path -> utilities -> foundation -> laughtrack -> src -> project root
        return current.parent.parent.parent.parent.parent.parent

    @staticmethod
    def get_template_path(template_name: str) -> Path:
        """Get the path to a template file."""
        project_root = PathUtils.get_project_root()
        template_path = project_root / "scripts" / "utils" / "templates" / template_name
        return template_path

    @staticmethod
    def get_sql_dir() -> Path:
        """Get the path to the repository-level SQL directory."""
        project_root = PathUtils.get_project_root()
        sql_dir = project_root / "sql"
        return sql_dir

    @staticmethod
    def get_metrics_dir() -> Path:
        """Get the metrics directory path."""
        project_root = PathUtils.get_project_root()
        metrics_dir = project_root / "metrics"
        metrics_dir.mkdir(exist_ok=True)  # Ensure directory exists
        return metrics_dir

    @staticmethod
    def load_metrics_files() -> List[JSONDict]:
        """Load only the most recent metrics file from the metrics directory.

        This function intentionally returns metrics from a single JSON file (the
        newest by modification time) to avoid aggregating historical runs in the
        dashboard. If the latest file contains a list, it's returned as-is; if it
        contains a single dict, it's wrapped in a list for downstream consumers.
        """
        metrics_dir = PathUtils.get_metrics_dir()

        try:
            files = sorted(
                metrics_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            files = []

        if not files:
            return []

        latest = files[0]
        try:
            with open(latest, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load metrics file {latest}: {e}")
            return []

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            return []

    @staticmethod
    def resolve_output_path(output_path: Optional[str] = None) -> Path:
        """Resolve the output path for generated files."""
        if output_path:
            return Path(output_path).resolve()

        # Default to project root
        project_root = PathUtils.get_project_root()
        return project_root / "dashboard.html"

    @staticmethod
    def get_logs_dir() -> Path:
        """Get the logs directory path."""
        project_root = PathUtils.get_project_root()
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)  # Ensure directory exists
        return logs_dir

    @staticmethod
    def get_data_dir() -> Path:
        """Get the data directory path."""
        project_root = PathUtils.get_project_root()
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)  # Ensure directory exists
        return data_dir

    @staticmethod
    def get_schemas_dir() -> Path:
        """Get the schemas directory path."""
        data_dir = PathUtils.get_data_dir()
        schemas_dir = data_dir / "schemas"
        return schemas_dir

    @staticmethod
    def get_processed_data_dir() -> Path:
        """Get the processed data directory path."""
        data_dir = PathUtils.get_data_dir()
        processed_dir = data_dir / "processed"
        processed_dir.mkdir(exist_ok=True)  # Ensure directory exists
        return processed_dir

    @staticmethod
    def get_dashboard_path() -> Path:
        """Get the default dashboard output path."""
        project_root = PathUtils.get_project_root()
        return project_root / "dashboard.html"


# Legacy compatibility alias
ProjectPaths = PathUtils
