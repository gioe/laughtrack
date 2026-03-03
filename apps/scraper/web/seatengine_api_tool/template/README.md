# SeatEngine API Tool Templates

This directory contains HTML templates for the SeatEngine API tool web application.

## Files

### `seatengine_api_tool.html`

- **Purpose**: SeatEngine API testing tool for querying venue data and events
- **Features**:
  - SeatEngine venue lookup by ID
  - Event data retrieval
  - JSON response display
  - Real-time API testing

## Usage

The templates are served by the Flask application in the parent directory.

### Development

To edit templates during development:

```bash
# Edit the template
open web/seatengine_api_tool/templates/seatengine_api_tool.html

# Run the web app to test changes
cd web/seatengine_api_tool
