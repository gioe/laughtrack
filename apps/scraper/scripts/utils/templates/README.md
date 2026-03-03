# Dashboard Templates

This directory contains HTML templates for the dashboard generation script.

## Templates

### `scraper_dashboard.html`

- **Purpose**: Analytics dashboard template for scraping metrics
- **Type**: Template with placeholder variables (e.g., `{{total_shows}}`)
- **Usage**: Consumed by the dashboard generator (`laughtrack.core.dashboard`) via wrapper script
- **Features**:
  - Comprehensive scraping metrics display
  - Interactive charts using Plotly.js
  - Recent sessions table
  - Club performance breakdown
  - Error reporting

### `scraper_dashboard_fallback.html`

- **Purpose**: Simple fallback template when no metrics data exists
- **Type**: Static HTML with error message
- **Usage**: Used by dashboard generator when no metrics found
- **Features**: Clean error state with instructions

## Usage

Generate dashboard from metrics:

```bash
python scripts/utils/generate_dashboard_wrapper.py
# Output: data/processed/scraper_dashboard.html
```

## Architecture

- **Self-contained**: Templates include all CSS and JavaScript inline for portability
- **Responsive**: Mobile-friendly design
- **Template System**: Uses simple placeholder replacement (`{{variable}}` syntax)
