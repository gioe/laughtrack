# Laughtrack Scraper System Architecture

This document provides a comprehensive system architecture diagram for the Laughtrack Scraper project, showing the relationships between components and data flow.

## High-Level System Architecture

```mermaid
graph TB
    %% Entry Points
    CLI["`**Entry Points**
    scripts/core/scrape_shows.py
    Makefile targets`"]
    
    %% Core Configuration
    Config["`**Configuration Layer**
    ConfigManager
    Club Model (schema_dir)`"]
    
    %% Factory & Mapping
    Factory["`**Scraper Factory**
    ScraperMappingService
    SCRAPER_CLASS_MAP`"]
    
    %% Database
    DB[("`**Database Layer**
    PostgreSQL
    Connection Manager
    Transaction Manager`")]
    
    CLI --> Config
    Config --> Factory
    Factory --> ScraperTypes
    
    %% Core Data Models
    subgraph Models["`**Core Data Models**`"]
        ClubModel["`Club Model
        • scraping_url
        • schema_dir property
        • scraper type`"]
        
        EventModel["`Event Model
        • Intermediate format
        • Raw venue data`"]
        
        ShowModel["`Show Model  
        • Final output format
        • Standardized fields`"]
        
        ComedianModel["`Comedian Model`"]
        TicketModel["`Ticket Model`"]
    end
    
    Config --> ClubModel
    
    %% Scraper Types
    subgraph ScraperTypes["`**Scraper Implementations**`"]
        JsonLD["`JSON-LD Scraper
        • Generic JSON-LD extraction
        • Most venues`"]
        
        VenueSpecific["`Venue-Specific Scrapers
        • ComedyCellarScraper
        • BroadwayComedyClubScraper
        • Grove34Scraper
        • BushwickComedyClubScraper
        • TheStandNYCScraper
        • StandupNYScraper
        • ImprovScraper
        • ComicStripScraper
        • + 12 more venues`"]
        
        APIScrapers["`API Scrapers
        • EventbriteScraper
        • TicketmasterScraper
        • SeatEngineScraper`"]
    end
    
    %% Data Transformation Pipeline
    subgraph Pipeline["`**Data Transformation Pipeline**`"]
        Extract["`Data Extraction
        • HTTP sessions
        • Rate limiting
        • Error handling`"]
        
        Transform["`Data Transformation
        • Event → Show conversion
        • Field mapping
        • Validation`"]
        
        Validate["`Schema Validation
        • Venue-specific schemas
        • Data integrity checks`"]
    end
    
    ScraperTypes --> Extract
    Extract --> Transform
    Transform --> Validate
    Validate --> ShowModel
    Schema --> Validate
    
    %% Infrastructure Layer
    subgraph Infrastructure["`**Infrastructure Layer**`"]
        HTTP["`HTTP Management
        • AsyncHttpMixin
        • Session management
        • BaseHeaders`"]
        
        ErrorHandling["`Error Handling
        • Retry logic
        • Rate limiting
        • Protection handlers`"]
        
        Monitoring["`Monitoring
        • Logging system
        • Error tracking
        • Performance metrics`"]
    end
    
    Extract --> HTTP
    Extract --> ErrorHandling
    HTTP --> ErrorHandling
    ErrorHandling --> Monitoring
    
    %% Utils & Specialized Components
    subgraph Utils["`**Utilities & Specialized**`"]
        WebUtils["`Web Scraping Utils
        • URLUtils.normalize_url()
        • BatchScraper
        • GraphQLClient`"]
        
        DataUtils["`Data Processing
        • DateTimeUtils
        • OCR Processing`"]
        
        SpecializedUtils["`Specialized Utils
        • Task Queue
        • Custom Logger
        • Anti-detection`"]
    end
    
    Extract --> WebUtils
    Transform --> DataUtils
    Monitoring --> SpecializedUtils
    
    %% Final Output
    ShowModel --> DB
    
    %% Configuration connections
    ClubModel -.->|schema_dir property| Schema
    ClubModel -.->|scraper field| Factory
    
    %% Styling
    classDef entryPoint fill:#e1f5fe
    classDef core fill:#f3e5f5
    classDef data fill:#e8f5e8
    classDef infrastructure fill:#fff3e0
    classDef storage fill:#fce4ec
    
    class CLI entryPoint
    class Config,Factory core
    class Models,Pipeline,Utils data
    class Infrastructure infrastructure
    class DB,Schema storage
```

## Component Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as scrape_shows.py
    participant Config as ConfigManager
    participant Factory as ScraperMappingService
    participant Club as Club Model
    participant Scraper as Venue Scraper
    participant Pipeline as Data Pipeline
    participant Schema as Schema Registry
    participant DB as Database
    
    User->>CLI: Execute scraping command
    CLI->>Config: Load configuration
    CLI->>Factory: Request scraper mapping
    Factory->>Club: Get club configuration
    Club->>Factory: Return scraper type + schema_dir
    Factory->>Scraper: Create scraper instance
    
    Scraper->>Scraper: discover_urls()
    Scraper->>Scraper: extract_data()
    Scraper->>Pipeline: transform_data()
    Pipeline->>Schema: Validate against schema
    Schema->>Pipeline: Validation result
    Pipeline->>Scraper: Return Show objects
    
    Scraper->>CLI: Return scraped shows
    CLI->>DB: Store shows
    CLI->>User: Report results
```

## Data Flow Architecture

```mermaid
flowchart LR
    %% Input Sources
    subgraph Sources["`**Data Sources**`"]
        VenueWebsites["`Venue Websites
        • JSON-LD data
        • HTML content
        • JavaScript APIs`"]
        
        ExternalAPIs["`External APIs
        • EventBrite API
        • Ticketmaster API
        • SeatEngine API`"]
    end
    
    %% Processing Stages
    subgraph Processing["`**Processing Pipeline**`"]
        RawData["`Raw Data
        • HTTP responses
        • JSON payloads
        • HTML content`"]
        
        EventModels["`Event Models
        • Venue-specific format
        • Intermediate validation`"]
        
        ShowModels["`Show Models
        • Standardized format
        • Final validation`"]
    end
    
    %% Validation & Storage
    subgraph Storage["`**Validation & Storage**`"]
        SchemaValidation["`Schema Validation
        • Venue-specific rules
        • Data integrity checks`"]
        
        Database["`PostgreSQL Database
        • Normalized tables
        • Relationship management`"]
    end
    
    %% Flow connections
    Sources --> RawData
    RawData --> EventModels
    EventModels --> ShowModels
    ShowModels --> SchemaValidation
    SchemaValidation --> Database
    
    %% Quality Gates
    EventModels -.->|Validation| SchemaValidation
    SchemaValidation -.->|Feedback| EventModels
```

## Key Architectural Patterns

### 1. Factory Pattern

- **ScraperMappingService** maps scraper names to classes
- **SCRAPER_CLASS_MAP** maintains type-safe registry
- Enables dynamic scraper instantiation

### 2. Strategy Pattern

- **URL Discovery Strategies**: static, pagination, calendar, api_discovery
- **Data Transformation Strategies**: JSON-LD, GraphQL, API responses
- **Error Handling Strategies**: retry, circuit breaker, fallback

### 3. Pipeline Pattern

- **Data Transformation Pipeline**: extract → transform → validate → store
- **Pluggable Transformers**: venue-specific logic encapsulation
- **Validation Pipeline**: schema-based data integrity

### 4. Mixin Pattern

- **AsyncHttpMixin**: HTTP session management
- **Reusable across all scrapers**
- **Consistent timeout and header configuration**

## Directory Structure Mapping

```text
laughtrack-scraper/
├── scripts/core/                    # Entry points
├── src/laughtrack/
│   ├── core/                       # Core business logic
│   │   ├── models/                 # Data models
│   │   └── services/               # Business services
│   ├── scrapers/                   # Scraper implementations
│   │   ├── base/                   # Base classes & mixins
│   │   ├── implementations/        # Specific scrapers
│   │   └── utils/                  # Scraper utilities
│   ├── infrastructure/             # Infrastructure concerns
│   │   ├── config/                 # Configuration management
│   │   ├── http/                   # HTTP utilities
│   │   └── monitoring/             # Monitoring & alerts
│   ├── data/                       # Data access layer
│   │   ├── handlers/               # Database handlers
│   │   └── queries/                # SQL queries
│   └── utils/                      # General utilities
├── data/schemas/                   # Schema definitions
└── tests/                         # Test suites
```

## Task → Component Mapping

| Task Type | Primary Components | Key Files |
|-----------|-------------------|-----------|
| **Add New Scraper** | Club Model → ScraperMapping → Scraper Class | `core/models/club.py`, `core/services/scraper_mapping.py`, `scrapers/implementations/venues/` |
| **Debug Data Issues** | Schema Registry → Scraper Implementation → Data Transform | `data/schemas/{venue}/`, specific scraper files |
| **Fix HTTP Issues** | AsyncHttpMixin → BaseHeaders → Error Handling | `core/data/mixins/async_http_mixin.py`, `infrastructure/http/` |
| **Add New Venue** | Database → Club Config → Schema → Scraper | Club table, `data/schemas/{hostname}/`, new scraper class |
| **Performance Tuning** | Rate Limiter → Batch Scraper → Monitoring | `scrapers/utils/rate_limiting.py`, `utilities/infrastructure/scraper/scraper.py` |

---

*This architecture diagram was generated based on the actual codebase structure as of July 7, 2025.*
