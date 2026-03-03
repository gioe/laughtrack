# Web Applications

This directory contains web-based tools for the Laughtrack Scraper project.

## Directory Structure

```
web/
├── seatengine_api_tool/           # SeatEngine API testing tool
│   ├── app.py                     # Flask web application
│   └── template/                  # HTML templates for this app
│       ├── seatengine_api_tool.html  # SeatEngine API tool (colocated)
│       └── README.md              # Template documentation
└── README.md                      # This file
```

## SeatEngine API Tool

A web-based tool for testing and interacting with the SeatEngine API:

### Features

- **Live SeatEngine API Integration**: Direct requests to SeatEngine API
- **Venue Details**: Fetch comprehensive venue information by ID
- **Events Lookup**: Get current events for any venue
- **JSON Response Display**: Pretty-printed API responses
- **Real-time Testing**: Interactive API testing interface

### Quick Start

From the project root directory:

```bash
# Using make command (recommended)
make seatengine-api-tool

# Or run directly
python web/seatengine_api_tool/app.py
```

### API Endpoints

- `GET /` - Main web interface
- `GET /api/venue/{venue_id}` - Fetch venue details
- `GET /api/venue/{venue_id}/events` - Fetch venue events
- `GET /api/stats` - API information

### Usage

Start the Flask web application and use the web interface:

```bash
make seatengine-api-tool
```

This allows you to:

- Enter any SeatEngine venue ID
- View real-time venue details and events
- Copy JSON responses to clipboard
- Handle API errors gracefully

### Development

The Flask app automatically configures paths to work from the project root and includes proper imports for the SeatEngine client infrastructure.
