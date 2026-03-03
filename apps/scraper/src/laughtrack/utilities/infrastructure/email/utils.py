from pathlib import Path
from typing import Optional, Union

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.path.utils import PathUtils


class EmailUtils:
    """Utility functions for email operations, specifically for dashboard HTML handling."""

    @staticmethod
    def get_default_dashboard_path() -> Path:
        """Get the default dashboard output path."""
        return PathUtils.get_dashboard_path()

    @staticmethod
    def read_dashboard_html(dashboard_path: Union[str, Path]) -> Optional[str]:
        """Read HTML content from a dashboard file."""
        try:
            path = Path(dashboard_path)
            if not path.exists():
                Logger.error(f"Dashboard file does not exist: {path}")
                return None

            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        except Exception as e:
            Logger.error(f"Error reading dashboard HTML from {dashboard_path}: {str(e)}")
            return None

    @staticmethod
    def create_email_wrapper_html(dashboard_html: str) -> str:
        """Wrap dashboard HTML content for email compatibility."""
        # Add email-specific CSS and meta tags for better email client compatibility
        email_wrapper_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Laughtrack Scraper Dashboard Report</title>
    <style>
        /* Email-specific CSS for better compatibility */
        body {{
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }}
        .email-container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        /* Ensure tables display properly in email clients */
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .success {{
            color: #28a745;
        }}
        .error {{
            color: #dc3545;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <h2>📊 Laughtrack Scraper Dashboard Report</h2>
        <p><em>Generated automatically from the scraping system</em></p>
        <hr>
        {dashboard_html}
        <hr>
        <p style="font-size: 12px; color: #666; margin-top: 20px;">
            This is an automated report from the Laughtrack Scraper system.
        </p>
    </div>
</body>
</html>
"""
        return email_wrapper_html
