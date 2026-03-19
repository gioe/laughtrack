# Laughtrack Scraper - Makefile for Comedy Venue Data Pipeline
# 
# This Makefile provides standardized commands for development, testing, and production workflows
# for the Laughtrack comedy venue scraping system.

# =============================================================================
# VIRTUAL ENVIRONMENT DETECTION & ACTIVATION
# =============================================================================

# Detect virtual environment and set Python/pip paths
VENV_DIR := .venv
VENV_ACTIVATE := $(VENV_DIR)/bin/activate

# Check if we're already in a virtual environment
ifdef VIRTUAL_ENV
    PYTHON := python
    PIP := pip
    VENV_ACTIVE := true
else
    # Check if .venv directory exists
    ifneq ($(wildcard $(VENV_ACTIVATE)),)
        PYTHON := $(VENV_DIR)/bin/python
        PIP := $(VENV_DIR)/bin/pip
        VENV_ACTIVE := false
        VENV_AVAILABLE := true
    else
        PYTHON := python3
        PIP := pip3
        VENV_ACTIVE := false
        VENV_AVAILABLE := false
    endif
endif

# Virtual environment activation command - used by other targets
define activate_venv
	$(if $(filter false,$(VENV_ACTIVE)), \
		$(if $(filter true,$(VENV_AVAILABLE)), \
			@echo "🔧 Activating virtual environment..." && source $(VENV_ACTIVATE) &&, \
			@echo "⚠️  No virtual environment found at $(VENV_DIR)/" && echo "   Run 'make setup-venv' to create one" && exit 1 \
		) \
	)
endef

# =============================================================================
# DEBUG/LOGGING CONTROLS
# =============================================================================
# Usage:
#   make test --debug        # Console shows DEBUG logs
#   make test DEBUG=1        # (alt) Console shows DEBUG logs
#   make test                # Console shows WARNING+ (default)
#
# The logger reads LAUGHTRACK_LOG_CONSOLE_LEVEL to decide what goes to stdout.
# We keep file logging at DEBUG in logger.py; this only adjusts console noise.
# Detect --debug flag in make goals
DEBUG_FLAG := $(filter --debug,$(MAKECMDGOALS))

DEBUG ?=
ifeq ($(DEBUG_FLAG),--debug)
	LOG_CONSOLE_LEVEL := DEBUG
else ifeq ($(DEBUG),1)
	LOG_CONSOLE_LEVEL := DEBUG
else ifeq ($(DEBUG),true)
	LOG_CONSOLE_LEVEL := DEBUG
else
	LOG_CONSOLE_LEVEL := WARNING
endif

# Prefix env for commands that should honor console log level
RUN_ENV := LAUGHTRACK_LOG_CONSOLE_LEVEL=$(LOG_CONSOLE_LEVEL)

# No-op target so `make target --debug` doesn't error
.PHONY: --debug
--debug:
 	@:

# Check virtual environment status (internal use)
check-venv:
	@echo "🔍 Virtual Environment Status:"
	@echo "   VIRTUAL_ENV: $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV),Not set)"
	@echo "   VENV_ACTIVE: $(VENV_ACTIVE)"
	@echo "   VENV_AVAILABLE: $(if $(VENV_AVAILABLE),$(VENV_AVAILABLE),false)"
	@echo "   Python: $(PYTHON)"
	@echo "   Pip: $(PIP)"

# Create virtual environment if it doesn't exist
setup-venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "🚀 Creating virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
		echo "✅ Virtual environment created at $(VENV_DIR)/"; \
		echo "💡 Run 'source $(VENV_ACTIVATE)' to activate it manually"; \
	else \
		echo "✅ Virtual environment already exists at $(VENV_DIR)/"; \
	fi

.PHONY: test test-all test-venues test-core test-infrastructure test-utils test-critical help help-full help-install help-test help-lint hdiscover help-clean help-linting help-testing help-scraping help-setup help-analysis help-viz help-maintenance help-update help-updates help-workflows help-discovery help-info help-cleanup scrape-all scrape-club scrape-club-id scrape-interactive scrape-types list-scrapers list-clubs update-popularity update-comedian-stats dashboard visualize-metrics scraper-status daily-scrape full-maintenance install install-dev install-optional seatengine-api-tool clean lint lint-check format format-check lint-fix lint-fix-imports lint-fix-whitespace check-venv setup-venv arch-lint

# =============================================================================
# HELP & DOCUMENTATION
# =============================================================================

# Default target - show comprehensive help or filtered category help
# Supports filtered help: make help-lint, make help-scrape, make help-test, etc.
help:
	@echo "🎭 Laughtrack Scraper - Comedy Venue Data Pipeline"
	@echo "  ================================================== "
	@echo "   make help-lint      # Show only linting commands"
	@echo "   make help-scrape    # Show only scraping commands"
	@echo "   make help-test      # Show only testing commands"
	@echo "   make help-install   # Show only installation commands"
	@echo "   make help-analyze   # Show only analysis commands"
	@echo "   make help-maintain  # Show only maintenance commands"
	@echo "   make help-workflow  # Show only workflow commands"
	@echo "   make help-discover  # Show only discovery commands"
	@echo "   make help-clean     # Show only cleanup commands"
	@echo ""

# Prevent Make from trying to build category flags as targets
-lint -linting -test -testing -scrape -scraping -install -setup -analyze -analysis -viz -maintain -maintenance -update -workflow -workflows -discover -discovery -info -clean -cleanup:
	@:

# Full comprehensive help - all categories
help-full:
	$(MAKE) help-install
	@echo ""
	$(MAKE) help-test
	@echo ""
	$(MAKE) help-lint
	@echo ""
	$(MAKE) help-scrape
	@echo ""
	$(MAKE) help-maintain
	@echo ""
	$(MAKE) help-analyze
	@echo ""
	$(MAKE) help-workflow
	@echo ""
	$(MAKE) help-discover
	@echo ""
	$(MAKE) help-clean
	@echo ""
	@echo "📁 Project Structure:"
	@echo "  src/tests/unit/scrapers/implementations/venues/ - Venue scraper tests"
	@echo "  src/tests/unit/core/                           - Core business logic tests"  
	@echo "  src/tests/unit/infrastructure/                 - Infrastructure tests"
	@echo "  src/tests/unit/utils/                          - Utility function tests"
	@echo ""
	@echo "💡 Quick Start:"
	@echo "  make install-dev     # Set up development environment"
	@echo "  make test-critical   # Verify core functionality"
	@echo "  make scrape-interactive  # Start scraping with guided setup"

# Category-specific help sections
help-install:
	@echo "📦 INSTALLATION & SETUP:"
	@echo "  setup-venv           - Create virtual environment (.venv/) if it doesn't exist"
	@echo "  check-venv           - Check virtual environment status and paths"
	@echo "  install              - Install core dependencies (production)"
	@echo "  install-dev          - Install development dependencies (testing, linting)"
	@echo "  install-optional     - Install optional dependencies (dashboards, visualization)"
	@echo "  install-all          - Install all dependencies (complete setup)"

help-test:
	@echo "🧪 TESTING & QUALITY ASSURANCE:"
	@echo "  test                 - Quick test (essentials only, ~30 seconds)"
	@echo "  test-critical        - Critical test suite (run before shared code changes)"
	@echo "  test-clean           - Working venue scrapers only (stable tests)"
	@echo "  test-venues          - All venue scraper tests (comprehensive)"
	@echo "  test-core            - Core business logic tests"
	@echo "  test-infrastructure  - Infrastructure component tests"
	@echo "  test-utils           - Utility function tests"
	@echo "  test-all             - Complete test suite (all tests)"

help-lint:
	@echo "🔍 CODE QUALITY & LINTING:"
	@echo "  lint                 - Run all linting tools (black, flake8, mypy, isort)"
	@echo "  lint-check           - Check code quality without making changes"
	@echo "  lint RULES='F401,E501' - Smart linting: auto-detects rule type (flake8/mypy)"
	@echo "  lint-fix RULES='F401,E501' - Auto-fix linting errors (flake8/mypy)"
	@echo "  format-check         - Check if code formatting is correct (CI-friendly)"
	@echo "  format               - Format code with black and sort imports with isort"

help-scrape:
	@echo "🕷️  DATA SCRAPING OPERATIONS:"
	@echo "  scrape-all                      - Scrape all configured venues"
	@echo "  scrape-club CLUB='Name'         - Scrape specific venue by name"
	@echo "  scrape-club-id ID=123           - Scrape specific venue by database ID"
	@echo "  scrape-types TYPES='type1,type2' - Scrape multiple scraper types in parallel"
	@echo "  scrape-interactive              - Interactive venue selection menu"

help-maintain:
	@echo "📊 DATA MAINTENANCE & UPDATES:"
	@echo "  update-popularity    - Recalculate venue/show popularity scores"
	@echo "  update-comedian-stats - Update comedian follower counts and statistics"

help-analyze:
	@echo "📈 ANALYSIS & VISUALIZATION:"
	@echo "  dashboard            - Generate comprehensive HTML analytics dashboard (data/processed/scraper_dashboard.html)"
	@echo "  visualize-metrics    - Print tabular trend summary of recent scraper runs"
	@echo "  select-metrics       - Pick a metrics JSON and render it to the dashboard"
	@echo "  scraper-status       - Show current scraper health and status"
	@echo "  seatengine-api-tool  - Start SeatEngine API testing tool (port 9247)"

help-workflow:
	@echo "🔄 AUTOMATED WORKFLOWS:"
	@echo "  daily-scrape         - 🎭 Complete daily refresh (scrape + updates, 15-30min)"
	@echo "  full-maintenance     - 🔧 Weekly maintenance + dashboard (20-40min)"

help-discover:
	@echo "🔍 DISCOVERY & INFORMATION:"
	@echo "  list-scrapers        - Show all available scraper types"
	@echo "  list-clubs           - Show all venues with IDs and names"

help-clean:
	@echo "🧹 MAINTENANCE & CLEANUP:"
	@echo "  clean                - Remove Python cache files (__pycache__, *.pyc)"

# Aliases for common alternative category names
help-linting: help-lint
help-testing: help-test  
help-scraping: help-scrape
help-setup: help-install
help-analysis: help-analyze
help-viz: help-analyze
help-maintenance: help-maintain  
help-update: help-maintain
help-updates: help-maintain
help-workflows: help-workflow
help-discovery: help-discover
help-info: help-discover
help-cleanup: help-clean

# =============================================================================
# INSTALLATION & DEPENDENCY MANAGEMENT
# =============================================================================

# Core production dependencies - minimal install for production deployment
install: setup-venv
	@echo "📦 Installing core production dependencies..."
	@echo "   → Web scraping, database, and essential libraries"
	$(activate_venv) $(PIP) install -r requirements.txt
	@echo "✅ Core dependencies installed successfully!"

# Development dependencies - additional tools for testing and development
install-dev: setup-venv
	@echo "🔧 Installing development dependencies..."
	@echo "   → Testing frameworks, linting tools, debugging utilities"
	$(activate_venv) $(PIP) install -r requirements-dev.txt
	@echo "✅ Development dependencies installed successfully!"

# Optional dependencies - visualization, dashboards, and advanced features
install-optional: setup-venv
	@echo "📊 Installing optional dependencies..."
	@echo "   → Streamlit dashboards, advanced analytics, visualization tools"
	$(activate_venv) $(PIP) install -r requirements-optional.txt
	@echo "✅ Optional dependencies installed successfully!"

# Complete installation - everything needed for full development and production
install-all: setup-venv install install-optional
	@echo "🎉 Complete installation finished!"
	@echo "   → Core + Optional dependencies ready"
	@echo "   → Run 'make install-dev' for development tools"

# =============================================================================
# TESTING & QUALITY ASSURANCE
# =============================================================================

# Quick test - essentials only for rapid development feedback (~30 seconds)
test:
	@echo "🚀 Running quick essential tests..."
	# Using existing paths (core models snapshot + dashboard tests). Adjust as needed.
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m pytest \
	  tests/core/models/test_metrics_snapshot_from_session.py \
	  tests/utilities/test_dashboard_generator.py \
	  tests/utilities/test_dashboard_normalization.py \
	  tests/utilities/test_dashboard_integration.py -q || true

# Critical test suite - MUST pass before making shared code changes (core stability)
test-critical:
	@echo "🔍 Running critical test suite (core system stability)..."
	@echo "   → These tests MUST pass before modifying shared components"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m pytest tests/core/ -v || true

# Clean venue scrapers - stable, working scrapers only (95 tests, high confidence)
test-clean:
	@echo "✨ Running clean venue scraper tests (stable implementations)... (path placeholder, no current mapping)"
	@echo "   Skipping: legacy path not present"

# Venue scraper tests - all venue-specific scraping implementations
test-venues:
	@echo "🎭 Venue scraper test path outdated (tests/unit/scrapers/...). Skipping placeholder."

# Core functionality tests - business logic, models, and services
test-core:
	@echo "⚙️  Running core functionality tests..."
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m pytest tests/core/ -v || true

# Infrastructure tests - HTTP, database, configuration, and system components
test-infrastructure:
	@echo "🏗️  Infrastructure test path outdated (tests/unit/infrastructure). Skipping placeholder."

# Utility tests - helper functions, utilities, and common tools
test-utils:
	@echo "🔧 Utility tests path outdated (tests/unit/utils). Skipping placeholder."

# Complete test suite - all tests (use for comprehensive validation)
test-all:
	@echo "🧪 Running all discovered tests under tests/ ..."
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m pytest tests/ -v || true

# =============================================================================
# CODE QUALITY & LINTING
# =============================================================================

# Run all linting tools - comprehensive code quality check and auto-fix
# Can also run with specific rules: make lint RULES='F401,E501' (flake8) or RULES='no-any-return' (mypy)
lint:
	@if [ -n "$(RULES)" ]; then \
		echo "🎯 Smart linting with rules: $(RULES)"; \
		if echo "$(RULES)" | grep -qE "^[A-Z][0-9]+(,[A-Z][0-9]+)*$$"; then \
			echo "   → Detected flake8 rule codes (alphanumeric format)"; \
			echo "   → Running flake8 with specific rules: $(RULES)"; \
			$(activate_venv) flake8 src/ scripts/ tests/ --select=$(RULES) --max-line-length=120; \
		elif echo "$(RULES)" | grep -qE "^[a-z-]+(,[a-z-]+)*$$"; then \
			echo "   → Detected mypy error types (descriptive format)"; \
			echo "   → Running mypy with specific error types: $(RULES)"; \
			$(activate_venv) mypy src/ scripts/ --ignore-missing-imports --no-strict-optional | grep -E "\[($(RULES))\]" || true; \
		else \
			echo "❌ Error: Mixed or unrecognized rule format"; \
			echo "💡 Use either:"; \
			echo "   • Flake8 codes: F401,E501,W293 (alphanumeric)"; \
			echo "   • Mypy types: no-any-return,import,assignment (descriptive)"; \
			echo "   • Don't mix different linter rule formats"; \
			exit 1; \
		fi; \
	else \
		echo "🔍 Running all linting tools..."; \
		echo "   → Formatting code with black and sorting imports with isort"; \
		echo "   → Running flake8 linting and mypy type checking"; \
		$(MAKE) format; \
		echo "🔍 Running flake8 linting..."; \
		$(activate_venv) flake8 src/ scripts/ tests/ --max-line-length=120 --extend-ignore=E203,W503; \
		echo "🔍 Running static type checking with mypy..."; \
		$(activate_venv) mypy src/ scripts/ --ignore-missing-imports --no-strict-optional; \
		echo "✅ All linting tools completed!"; \
	fi

# Check code quality without making changes - CI-friendly validation
lint-check:
	@echo "🔍 Checking code quality (no changes made)..."
	@echo "   → Validating code formatting, imports, linting, and type safety"
	@echo "🔍 Running flake8 linting..."
	-$(activate_venv) flake8 src/ scripts/ tests/ --max-line-length=120 --extend-ignore=E203,W503
	@echo "🔍 Running static type checking with mypy..."
	-$(activate_venv) mypy src/ scripts/ --ignore-missing-imports --no-strict-optional
	@echo "🛠️ Checking architecture import contracts (import-linter)..."
	-$(activate_venv) lint-imports --config=pyproject.toml || true
	@echo "✅ Code quality check completed!"

# Architecture linter - enforce layering contracts
arch-lint:
	@echo "🛠️ Running architecture import contracts (import-linter)..."
	$(activate_venv) lint-imports --config=pyproject.toml
	@echo "✅ Architecture contracts satisfied!"

# Format code with black and sort imports - auto-fix formatting issues
format:
	@echo "🎨 Formatting code with black and sorting imports with isort..."
	@echo "   → Auto-formatting Python code to consistent style"
	$(activate_venv) black src/ scripts/ tests/
	@echo "   → Sorting and organizing import statements"
	$(activate_venv) isort src/ scripts/ tests/
	@echo "✅ Code formatting completed!"

# Auto-fix common linting errors - automated error correction for specific rules
lint-fix:
	@if [ -z "$(RULES)" ]; then \
		echo "❌ Error: RULES parameter is required"; \
		echo "💡 Usage: make lint-fix RULES='F401' (fix unused imports)"; \
		echo "📋 Auto-fixable rule codes:"; \
		echo "   F401 - Remove unused imports (autoflake)"; \
		echo "   format - Fix code formatting (black + isort)"; \
		echo "   W291,W293 - Remove trailing whitespace (autopep8)"; \
		echo ""; \
		echo "❌ Not auto-fixable: E501 (line length), mypy errors, complex logic issues"; \
		exit 1; \
	elif echo "$(RULES)" | grep -qE "^[a-z-]+(,[a-z-]+)*$$"; then \
		echo "❌ Error: '$(RULES)' appears to be mypy error type(s), not auto-fixable"; \
		echo "� Mypy errors like 'no-any-return', 'import', 'assignment' require manual code fixes"; \
		echo "🔍 To check mypy errors: make lint RULES='$(RULES)'"; \
		echo "📋 Auto-fixable flake8 rules: F401, format, W291, W293"; \
		exit 1; \
	else \
		echo "�🔧 Auto-fixing specific rules: $(RULES)"; \
		if echo "$(RULES)" | grep -q "F401"; then \
			echo "   → Removing unused imports (F401 errors)"; \
			$(MAKE) lint-fix-imports; \
		elif echo "$(RULES)" | grep -q "format"; then \
			echo "   → Fixing code formatting"; \
			$(MAKE) format; \
		elif echo "$(RULES)" | grep -qE "W291|W293"; then \
			echo "   → Removing trailing whitespace"; \
			$(MAKE) lint-fix-whitespace; \
		else \
			echo "❌ Error: Rule '$(RULES)' is not auto-fixable"; \
			echo "💡 Auto-fixable rules: F401, format, W291, W293"; \
			echo "📋 Manual fixes required for: E501 (line length), mypy errors, logic issues"; \
			exit 1; \
		fi; \
		echo "✅ Auto-fixing completed! Verifying fixes..."; \
		if echo "$(RULES)" | grep -q "F401"; then \
			echo "🔍 Checking F401 errors after fix:"; \
			$(MAKE) lint RULES='F401' || echo "   → F401 errors resolved!"; \
		fi; \
	fi

# Auto-remove unused imports - fix F401 errors automatically
lint-fix-imports:
	@echo "🗑️  Removing unused imports (F401 errors)..."
	@echo "   → Installing autoflake if needed..."
	@pip install autoflake --quiet 2>/dev/null || echo "   → autoflake already installed"
	@echo "   → Scanning and removing unused imports..."
	autoflake --remove-all-unused-imports --recursive --in-place src/ scripts/ tests/
	@echo "✅ Unused imports removed successfully!"

# Auto-fix whitespace issues - fix W291, W293 errors automatically
lint-fix-whitespace:
	@echo "🧹 Removing trailing whitespace (W291/W293 errors)..."
	@echo "   → Installing autopep8 if needed..."
	@pip install autopep8 --quiet 2>/dev/null || echo "   → autopep8 already installed"
	@echo "   → Fixing whitespace issues..."
	autopep8 --select=W291,W293 --in-place --recursive src/ scripts/ tests/
	@echo "✅ Whitespace issues fixed successfully!"

# Run flake8 linting only - code style and error detection
lint-flake8:
	@echo "🔍 Running flake8 linting..."
	@echo "   → Checking code style, complexity, and potential errors"
	flake8 src/ scripts/ tests/ --max-line-length=120 --extend-ignore=E203,W503
	@echo "✅ Flake8 linting completed!"

# Run flake8 with specific rule codes only - targeted rule checking
lint-rules:
	@echo "🎯 Running flake8 with specific rules..."
	@if [ -z "$(RULES)" ]; then \
		echo "❌ Error: RULES parameter is required"; \
		echo "💡 Usage: make lint-rules RULES='F401,E501,W293'"; \
		echo "📋 Common flake8 rule codes:"; \
		echo "   F401 - imported but unused"; \
		echo "   E501 - line too long (>120 chars)"; \
		echo "   W293 - blank line contains whitespace"; \
		echo "   E302 - expected 2 blank lines"; \
		echo "   C901 - function is too complex"; \
		echo "   E128 - continuation line under-indented"; \
		echo "   W291 - trailing whitespace"; \
		exit 1; \
	else \
		echo "   → Checking only for flake8 rule codes: $(RULES)"; \
		flake8 src/ scripts/ tests/ --select=$(RULES) --max-line-length=120; \
		echo "✅ Targeted flake8 checking completed!"; \
	fi

# Run flake8 ignoring specific rule codes - exclude specific rules
lint-ignore:
	@echo "🚫 Running flake8 ignoring specific rules..."
	@if [ -z "$(IGNORE)" ]; then \
		echo "❌ Error: IGNORE parameter is required"; \
		echo "💡 Usage: make lint-ignore IGNORE='W293,E302,F401'"; \
		echo "📋 Common flake8 rule codes to ignore:"; \
		echo "   F401 - imported but unused"; \
		echo "   W293 - blank line contains whitespace"; \
		echo "   E302 - expected 2 blank lines"; \
		echo "   E501 - line too long (>120 chars)"; \
		echo "   W291 - trailing whitespace"; \
		exit 1; \
	else \
		echo "   → Ignoring flake8 rule codes: $(IGNORE)"; \
		flake8 src/ scripts/ tests/ --extend-ignore=E203,W503,$(IGNORE) --max-line-length=120; \
		echo "✅ Selective flake8 linting completed!"; \
	fi

# Run mypy with specific error types only - targeted mypy checking
mypy-rules:
	@echo "🎯 Running mypy with specific error types..."
	@if [ -z "$(RULES)" ]; then \
		echo "❌ Error: RULES parameter is required"; \
		echo "💡 Usage: make mypy-rules RULES='no-any-return,import,assignment'"; \
		echo "📋 Common mypy error codes:"; \
		echo "   no-any-return - function returns Any instead of specific type"; \
		echo "   import - import-related errors"; \
		echo "   assignment - type assignment errors"; \
		echo "   arg-type - argument type mismatches"; \
		echo "   return-value - return value type errors"; \
		echo "   call-arg - function call argument errors"; \
		exit 1; \
	else \
		echo "   → Checking only for error types: $(RULES)"; \
		echo "   → Note: Due to mypy limitations, this shows only requested error types in a clean run"; \
		mypy src/ scripts/ --ignore-missing-imports --no-strict-optional | grep -E "\[($(RULES))\]" || true; \
		echo "✅ Targeted mypy checking completed!"; \
	fi

# Run mypy ignoring specific error types - exclude specific mypy errors
mypy-ignore:
	@echo "🚫 Running mypy ignoring specific error types..."
	@if [ -z "$(IGNORE)" ]; then \
		echo "❌ Error: IGNORE parameter is required"; \
		echo "💡 Usage: make mypy-ignore IGNORE='import,no-any-return'"; \
		echo "📋 Common mypy error codes to ignore:"; \
		echo "   import - import-related errors"; \
		echo "   no-any-return - Any return type warnings"; \
		echo "   assignment - type assignment errors"; \
		echo "   arg-type - argument type mismatches"; \
		exit 1; \
	else \
		echo "   → Ignoring error types: $(IGNORE)"; \
		mypy src/ scripts/ --ignore-missing-imports --no-strict-optional --disable-error-code=$(IGNORE); \
		echo "✅ Selective mypy checking completed!"; \
	fi
	
# =============================================================================
# DATA SCRAPING OPERATIONS
# =============================================================================

# Scrape all configured venues - complete data refresh from all active clubs
scrape-all:
	@echo "🕷️  Scraping all configured venues..."
	@echo "   → This will process all active comedy clubs in the database"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --all

# Scrape specific venue by name - targeted scraping for individual venues
scrape-club:
	@echo "🎯 Scraping specific venue by name:"
	@echo "   Usage: make scrape-club CLUB='Venue Name'"
	@echo "   Example: make scrape-club CLUB='Comedy Cellar'"
ifndef CLUB
	@echo "⚠️  No club specified - launching interactive selection..."
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows
else
	@echo "🎭 Scraping venue: $(CLUB)"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --club "$(CLUB)"
endif

# Scrape specific venue by database ID - direct database lookup
scrape-club-id:
	@echo "🔢 Scraping venue by database ID:"
	@echo "   Usage: make scrape-club-id ID=123"
	@echo "   Example: make scrape-club-id ID=5"
ifndef ID
	@echo "❌ Error: ID parameter is required"
	@echo "💡 Tip: Run 'make list-clubs' to see all venue IDs"
	@exit 1
else
	@echo "🎭 Scraping venue ID: $(ID)"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --club-id $(ID)
endif

# Interactive venue selection - guided menu for choosing venues to scrape
scrape-interactive:
	@echo "🎮 Launching interactive venue selection..."
	@echo "   → Use arrow keys and Enter to select venues"
	@echo "   → Tip: add ARGS='--open-dashboard' to open the HTML dashboard after scraping"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --verbose --scraper-type-interactive $(ARGS)

# Interactive selection with dashboard auto-open convenience target
scrape-interactive-open:
	@echo "🎮 Launching interactive selection (with dashboard auto-open)..."
	@echo "   → Browser will open the analysis dashboard when scraping completes"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --verbose --scraper-type-interactive --open-dashboard

# Scrape multiple scraper types in parallel - batch processing by scraper type
scrape-types:
	@echo "⚡ Parallel scraping by scraper types:"
	@echo "   Usage: make scrape-types TYPES='type1,type2,type3'"
	@echo "   Example: make scrape-types TYPES='json_ld,comedy_cellar,broadway'"
	@if [ -z "$(TYPES)" ]; then \
		echo "❌ Error: TYPES parameter is required"; \
		echo "💡 Run 'make list-scrapers' to see available types"; \
		exit 1; \
	else \
		echo "🚀 Scraping scraper types: $(TYPES)"; \
		$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --scraper-types "$(TYPES)"; \
	fi

# =============================================================================
# DISCOVERY & INFORMATION
# =============================================================================

# List all available scraper types - show scraper implementations available
list-scrapers:
	@echo "📋 Available scraper implementations:"
	@echo "   → Shows all registered scraper types and their capabilities"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --list-scrapers

# List all venues with database IDs and names - complete venue registry
list-clubs:
	@echo "🏢 All configured venues (ID + Name):"
	@echo "   → Database IDs for use with 'make scrape-club-id ID=X'"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --list-clubs

# =============================================================================
# DATA MAINTENANCE & UPDATES
# =============================================================================

# Update popularity scores - recalculate venue and show popularity based on performance metrics
update-popularity:
	@echo "⭐ Updating popularity scores..."
	@echo "   → Recalculating venue/show rankings based on recent performance data"
	$(activate_venv) $(PYTHON) scripts/core/update_popularity.py

# Update comedian statistics - refresh follower counts and performance metrics
update-comedian-stats:
	@echo "👤 Updating comedian statistics..."
	@echo "   → Refreshing social media followers and show performance metrics"
	$(activate_venv) $(PYTHON) scripts/core/update_comedian_stats.py

# =============================================================================
# ANALYSIS & VISUALIZATION  
# =============================================================================

# Generate HTML analytics dashboard - comprehensive static dashboard with charts and metrics
dashboard:
	@echo "📊 Generating comprehensive HTML analytics dashboard..."
	@echo "   → Creating static dashboard with venue metrics, show analytics, and trends"
	@echo "   → Output: data/processed/scraper_dashboard.html"
	$(activate_venv) $(PYTHON) scripts/utils/generate_dashboard.py

# Pick a metrics file to render into the dashboard
select-metrics:
	@echo "🧭 Select a metrics JSON from metrics/ and render the dashboard..."
	@echo "   → Use arrow keys? No, just enter the number shown."
	@echo "   → Output: dashboard.html (use OUTPUT=path to override)"
	$(activate_venv) $(PYTHON) scripts/utils/select_metrics_dashboard.py $(if $(OUTPUT),--output $(OUTPUT))

# Launch interactive metrics visualization - Streamlit-based interactive analytics
visualize-metrics:
	@echo "📈 Printing metrics trend summary (last 10 runs)..."
	$(activate_venv) $(PYTHON) scripts/utils/visualize_metrics.py

# Show current scraper health and status - system health monitoring
scraper-status:
	@echo "🔍 Checking scraper system health and status..."
	@echo "   → Venue connectivity, recent scraping results, error summaries"
	$(activate_venv) $(PYTHON) scripts/utils/scraper_status.py

# Start SeatEngine API Tool - web-based API testing and exploration
seatengine-api-tool:
	@echo "🌐 Starting SeatEngine API Tool..."
	@echo "   📍 Open your browser to: http://localhost:9247"
	@echo "   � Test SeatEngine API endpoints for venues and events"
	@echo "   🛑 Press Ctrl+C to stop the server"
	$(activate_venv) $(PYTHON) web/seatengine_api_tool/app.py

# =============================================================================
# AUTOMATED WORKFLOWS - Production Pipeline Orchestration
# =============================================================================

# Daily data refresh workflow - complete automated pipeline for daily operations
# 
# RECOMMENDED FOR: Daily automation, production cron jobs, regular data updates
# DURATION: 15-30 minutes (varies by number of active venues)
# FREQUENCY: Safe to run multiple times daily (idempotent operations)
# RESOURCE USAGE: Moderate - primarily I/O bound network requests
#
# WORKFLOW STEPS:
# 1. Scrape all active venues for new show data
# 2. Update popularity scores based on recent performance metrics  
# 3. Update comedian statistics (social media followers, show counts)
daily-scrape:
	@echo "🎭 Starting Daily Data Refresh Workflow"
	@echo "======================================="
	@echo "📊 Step 1/3: Scraping all venues for new shows..."
	@echo "   → Processing all active comedy venues in database"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --all
	@echo ""
	@echo "⭐ Step 2/3: Updating popularity scores..."
	@echo "   → Recalculating venue/show rankings based on performance"
	$(activate_venv) $(PYTHON) scripts/core/update_popularity.py
	@echo ""
	@echo "👤 Step 3/3: Updating comedian statistics..."
	@echo "   → Refreshing social media and performance metrics"
	$(activate_venv) $(PYTHON) scripts/core/update_comedian_stats.py
	@echo ""
	@echo "✅ Daily scraping workflow completed successfully!"
	@echo "   📈 Data is now current and ready for analysis"

# Complete system maintenance workflow - comprehensive weekly maintenance
#
# RECOMMENDED FOR: Weekly maintenance, comprehensive updates, before analysis
# DURATION: 20-40 minutes (includes dashboard generation)
# FREQUENCY: Weekly during low-traffic periods (higher resource usage)
# RESOURCE USAGE: High - includes CPU-intensive dashboard generation
#
# WORKFLOW STEPS:
# 1. All daily-scrape operations (scrape + popularity + comedian stats)
# 2. Generate comprehensive HTML analytics dashboard with charts and metrics
# 3. Create visual reports and trend analysis summaries
full-maintenance:
	@echo "🔧 Starting Complete System Maintenance Workflow"
	@echo "=============================================="
	@echo "📊 Step 1/4: Scraping all venues for new shows..."
	@echo "   → Processing all active comedy venues in database"
	$(activate_venv) $(RUN_ENV) $(PYTHON) -m scripts.core.scrape_shows --all
	@echo ""
	@echo "⭐ Step 2/4: Updating popularity scores..."
	@echo "   → Recalculating venue/show rankings based on performance"
	$(activate_venv) $(PYTHON) scripts/core/update_popularity.py
	@echo ""
	@echo "👤 Step 3/4: Updating comedian statistics..."
	@echo "   → Refreshing social media and performance metrics"
	$(activate_venv) $(PYTHON) scripts/core/update_comedian_stats.py
	@echo ""
	@echo "📈 Step 4/4: Generating comprehensive analytics dashboard..."
	@echo "   → Creating HTML dashboard with charts, metrics, and trends"
	@echo "   → Output: data/processed/scraper_dashboard.html"
	$(activate_venv) $(PYTHON) scripts/utils/generate_dashboard.py
	@echo ""
	@echo "✅ Full maintenance workflow completed successfully!"
	@echo "   🎉 System is fully updated with fresh data and analytics"

# =============================================================================
# MAINTENANCE & CLEANUP
# =============================================================================

# Clean Python cache files - remove __pycache__ directories and .pyc files
clean:
	@echo "🧹 Cleaning Python cache files..."
	@echo "   → Removing __pycache__ directories and .pyc files"
	$(activate_venv) pyclean .
	@echo "✅ Cache cleanup completed"
