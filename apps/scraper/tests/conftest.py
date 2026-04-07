"""
Root conftest for the scraper test suite.

Pre-imports real foundation modules so that module-level sys.modules.setdefault()
stubs in subdirectory conftest files (e.g. tests/core/entities/conftest.py) become
no-ops. Without this, the stub MagicMocks persist across the entire pytest session
and break tests that depend on the real Logger (test_logger_error_count,
test_validator, pipeline smoke tests).
"""

import os
import tempfile

# Redirect log files to a temp directory so test runs don't pollute the real
# app.log used by production scraping. Must be set before Logger.configure()
# is triggered by the imports below.
os.environ.setdefault("LAUGHTRACK_LOG_DIR", os.path.join(tempfile.gettempdir(), "laughtrack_test_logs"))

# Import the real Logger module chain — this populates sys.modules with the real
# modules BEFORE any test subdirectory conftest can register MagicMock stubs via
# setdefault(). Since setdefault() only sets if absent, these real entries win.
import laughtrack.foundation.infrastructure.logger.logger  # noqa: F401
import laughtrack.foundation.infrastructure.logger  # noqa: F401
import laughtrack.foundation.infrastructure  # noqa: F401
