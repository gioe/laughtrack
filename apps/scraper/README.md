# Laughtrack Scraper

A Python-based web scraping project designed to extract and process comedy show data from various venue websites. The project implements a robust schema validation system where all scraped data must conform to predefined schemas.

## Quick Start

### Installation

```bash
# Install core dependencies
make install
# OR
pip install -r requirements.txt

# Install development dependencies (optional)
make install-dev

# Install visualization tools (optional)  
make install-optional
```

Tip: use make help to see all available commands.

### Basic Usage

```bash
# Scrape all venues
make scrape-all

# Scrape specific venue
make scrape-club CLUB="Comedy Cellar"

# Interactive venue selection
make scrape-interactive

# Show available scrapers
make list-scrapers
```

### Common tasks

Prefer the Makefile targets (they ensure a virtualenv and correct paths):

```bash
# Discover commands
make help

# Scraping
make list-scrapers
make scrape-all
make scrape-club CLUB="Comedy Cellar"
make scrape-interactive

# Maintenance
make update-popularity

# Analytics
make dashboard               # Generate HTML dashboard
make visualize-metrics       # Optional deps required
make scraper-status
```

## Project Status

✅ **All scripts are functional and tested**
✅ **Core dependencies documented**  
✅ **Installation process streamlined**
✅ **Optional dependencies handled gracefully**

### Requirements

- **Core**: `requirements.txt` - Basic scraping functionality
- **Development**: `requirements-dev.txt` - Development tools and testing
- **Optional**: `requirements-optional.txt` - Visualization and analysis tools

### Testing

```bash
# Run all tests
make test-all

# Quick test
make test

# Critical tests (run before shared code changes)
make test-critical
```

## Dependencies

### Core Dependencies

- `aiohttp` - Async HTTP client for scrapers
- `requests` - HTTP library for synchronous requests
- `beautifulsoup4` - HTML/XML parsing
- `psycopg2-binary` - PostgreSQL database adapter
- `pydantic` - Data validation
- `loguru` - Advanced logging
- `pytz` - Timezone handling

### Optional Dependencies

- `streamlit`, `plotly`, `pandas` - Visualization dashboards
- `Pillow` - Image processing

## Environment variables

All variables below are optional — the scraper degrades gracefully when
they are unset. See `.env.example` for the canonical comment style and
copy that file to `.env` to configure them locally.

- `RESIDENTIAL_PROXY_URL` — egress proxy for scrapers flagged
  `use_residential_proxy=true` in the `scrapers` table (currently `tixr`,
  `ticketweb`, `comedy_mothership`, `comedy_clubhouse`,
  `palm_beach_improv`). Unset = direct egress for everyone.
- `CAPSOLVER_API_KEY` — capsolver.com API key for the DataDome
  interactive-CAPTCHA solver (TASK-1658). Required to recover the etix.com
  venues that DataDome 'bv' mode has been blocking since 2026-04-16, plus
  any tixr venue serving DataDome challenges. When unset, the Playwright
  browser still detects the DataDome iframe but logs a warning and returns
  the challenge HTML unchanged — non-DataDome scrapers are unaffected.
  DataDome solves cost ~$2/1000; expected steady-state spend at current
  scrape volume is ~$1.50/month. Get a key at https://capsolver.com.
- `SEATENGINE_AUTH_TOKEN` — only needed for SeatEngine-backed venues; run
  `bash apps/scraper/scripts/fetch_seatengine_token.sh` to refresh.
- `DISCORD_WEBHOOK_URL`, `HEALTHCHECKS_PING_URL`,
  `BUNNYCDN_STORAGE_*` — alerting / heartbeat / image-upload helpers; see
  `.env.example` for full descriptions.

## Documentation

- docs/architecture-diagram.md - Visual system architecture
- docs/scraper-architecture-patterns.md - Scraper design conventions
- docs/README.md - Project docs index and guides

## Where things live

- Domain models and entities: `src/laughtrack/domain/` (public surface for types)
- Scraper base + pipeline: `src/laughtrack/scrapers/base/` (`pipeline.py` re-exports the standard pipeline)
- Scraper utilities: `src/laughtrack/scrapers/utils/` (`url_discovery.py`, `rate_limiting.py`)
- Batch concurrency helper: `src/laughtrack/utilities/infrastructure/scraper/scraper.py` (`BatchScraper`)
- HTTP/DB ports: `src/laughtrack/ports/` (protocols); adapters and implementations under `src/laughtrack/adapters/` and `src/laughtrack/infrastructure/`
- Orchestration: `src/laughtrack/scrapers/orchestration/`

## Development

```bash
# Setup development environment
make install-dev
make test

# Before making shared code changes, run critical tests
make test-critical
```

For contribution guidelines and development setup, see the installation guide.
