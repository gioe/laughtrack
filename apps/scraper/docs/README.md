# Laughtrack Scraper Documentation

This directory contains comprehensive documentation for the Laughtrack Scraper project.

**📋 For visual system architecture, see: [System Architecture Diagram](architecture-diagram.md)**

## Quick Navigation

- **[Architecture Diagram](architecture-diagram.md)** - Visual system architecture with component relationships
- **[Scripts Guide](#scripts-and-entry-points)** - Main entry points and utility scripts
- **[Data Transformers](#data-transformers)** - Modular data transformation system
- **[Monitoring System](#monitoring-system)** - Tixr monitoring and alerting
- **[Web Applications](#web-applications)** - Web-based tools and interfaces
- **[Testing Framework](#testing-framework)** - Unit test structure and guidelines

---

## Scripts and Entry Points

### Main Scraping Scripts (via Makefile or scripts/core)

#### `scrape_shows.py` - Main Scraper Interface

**Basic Usage:**

```bash
# Recommended: use Make targets
make scrape-all
make scrape-club CLUB="Comedy Cellar"
make scrape-interactive

# Direct script usage
python scripts/core/scrape_shows.py --all
python scripts/core/scrape_shows.py --club "Comedy Cellar"
python scripts/core/scrape_shows.py
```

**Advanced Usage:**

```bash
# Scrape by scraper type
./scripts/core/scrape_shows.py --scraper-type json_ld

# Multiple scraper types in parallel
./scripts/core/scrape_shows.py --scraper-types json_ld,comedy_cellar,broadway

# Interactive scraper type selection
./scripts/core/scrape_shows.py --scraper-type-interactive

# List available scraper types
./scripts/core/scrape_shows.py --list-scrapers
```

#### Other Core Scripts

```bash
# Update popularity scores
make update-popularity
```

### Utility Scripts (`scripts/utils/`)

Development and analysis tools:

- Dashboard generation now provided by `laughtrack.core.dashboard.generate_html_dashboard` (invoke via wrapper script or Makefile target)
- `visualize_metrics.py` - Interactive Streamlit visualization (via `make visualize-metrics`)
- `scraper_status.py` - Command-line status checking tool (via `make scraper-status`)

### Key Features

- **Parallel Processing**: Clubs are scraped in parallel batches per scraper type using ThreadPoolExecutor (8 workers)
- **Deduplication**: Robust deduplication logic prevents database constraint violations
- **Error Handling**: Individual club failures don't stop the entire scraping process
- **Result Aggregation**: Shows are converted to standardized Show objects and stored in database

---

## Data Transformers

Modular data transformation system for converting scraped data to Show objects.

### Architecture

- Base and pipeline: `src/laughtrack/scrapers/base/` (`pipeline.py` re-exports the standard pipeline)
- Transformers: venue/API-specific transformer classes under `src/laughtrack/scrapers/implementations/**/transformer.py`

### Basic Usage

```python
from laughtrack.scrapers.base import create_standard_pipeline

# Create pipeline with standard transformers
pipeline = create_standard_pipeline(club)

# Transform raw data to shows
shows = pipeline.transform(raw_data, source_url)
```

### Custom Transformers

```python
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.utilities.infrastructure.pipeline.pipeline import ShowTransformationPipeline

class CustomTransformer(DataTransformer[JSONDict]):
    def can_transform(self, raw_data):
        return 'custom_field' in raw_data
    
    def transform_to_shows(self, raw_data, source_url):
        # Custom transformation logic
        return [show]

// Register custom transformer
pipeline = ShowTransformationPipeline(club)
pipeline.register_transformer(CustomTransformer(club))
```

### Available Components

**Transformers:**

1. **JSONLdTransformer** - Handles JSON-LD Event and ComedyEvent types
2. **GraphQLEventTransformer** - Handles GraphQL API responses with events/publicEvents

**Validators:**

1. **validate_required_fields** - Ensures name, date, and club_id are present
2. **validate_future_date** - Allows shows up to 1 day in the past for timezone issues

**Notes:** Prefer `laughtrack.scrapers.base` re-exports for the pipeline; core transformer base lives under `laughtrack.utilities.infrastructure.transformer`.

---

## Monitoring System

Comprehensive monitoring and alerting system for Tixr API failures, designed to detect DataDome protection, classify failure types, and provide real-time alerts.

### Key Capabilities

- **🔍 Failure Detection & Classification**: DataDome protection, rate limiting, automation detection, network errors
- **📊 Real-time Monitoring**: Failure rate tracking, pattern analysis, consecutive failure detection
- **🚨 Multi-Channel Alerting**: Email alerts, Slack integration, custom webhooks, configurable thresholds
- **⚙️ Easy Integration**: TixrClient integration, background monitoring, configuration management

### Basic Setup

```python
from laughtrack.infrastructure.monitoring import (
    MonitoringConfig, 
    MonitoringFactory
)

# Create configuration
config = MonitoringConfig(
    failure_rate_warning_threshold=25.0,
    failure_rate_critical_threshold=50.0,
    alert_recipients=['admin@yourcompany.com']
)

# Create monitoring service
monitoring_service = MonitoringFactory.create_monitoring_service(config)

# Integrate with TixrClient
tixr_client = TixrClient(
    club=your_club,
    failure_monitor=monitoring_service.get_failure_monitor()
)
```

### Environment Configuration

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export EMAIL_FROM=alerts@yourcompany.com
export ALERT_RECIPIENTS=admin@yourcompany.com,dev@yourcompany.com
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
export FAILURE_RATE_WARNING_THRESHOLD=20.0
```

```python
# Load configuration from environment
config = MonitoringConfig.from_env()
monitoring_service = MonitoringFactory.create_monitoring_service(config)
```

---

## Web Applications

Web-based tools for the Laughtrack Scraper project.

### Venue Lookup Tool

A lightweight web application for looking up venue information via the SeatEngine API.

```bash
# Using the convenience script
python web/start_venue_lookup.py

# Or using make command (recommended)
make venue-lookup
```

**Features:**

- **Live SeatEngine API Integration**: Direct requests to SeatEngine API
- **Venue Details**: Fetch comprehensive venue information
- **Events Lookup**: Get current events for any venue
- **Tabbed Interface**: Switch between venue details and events

**API Endpoints:**

- `GET /` - Main web interface
- `GET /api/venue/{venue_id}` - Fetch venue details
- `GET /api/venue/{venue_id}/events` - Fetch venue events
- `GET /api/stats` - API information

**Usage:**

Start the Flask web application and use the web interface:

```bash
make venue-lookup
```

This allows you to:

- Enter any SeatEngine venue ID
- View real-time venue details and events
- Copy JSON responses to clipboard
- Handle API errors gracefully

---

## Testing Framework

Comprehensive unit test structure for the Laughtrack Scraper project.

### Directory Organization

```text
tests/unit/
├── core/                           # Tests for core business logic
│   └── models/                     # Core data model tests
├── infrastructure/                 # Tests for infrastructure components
│   ├── http/                      # HTTP infrastructure tests
│   └── pagination/                # Pagination tests
├── scrapers/                       # Tests for web scrapers
│   └── implementations/           # Scraper implementation tests
│       └── venues/                # Venue-specific scraper tests
└── utils/                          # Tests for utility functions
```

### Core Test Suite

**Before making changes to shared code, always run:**

```bash
pytest tests/unit/test_comedy_cellar_scraper.py tests/unit/test_grove34_scraper.py tests/unit/test_club_schema_dir.py tests/unit/test_club_schema_dir_property.py -v
```

**Current Status:** 55/55 tests passing (100% success rate)

### Test Categories

1. **Core Tests (`tests/unit/core/`)** - Core business logic and data models
2. **Infrastructure Tests (`tests/unit/infrastructure/`)** - HTTP clients, protection handlers, session management
3. **Scraper Tests (`tests/unit/scrapers/`)** - Venue-specific and generic scraper tests
4. **Utility Tests (`tests/unit/utils/`)** - Data processing, URL utilities, date/time handling

### Test Execution

```bash
# Full test suite
pytest -v --tb=short

# Core working tests only
pytest tests/unit/test_comedy_cellar_scraper.py tests/unit/test_grove34_scraper.py tests/unit/test_club_schema_dir.py tests/unit/test_club_schema_dir_property.py -v

# Individual scraper tests
pytest tests/unit/test_comedy_cellar_scraper.py -v
```

### Test Coverage Status

#### Venue Scrapers (All Passing)

- ✅ Broadway Comedy Club: 27/27 tests
- ✅ Bushwick Comedy Club: 7/7 tests  
- ✅ Comedy Cellar: 21/21 tests
- ✅ Grove 34: 17/17 tests
- ✅ Improv: 21/21 tests
- ✅ Rodneys Comedy Club: 12/12 tests
- ✅ StandUp NY: 11/11 tests
- ✅ The Stand NYC: 17/17 tests

#### Core & Infrastructure

- ✅ Core Models: 17/17 tests
- ✅ HTTP Clients: 8/8 tests
- ✅ Infrastructure: 15/15 tests
- ✅ Utilities: 3/3 tests

#### Total Coverage

150+ tests with comprehensive coverage across all components.

### Test-Driven Development Guidelines

- **Red-Green-Refactor**: Write failing tests first, implement code to pass, then refactor
- **Mock External Dependencies**: Use mocks for HTTP requests, database calls, and external APIs
- **Schema-Based Testing**: Validate scrapers against real schema files, not live requests
- **Error Condition Testing**: Test failure scenarios (network errors, malformed data, etc.)

### Benefits of Test Structure

1. **Discoverability**: Tests are easy to find based on the component being tested
2. **Scalability**: New tests can be added to appropriate directories without cluttering
3. **Organization**: Clear separation between different types of tests
4. **Maintainability**: Tests are grouped logically, making maintenance easier
5. **IDE Support**: Better IDE navigation and code completion
6. **Parallel Execution**: Test runners can better parallelize tests by directory

---

*This documentation is maintained as part of the Laughtrack Scraper project. For the latest updates and detailed implementation guides, refer to the individual component documentation and the [System Architecture Diagram](architecture-diagram.md).*
